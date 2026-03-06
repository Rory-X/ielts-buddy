"""测试写作辅助服务 WritingService"""

from __future__ import annotations

import pytest

from ielts_buddy.services.writing_service import WritingService


@pytest.fixture
def writing_service() -> WritingService:
    return WritingService()


class TestGetTopics:
    """测试 get_topics"""

    def test_get_all_topics(self, writing_service: WritingService):
        topics = writing_service.get_topics()
        assert len(topics) >= 40
        for t in topics:
            assert "topic" in t
            assert "question" in t
            assert "category" in t
            assert "keywords" in t
            assert "band7_vocab" in t

    def test_get_topics_by_category(self, writing_service: WritingService):
        topics = writing_service.get_topics(category="education")
        assert len(topics) >= 1
        for t in topics:
            assert t["category"] == "education"

    def test_get_topics_category_case_insensitive(self, writing_service: WritingService):
        topics_lower = writing_service.get_topics(category="education")
        topics_upper = writing_service.get_topics(category="EDUCATION")
        assert len(topics_lower) == len(topics_upper)

    def test_get_topics_nonexistent_category(self, writing_service: WritingService):
        topics = writing_service.get_topics(category="nonexistent")
        assert topics == []

    def test_all_categories_present(self, writing_service: WritingService):
        categories = writing_service.get_categories()
        expected = {"education", "environment", "technology", "health", "society", "culture", "economy"}
        assert expected == set(categories)

    def test_topics_have_keywords(self, writing_service: WritingService):
        topics = writing_service.get_topics()
        for t in topics:
            assert isinstance(t["keywords"], list)
            assert len(t["keywords"]) >= 1

    def test_topics_have_band7_vocab(self, writing_service: WritingService):
        topics = writing_service.get_topics()
        for t in topics:
            assert isinstance(t["band7_vocab"], list)
            assert len(t["band7_vocab"]) >= 1


class TestGetTopicDetail:
    """测试 get_topic_detail"""

    def test_valid_topic_id(self, writing_service: WritingService):
        detail = writing_service.get_topic_detail(1)
        assert detail is not None
        assert "topic" in detail
        assert "question" in detail

    def test_last_topic_id(self, writing_service: WritingService):
        all_topics = writing_service.get_topics()
        detail = writing_service.get_topic_detail(len(all_topics))
        assert detail is not None

    def test_invalid_topic_id_zero(self, writing_service: WritingService):
        assert writing_service.get_topic_detail(0) is None

    def test_invalid_topic_id_negative(self, writing_service: WritingService):
        assert writing_service.get_topic_detail(-1) is None

    def test_invalid_topic_id_too_large(self, writing_service: WritingService):
        assert writing_service.get_topic_detail(9999) is None


class TestGetTemplates:
    """测试 get_templates"""

    def test_get_all_templates(self, writing_service: WritingService):
        templates = writing_service.get_templates()
        assert len(templates) >= 30
        for t in templates:
            assert "type" in t
            assert "template" in t
            assert "translation" in t
            assert "example" in t

    def test_get_templates_by_type(self, writing_service: WritingService):
        for ttype in ["introduction", "body", "conclusion", "transition"]:
            templates = writing_service.get_templates(type=ttype)
            assert len(templates) >= 1
            for t in templates:
                assert t["type"] == ttype

    def test_get_templates_type_case_insensitive(self, writing_service: WritingService):
        t_lower = writing_service.get_templates(type="introduction")
        t_upper = writing_service.get_templates(type="INTRODUCTION")
        assert len(t_lower) == len(t_upper)

    def test_get_templates_nonexistent_type(self, writing_service: WritingService):
        assert writing_service.get_templates(type="nonexistent") == []

    def test_template_types(self, writing_service: WritingService):
        types = writing_service.get_template_types()
        expected = {"introduction", "body", "conclusion", "transition"}
        assert expected == set(types)


class TestGetSynonyms:
    """测试 get_synonyms"""

    def test_get_all_synonyms(self, writing_service: WritingService):
        synonyms = writing_service.get_synonyms()
        assert len(synonyms) >= 50
        for s in synonyms:
            assert "common" in s
            assert "synonyms" in s
            assert "context" in s

    def test_get_synonyms_by_word(self, writing_service: WritingService):
        results = writing_service.get_synonyms("important")
        assert len(results) >= 1
        assert any(r["common"] == "important" for r in results)

    def test_get_synonyms_case_insensitive(self, writing_service: WritingService):
        r_lower = writing_service.get_synonyms("important")
        r_upper = writing_service.get_synonyms("IMPORTANT")
        assert len(r_lower) == len(r_upper)

    def test_get_synonyms_by_synonym_word(self, writing_service: WritingService):
        """通过同义词反向查找"""
        results = writing_service.get_synonyms("crucial")
        assert len(results) >= 1

    def test_get_synonyms_not_found(self, writing_service: WritingService):
        results = writing_service.get_synonyms("xyznonexistent")
        assert results == []

    def test_synonyms_have_multiple_entries(self, writing_service: WritingService):
        synonyms = writing_service.get_synonyms()
        for s in synonyms:
            assert isinstance(s["synonyms"], list)
            assert len(s["synonyms"]) >= 2


class TestGetWritingVocab:
    """测试 get_writing_vocab"""

    def test_vocab_by_topic_name(self, writing_service: WritingService):
        result = writing_service.get_writing_vocab("气候变化")
        assert result is not None
        assert "topic" in result
        assert "keywords" in result
        assert "band7_vocab" in result

    def test_vocab_by_partial_match(self, writing_service: WritingService):
        result = writing_service.get_writing_vocab("教育")
        assert result is not None

    def test_vocab_by_english_keyword(self, writing_service: WritingService):
        result = writing_service.get_writing_vocab("climate")
        assert result is not None

    def test_vocab_not_found(self, writing_service: WritingService):
        result = writing_service.get_writing_vocab("xyznonexistent")
        assert result is None

    def test_vocab_result_structure(self, writing_service: WritingService):
        result = writing_service.get_writing_vocab("气候")
        assert result is not None
        assert "topic" in result
        assert "question" in result
        assert "category" in result
        assert "keywords" in result
        assert "band7_vocab" in result


class TestLazyLoading:
    """测试延迟加载"""

    def test_topics_lazy_loaded(self):
        svc = WritingService()
        assert svc._topics is None
        svc.get_topics()
        assert svc._topics is not None

    def test_templates_lazy_loaded(self):
        svc = WritingService()
        assert svc._templates is None
        svc.get_templates()
        assert svc._templates is not None

    def test_synonyms_lazy_loaded(self):
        svc = WritingService()
        assert svc._synonyms is None
        svc.get_synonyms()
        assert svc._synonyms is not None

    def test_repeated_calls_use_cache(self):
        svc = WritingService()
        topics1 = svc.get_topics()
        topics2 = svc.get_topics()
        assert topics1 is topics2  # 同一个列表对象
