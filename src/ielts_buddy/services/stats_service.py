"""学习统计服务：今日/总计学习数据、正确率等"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
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
