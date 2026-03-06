"""测试听力服务"""

from __future__ import annotations

import json

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.listening_service import ListeningService


@pytest.fixture
def listening_service() -> ListeningService:
    return ListeningService()


@pytest.fixture
def sample_words() -> list[Word]:
    """用于听写测验的示例单词"""
    return [
        Word(word="contribute", phonetic="/kənˈtrɪbjuːt/", meaning="贡献，促成", pos="v.", band=6, topic="society"),
        Word(word="analyze", phonetic="/ˈænəlaɪz/", meaning="分析", pos="v.", band=6, topic="education"),
        Word(word="significant", phonetic="/sɪɡˈnɪfɪkənt/", meaning="重要的，显著的", pos="adj.", band=6, topic="science"),
        Word(word="evidence", phonetic="/ˈevɪdəns/", meaning="证据，证明", pos="n.", band=5, topic="education"),
        Word(word="acknowledge", phonetic="/əkˈnɒlɪdʒ/", meaning="承认；确认", pos="v.", band=7, topic="education"),
    ]


class TestGetResources:
    """测试获取听力资源"""

    def test_get_all_resources(self, listening_service: ListeningService):
        items = listening_service.get_resources()
        assert len(items) >= 30
        # 每个资源都有必要字段
        for item in items:
            assert "title" in item
            assert "type" in item
            assert "url" in item
            assert "difficulty" in item
            assert "description" in item
            assert "free" in item

    def test_filter_by_type_podcast(self, listening_service: ListeningService):
        items = listening_service.get_resources(type="podcast")
        assert len(items) > 0
        for item in items:
            assert item["type"] == "podcast"

    def test_filter_by_type_video(self, listening_service: ListeningService):
        items = listening_service.get_resources(type="video")
        assert len(items) > 0
        for item in items:
            assert item["type"] == "video"

    def test_filter_by_type_course(self, listening_service: ListeningService):
        items = listening_service.get_resources(type="course")
        assert len(items) > 0
        for item in items:
            assert item["type"] == "course"

    def test_filter_by_type_website(self, listening_service: ListeningService):
        items = listening_service.get_resources(type="website")
        assert len(items) > 0
        for item in items:
            assert item["type"] == "website"

    def test_filter_by_difficulty_beginner(self, listening_service: ListeningService):
        items = listening_service.get_resources(difficulty="beginner")
        assert len(items) > 0
        for item in items:
            assert item["difficulty"] == "beginner"

    def test_filter_by_difficulty_intermediate(self, listening_service: ListeningService):
        items = listening_service.get_resources(difficulty="intermediate")
        assert len(items) > 0
        for item in items:
            assert item["difficulty"] == "intermediate"

    def test_filter_by_difficulty_advanced(self, listening_service: ListeningService):
        items = listening_service.get_resources(difficulty="advanced")
        assert len(items) > 0
        for item in items:
            assert item["difficulty"] == "advanced"

    def test_filter_by_type_and_difficulty(self, listening_service: ListeningService):
        items = listening_service.get_resources(type="podcast", difficulty="intermediate")
        assert len(items) > 0
        for item in items:
            assert item["type"] == "podcast"
            assert item["difficulty"] == "intermediate"

    def test_filter_no_match(self, listening_service: ListeningService):
        """类型大小写不敏感"""
        items = listening_service.get_resources(type="PODCAST")
        # 转小写后应匹配
        assert len(items) > 0


class TestGetResourceDetail:
    """测试获取资源详情"""

    def test_valid_index(self, listening_service: ListeningService):
        detail = listening_service.get_resource_detail(1)
        assert detail is not None
        assert "title" in detail
        assert "url" in detail

    def test_last_index(self, listening_service: ListeningService):
        all_items = listening_service.get_resources()
        detail = listening_service.get_resource_detail(len(all_items))
        assert detail is not None

    def test_index_zero(self, listening_service: ListeningService):
        detail = listening_service.get_resource_detail(0)
        assert detail is None

    def test_index_negative(self, listening_service: ListeningService):
        detail = listening_service.get_resource_detail(-1)
        assert detail is None

    def test_index_overflow(self, listening_service: ListeningService):
        detail = listening_service.get_resource_detail(9999)
        assert detail is None


class TestGenerateDictation:
    """测试生成听写测验"""

    def test_basic_dictation(self, listening_service: ListeningService, sample_words: list[Word]):
        result = listening_service.generate_dictation(sample_words, count=3)
        assert len(result) == 3
        for item in result:
            assert "word" in item
            assert "phonetic" in item
            assert "definition" in item

    def test_dictation_count_exceeds_pool(self, listening_service: ListeningService, sample_words: list[Word]):
        result = listening_service.generate_dictation(sample_words, count=100)
        assert len(result) == len(sample_words)

    def test_dictation_empty_words(self, listening_service: ListeningService):
        result = listening_service.generate_dictation([], count=5)
        assert result == []

    def test_dictation_single_word(self, listening_service: ListeningService, sample_words: list[Word]):
        result = listening_service.generate_dictation(sample_words[:1], count=1)
        assert len(result) == 1
        assert result[0]["word"] == sample_words[0].word

    def test_dictation_fields_match_word(self, listening_service: ListeningService, sample_words: list[Word]):
        # 只用一个词，确保字段一一对应
        word = sample_words[0]
        result = listening_service.generate_dictation([word], count=1)
        assert result[0]["word"] == word.word
        assert result[0]["phonetic"] == word.phonetic
        assert result[0]["definition"] == word.meaning
