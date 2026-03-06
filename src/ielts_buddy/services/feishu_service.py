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
    sync_dir = parent / "sync"
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
