"""测试口语练习服务 SpeakingService"""

from __future__ import annotations

import pytest

from ielts_buddy.services.speaking_service import SpeakingService


@pytest.fixture
def speaking_service() -> SpeakingService:
    return SpeakingService()


class TestGetTopics:
    """测试 get_topics"""

    def test_get_all_topics(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics()
        assert len(topics) >= 60  # Part 1/2/3 各 20+
        for t in topics:
            assert "part" in t
            assert "topic" in t
            assert "questions" in t
            assert "vocab" in t
            assert "sample_answer" in t
            assert "tips" in t

    def test_get_topics_part1(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics(part=1)
        assert len(topics) >= 20
        for t in topics:
            assert t["part"] == 1

    def test_get_topics_part2(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics(part=2)
        assert len(topics) >= 20
        for t in topics:
            assert t["part"] == 2

    def test_get_topics_part3(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics(part=3)
        assert len(topics) >= 20
        for t in topics:
            assert t["part"] == 3

    def test_get_topics_nonexistent_part(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics(part=99)
        assert topics == []

    def test_topics_have_questions(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics()
        for t in topics:
            assert isinstance(t["questions"], list)
            assert len(t["questions"]) >= 1

    def test_topics_have_vocab(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics()
        for t in topics:
            assert isinstance(t["vocab"], list)
            assert len(t["vocab"]) >= 1

    def test_topics_have_sample_answer(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics()
        for t in topics:
            assert isinstance(t["sample_answer"], str)
            assert len(t["sample_answer"]) > 0

    def test_topics_have_tips(self, speaking_service: SpeakingService):
        topics = speaking_service.get_topics()
        for t in topics:
            assert isinstance(t["tips"], str)
            assert len(t["tips"]) > 0


class TestGetTopicDetail:
    """测试 get_topic_detail"""

    def test_valid_topic_id(self, speaking_service: SpeakingService):
        detail = speaking_service.get_topic_detail(1)
        assert detail is not None
        assert "topic" in detail
        assert "part" in detail

    def test_last_topic_id(self, speaking_service: SpeakingService):
        all_topics = speaking_service.get_topics()
        detail = speaking_service.get_topic_detail(len(all_topics))
        assert detail is not None

    def test_invalid_topic_id_zero(self, speaking_service: SpeakingService):
        assert speaking_service.get_topic_detail(0) is None

    def test_invalid_topic_id_negative(self, speaking_service: SpeakingService):
        assert speaking_service.get_topic_detail(-1) is None

    def test_invalid_topic_id_too_large(self, speaking_service: SpeakingService):
        assert speaking_service.get_topic_detail(9999) is None


class TestGetRandomTopic:
    """测试 get_random_topic"""

    def test_random_topic_all(self, speaking_service: SpeakingService):
        topic = speaking_service.get_random_topic()
        assert topic is not None
        assert "part" in topic
        assert "topic" in topic

    def test_random_topic_part1(self, speaking_service: SpeakingService):
        topic = speaking_service.get_random_topic(part=1)
        assert topic is not None
        assert topic["part"] == 1

    def test_random_topic_part2(self, speaking_service: SpeakingService):
        topic = speaking_service.get_random_topic(part=2)
        assert topic is not None
        assert topic["part"] == 2

    def test_random_topic_part3(self, speaking_service: SpeakingService):
        topic = speaking_service.get_random_topic(part=3)
        assert topic is not None
        assert topic["part"] == 3

    def test_random_topic_nonexistent_part(self, speaking_service: SpeakingService):
        assert speaking_service.get_random_topic(part=99) is None

    def test_random_topic_is_random(self, speaking_service: SpeakingService):
        """多次抽取应该不全相同（概率性测试）"""
        results = {speaking_service.get_random_topic()["topic"] for _ in range(20)}
        assert len(results) > 1


class TestGetSpeakingVocab:
    """测试 get_speaking_vocab"""

    def test_vocab_by_topic_name(self, speaking_service: SpeakingService):
        result = speaking_service.get_speaking_vocab("Hometown")
        assert result is not None
        assert "topic" in result
        assert "vocab" in result
        assert "questions" in result

    def test_vocab_case_insensitive(self, speaking_service: SpeakingService):
        result = speaking_service.get_speaking_vocab("hometown")
        assert result is not None

    def test_vocab_partial_match(self, speaking_service: SpeakingService):
        result = speaking_service.get_speaking_vocab("Work")
        assert result is not None

    def test_vocab_not_found(self, speaking_service: SpeakingService):
        result = speaking_service.get_speaking_vocab("xyznonexistent")
        assert result is None

    def test_vocab_result_structure(self, speaking_service: SpeakingService):
        result = speaking_service.get_speaking_vocab("Hometown")
        assert result is not None
        assert "part" in result
        assert "topic" in result
        assert "vocab" in result
        assert "questions" in result
        assert isinstance(result["vocab"], list)
        assert isinstance(result["questions"], list)


class TestGetParts:
    """测试 get_parts"""

    def test_all_parts_present(self, speaking_service: SpeakingService):
        parts = speaking_service.get_parts()
        assert parts == [1, 2, 3]


class TestCount:
    """测试 count"""

    def test_count_all(self, speaking_service: SpeakingService):
        assert speaking_service.count() >= 60

    def test_count_part1(self, speaking_service: SpeakingService):
        assert speaking_service.count(part=1) >= 20

    def test_count_part2(self, speaking_service: SpeakingService):
        assert speaking_service.count(part=2) >= 20

    def test_count_part3(self, speaking_service: SpeakingService):
        assert speaking_service.count(part=3) >= 20

    def test_count_nonexistent_part(self, speaking_service: SpeakingService):
        assert speaking_service.count(part=99) == 0


class TestLazyLoading:
    """测试延迟加载"""

    def test_topics_lazy_loaded(self):
        svc = SpeakingService()
        assert svc._topics is None
        svc.get_topics()
        assert svc._topics is not None

    def test_repeated_calls_use_cache(self):
        svc = SpeakingService()
        topics1 = svc.get_topics()
        topics2 = svc.get_topics()
        assert topics1 is topics2  # 同一个列表对象
