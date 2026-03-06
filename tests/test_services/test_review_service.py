"""测试复习服务和学习记录持久化"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from ielts_buddy.core.models import LearningRecord, Word
from ielts_buddy.services.review_service import (
    REVIEW_INTERVALS,
    ReviewService,
    _next_review_date,
)


class TestNextReviewDate:
    """测试复习日期计算"""

    def test_level_0(self):
        result = _next_review_date("2026-03-06", 0)
        assert result == "2026-03-06"  # interval=0, 当天

    def test_level_1(self):
        result = _next_review_date("2026-03-06", 1)
        assert result == "2026-03-07"  # interval=1

    def test_level_2(self):
        result = _next_review_date("2026-03-06", 2)
        assert result == "2026-03-08"  # interval=2

    def test_level_3(self):
        result = _next_review_date("2026-03-06", 3)
        assert result == "2026-03-10"  # interval=4

    def test_level_4(self):
        result = _next_review_date("2026-03-06", 4)
        assert result == "2026-03-13"  # interval=7

    def test_level_5(self):
        result = _next_review_date("2026-03-06", 5)
        assert result == "2026-03-21"  # interval=15

    def test_level_6(self):
        result = _next_review_date("2026-03-06", 6)
        assert result == "2026-04-05"  # interval=30

    def test_level_exceeds_max(self):
        result = _next_review_date("2026-03-06", 10)
        # Should clamp to max level (6), interval=30
        assert result == "2026-04-05"

    def test_all_intervals_match(self):
        base = "2026-01-01"
        base_date = date.fromisoformat(base)
        for level, interval in enumerate(REVIEW_INTERVALS):
            result = _next_review_date(base, level)
            expected = (base_date + timedelta(days=interval)).isoformat()
            assert result == expected, f"Level {level}: expected {expected}, got {result}"


class TestReviewServiceRecordLearn:
    """测试学习记录"""

    def test_first_learn_correct(self, review_service: ReviewService, sample_word: Word):
        rec = review_service.record_learn(sample_word, correct=True)
        assert rec.memory_level == 1
        assert rec.learn_count == 1
        assert rec.correct_count == 1
        assert rec.wrong_count == 0
        assert rec.first_learned is not None
        assert rec.last_reviewed is not None

    def test_first_learn_wrong(self, review_service: ReviewService, sample_word: Word):
        rec = review_service.record_learn(sample_word, correct=False)
        assert rec.memory_level == 0
        assert rec.learn_count == 1
        assert rec.correct_count == 0
        assert rec.wrong_count == 1

    def test_subsequent_learn_correct(self, review_service: ReviewService, sample_word: Word):
        review_service.record_learn(sample_word, correct=True)
        rec = review_service.record_learn(sample_word, correct=True)
        assert rec.memory_level == 2
        assert rec.learn_count == 2
        assert rec.correct_count == 2

    def test_subsequent_learn_wrong_decrements(self, review_service: ReviewService, sample_word: Word):
        review_service.record_learn(sample_word, correct=True)  # level 1
        review_service.record_learn(sample_word, correct=True)  # level 2
        rec = review_service.record_learn(sample_word, correct=False)  # level 1
        assert rec.memory_level == 1

    def test_level_does_not_go_below_zero(self, review_service: ReviewService, sample_word: Word):
        review_service.record_learn(sample_word, correct=False)  # level 0
        rec = review_service.record_learn(sample_word, correct=False)  # still 0
        assert rec.memory_level == 0

    def test_level_caps_at_max(self, review_service: ReviewService, sample_word: Word):
        max_level = len(REVIEW_INTERVALS) - 1
        # Learn correctly many times
        for _ in range(max_level + 5):
            rec = review_service.record_learn(sample_word, correct=True)
        assert rec.memory_level == max_level

    def test_multiple_words(self, review_service: ReviewService, sample_words: list[Word]):
        for w in sample_words:
            review_service.record_learn(w, correct=True)
        assert review_service.get_learned_count() == len(sample_words)


class TestReviewServiceDueWords:
    """测试到期复习"""

    def test_no_due_words_initially(self, review_service: ReviewService):
        due = review_service.get_due_words()
        assert due == []
        assert review_service.get_due_count() == 0

    def test_due_words_after_learn(self, review_service: ReviewService, sample_word: Word):
        review_service.record_learn(sample_word, correct=False)
        # level 0 => interval 0 => due today
        due = review_service.get_due_words()
        assert len(due) >= 1
        assert due[0]["word"] == sample_word.word

    def test_due_words_limit(self, review_service: ReviewService, sample_words: list[Word]):
        for w in sample_words:
            review_service.record_learn(w, correct=False)
        due = review_service.get_due_words(limit=2)
        assert len(due) == 2

    def test_due_words_word_data_integrity(self, review_service: ReviewService, sample_word: Word):
        review_service.record_learn(sample_word, correct=False)
        due = review_service.get_due_words()
        assert len(due) == 1
        word_data = due[0]["word_data"]
        assert isinstance(word_data, Word)
        assert word_data.word == sample_word.word
        assert word_data.meaning == sample_word.meaning


class TestReviewServiceQuery:
    """测试查询功能"""

    def test_get_all_records_empty(self, review_service: ReviewService):
        records = review_service.get_all_records()
        assert records == []

    def test_get_all_records(self, review_service: ReviewService, sample_words: list[Word]):
        for w in sample_words:
            review_service.record_learn(w, correct=True)
        records = review_service.get_all_records()
        assert len(records) == len(sample_words)
        assert all(isinstance(r, LearningRecord) for r in records)

    def test_get_learned_count(self, review_service: ReviewService, sample_words: list[Word]):
        assert review_service.get_learned_count() == 0
        for w in sample_words:
            review_service.record_learn(w, correct=True)
        assert review_service.get_learned_count() == len(sample_words)


class TestReviewServiceStar:
    """测试星标功能"""

    def test_toggle_star_on(self, review_service: ReviewService, sample_word: Word):
        review_service.record_learn(sample_word, correct=True)
        state = review_service.toggle_star(sample_word.word)
        assert state is True

    def test_toggle_star_off(self, review_service: ReviewService, sample_word: Word):
        review_service.record_learn(sample_word, correct=True)
        review_service.toggle_star(sample_word.word)  # on
        state = review_service.toggle_star(sample_word.word)  # off
        assert state is False

    def test_toggle_star_nonexistent(self, review_service: ReviewService):
        with pytest.raises(ValueError, match="未找到单词"):
            review_service.toggle_star("nonexistent_word")


class TestReviewServicePersistence:
    """测试数据持久化"""

    def test_data_persists_across_instances(self, tmp_db: Path, sample_word: Word):
        # First instance: record learning
        svc1 = ReviewService(db_path=tmp_db)
        svc1.record_learn(sample_word, correct=True)
        svc1.close()

        # Second instance: verify data
        svc2 = ReviewService(db_path=tmp_db)
        count = svc2.get_learned_count()
        svc2.close()
        assert count == 1

    def test_records_persist_correctly(self, tmp_db: Path, sample_word: Word):
        svc1 = ReviewService(db_path=tmp_db)
        svc1.record_learn(sample_word, correct=True)
        svc1.record_learn(sample_word, correct=True)
        svc1.close()

        svc2 = ReviewService(db_path=tmp_db)
        records = svc2.get_all_records()
        svc2.close()

        assert len(records) == 1
        assert records[0].memory_level == 2
        assert records[0].learn_count == 2
        assert records[0].correct_count == 2

    def test_star_persists(self, tmp_db: Path, sample_word: Word):
        svc1 = ReviewService(db_path=tmp_db)
        svc1.record_learn(sample_word, correct=True)
        svc1.toggle_star(sample_word.word)
        svc1.close()

        svc2 = ReviewService(db_path=tmp_db)
        records = svc2.get_all_records()
        svc2.close()
        assert records[0].is_starred is True
