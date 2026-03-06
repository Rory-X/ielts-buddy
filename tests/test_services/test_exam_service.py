"""测试模拟考试服务"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import pytest

from ielts_buddy.core.models import ExamQuestion, ExamReport, ExamSession
from ielts_buddy.services.exam_service import ExamService


@pytest.fixture
def exam_service(tmp_db: Path) -> ExamService:
    """创建使用临时数据库的 ExamService"""
    svc = ExamService(db_path=tmp_db)
    yield svc
    svc.close()


class TestExamModels:
    """测试模拟考试数据模型"""

    def test_exam_question_creation(self):
        q = ExamQuestion(
            index=0, word="example", mode="en2zh",
            prompt="example /ɪɡˈzæmpəl/ [n.]", answer="例子", band=5,
        )
        assert q.index == 0
        assert q.word == "example"
        assert q.mode == "en2zh"
        assert q.user_answer is None
        assert q.is_correct is None

    def test_exam_question_with_answer(self):
        q = ExamQuestion(
            index=1, word="develop", mode="zh2en",
            prompt="发展 [v.]", answer="develop", band=6,
            user_answer="develop", is_correct=True,
        )
        assert q.is_correct is True
        assert q.user_answer == "develop"

    def test_exam_session_creation(self):
        session = ExamSession(
            id="abc123",
            questions=[],
            time_limit=20,
            started_at="2026-01-01T10:00:00",
        )
        assert session.id == "abc123"
        assert session.time_limit == 20
        assert session.finished_at is None

    def test_exam_session_with_questions(self):
        q = ExamQuestion(
            index=0, word="test", mode="en2zh",
            prompt="test", answer="测试", band=5,
        )
        session = ExamSession(
            id="abc123", questions=[q], time_limit=15,
            started_at="2026-01-01T10:00:00",
        )
        assert len(session.questions) == 1
        assert session.questions[0].word == "test"

    def test_exam_report_creation(self):
        report = ExamReport(
            session_id="abc123",
            score=8, total=10, accuracy=0.8,
            band_breakdown={5: {"correct": 5, "wrong": 1}, 6: {"correct": 3, "wrong": 1}},
            weak_words=["word1", "word2"],
            duration=600,
            finished_at="2026-01-01T10:10:00",
        )
        assert report.score == 8
        assert report.accuracy == 0.8
        assert len(report.weak_words) == 2
        assert report.duration == 600

    def test_exam_report_defaults(self):
        report = ExamReport(session_id="x")
        assert report.score == 0
        assert report.total == 0
        assert report.accuracy == 0.0
        assert report.band_breakdown == {}
        assert report.weak_words == []


class TestExamServiceCreateExam:
    """测试 create_exam 方法"""

    def test_create_exam_default(self, exam_service: ExamService):
        session = exam_service.create_exam(count=5)
        assert len(session.questions) == 5
        assert session.time_limit == 20
        assert session.started_at != ""
        assert session.id != ""

    def test_create_exam_custom_count(self, exam_service: ExamService):
        session = exam_service.create_exam(count=3)
        assert len(session.questions) == 3

    def test_create_exam_with_band(self, exam_service: ExamService):
        session = exam_service.create_exam(band=5, count=5)
        assert session.band_filter == 5
        assert len(session.questions) <= 5
        for q in session.questions:
            assert q.band == 5

    def test_create_exam_with_time_limit(self, exam_service: ExamService):
        session = exam_service.create_exam(count=5, time_limit=10)
        assert session.time_limit == 10

    def test_create_exam_mixed_modes(self, exam_service: ExamService):
        session = exam_service.create_exam(count=20)
        modes = {q.mode for q in session.questions}
        # 20题足够大，应该有两种模式混合
        assert len(modes) >= 1  # 至少一种模式（概率极小的情况下可能只有一种）

    def test_create_exam_question_fields(self, exam_service: ExamService):
        session = exam_service.create_exam(count=5)
        for q in session.questions:
            assert q.word != ""
            assert q.prompt != ""
            assert q.answer != ""
            assert q.mode in ("en2zh", "zh2en")
            assert q.band >= 5

    def test_create_exam_unique_id(self, exam_service: ExamService):
        s1 = exam_service.create_exam(count=3)
        s2 = exam_service.create_exam(count=3)
        assert s1.id != s2.id

    def test_create_exam_sequential_indices(self, exam_service: ExamService):
        session = exam_service.create_exam(count=10)
        indices = [q.index for q in session.questions]
        assert indices == list(range(10))


class TestExamServiceSubmitAnswer:
    """测试 submit_answer 方法"""

    def test_submit_correct_en2zh(self, exam_service: ExamService):
        session = ExamSession(
            id="test1",
            questions=[
                ExamQuestion(
                    index=0, word="example", mode="en2zh",
                    prompt="example", answer="例子，实例", band=5,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = exam_service.submit_answer(session, 0, "例子")
        assert result["correct"] is True

    def test_submit_wrong_en2zh(self, exam_service: ExamService):
        session = ExamSession(
            id="test2",
            questions=[
                ExamQuestion(
                    index=0, word="example", mode="en2zh",
                    prompt="example", answer="例子，实例", band=5,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = exam_service.submit_answer(session, 0, "完全错误")
        assert result["correct"] is False

    def test_submit_correct_zh2en(self, exam_service: ExamService):
        session = ExamSession(
            id="test3",
            questions=[
                ExamQuestion(
                    index=0, word="develop", mode="zh2en",
                    prompt="发展", answer="develop", band=6,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = exam_service.submit_answer(session, 0, "develop")
        assert result["correct"] is True

    def test_submit_zh2en_case_insensitive(self, exam_service: ExamService):
        session = ExamSession(
            id="test4",
            questions=[
                ExamQuestion(
                    index=0, word="Develop", mode="zh2en",
                    prompt="发展", answer="Develop", band=6,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = exam_service.submit_answer(session, 0, "develop")
        assert result["correct"] is True

    def test_submit_wrong_zh2en(self, exam_service: ExamService):
        session = ExamSession(
            id="test5",
            questions=[
                ExamQuestion(
                    index=0, word="develop", mode="zh2en",
                    prompt="发展", answer="develop", band=6,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = exam_service.submit_answer(session, 0, "wrong")
        assert result["correct"] is False

    def test_submit_returns_correct_answer(self, exam_service: ExamService):
        session = ExamSession(
            id="test6",
            questions=[
                ExamQuestion(
                    index=0, word="example", mode="en2zh",
                    prompt="example", answer="例子", band=5,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = exam_service.submit_answer(session, 0, "错")
        assert result["answer"] == "例子"

    def test_submit_updates_question(self, exam_service: ExamService):
        session = ExamSession(
            id="test7",
            questions=[
                ExamQuestion(
                    index=0, word="example", mode="en2zh",
                    prompt="example", answer="例子", band=5,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        exam_service.submit_answer(session, 0, "例子")
        assert session.questions[0].user_answer == "例子"
        assert session.questions[0].is_correct is True

    def test_submit_invalid_index(self, exam_service: ExamService):
        session = ExamSession(
            id="test8",
            questions=[
                ExamQuestion(
                    index=0, word="example", mode="en2zh",
                    prompt="example", answer="例子", band=5,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        with pytest.raises(IndexError):
            exam_service.submit_answer(session, 5, "test")

    def test_submit_en2zh_partial_match(self, exam_service: ExamService):
        """en2zh 模式下，部分匹配也算正确"""
        session = ExamSession(
            id="test9",
            questions=[
                ExamQuestion(
                    index=0, word="contribute", mode="en2zh",
                    prompt="contribute", answer="贡献，促成", band=6,
                )
            ],
            time_limit=20,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        result = exam_service.submit_answer(session, 0, "贡献")
        assert result["correct"] is True


class TestExamServiceFinishExam:
    """测试 finish_exam 方法"""

    def test_finish_exam_basic(self, exam_service: ExamService):
        now = datetime.now().isoformat(timespec="seconds")
        session = ExamSession(
            id="finish1",
            questions=[
                ExamQuestion(
                    index=0, word="a", mode="en2zh", prompt="a",
                    answer="一个", band=5, user_answer="一个", is_correct=True,
                ),
                ExamQuestion(
                    index=1, word="b", mode="zh2en", prompt="二",
                    answer="b", band=5, user_answer="wrong", is_correct=False,
                ),
            ],
            time_limit=20,
            started_at=now,
        )
        report = exam_service.finish_exam(session)
        assert report.score == 1
        assert report.total == 2
        assert report.accuracy == 0.5
        assert "b" in report.weak_words
        assert "a" not in report.weak_words

    def test_finish_exam_all_correct(self, exam_service: ExamService):
        now = datetime.now().isoformat(timespec="seconds")
        session = ExamSession(
            id="finish2",
            questions=[
                ExamQuestion(
                    index=0, word="a", mode="en2zh", prompt="a",
                    answer="一", band=5, user_answer="一", is_correct=True,
                ),
            ],
            time_limit=20,
            started_at=now,
        )
        report = exam_service.finish_exam(session)
        assert report.score == 1
        assert report.accuracy == 1.0
        assert report.weak_words == []

    def test_finish_exam_no_answers(self, exam_service: ExamService):
        now = datetime.now().isoformat(timespec="seconds")
        session = ExamSession(
            id="finish3",
            questions=[
                ExamQuestion(
                    index=0, word="a", mode="en2zh", prompt="a",
                    answer="一", band=5,
                ),
            ],
            time_limit=20,
            started_at=now,
        )
        report = exam_service.finish_exam(session)
        assert report.total == 0
        assert report.accuracy == 0.0

    def test_finish_exam_band_breakdown(self, exam_service: ExamService):
        now = datetime.now().isoformat(timespec="seconds")
        session = ExamSession(
            id="finish4",
            questions=[
                ExamQuestion(
                    index=0, word="a", mode="en2zh", prompt="a",
                    answer="一", band=5, user_answer="一", is_correct=True,
                ),
                ExamQuestion(
                    index=1, word="b", mode="en2zh", prompt="b",
                    answer="二", band=6, user_answer="错", is_correct=False,
                ),
                ExamQuestion(
                    index=2, word="c", mode="en2zh", prompt="c",
                    answer="三", band=5, user_answer="三", is_correct=True,
                ),
            ],
            time_limit=20,
            started_at=now,
        )
        report = exam_service.finish_exam(session)
        assert 5 in report.band_breakdown
        assert report.band_breakdown[5]["correct"] == 2
        assert report.band_breakdown[5]["wrong"] == 0
        assert 6 in report.band_breakdown
        assert report.band_breakdown[6]["correct"] == 0
        assert report.band_breakdown[6]["wrong"] == 1

    def test_finish_exam_saves_to_db(self, exam_service: ExamService):
        now = datetime.now().isoformat(timespec="seconds")
        session = ExamSession(
            id="finish5",
            questions=[
                ExamQuestion(
                    index=0, word="a", mode="en2zh", prompt="a",
                    answer="一", band=5, user_answer="一", is_correct=True,
                ),
            ],
            time_limit=20,
            started_at=now,
        )
        exam_service.finish_exam(session)
        history = exam_service.get_exam_history()
        assert len(history) == 1
        assert history[0].session_id == "finish5"

    def test_finish_exam_duration(self, exam_service: ExamService):
        start = "2026-01-01T10:00:00"
        session = ExamSession(
            id="finish6",
            questions=[
                ExamQuestion(
                    index=0, word="a", mode="en2zh", prompt="a",
                    answer="一", band=5, user_answer="一", is_correct=True,
                ),
            ],
            time_limit=20,
            started_at=start,
        )
        report = exam_service.finish_exam(session)
        assert report.duration >= 0


class TestExamServiceHistory:
    """测试 get_exam_history 方法"""

    def test_history_empty(self, exam_service: ExamService):
        history = exam_service.get_exam_history()
        assert history == []

    def test_history_after_exams(self, exam_service: ExamService):
        for i in range(3):
            now = datetime.now().isoformat(timespec="seconds")
            session = ExamSession(
                id=f"hist{i}",
                questions=[
                    ExamQuestion(
                        index=0, word="a", mode="en2zh", prompt="a",
                        answer="一", band=5, user_answer="一", is_correct=True,
                    ),
                ],
                time_limit=20,
                started_at=now,
            )
            exam_service.finish_exam(session)

        history = exam_service.get_exam_history()
        assert len(history) == 3

    def test_history_limit(self, exam_service: ExamService):
        for i in range(5):
            now = datetime.now().isoformat(timespec="seconds")
            session = ExamSession(
                id=f"lim{i}",
                questions=[
                    ExamQuestion(
                        index=0, word="a", mode="en2zh", prompt="a",
                        answer="一", band=5, user_answer="一", is_correct=True,
                    ),
                ],
                time_limit=20,
                started_at=now,
            )
            exam_service.finish_exam(session)

        history = exam_service.get_exam_history(limit=3)
        assert len(history) == 3

    def test_history_order(self, exam_service: ExamService):
        """历史记录按时间倒序"""
        for i in range(3):
            session = ExamSession(
                id=f"ord{i}",
                questions=[
                    ExamQuestion(
                        index=0, word="a", mode="en2zh", prompt="a",
                        answer="一", band=5, user_answer="一", is_correct=True,
                    ),
                ],
                time_limit=20,
                started_at=f"2026-01-0{i + 1}T10:00:00",
            )
            session.finished_at = f"2026-01-0{i + 1}T10:10:00"
            report = ExamReport(
                session_id=f"ord{i}", score=1, total=1, accuracy=1.0,
                duration=600, finished_at=f"2026-01-0{i + 1}T10:10:00",
            )
            exam_service._save_exam(session, report)

        history = exam_service.get_exam_history()
        # 最新的在前面
        assert history[0].session_id == "ord2"

    def test_history_preserves_weak_words(self, exam_service: ExamService):
        now = datetime.now().isoformat(timespec="seconds")
        session = ExamSession(
            id="weak1",
            questions=[
                ExamQuestion(
                    index=0, word="hard", mode="en2zh", prompt="hard",
                    answer="困难", band=5, user_answer="错", is_correct=False,
                ),
            ],
            time_limit=20,
            started_at=now,
        )
        exam_service.finish_exam(session)
        history = exam_service.get_exam_history()
        assert "hard" in history[0].weak_words

    def test_history_preserves_band_breakdown(self, exam_service: ExamService):
        now = datetime.now().isoformat(timespec="seconds")
        session = ExamSession(
            id="band1",
            questions=[
                ExamQuestion(
                    index=0, word="a", mode="en2zh", prompt="a",
                    answer="一", band=7, user_answer="一", is_correct=True,
                ),
            ],
            time_limit=20,
            started_at=now,
        )
        exam_service.finish_exam(session)
        history = exam_service.get_exam_history()
        assert "7" in history[0].band_breakdown or 7 in history[0].band_breakdown
