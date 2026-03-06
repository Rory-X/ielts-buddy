"""模拟考试服务：生成考试、提交答案、生成报告、历史记录"""

from __future__ import annotations

import json
import random
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from ielts_buddy.core.config import get_db_path
from ielts_buddy.core.models import ExamQuestion, ExamReport, ExamSession
from ielts_buddy.services.vocab_service import VocabService

_EXAM_SCHEMA = """
CREATE TABLE IF NOT EXISTS exam_sessions (
    id TEXT PRIMARY KEY,
    questions TEXT NOT NULL,
    time_limit INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    band_filter INTEGER,
    score INTEGER,
    total INTEGER,
    accuracy REAL,
    duration INTEGER,
    weak_words TEXT,
    band_breakdown TEXT
);
"""


class ExamService:
    """模拟考试服务"""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(_EXAM_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def create_exam(
        self,
        band: int | None = None,
        count: int = 30,
        time_limit: int = 20,
    ) -> ExamSession:
        """生成模拟考试，从词库随机选词并混合 en2zh/zh2en 题型"""
        svc = VocabService()
        svc.load_all()

        words = svc.random_words(count, band)
        if not words:
            raise ValueError("词库中没有足够的单词生成考试")

        questions: list[ExamQuestion] = []
        for i, w in enumerate(words):
            mode = random.choice(["en2zh", "zh2en"])
            if mode == "en2zh":
                prompt = f"{w.word}  {w.phonetic}  [{w.pos}]"
                answer = w.meaning
            else:
                prompt = f"{w.meaning}  [{w.pos}]"
                answer = w.word

            questions.append(
                ExamQuestion(
                    index=i,
                    word=w.word,
                    mode=mode,
                    prompt=prompt,
                    answer=answer,
                    band=w.band,
                )
            )

        session = ExamSession(
            id=uuid.uuid4().hex[:12],
            questions=questions,
            time_limit=time_limit,
            started_at=datetime.now().isoformat(timespec="seconds"),
            band_filter=band,
        )
        return session

    def submit_answer(
        self, session: ExamSession, q_index: int, answer: str
    ) -> dict:
        """提交单题答案，返回 {correct, answer}"""
        if q_index < 0 or q_index >= len(session.questions):
            raise IndexError(f"题号 {q_index} 超出范围 (共 {len(session.questions)} 题)")

        q = session.questions[q_index]
        q.user_answer = answer

        if q.mode == "en2zh":
            # 英译中：答案包含释义中的关键词即算对
            meanings = q.answer.replace("；", "，").replace(",", "，").split("，")
            q.is_correct = any(
                m.strip() in answer or answer in m.strip()
                for m in meanings
                if m.strip()
            )
        else:
            # 中译英：忽略大小写
            q.is_correct = answer.strip().lower() == q.answer.strip().lower()

        return {"correct": q.is_correct, "answer": q.answer}

    def finish_exam(self, session: ExamSession) -> ExamReport:
        """结束考试，生成报告并保存到数据库"""
        now = datetime.now().isoformat(timespec="seconds")
        session.finished_at = now

        # 统计
        answered = [q for q in session.questions if q.is_correct is not None]
        correct_count = sum(1 for q in answered if q.is_correct)
        total = len(answered)
        accuracy = correct_count / total if total > 0 else 0.0

        # band 分布
        band_breakdown: dict[int, dict[str, int]] = {}
        for q in answered:
            if q.band not in band_breakdown:
                band_breakdown[q.band] = {"correct": 0, "wrong": 0}
            if q.is_correct:
                band_breakdown[q.band]["correct"] += 1
            else:
                band_breakdown[q.band]["wrong"] += 1

        # 薄弱单词
        weak_words = [q.word for q in answered if not q.is_correct]

        # 耗时
        started = datetime.fromisoformat(session.started_at)
        finished = datetime.fromisoformat(session.finished_at)
        duration = int((finished - started).total_seconds())

        report = ExamReport(
            session_id=session.id,
            score=correct_count,
            total=total,
            accuracy=accuracy,
            band_breakdown=band_breakdown,
            weak_words=weak_words,
            duration=duration,
            finished_at=now,
        )

        # 保存到数据库
        self._save_exam(session, report)

        return report

    def _save_exam(self, session: ExamSession, report: ExamReport) -> None:
        """保存考试记录到 SQLite"""
        questions_json = json.dumps(
            [q.model_dump() for q in session.questions], ensure_ascii=False
        )
        self._conn.execute(
            """INSERT OR REPLACE INTO exam_sessions
               (id, questions, time_limit, started_at, finished_at, band_filter,
                score, total, accuracy, duration, weak_words, band_breakdown)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session.id,
                questions_json,
                session.time_limit,
                session.started_at,
                session.finished_at,
                session.band_filter,
                report.score,
                report.total,
                report.accuracy,
                report.duration,
                json.dumps(report.weak_words, ensure_ascii=False),
                json.dumps(report.band_breakdown, ensure_ascii=False),
            ),
        )
        self._conn.commit()

    def get_exam_history(self, limit: int = 10) -> list[ExamReport]:
        """获取历史考试记录"""
        rows = self._conn.execute(
            """SELECT * FROM exam_sessions
               WHERE finished_at IS NOT NULL
               ORDER BY finished_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

        reports = []
        for row in rows:
            reports.append(
                ExamReport(
                    session_id=row["id"],
                    score=row["score"] or 0,
                    total=row["total"] or 0,
                    accuracy=row["accuracy"] or 0.0,
                    band_breakdown=json.loads(row["band_breakdown"])
                    if row["band_breakdown"]
                    else {},
                    weak_words=json.loads(row["weak_words"])
                    if row["weak_words"]
                    else [],
                    duration=row["duration"] or 0,
                    finished_at=row["finished_at"] or "",
                )
            )
        return reports
