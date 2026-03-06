"""学习统计服务：今日/总计学习数据、正确率、连续学习天数、趋势等"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from ielts_buddy.core.config import get_db_path


class StatsService:
    """学习统计服务"""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def _table_exists(self) -> bool:
        row = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='learning_records'"
        ).fetchone()
        return row is not None

    def total_stats(self) -> dict:
        """获取总体统计数据"""
        if not self._table_exists():
            return {
                "total_words": 0,
                "total_reviews": 0,
                "total_correct": 0,
                "total_wrong": 0,
                "accuracy": 0.0,
                "mastered": 0,
            }
        row = self._conn.execute(
            """SELECT
               COUNT(*) as total_words,
               COALESCE(SUM(learn_count), 0) as total_reviews,
               COALESCE(SUM(correct_count), 0) as total_correct,
               COALESCE(SUM(wrong_count), 0) as total_wrong,
               COUNT(CASE WHEN memory_level >= 5 THEN 1 END) as mastered
               FROM learning_records"""
        ).fetchone()

        total_attempts = row["total_correct"] + row["total_wrong"]
        accuracy = row["total_correct"] / total_attempts if total_attempts > 0 else 0.0

        return {
            "total_words": row["total_words"],
            "total_reviews": row["total_reviews"],
            "total_correct": row["total_correct"],
            "total_wrong": row["total_wrong"],
            "accuracy": accuracy,
            "mastered": row["mastered"],
        }

    def today_stats(self) -> dict:
        """获取今日学习统计"""
        if not self._table_exists():
            return {
                "new_words": 0,
                "reviewed_words": 0,
                "correct": 0,
                "wrong": 0,
                "accuracy": 0.0,
            }

        today = date.today().isoformat()

        # 今日新学单词（first_learned 在今天）
        new_row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM learning_records WHERE first_learned LIKE ?",
            (f"{today}%",),
        ).fetchone()

        # 今日复习单词（last_reviewed 在今天）
        review_row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM learning_records WHERE last_reviewed LIKE ?",
            (f"{today}%",),
        ).fetchone()

        # 简化处理：今日正确/错误无法精确拆分（因为只存累计值）
        # 用 reviewed_words 作为近似
        return {
            "new_words": new_row["cnt"],
            "reviewed_words": review_row["cnt"],
            "correct": 0,
            "wrong": 0,
            "accuracy": 0.0,
        }

    def due_count(self) -> int:
        """获取待复习单词数量"""
        if not self._table_exists():
            return 0
        today = date.today().isoformat()
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM learning_records WHERE next_review <= ?",
            (today,),
        ).fetchone()
        return row["cnt"]

    def level_distribution(self) -> dict[int, int]:
        """获取记忆等级分布"""
        if not self._table_exists():
            return {}
        rows = self._conn.execute(
            """SELECT memory_level, COUNT(*) as cnt
               FROM learning_records
               GROUP BY memory_level
               ORDER BY memory_level"""
        ).fetchall()
        return {row["memory_level"]: row["cnt"] for row in rows}

    def get_streak(self) -> tuple[int, int]:
        """获取连续学习天数: (当前连续天数, 历史最长连续天数)"""
        if not self._table_exists():
            return (0, 0)

        rows = self._conn.execute(
            """SELECT DISTINCT DATE(last_reviewed) as study_date
               FROM learning_records
               WHERE last_reviewed IS NOT NULL
               ORDER BY study_date DESC"""
        ).fetchall()

        if not rows:
            return (0, 0)

        dates = [date.fromisoformat(row["study_date"]) for row in rows]
        today = date.today()

        # 当前连续天数：从今天或昨天开始向前数
        current_streak = 0
        if dates[0] == today or dates[0] == today - timedelta(days=1):
            current_streak = 1
            for i in range(1, len(dates)):
                if dates[i] == dates[i - 1] - timedelta(days=1):
                    current_streak += 1
                else:
                    break

        # 历史最长连续天数
        max_streak = 1
        streak = 1
        for i in range(1, len(dates)):
            if dates[i] == dates[i - 1] - timedelta(days=1):
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1
        max_streak = max(max_streak, streak)

        return (current_streak, max_streak)

    def get_daily_trend(self, days: int = 7) -> list[tuple[str, int, float]]:
        """获取每日学习趋势: [(日期, 学习数, 正确率), ...]

        注意：由于数据库只存储累计正确/错误次数，无法精确计算每日正确率，
        此处正确率返回 0.0。
        """
        today = date.today()
        start = today - timedelta(days=days - 1)

        if not self._table_exists():
            return [
                ((start + timedelta(days=i)).isoformat(), 0, 0.0)
                for i in range(days)
            ]

        rows = self._conn.execute(
            """SELECT DATE(last_reviewed) as study_date, COUNT(*) as cnt
               FROM learning_records
               WHERE DATE(last_reviewed) >= ?
               GROUP BY DATE(last_reviewed)""",
            (start.isoformat(),),
        ).fetchall()

        date_counts = {row["study_date"]: row["cnt"] for row in rows}

        result = []
        for i in range(days):
            d = (start + timedelta(days=i)).isoformat()
            result.append((d, date_counts.get(d, 0), 0.0))

        return result

    def get_band_progress(self) -> list[tuple[int, int, int, float]]:
        """获取各Band掌握进度: [(band, 词库总数, 已掌握, 比例), ...]

        掌握定义：记忆等级 >= 4
        """
        from ielts_buddy.services.vocab_service import VocabService

        vocab_svc = VocabService()
        vocab_svc.load_all()
        band_totals = vocab_svc.get_vocab_stats()["bands"]

        if not self._table_exists():
            return [(band, total, 0, 0.0) for band, total in sorted(band_totals.items())]

        rows = self._conn.execute(
            "SELECT word_data, memory_level FROM learning_records"
        ).fetchall()

        band_mastered: dict[int, int] = {}
        for row in rows:
            try:
                word_data = json.loads(row["word_data"])
                band = word_data.get("band", 0)
                if row["memory_level"] >= 4:
                    band_mastered[band] = band_mastered.get(band, 0) + 1
            except (json.JSONDecodeError, KeyError):
                continue

        result = []
        for band, total in sorted(band_totals.items()):
            mastered = band_mastered.get(band, 0)
            ratio = mastered / total if total > 0 else 0.0
            result.append((band, total, mastered, ratio))

        return result

    def get_history(self, days: int = 7) -> list[dict]:
        """获取学习历史: [{date, new_words, reviewed_words}, ...]"""
        today = date.today()
        start = today - timedelta(days=days - 1)

        if not self._table_exists():
            return [
                {"date": (start + timedelta(days=i)).isoformat(), "new_words": 0, "reviewed_words": 0}
                for i in range(days)
            ]

        # 每天新学单词数
        new_rows = self._conn.execute(
            """SELECT DATE(first_learned) as learn_date, COUNT(*) as cnt
               FROM learning_records
               WHERE DATE(first_learned) >= ?
               GROUP BY DATE(first_learned)""",
            (start.isoformat(),),
        ).fetchall()

        # 每天复习单词数
        review_rows = self._conn.execute(
            """SELECT DATE(last_reviewed) as review_date, COUNT(*) as cnt
               FROM learning_records
               WHERE DATE(last_reviewed) >= ?
               GROUP BY DATE(last_reviewed)""",
            (start.isoformat(),),
        ).fetchall()

        new_counts = {row["learn_date"]: row["cnt"] for row in new_rows}
        review_counts = {row["review_date"]: row["cnt"] for row in review_rows}

        result = []
        for i in range(days):
            d = (start + timedelta(days=i)).isoformat()
            result.append({
                "date": d,
                "new_words": new_counts.get(d, 0),
                "reviewed_words": review_counts.get(d, 0),
            })

        return result
