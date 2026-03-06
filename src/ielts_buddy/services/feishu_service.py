"""飞书多维表格同步服务：生成 Bitable 兼容的 JSON 数据

不直接调用飞书 API，仅生成标准 JSON 文件供外部工具导入。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ielts_buddy.core.config import get_app_dir
from ielts_buddy.core.models import Word
from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.stats_service import StatsService
from ielts_buddy.services.vocab_service import VocabService

# 飞书 Bitable 应用 token
BITABLE_APP_TOKEN = "PokablBmbauj7xsQFZXcdChxnkc"


def _get_sync_dir(base_dir: Path | None = None) -> Path:
    """获取同步数据输出目录"""
    parent = base_dir or get_app_dir()
    sync_dir = parent / "sync" / "feishu"
    sync_dir.mkdir(parents=True, exist_ok=True)
    return sync_dir


class FeishuService:
    """飞书多维表格同步服务

    生成符合 Bitable API 格式的 JSON 数据，
    实际 API 调用由外部工具完成。
    """

    def __init__(self, db_path: Path | None = None, sync_dir: Path | None = None) -> None:
        self._db_path = db_path
        self._sync_dir = sync_dir

    def _get_sync_dir(self) -> Path:
        return _get_sync_dir(self._sync_dir)

    # ---- 数据准备 ----

    def prepare_vocab_data(self, band: int | None = None) -> list[dict]:
        """准备词库数据，转为 Bitable 记录格式

        每条记录包含 fields 字段，字段名使用中文（与 Bitable 表头一致）。
        """
        svc = VocabService()
        svc.load_all()

        words = svc.filter_by_band(band) if band else svc.words

        records = []
        for w in words:
            records.append({
                "fields": {
                    "单词": w.word,
                    "音标": w.phonetic,
                    "词性": w.pos,
                    "释义": w.meaning,
                    "Band": w.band,
                    "主题": w.topic,
                    "例句": w.example,
                    "例句翻译": w.example_cn,
                    "搭配": ", ".join(w.collocations),
                    "同义词": ", ".join(w.synonyms),
                    "词源": w.etymology,
                }
            })
        return records

    def prepare_records_data(self) -> list[dict]:
        """准备学习记录数据，转为 Bitable 记录格式"""
        review_svc = ReviewService(db_path=self._db_path)
        try:
            all_records = review_svc.get_all_records()
            # 同时获取原始数据库行以拿到 word 字段
            rows = review_svc._conn.execute(
                "SELECT word, word_data, memory_level, next_review, "
                "learn_count, correct_count, wrong_count, "
                "first_learned, last_reviewed, is_starred, is_difficult "
                "FROM learning_records ORDER BY last_reviewed DESC"
            ).fetchall()
        finally:
            review_svc.close()

        records = []
        for row in rows:
            total_attempts = row["correct_count"] + row["wrong_count"]
            accuracy = row["correct_count"] / total_attempts if total_attempts > 0 else 0.0

            records.append({
                "fields": {
                    "单词": row["word"],
                    "记忆等级": row["memory_level"],
                    "下次复习": row["next_review"] or "",
                    "学习次数": row["learn_count"],
                    "正确次数": row["correct_count"],
                    "错误次数": row["wrong_count"],
                    "正确率": round(accuracy, 4),
                    "首次学习": row["first_learned"] or "",
                    "最近复习": row["last_reviewed"] or "",
                    "星标": bool(row["is_starred"]),
                    "困难词": bool(row["is_difficult"]),
                }
            })
        return records

    def prepare_stats_data(self) -> list[dict]:
        """准备统计摘要数据，转为 Bitable 记录格式"""
        stats_svc = StatsService(db_path=self._db_path)
        try:
            total = stats_svc.total_stats()
            today = stats_svc.today_stats()
            due = stats_svc.due_count()
            current_streak, max_streak = stats_svc.get_streak()
            levels = stats_svc.level_distribution()
            band_progress = stats_svc.get_band_progress()
        finally:
            stats_svc.close()

        # 生成一条统计摘要记录
        now = datetime.now().isoformat(timespec="seconds")

        # 等级分布文本
        level_labels = {
            0: "未掌握", 1: "刚学习", 2: "初记忆",
            3: "短期记忆", 4: "中期记忆", 5: "长期记忆", 6: "已掌握",
        }
        level_text = "; ".join(
            f"{level_labels.get(lv, f'等级{lv}')}: {cnt}"
            for lv, cnt in sorted(levels.items())
        )

        # Band 进度文本
        band_text = "; ".join(
            f"Band {band}: {mastered}/{total_count} ({ratio:.0%})"
            for band, total_count, mastered, ratio in band_progress
        )

        record = {
            "fields": {
                "同步时间": now,
                "已学单词": total["total_words"],
                "总复习次数": total["total_reviews"],
                "总正确率": round(total["accuracy"], 4),
                "已掌握数": total["mastered"],
                "待复习数": due,
                "今日新学": today["new_words"],
                "今日复习": today["reviewed_words"],
                "连续学习天数": current_streak,
                "最长连续天数": max_streak,
                "等级分布": level_text,
                "Band进度": band_text,
            }
        }
        return [record]

    # ---- JSON 导出 ----

    def export_vocab(self, band: int | None = None) -> Path:
        """导出词库数据到 JSON 文件"""
        records = self.prepare_vocab_data(band=band)
        data = {
            "app_token": BITABLE_APP_TOKEN,
            "table": "词库",
            "records": records,
            "total": len(records),
            "exported_at": datetime.now().isoformat(timespec="seconds"),
        }
        return self._write_json(data, "vocab.json")

    def export_records(self) -> Path:
        """导出学习记录到 JSON 文件"""
        records = self.prepare_records_data()
        data = {
            "app_token": BITABLE_APP_TOKEN,
            "table": "学习记录",
            "records": records,
            "total": len(records),
            "exported_at": datetime.now().isoformat(timespec="seconds"),
        }
        return self._write_json(data, "records.json")

    def export_stats(self) -> Path:
        """导出统计摘要到 JSON 文件"""
        records = self.prepare_stats_data()
        data = {
            "app_token": BITABLE_APP_TOKEN,
            "table": "学习统计",
            "records": records,
            "total": len(records),
            "exported_at": datetime.now().isoformat(timespec="seconds"),
        }
        return self._write_json(data, "stats.json")

    def export_all(self) -> list[Path]:
        """导出全部数据，返回所有导出文件路径"""
        return [
            self.export_vocab(),
            self.export_records(),
            self.export_stats(),
        ]

    def _write_json(self, data: dict, filename: str) -> Path:
        """将数据写入 JSON 文件"""
        sync_dir = self._get_sync_dir()
        file_path = sync_dir / filename
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return file_path

    # ---- Phase 6: Bitable 兼容导出 ----

    def sync_to_bitable(self, app_token: str, table_id: str) -> Path:
        """同步学习数据到飞书 Bitable 兼容 JSON

        字段: 单词/Band/掌握等级/正确次数/错误次数/上次复习/下次复习

        Returns:
            导出的 JSON 文件路径
        """
        review_svc = ReviewService(db_path=self._db_path)
        try:
            rows = review_svc._conn.execute(
                "SELECT * FROM learning_records ORDER BY last_reviewed DESC"
            ).fetchall()
        except Exception:
            rows = []
        finally:
            review_svc.close()

        export_data = []
        for row in rows:
            try:
                word_data = json.loads(row["word_data"])
            except (json.JSONDecodeError, TypeError):
                word_data = {}

            export_data.append({
                "单词": row["word"],
                "Band": word_data.get("band", 0),
                "掌握等级": row["memory_level"],
                "正确次数": row["correct_count"],
                "错误次数": row["wrong_count"],
                "上次复习": row["last_reviewed"] or "",
                "下次复习": row["next_review"] or "",
            })

        sync_dir = self._get_sync_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vocab_{app_token}_{table_id}_{timestamp}.json"
        filepath = sync_dir / filename
        filepath.write_text(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._write_instructions(sync_dir, app_token, table_id)
        return filepath

    def create_bitable_schema(self, app_token: str, table_id: str) -> dict:
        """返回飞书 Bitable 建表 schema（供手动建表参考）"""
        return {
            "app_token": app_token,
            "table_id": table_id,
            "fields": [
                {"field_name": "单词", "type": 1, "description": "英文单词"},
                {"field_name": "Band", "type": 2, "description": "雅思 Band 等级 (5-9)"},
                {"field_name": "掌握等级", "type": 2, "description": "记忆等级 (0-6)"},
                {"field_name": "正确次数", "type": 2, "description": "答对次数"},
                {"field_name": "错误次数", "type": 2, "description": "答错次数"},
                {"field_name": "上次复习", "type": 5, "description": "上次复习时间"},
                {"field_name": "下次复习", "type": 5, "description": "下次复习日期"},
            ],
        }

    def sync_stats_to_bitable(self, app_token: str, table_id: str) -> Path:
        """同步统计数据到飞书 Bitable 兼容 JSON

        字段: 日期/学习量/正确率/新学/复习/streak

        Returns:
            导出的 JSON 文件路径
        """
        stats_svc = StatsService(db_path=self._db_path)
        try:
            total = stats_svc.total_stats()
            history = stats_svc.get_history(days=30)
            current_streak, _ = stats_svc.get_streak()
        finally:
            stats_svc.close()

        export_data = []
        for day in history:
            total_day = day["new_words"] + day["reviewed_words"]
            export_data.append({
                "日期": day["date"],
                "学习量": total_day,
                "正确率": round(total["accuracy"], 4),
                "新学": day["new_words"],
                "复习": day["reviewed_words"],
                "streak": current_streak,
            })

        sync_dir = self._get_sync_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stats_{app_token}_{table_id}_{timestamp}.json"
        filepath = sync_dir / filename
        filepath.write_text(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return filepath

    # ---- 配置管理 ----

    def get_config_path(self) -> Path:
        """获取飞书配置文件路径"""
        return get_app_dir() / "feishu.json"

    def load_config(self) -> dict | None:
        """加载飞书配置"""
        config_path = self.get_config_path()
        if not config_path.exists():
            return None
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_config(self, app_token: str, table_id: str) -> Path:
        """保存飞书配置到 ~/.ib/feishu.json"""
        config = {
            "app_token": app_token,
            "table_id": table_id,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        config_path = self.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return config_path

    def _write_instructions(self, sync_dir: Path, app_token: str, table_id: str) -> None:
        """生成飞书 Bitable 导入说明"""
        instructions = f"""# 飞书 Bitable 数据导入说明

## 导出信息
- App Token: {app_token}
- Table ID: {table_id}
- 导出目录: {sync_dir}

## 导入步骤

### 词汇数据导入
1. 打开飞书多维表格，进入目标数据表
2. 点击右上角「...」→「导入数据」
3. 选择 JSON 文件格式
4. 上传 `vocab_*.json` 文件
5. 确认字段映射：
   - 单词 → 文本类型
   - Band → 数字类型
   - 掌握等级 → 数字类型
   - 正确次数 → 数字类型
   - 错误次数 → 数字类型
   - 上次复习 → 日期类型
   - 下次复习 → 日期类型

### 统计数据导入
1. 新建一个统计数据表
2. 上传 `stats_*.json` 文件
3. 字段映射：
   - 日期 → 日期类型
   - 学习量 → 数字类型
   - 正确率 → 数字类型（百分比格式）
   - 新学 → 数字类型
   - 复习 → 数字类型
   - streak → 数字类型
"""
        (sync_dir / "sync_instructions.md").write_text(instructions, encoding="utf-8")
