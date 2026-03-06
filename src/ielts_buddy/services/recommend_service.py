"""智能学习推荐服务：薄弱词、到期词、新词推荐、掌握率预测、综合建议"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from ielts_buddy.core.config import get_db_path
from ielts_buddy.services.review_service import REVIEW_INTERVALS
from ielts_buddy.services.vocab_service import VocabService


class RecommendService:
    """智能学习推荐服务"""

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

    def get_weak_words(self, limit: int = 20) -> list[dict]:
        """获取薄弱词（错误率最高的词）

        返回: [{word, meaning, band, learn_count, correct_count, wrong_count, error_rate}, ...]
        """
        if not self._table_exists():
            return []

        rows = self._conn.execute(
            """SELECT word, word_data, learn_count, correct_count, wrong_count
               FROM learning_records
               WHERE learn_count > 0
               ORDER BY
                   CAST(wrong_count AS REAL) / CASE WHEN learn_count = 0 THEN 1 ELSE learn_count END DESC,
                   wrong_count DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

        results = []
        for row in rows:
            learn_count = row["learn_count"]
            wrong_count = row["wrong_count"]
            error_rate = wrong_count / learn_count if learn_count > 0 else 0.0

            # 只返回有错误记录的词
            if wrong_count == 0:
                continue

            try:
                word_data = json.loads(row["word_data"])
                meaning = word_data.get("meaning", "")
                band = word_data.get("band", 0)
            except (json.JSONDecodeError, TypeError):
                meaning = ""
                band = 0

            results.append({
                "word": row["word"],
                "meaning": meaning,
                "band": band,
                "learn_count": learn_count,
                "correct_count": row["correct_count"],
                "wrong_count": wrong_count,
                "error_rate": error_rate,
            })

        return results

    def get_due_words(self, limit: int = 20) -> list[dict]:
        """获取到期需复习的词

        返回: [{word, meaning, band, memory_level, next_review, overdue_days}, ...]
        """
        if not self._table_exists():
            return []

        today = date.today().isoformat()
        rows = self._conn.execute(
            """SELECT word, word_data, memory_level, next_review
               FROM learning_records
               WHERE next_review <= ?
               ORDER BY next_review ASC, memory_level ASC
               LIMIT ?""",
            (today, limit),
        ).fetchall()

        today_date = date.today()
        results = []
        for row in rows:
            next_review = row["next_review"]
            overdue_days = 0
            if next_review:
                review_date = date.fromisoformat(next_review)
                overdue_days = (today_date - review_date).days

            try:
                word_data = json.loads(row["word_data"])
                meaning = word_data.get("meaning", "")
                band = word_data.get("band", 0)
            except (json.JSONDecodeError, TypeError):
                meaning = ""
                band = 0

            results.append({
                "word": row["word"],
                "meaning": meaning,
                "band": band,
                "memory_level": row["memory_level"],
                "next_review": next_review,
                "overdue_days": overdue_days,
            })

        return results

    def get_recommended_new(self, band: int | None = None, count: int = 10) -> list[dict]:
        """推荐新词（排除已学过的词，优先推荐目标 Band）

        返回: [{word, meaning, band, phonetic, topic}, ...]
        """
        # 获取已学过的词集合
        learned_words: set[str] = set()
        if self._table_exists():
            rows = self._conn.execute("SELECT word FROM learning_records").fetchall()
            learned_words = {row["word"] for row in rows}

        # 加载词库
        vocab_svc = VocabService()
        vocab_svc.load_all()

        # 筛选候选词
        if band is not None:
            candidates = vocab_svc.filter_by_band(band)
        else:
            candidates = vocab_svc.words

        # 排除已学过的词
        new_words = [w for w in candidates if w.word not in learned_words]

        # 取前 count 个
        selected = new_words[:count]

        return [
            {
                "word": w.word,
                "meaning": w.meaning,
                "band": w.band,
                "phonetic": w.phonetic,
                "topic": w.topic,
            }
            for w in selected
        ]

    def predict_mastery(self, days: int = 7) -> dict:
        """预测 N 天后的掌握率

        基于当前复习间隔和遗忘曲线计算。
        返回: {current_mastery, predicted_mastery, total_words, mastered_now, predicted_mastered}
        """
        if not self._table_exists():
            return {
                "current_mastery": 0.0,
                "predicted_mastery": 0.0,
                "total_words": 0,
                "mastered_now": 0,
                "predicted_mastered": 0,
            }

        rows = self._conn.execute(
            "SELECT memory_level, next_review, correct_count, wrong_count FROM learning_records"
        ).fetchall()

        total = len(rows)
        if total == 0:
            return {
                "current_mastery": 0.0,
                "predicted_mastery": 0.0,
                "total_words": 0,
                "mastered_now": 0,
                "predicted_mastered": 0,
            }

        mastered_now = sum(1 for r in rows if r["memory_level"] >= 4)
        current_mastery = mastered_now / total

        # 预测：基于遗忘曲线估算
        # 假设每个词如果持续复习，level 会逐步提升
        # 如果不复习且到期，level 可能下降
        future_date = date.today() + timedelta(days=days)
        predicted_mastered = 0

        for row in rows:
            level = row["memory_level"]
            next_review = row["next_review"]

            if next_review:
                review_date = date.fromisoformat(next_review)
                if review_date <= future_date:
                    # 假设用户会复习到期的词，每次复习 level +1
                    # 估算在 days 天内能复习几次
                    reviews_possible = _estimate_reviews(level, days)
                    predicted_level = min(level + reviews_possible, len(REVIEW_INTERVALS) - 1)
                else:
                    predicted_level = level
            else:
                predicted_level = level

            # 应用遗忘衰减：如果长时间不复习，记忆会衰减
            accuracy = (
                row["correct_count"] / (row["correct_count"] + row["wrong_count"])
                if (row["correct_count"] + row["wrong_count"]) > 0
                else 0.5
            )
            # 高正确率的词更可能维持记忆
            retention = min(1.0, accuracy * 1.1)
            effective_level = predicted_level * retention

            if effective_level >= 4:
                predicted_mastered += 1

        predicted_mastery = predicted_mastered / total

        return {
            "current_mastery": current_mastery,
            "predicted_mastery": predicted_mastery,
            "total_words": total,
            "mastered_now": mastered_now,
            "predicted_mastered": predicted_mastered,
        }

    def get_study_suggestion(self) -> dict:
        """综合学习建议

        返回: {weak_count, due_count, suggested_new, priority_band, message}
        """
        weak = self.get_weak_words(limit=100)
        due = self.get_due_words(limit=100)
        weak_count = len(weak)
        due_count = len(due)

        # 确定优先 band：基于薄弱词的 band 分布
        band_errors: dict[int, int] = {}
        for w in weak:
            b = w.get("band", 0)
            if b > 0:
                band_errors[b] = band_errors.get(b, 0) + 1

        priority_band = max(band_errors, key=band_errors.get) if band_errors else 5

        # 建议新词数：如果薄弱词多，少学新词；如果掌握好，多学新词
        if weak_count > 10:
            suggested_new = 5
        elif weak_count > 5:
            suggested_new = 10
        else:
            suggested_new = 15

        # 如果待复习词太多，优先复习
        if due_count > 20:
            suggested_new = max(suggested_new - 5, 0)

        # 生成建议消息
        parts = []
        if due_count > 0:
            parts.append(f"有 {due_count} 个单词需要复习")
        if weak_count > 0:
            parts.append(f"{weak_count} 个薄弱词需要加强")

        if due_count > 20:
            parts.append("建议优先完成复习再学新词")
        elif due_count > 0:
            parts.append(f"建议先复习，再学 {suggested_new} 个新词")
        else:
            parts.append(f"状态良好，建议学习 {suggested_new} 个新词")

        if priority_band > 0 and weak_count > 0:
            parts.append(f"Band {priority_band} 的词需要重点关注")

        message = "；".join(parts) + "。"

        return {
            "weak_count": weak_count,
            "due_count": due_count,
            "suggested_new": suggested_new,
            "priority_band": priority_band,
            "message": message,
        }


def _estimate_reviews(current_level: int, days: int) -> int:
    """估算在给定天数内可能完成的复习次数"""
    reviews = 0
    level = current_level
    total_days = 0
    while total_days < days and level < len(REVIEW_INTERVALS) - 1:
        interval = REVIEW_INTERVALS[min(level, len(REVIEW_INTERVALS) - 1)]
        total_days += max(interval, 1)
        if total_days <= days:
            reviews += 1
            level += 1
    return reviews
