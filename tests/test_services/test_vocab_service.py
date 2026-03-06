"""测试词库服务"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.vocab_service import VocabService


class TestVocabServiceLoad:
    """测试词库加载"""

    def test_load_band5(self, vocab_service: VocabService):
        vocab_service.load_band(5)
        assert vocab_service.count(5) > 0
        assert 5 in vocab_service.get_bands()

    def test_load_band6(self, vocab_service: VocabService):
        vocab_service.load_band(6)
        assert vocab_service.count(6) > 0

    def test_load_band7(self, vocab_service: VocabService):
        vocab_service.load_band(7)
        assert vocab_service.count(7) > 0

    def test_load_band8(self, vocab_service: VocabService):
        vocab_service.load_band(8)
        assert vocab_service.count(8) > 0

    def test_load_band9(self, vocab_service: VocabService):
        vocab_service.load_band(9)
        assert vocab_service.count(9) > 0

    def test_load_all(self, vocab_service: VocabService):
        vocab_service.load_all()
        assert vocab_service.count() > 0
        assert set(vocab_service.get_bands()) == {5, 6, 7, 8, 9}

    def test_load_band_idempotent(self, vocab_service: VocabService):
        vocab_service.load_band(5)
        count1 = vocab_service.count()
        vocab_service.load_band(5)
        count2 = vocab_service.count()
        assert count1 == count2

    def test_load_unsupported_band(self, vocab_service: VocabService):
        with pytest.raises(ValueError, match="不支持的 band 等级"):
            vocab_service.load_band(4)

    def test_load_custom(self, vocab_service: VocabService, custom_vocab_file: Path):
        vocab_service.load_custom(custom_vocab_file)
        words = vocab_service.words
        custom = [w for w in words if w.is_custom]
        assert len(custom) == 2
        assert custom[0].word == "custom_word_1"

    def test_load_custom_nonexistent(self, vocab_service: VocabService, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            vocab_service.load_custom(tmp_path / "nonexistent.json")


class TestVocabServiceFilter:
    """测试词库筛选"""

    def test_filter_by_band(self, vocab_service: VocabService):
        vocab_service.load_all()
        band5 = vocab_service.filter_by_band(5)
        assert all(w.band == 5 for w in band5)
        assert len(band5) > 0

    def test_filter_by_band_empty(self, vocab_service: VocabService):
        vocab_service.load_all()
        result = vocab_service.filter_by_band(4)
        assert result == []

    def test_filter_by_topic(self, vocab_service: VocabService):
        vocab_service.load_all()
        education = vocab_service.filter_by_topic("education")
        assert all(w.topic.lower() == "education" for w in education)
        assert len(education) > 0

    def test_filter_by_topic_case_insensitive(self, vocab_service: VocabService):
        vocab_service.load_all()
        r1 = vocab_service.filter_by_topic("Education")
        r2 = vocab_service.filter_by_topic("education")
        assert len(r1) == len(r2)

    def test_filter_by_topic_nonexistent(self, vocab_service: VocabService):
        vocab_service.load_all()
        result = vocab_service.filter_by_topic("nonexistent_topic")
        assert result == []


class TestVocabServiceSearch:
    """测试搜索功能"""

    def test_search_by_english(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search("important")
        assert any(w.word == "important" for w in results)

    def test_search_by_chinese(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search("重要")
        assert len(results) > 0

    def test_search_partial(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search("environ")
        assert any("environ" in w.word.lower() for w in results)

    def test_search_case_insensitive(self, vocab_service: VocabService):
        vocab_service.load_all()
        r1 = vocab_service.search("Important")
        r2 = vocab_service.search("important")
        assert len(r1) == len(r2)

    def test_search_no_results(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search("zzzzzznonexistent")
        assert results == []


class TestVocabServiceRandom:
    """测试随机抽词"""

    def test_random_words(self, vocab_service: VocabService):
        vocab_service.load_all()
        words = vocab_service.random_words(5)
        assert len(words) == 5
        assert all(isinstance(w, Word) for w in words)

    def test_random_words_with_band(self, vocab_service: VocabService):
        vocab_service.load_all()
        words = vocab_service.random_words(3, band=6)
        assert len(words) == 3
        assert all(w.band == 6 for w in words)

    def test_random_words_count_exceeds_pool(self, vocab_service: VocabService):
        vocab_service.load_band(5)
        total = vocab_service.count(5)
        words = vocab_service.random_words(total + 100, band=5)
        assert len(words) == total

    def test_random_words_zero(self, vocab_service: VocabService):
        vocab_service.load_all()
        words = vocab_service.random_words(0)
        assert words == []

    def test_random_words_empty_pool(self, vocab_service: VocabService):
        vocab_service.load_all()
        words = vocab_service.random_words(5, band=4)
        assert words == []


class TestVocabServiceTopics:
    """测试主题功能"""

    def test_get_topics(self, vocab_service: VocabService):
        vocab_service.load_all()
        topics = vocab_service.get_topics()
        assert len(topics) > 0
        assert "education" in topics
        assert topics == sorted(topics)  # 确保排序

    def test_get_topics_empty(self, vocab_service: VocabService):
        topics = vocab_service.get_topics()
        assert topics == []


class TestVocabDataIntegrity:
    """测试词库数据完整性"""

    @pytest.fixture(autouse=True)
    def _load_all(self, vocab_service: VocabService):
        vocab_service.load_all()
        self.svc = vocab_service

    def test_all_words_have_required_fields(self):
        for w in self.svc.words:
            assert w.word, f"单词缺少 word 字段"
            assert w.meaning, f"单词 {w.word} 缺少 meaning 字段"
            assert 5 <= w.band <= 9, f"单词 {w.word} 的 band={w.band} 超出范围"

    def test_no_duplicate_words_per_band(self):
        for band in [5, 6, 7, 8, 9]:
            words = self.svc.filter_by_band(band)
            word_set = {w.word for w in words}
            assert len(word_set) == len(words), (
                f"Band {band} 存在重复单词: "
                f"{[w.word for w in words if [x.word for x in words].count(w.word) > 1]}"
            )

    def test_all_words_have_topic(self):
        missing = [w.word for w in self.svc.words if not w.topic]
        assert missing == [], f"以下单词缺少 topic: {missing}"

    def test_all_words_have_pos(self):
        missing = [w.word for w in self.svc.words if not w.pos]
        assert missing == [], f"以下单词缺少 pos: {missing}"

    def test_all_words_have_example(self):
        missing = [w.word for w in self.svc.words if not w.example]
        assert missing == [], f"以下单词缺少 example: {missing}"

    def test_all_words_have_phonetic(self):
        missing = [w.word for w in self.svc.words if not w.phonetic]
        assert missing == [], f"以下单词缺少 phonetic: {missing}"

    def test_word_count_reasonable(self):
        total = self.svc.count()
        assert total >= 100, f"词库总数 {total} 少于预期"

    def test_band_distribution(self):
        for band in [5, 6, 7, 8, 9]:
            count = self.svc.count(band)
            assert count >= 20, f"Band {band} 词汇数 {count} 少于 20"

    def test_json_files_valid(self):
        """验证 JSON 文件格式正确"""
        from importlib import resources

        data_pkg = resources.files("ielts_buddy") / "data"
        for filename in [
            "vocab_band5.json", "vocab_band6.json", "vocab_band7.json",
            "vocab_band8.json", "vocab_band9.json",
        ]:
            path = Path(str(data_pkg / filename))
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list), f"{filename} 顶层不是列表"
            assert len(data) > 0, f"{filename} 为空"
            for item in data:
                assert "word" in item, f"{filename} 中有词条缺少 word 字段"
                assert "meaning" in item, f"{filename} 中有词条缺少 meaning 字段"


class TestSearchWords:
    """测试 search_words 方法"""

    def test_search_words_by_english(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search_words("important")
        assert any(w.word == "important" for w in results)

    def test_search_words_by_topic(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search_words("education")
        assert len(results) > 0
        assert any(w.topic == "education" for w in results)

    def test_search_words_by_chinese(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search_words("分析")
        assert len(results) > 0

    def test_search_words_no_results(self, vocab_service: VocabService):
        vocab_service.load_all()
        results = vocab_service.search_words("xyznonexistent")
        assert results == []


class TestListWords:
    """测试 list_words 分页列表"""

    def test_list_all(self, vocab_service: VocabService):
        vocab_service.load_all()
        words, total = vocab_service.list_words()
        assert len(words) <= 20
        assert total == vocab_service.count()

    def test_list_by_band(self, vocab_service: VocabService):
        vocab_service.load_all()
        words, total = vocab_service.list_words(band=5)
        assert all(w.band == 5 for w in words)
        assert total == vocab_service.count(5)

    def test_list_by_topic(self, vocab_service: VocabService):
        vocab_service.load_all()
        words, total = vocab_service.list_words(topic="education")
        assert all(w.topic.lower() == "education" for w in words)
        assert total > 0

    def test_list_by_band_and_topic(self, vocab_service: VocabService):
        vocab_service.load_all()
        words, total = vocab_service.list_words(band=5, topic="education")
        assert all(w.band == 5 and w.topic.lower() == "education" for w in words)

    def test_list_pagination(self, vocab_service: VocabService):
        vocab_service.load_all()
        page1, total1 = vocab_service.list_words(page=1, per_page=5)
        page2, total2 = vocab_service.list_words(page=2, per_page=5)
        assert len(page1) == 5
        assert len(page2) == 5
        assert total1 == total2
        assert page1[0].word != page2[0].word

    def test_list_last_page_partial(self, vocab_service: VocabService):
        vocab_service.load_band(5)
        total_count = vocab_service.count(5)
        per_page = total_count - 1
        words, total = vocab_service.list_words(band=5, page=2, per_page=per_page)
        assert len(words) == 1
        assert total == total_count

    def test_list_empty_result(self, vocab_service: VocabService):
        vocab_service.load_all()
        words, total = vocab_service.list_words(band=4)
        assert words == []
        assert total == 0

    def test_list_page_beyond_range(self, vocab_service: VocabService):
        vocab_service.load_all()
        words, total = vocab_service.list_words(page=9999)
        assert words == []
        assert total > 0


class TestGetVocabStats:
    """测试 get_vocab_stats 方法"""

    def test_stats_total(self, vocab_service: VocabService):
        vocab_service.load_all()
        stats = vocab_service.get_vocab_stats()
        assert stats["total"] == vocab_service.count()

    def test_stats_bands(self, vocab_service: VocabService):
        vocab_service.load_all()
        stats = vocab_service.get_vocab_stats()
        assert 5 in stats["bands"]
        assert 6 in stats["bands"]
        assert 7 in stats["bands"]
        assert 8 in stats["bands"]
        assert 9 in stats["bands"]
        assert sum(stats["bands"].values()) == stats["total"]

    def test_stats_topics(self, vocab_service: VocabService):
        vocab_service.load_all()
        stats = vocab_service.get_vocab_stats()
        assert "education" in stats["topics"]
        assert sum(stats["topics"].values()) == stats["total"]

    def test_stats_empty(self, vocab_service: VocabService):
        stats = vocab_service.get_vocab_stats()
        assert stats["total"] == 0
        assert stats["bands"] == {}
        assert stats["topics"] == {}

    def test_stats_bands_sorted(self, vocab_service: VocabService):
        vocab_service.load_all()
        stats = vocab_service.get_vocab_stats()
        bands = list(stats["bands"].keys())
        assert bands == sorted(bands)

    def test_stats_topics_sorted(self, vocab_service: VocabService):
        vocab_service.load_all()
        stats = vocab_service.get_vocab_stats()
        topics = list(stats["topics"].keys())
        assert topics == sorted(topics)
