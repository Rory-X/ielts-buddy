"""测试智能学习推荐服务"""

from __future__ import annotations

from pathlib import Path

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.recommend_service import RecommendService, _estimate_reviews
from ielts_buddy.services.review_service import ReviewService


@pytest.fixture
def recommend_service(tmp_db: Path) -> RecommendService:
    """创建使用临时数据库的 RecommendService"""
    svc = RecommendService(db_path=tmp_db)
    yield svc
    svc.close()


def _seed_learning_data(db_path: Path, words: list[Word], patterns: list[bool]) -> None:
    """向数据库填充学习记录

    patterns: 每个词对应的 correct 值
    """
    review_svc = ReviewService(db_path=db_path)
    for word, correct in zip(words, patterns):
        review_svc.record_learn(word, correct=correct)
    review_svc.close()


class TestGetWeakWords:
    """测试薄弱词获取"""

    def test_empty_db(self, recommend_service: RecommendService):
        result = recommend_service.get_weak_words()
        assert result == []

    def test_no_errors_returns_empty(self, tmp_db: Path, sample_words: list[Word]):
        # 全部答对，不应有薄弱词
        _seed_learning_data(tmp_db, sample_words, [True] * len(sample_words))
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_weak_words()
        svc.close()
        assert result == []

    def test_returns_wrong_words(self, tmp_db: Path, sample_words: list[Word]):
        # 部分答错
        _seed_learning_data(tmp_db, sample_words, [False, True, False, True, False])
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_weak_words()
        svc.close()
        assert len(result) == 3
        # 错误率为 100%
        for w in result:
            assert w["error_rate"] == 1.0
            assert w["wrong_count"] > 0

    def test_limit(self, tmp_db: Path, sample_words: list[Word]):
        _seed_learning_data(tmp_db, sample_words, [False] * len(sample_words))
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_weak_words(limit=2)
        svc.close()
        assert len(result) == 2

    def test_result_structure(self, tmp_db: Path, sample_word: Word):
        _seed_learning_data(tmp_db, [sample_word], [False])
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_weak_words()
        svc.close()
        assert len(result) == 1
        w = result[0]
        assert "word" in w
        assert "meaning" in w
        assert "band" in w
        assert "learn_count" in w
        assert "correct_count" in w
        assert "wrong_count" in w
        assert "error_rate" in w


class TestGetDueWords:
    """测试到期词获取"""

    def test_empty_db(self, recommend_service: RecommendService):
        result = recommend_service.get_due_words()
        assert result == []

    def test_due_after_wrong(self, tmp_db: Path, sample_word: Word):
        # level 0 => interval 0 => due today
        _seed_learning_data(tmp_db, [sample_word], [False])
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_due_words()
        svc.close()
        assert len(result) >= 1
        assert result[0]["word"] == sample_word.word

    def test_due_word_structure(self, tmp_db: Path, sample_word: Word):
        _seed_learning_data(tmp_db, [sample_word], [False])
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_due_words()
        svc.close()
        assert len(result) == 1
        w = result[0]
        assert "word" in w
        assert "meaning" in w
        assert "band" in w
        assert "memory_level" in w
        assert "next_review" in w
        assert "overdue_days" in w

    def test_limit(self, tmp_db: Path, sample_words: list[Word]):
        _seed_learning_data(tmp_db, sample_words, [False] * len(sample_words))
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_due_words(limit=2)
        svc.close()
        assert len(result) == 2


class TestGetRecommendedNew:
    """测试新词推荐"""

    def test_returns_new_words(self, recommend_service: RecommendService):
        result = recommend_service.get_recommended_new(count=5)
        assert len(result) == 5
        for w in result:
            assert "word" in w
            assert "meaning" in w
            assert "band" in w

    def test_excludes_learned(self, tmp_db: Path, sample_words: list[Word]):
        _seed_learning_data(tmp_db, sample_words, [True] * len(sample_words))
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_recommended_new(count=10)
        svc.close()
        learned_set = {w.word for w in sample_words}
        for w in result:
            assert w["word"] not in learned_set

    def test_filter_by_band(self, recommend_service: RecommendService):
        result = recommend_service.get_recommended_new(band=5, count=5)
        assert len(result) > 0
        for w in result:
            assert w["band"] == 5

    def test_count_respected(self, recommend_service: RecommendService):
        result = recommend_service.get_recommended_new(count=3)
        assert len(result) == 3


class TestPredictMastery:
    """测试掌握率预测"""

    def test_empty_db(self, recommend_service: RecommendService):
        result = recommend_service.predict_mastery()
        assert result["current_mastery"] == 0.0
        assert result["predicted_mastery"] == 0.0
        assert result["total_words"] == 0

    def test_with_data(self, tmp_db: Path, sample_words: list[Word]):
        _seed_learning_data(tmp_db, sample_words, [True] * len(sample_words))
        svc = RecommendService(db_path=tmp_db)
        result = svc.predict_mastery(days=7)
        svc.close()
        assert result["total_words"] == len(sample_words)
        assert 0.0 <= result["current_mastery"] <= 1.0
        assert 0.0 <= result["predicted_mastery"] <= 1.0

    def test_result_structure(self, tmp_db: Path, sample_word: Word):
        _seed_learning_data(tmp_db, [sample_word], [True])
        svc = RecommendService(db_path=tmp_db)
        result = svc.predict_mastery()
        svc.close()
        assert "current_mastery" in result
        assert "predicted_mastery" in result
        assert "total_words" in result
        assert "mastered_now" in result
        assert "predicted_mastered" in result


class TestGetStudySuggestion:
    """测试综合学习建议"""

    def test_empty_db(self, recommend_service: RecommendService):
        result = recommend_service.get_study_suggestion()
        assert result["weak_count"] == 0
        assert result["due_count"] == 0
        assert result["suggested_new"] == 15  # 无薄弱词，建议多学
        assert "message" in result

    def test_with_weak_words(self, tmp_db: Path, sample_words: list[Word]):
        _seed_learning_data(tmp_db, sample_words, [False] * len(sample_words))
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_study_suggestion()
        svc.close()
        assert result["weak_count"] == len(sample_words)
        assert result["due_count"] >= 0
        assert "message" in result
        assert result["priority_band"] > 0

    def test_suggestion_structure(self, recommend_service: RecommendService):
        result = recommend_service.get_study_suggestion()
        assert "weak_count" in result
        assert "due_count" in result
        assert "suggested_new" in result
        assert "priority_band" in result
        assert "message" in result

    def test_suggested_new_decreases_with_many_weak(self, tmp_db: Path):
        # 创建 >10 个薄弱词
        words = [
            Word(word=f"testword{i}", meaning=f"测试词{i}", band=5, topic="test")
            for i in range(15)
        ]
        _seed_learning_data(tmp_db, words, [False] * 15)
        svc = RecommendService(db_path=tmp_db)
        result = svc.get_study_suggestion()
        svc.close()
        assert result["suggested_new"] == 5


class TestEstimateReviews:
    """测试复习次数估算"""

    def test_level_0_in_7_days(self):
        reviews = _estimate_reviews(0, 7)
        # level 0: interval 0 -> review -> level 1: interval 1 -> review -> level 2: interval 2 -> review -> level 3: interval 4 -> total 0+1+2+4=7
        assert reviews >= 3

    def test_high_level_few_reviews(self):
        reviews = _estimate_reviews(5, 7)
        # level 5: interval 15 days, so 0 reviews in 7 days
        assert reviews == 0

    def test_zero_days(self):
        reviews = _estimate_reviews(0, 0)
        assert reviews == 0
