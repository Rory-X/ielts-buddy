"""同步服务：导出学习数据为 JSON 文件，供外部工具（飞书等）导入"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ielts_buddy.core.config import get_app_dir
from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.stats_service import StatsService
from ielts_buddy.services.vocab_service import VocabService


def _get_sync_dir() -> Path:
    """获取同步输出目录 ~/.ib/sync/"""
    return get_app_dir() / "sync"


class SyncService:
    """数据导出服务"""

    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or _get_sync_dir()

    def _ensure_dir(self) -> None:
        """确保输出目录存在"""
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export_vocab(self) -> Path:
        """导出全部词库为 JSON（含掌握状态）

        每个单词附带 mastery 字段（来自学习记录）。
        返回输出文件路径。
        """
        self._ensure_dir()

        # 加载全部词库
        vocab_svc = VocabService()
        vocab_svc.load_all()
        words = vocab_svc.words

        # 加载学习记录，建立 word -> record 映射
        review_svc = ReviewService()
        mastery_map: dict[str, dict] = {}
        try:
            all_records = review_svc.get_all_records()
            # 需要从 DB 获取 word 名，用 _conn 直接查
            rows = review_svc._conn.execute(
                "SELECT word, memory_level, learn_count, correct_count, wrong_count, "
                "next_review, last_reviewed FROM learning_records"
            ).fetchall()
            for row in rows:
                mastery_map[row["word"]] = {
                    "memory_level": row["memory_level"],
                    "learn_count": row["learn_count"],
                    "correct_count": row["correct_count"],
                    "wrong_count": row["wrong_count"],
                    "next_review": row["next_review"],
                    "last_reviewed": row["last_reviewed"],
                }
        except Exception:
            pass  # 无学习记录时静默处理
        finally:
            review_svc.close()

        # 组装导出数据
        export_data = []
        for w in words:
            item = w.model_dump()
            mastery = mastery_map.get(w.word)
            if mastery:
                item["mastery"] = mastery
            else:
                item["mastery"] = {"memory_level": 0, "learn_count": 0}
            export_data.append(item)

        output_path = self._output_dir / "vocab.json"
        output_path.write_text(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def export_records(self) -> Path:
        """导出学习记录为 JSON

        返回输出文件路径。
        """
        self._ensure_dir()

        review_svc = ReviewService()
        records = []
        try:
            rows = review_svc._conn.execute(
                "SELECT * FROM learning_records ORDER BY last_reviewed DESC"
            ).fetchall()
            for row in rows:
                records.append({
                    "word": row["word"],
                    "memory_level": row["memory_level"],
                    "next_review": row["next_review"],
                    "learn_count": row["learn_count"],
                    "correct_count": row["correct_count"],
                    "wrong_count": row["wrong_count"],
                    "first_learned": row["first_learned"],
                    "last_reviewed": row["last_reviewed"],
                    "is_starred": bool(row["is_starred"]),
                    "is_difficult": bool(row["is_difficult"]),
                })
        except Exception:
            pass  # 无记录时返回空列表
        finally:
            review_svc.close()

        output_path = self._output_dir / "records.json"
        output_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def export_stats(self) -> Path:
        """导出统计摘要为 JSON

        返回输出文件路径。
        """
        self._ensure_dir()

        stats_svc = StatsService()
        try:
            total = stats_svc.total_stats()
            today = stats_svc.today_stats()
            due = stats_svc.due_count()
            current_streak, max_streak = stats_svc.get_streak()
            levels = stats_svc.level_distribution()
            band_progress = stats_svc.get_band_progress()
        finally:
            stats_svc.close()

        summary = {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "total": total,
            "today": today,
            "due_count": due,
            "streak": {"current": current_streak, "max": max_streak},
            "level_distribution": {str(k): v for k, v in levels.items()},
            "band_progress": [
                {"band": b, "total": t, "mastered": m, "ratio": round(r, 3)}
                for b, t, m, r in band_progress
            ],
        }

        output_path = self._output_dir / "stats.json"
        output_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def export_all(self) -> dict[str, Path]:
        """导出全部数据，返回 {类型: 文件路径}"""
        return {
            "vocab": self.export_vocab(),
            "records": self.export_records(),
            "stats": self.export_stats(),
        }
