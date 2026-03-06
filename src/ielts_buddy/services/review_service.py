"""复习服务：基于艾宾浩斯遗忘曲线的间隔重复，使用 SQLite 存储学习记录"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from ielts_buddy.core.config import DB_PATH
from ielts_buddy.core.models import LearningRecord, Word

# 艾宾浩斯复习间隔（天数），memory_level 0-6 对应
REVIEW_INTERVALS = [0, 1, 2, 4, 7, 15, 30]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE NOT NULL,
    word_data TEXT NOT NULL,
    memory_level INTEGER DEFAULT 0,
    next_review TEXT,
    learn_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    wrong_count INTEGER DEFAULT 0,
    first_learned TEXT,
    last_reviewed TEXT,
    is_starred INTEGER DEFAULT 0,
    is_difficult INTEGER DEFAULT 0
);
"""


class ReviewService:
    """艾宾浩斯复习服务"""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ---- 学习记录管理 ----

    def record_learn(self, word: Word, correct: bool) -> LearningRecord:
        """记录一次学习/复习结果，并更新下次复习时间"""
        now = datetime.now().isoformat(timespec="seconds")
        today = date.today().isoformat()

        row = self._conn.execute(
            "SELECT * FROM learning_records WHERE word = ?", (word.word,)
        ).fetchone()

        if row is None:
            # 首次学习
            level = 1 if correct else 0
            next_review = _next_review_date(today, level)
            import json
            word_data = word.model_dump_json()
            self._conn.execute(
                """INSERT INTO learning_records
                   (word, word_data, memory_level, next_review,
                    learn_count, correct_count, wrong_count,
                    first_learned, last_reviewed)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    word.word, word_data, level, next_review,
                    1 if correct else 0,
                    0 if correct else 1,
                    now, now,
                ),
            )
        else:
            # 更新记录
            level = row["memory_level"]
            if correct:
                level = min(level + 1, len(REVIEW_INTERVALS) - 1)
            else:
                level = max(level - 1, 0)

            next_review = _next_review_date(today, level)
            self._conn.execute(
                """UPDATE learning_records SET
                   memory_level = ?,
                   next_review = ?,
                   learn_count = learn_count + 1,
                   correct_count = correct_count + ?,
                   wrong_count = wrong_count + ?,
                   last_reviewed = ?
                   WHERE word = ?""",
                (
                    level, next_review,
                    1 if correct else 0,
                    0 if correct else 1,
                    now, word.word,
                ),
            )

        self._conn.commit()

        return self._get_record(word.word)

    def _get_record(self, word: str) -> LearningRecord:
        row = self._conn.execute(
            "SELECT * FROM learning_records WHERE word = ?", (word,)
        ).fetchone()
        if row is None:
            raise ValueError(f"未找到单词 '{word}' 的学习记录")
        return LearningRecord(
            id=row["id"],
            word_id=row["id"],
            memory_level=row["memory_level"],
            next_review=row["next_review"],
            learn_count=row["learn_count"],
            correct_count=row["correct_count"],
            wrong_count=row["wrong_count"],
            first_learned=row["first_learned"],
            last_reviewed=row["last_reviewed"],
            is_starred=bool(row["is_starred"]),
            is_difficult=bool(row["is_difficult"]),
        )

    # ---- 复习计划 ----

    def get_due_words(self, limit: int = 20) -> list[dict]:
        """获取今天需要复习的单词，返回 [{word, word_data, record}, ...]"""
        today = date.today().isoformat()
        rows = self._conn.execute(
            """SELECT * FROM learning_records
               WHERE next_review <= ?
               ORDER BY memory_level ASC, next_review ASC
               LIMIT ?""",
            (today, limit),
        ).fetchall()

        import json
        results = []
        for row in rows:
            word_data = Word(**json.loads(row["word_data"]))
            record = LearningRecord(
                id=row["id"],
                word_id=row["id"],
                memory_level=row["memory_level"],
                next_review=row["next_review"],
                learn_count=row["learn_count"],
                correct_count=row["correct_count"],
                wrong_count=row["wrong_count"],
                first_learned=row["first_learned"],
                last_reviewed=row["last_reviewed"],
                is_starred=bool(row["is_starred"]),
                is_difficult=bool(row["is_difficult"]),
            )
            results.append({"word": row["word"], "word_data": word_data, "record": record})
        return results

    def get_due_count(self) -> int:
        """获取今天待复习的单词数量"""
        today = date.today().isoformat()
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM learning_records WHERE next_review <= ?",
            (today,),
        ).fetchone()
        return row["cnt"]

    # ---- 查询 ----

    def get_all_records(self) -> list[LearningRecord]:
        """获取所有学习记录"""
        rows = self._conn.execute(
            "SELECT * FROM learning_records ORDER BY last_reviewed DESC"
        ).fetchall()
        return [
            LearningRecord(
                id=row["id"],
                word_id=row["id"],
                memory_level=row["memory_level"],
                next_review=row["next_review"],
                learn_count=row["learn_count"],
                correct_count=row["correct_count"],
                wrong_count=row["wrong_count"],
                first_learned=row["first_learned"],
                last_reviewed=row["last_reviewed"],
                is_starred=bool(row["is_starred"]),
                is_difficult=bool(row["is_difficult"]),
            )
            for row in rows
        ]

    def get_learned_count(self) -> int:
        """获取已学习的单词总数"""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM learning_records").fetchone()
        return row["cnt"]

    def toggle_star(self, word: str) -> bool:
        """切换单词的星标状态，返回新状态"""
        row = self._conn.execute(
            "SELECT is_starred FROM learning_records WHERE word = ?", (word,)
        ).fetchone()
        if row is None:
            raise ValueError(f"未找到单词 '{word}' 的学习记录")
        new_state = 0 if row["is_starred"] else 1
        self._conn.execute(
            "UPDATE learning_records SET is_starred = ? WHERE word = ?",
            (new_state, word),
        )
        self._conn.commit()
        return bool(new_state)


def _next_review_date(today_str: str, level: int) -> str:
    """根据记忆等级计算下次复习日期"""
    today = date.fromisoformat(today_str)
    interval = REVIEW_INTERVALS[min(level, len(REVIEW_INTERVALS) - 1)]
    return (today + timedelta(days=interval)).isoformat()
