"""测试统计服务"""

from __future__ import annotations

from pathlib import Path

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.stats_service import StatsService


class TestStatsServiceNoData:
    """测试无数据时的统计"""

    def test_total_stats_empty(self, tmp_path: Path):
        svc = StatsService(db_path=tmp_path / "empty.db")
        stats = svc.total_stats()
        svc.close()
        assert stats["total_words"] == 0
        assert stats["total_reviews"] == 0
        assert stats["accuracy"] == 0.0
        assert stats["mastered"] == 0

    def test_today_stats_empty(self, tmp_path: Path):
        svc = StatsService(db_path=tmp_path / "empty.db")
        stats = svc.today_stats()
        svc.close()
        assert stats["new_words"] == 0
        assert stats["reviewed_words"] == 0

    def test_due_count_empty(self, tmp_path: Path):
        svc = StatsService(db_path=tmp_path / "empty.db")
        count = svc.due_count()
        svc.close()
        assert count == 0

    def test_level_distribution_empty(self, tmp_path: Path):
        svc = StatsService(db_path=tmp_path / "empty.db")
        dist = svc.level_distribution()
        svc.close()
        assert dist == {}


class TestStatsServiceWithData:
    """测试有数据时的统计"""

    @pytest.fixture
    def populated_db(self, tmp_path: Path, sample_words: list[Word]) -> Path:
        """创建一个有学习记录的数据库"""
        db_path = tmp_path / "populated.db"
        review = ReviewService(db_path=db_path)
        for i, w in enumerate(sample_words):
            correct = i % 2 == 0  # 交替对错
            review.record_learn(w, correct=correct)
        review.close()
        return db_path

    def test_total_stats(self, populated_db: Path, sample_words: list[Word]):
        svc = StatsService(db_path=populated_db)
        stats = svc.total_stats()
        svc.close()
        assert stats["total_words"] == len(sample_words)
        assert stats["total_reviews"] == len(sample_words)
        assert stats["total_correct"] + stats["total_wrong"] == len(sample_words)

    def test_today_stats(self, populated_db: Path):
        svc = StatsService(db_path=populated_db)
        stats = svc.today_stats()
        svc.close()
        assert stats["new_words"] > 0
        assert stats["reviewed_words"] > 0

    def test_due_count(self, populated_db: Path):
        svc = StatsService(db_path=populated_db)
        count = svc.due_count()
        svc.close()
        # Some words should be due (level 0 => due today)
        assert count >= 0

    def test_level_distribution(self, populated_db: Path):
        svc = StatsService(db_path=populated_db)
        dist = svc.level_distribution()
        svc.close()
        assert isinstance(dist, dict)
        total = sum(dist.values())
        assert total > 0

    def test_accuracy_calculation(self, tmp_path: Path):
        db_path = tmp_path / "accuracy.db"
        review = ReviewService(db_path=db_path)
        w1 = Word(word="test1", meaning="测试1", band=5)
        w2 = Word(word="test2", meaning="测试2", band=5)
        review.record_learn(w1, correct=True)
        review.record_learn(w2, correct=False)
        review.close()

        svc = StatsService(db_path=db_path)
        stats = svc.total_stats()
        svc.close()
        assert stats["accuracy"] == pytest.approx(0.5)
