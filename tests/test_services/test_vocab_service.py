"""测试词库服务"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.vocab_service import (
    VocabService,
    _normalize_master_entry,
)


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


# ============================================================
# Phase 3: 大词库 + 索引 + 缓存 测试
# ============================================================


class TestMasterVocabLoad:
    """测试大词库加载"""

    def test_load_master(self, vocab_service: VocabService):
        vocab_service.load_master()
        assert vocab_service.count() == 4485
        assert vocab_service.source == "master"

    def test_load_master_has_all_bands(self, vocab_service: VocabService):
        vocab_service.load_master()
        bands = vocab_service.get_bands()
        assert set(bands) == {5, 6, 7, 8, 9}

    def test_load_master_band_distribution(self, vocab_service: VocabService):
        vocab_service.load_master()
        assert vocab_service.count(5) == 1227
        assert vocab_service.count(6) == 1127
        assert vocab_service.count(7) == 1076
        assert vocab_service.count(8) == 745
        assert vocab_service.count(9) == 310

    def test_load_master_idempotent(self, vocab_service: VocabService):
        vocab_service.load_master()
        count1 = vocab_service.count()
        vocab_service.load_master()
        count2 = vocab_service.count()
        assert count1 == count2

    def test_master_source_property(self, vocab_service: VocabService):
        assert vocab_service.source == ""
        vocab_service.load_master()
        assert vocab_service.source == "master"

    def test_curated_source_property(self, vocab_service: VocabService):
        vocab_service.load_all()
        assert vocab_service.source == "curated"

    def test_master_words_have_meaning(self, vocab_service: VocabService):
        """验证 master 词库的 definition 字段被正确转换为 meaning"""
        vocab_service.load_master()
        for w in vocab_service.words[:100]:  # 抽查前 100 个
            assert w.meaning, f"单词 {w.word} 缺少 meaning"

    def test_master_words_have_example(self, vocab_service: VocabService):
        """验证 master 词库的 example dict 被正确转换为 string"""
        vocab_service.load_master()
        for w in vocab_service.words[:100]:
            assert isinstance(w.example, str), f"单词 {w.word} 的 example 不是字符串"

    def test_master_larger_than_curated(self, vocab_service: VocabService):
        svc2 = VocabService()
        svc2.load_all()
        curated_count = svc2.count()

        vocab_service.load_master()
        master_count = vocab_service.count()

        assert master_count > curated_count


class TestNormalizeMasterEntry:
    """测试 master 词条格式转换"""

    def test_definition_to_meaning(self):
        entry = {"word": "test", "definition": "测试", "band": 5}
        result = _normalize_master_entry(entry)
        assert "meaning" in result
        assert result["meaning"] == "测试"
        assert "definition" not in result

    def test_definition_cleanup_leading_bracket(self):
        entry = {"word": "emperor", "definition": "] n. 皇帝；君主", "band": 5}
        result = _normalize_master_entry(entry)
        # 应该清除前导 '] ' 和词性前缀
        assert result["meaning"] == "皇帝；君主"

    def test_definition_cleanup_pos_prefix(self):
        entry = {"word": "test", "definition": "n. 测试", "band": 5}
        result = _normalize_master_entry(entry)
        assert result["meaning"] == "测试"

    def test_example_dict_to_strings(self):
        entry = {
            "word": "test",
            "definition": "测试",
            "example": {"en": "This is a test.", "zh": "这是一个测试。"},
            "band": 5,
        }
        result = _normalize_master_entry(entry)
        assert result["example"] == "This is a test."
        assert result["example_cn"] == "这是一个测试。"

    def test_example_dict_empty_zh(self):
        entry = {
            "word": "test",
            "definition": "测试",
            "example": {"en": "A test.", "zh": ""},
            "band": 5,
        }
        result = _normalize_master_entry(entry)
        assert result["example"] == "A test."
        assert result["example_cn"] == ""

    def test_meaning_already_present_not_overwritten(self):
        """如果已有 meaning 字段，不会被 definition 覆盖"""
        entry = {"word": "test", "meaning": "已有释义", "definition": "别的释义", "band": 5}
        result = _normalize_master_entry(entry)
        assert result["meaning"] == "已有释义"


class TestMemoryIndexes:
    """测试内存索引功能"""

    def test_word_index_exact_lookup(self, vocab_service: VocabService):
        vocab_service.load_all()
        word = vocab_service.get_word("important")
        assert word is not None
        assert word.word == "important"

    def test_word_index_case_insensitive(self, vocab_service: VocabService):
        vocab_service.load_all()
        w1 = vocab_service.get_word("Important")
        w2 = vocab_service.get_word("important")
        assert w1 is not None
        assert w1.word == w2.word

    def test_word_index_not_found(self, vocab_service: VocabService):
        vocab_service.load_all()
        assert vocab_service.get_word("zzzznonexistent") is None

    def test_band_index_filter(self, vocab_service: VocabService):
        vocab_service.load_all()
        band5 = vocab_service.filter_by_band(5)
        assert all(w.band == 5 for w in band5)
        assert len(band5) > 0

    def test_topic_index_filter(self, vocab_service: VocabService):
        vocab_service.load_all()
        edu = vocab_service.filter_by_topic("education")
        assert all(w.topic.lower() == "education" for w in edu)

    def test_search_index_exact_match_first(self, vocab_service: VocabService):
        """精确匹配的单词应排在搜索结果第一位"""
        vocab_service.load_all()
        results = vocab_service.search("important")
        assert results[0].word == "important"

    def test_indexes_invalidated_on_load(self, vocab_service: VocabService):
        """加载新词库后索引应被清除并重建"""
        vocab_service.load_band(5)
        _ = vocab_service.get_word("important")  # 触发索引构建
        count_before = vocab_service.count()

        vocab_service.load_band(6)  # 新加载应清除旧索引
        count_after = vocab_service.count()
        assert count_after > count_before

    def test_master_word_index(self, vocab_service: VocabService):
        vocab_service.load_master()
        word = vocab_service.get_word("emperor")
        assert word is not None
        assert word.band == 5

    def test_master_search(self, vocab_service: VocabService):
        vocab_service.load_master()
        results = vocab_service.search("traditional")
        assert any(w.word == "traditional" for w in results)


class TestVocabStats:
    """测试扩展的词库统计"""

    def test_stats_includes_source(self, vocab_service: VocabService):
        vocab_service.load_all()
        stats = vocab_service.get_vocab_stats()
        assert stats["source"] == "curated"

    def test_stats_master_source(self, vocab_service: VocabService):
        vocab_service.load_master()
        stats = vocab_service.get_vocab_stats()
        assert stats["source"] == "master"
        assert stats["total"] == 4485

    def test_stats_master_bands_sum(self, vocab_service: VocabService):
        vocab_service.load_master()
        stats = vocab_service.get_vocab_stats()
        assert sum(stats["bands"].values()) == stats["total"]

    def test_stats_master_topics(self, vocab_service: VocabService):
        vocab_service.load_master()
        stats = vocab_service.get_vocab_stats()
        assert len(stats["topics"]) > 0
        assert sum(stats["topics"].values()) == stats["total"]


class TestSQLiteCache:
    """测试 SQLite 词库缓存"""

    @pytest.fixture(autouse=True)
    def _setup_cache_dir(self, tmp_path, monkeypatch):
        """使用临时目录作为缓存路径"""
        monkeypatch.setenv("IELTS_BUDDY_HOME", str(tmp_path / ".ielts-buddy"))

    def test_cache_created_on_first_load(self, tmp_path):
        svc = VocabService()
        svc.load_master()
        cache_path = Path(os.environ["IELTS_BUDDY_HOME"]) / "vocab_cache.db"
        assert cache_path.exists()

    def test_cache_reused_on_second_load(self, tmp_path):
        svc1 = VocabService()
        svc1.load_master()
        count1 = svc1.count()

        # 第二次加载应走缓存
        svc2 = VocabService()
        svc2.load_master()
        count2 = svc2.count()

        assert count1 == count2

    def test_cache_data_integrity(self, tmp_path):
        """缓存加载的数据与 JSON 加载的应完全一致"""
        svc1 = VocabService()
        svc1.load_master()
        words1 = sorted(svc1.words, key=lambda w: w.word)

        # 第二次从缓存加载
        svc2 = VocabService()
        svc2.load_master()
        words2 = sorted(svc2.words, key=lambda w: w.word)

        assert len(words1) == len(words2)
        for w1, w2 in zip(words1[:50], words2[:50]):
            assert w1.word == w2.word
            assert w1.meaning == w2.meaning
            assert w1.band == w2.band
            assert w1.topic == w2.topic


class TestMasterVocabDataIntegrity:
    """测试大词库数据完整性"""

    @pytest.fixture(autouse=True)
    def _load_master(self, vocab_service: VocabService):
        vocab_service.load_master()
        self.svc = vocab_service

    def test_all_master_words_have_word(self):
        for w in self.svc.words:
            assert w.word, "大词库中有空 word"

    def test_all_master_words_have_meaning(self):
        missing = [w.word for w in self.svc.words if not w.meaning]
        # 大词库中允许少量空释义（数据质量问题，不阻塞加载）
        assert len(missing) <= 5, f"大词库中 {len(missing)} 个单词缺少 meaning: {missing}"

    def test_all_master_words_have_valid_band(self):
        for w in self.svc.words:
            assert 5 <= w.band <= 9, f"大词库单词 {w.word} band={w.band} 超出范围"

    def test_all_master_words_have_topic(self):
        for w in self.svc.words:
            assert w.topic, f"大词库单词 {w.word} 缺少 topic"

    def test_master_word_count(self):
        assert self.svc.count() == 4485

    def test_master_json_valid(self):
        """验证 master JSON 文件格式正确"""
        from importlib import resources
        data_pkg = resources.files("ielts_buddy") / "data"
        path = Path(str(data_pkg / "vocab_master.json"))
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 4485
        for item in data:
            assert "word" in item
            assert "definition" in item or "meaning" in item


class TestPerformance:
    """测试性能要求"""

    def test_master_load_under_500ms(self, vocab_service: VocabService):
        """大词库加载应在 500ms 内完成"""
        start = time.perf_counter()
        vocab_service.load_master()
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"大词库加载耗时 {elapsed:.3f}s，超过 500ms"

    def test_search_under_100ms(self, vocab_service: VocabService):
        """搜索应在 100ms 内完成"""
        vocab_service.load_master()
        start = time.perf_counter()
        vocab_service.search("education")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"搜索耗时 {elapsed:.3f}s，超过 100ms"

    def test_filter_by_band_under_100ms(self, vocab_service: VocabService):
        vocab_service.load_master()
        start = time.perf_counter()
        vocab_service.filter_by_band(7)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"按 band 筛选耗时 {elapsed:.3f}s"

    def test_get_word_under_10ms(self, vocab_service: VocabService):
        vocab_service.load_master()
        # 预热索引
        vocab_service.get_word("important")
        start = time.perf_counter()
        for _ in range(100):
            vocab_service.get_word("traditional")
        elapsed = (time.perf_counter() - start) / 100
        assert elapsed < 0.01, f"精确查找平均耗时 {elapsed*1000:.3f}ms"


class TestCLISourceFlag:
    """测试 CLI 命令的 --source 参数"""

    @pytest.fixture(autouse=True)
    def _tmp_home(self, tmp_path):
        os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
        yield
        os.environ.pop("IELTS_BUDDY_HOME", None)

    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_random_master_source(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(cli, ["vocab", "random", "-n", "3", "-s", "master"])
        assert result.exit_code == 0
        assert "随机单词" in result.output
        assert "大词库" in result.output

    def test_random_curated_source(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(cli, ["vocab", "random", "-n", "3", "-s", "curated"])
        assert result.exit_code == 0
        assert "精选" in result.output

    def test_search_master_source(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(cli, ["vocab", "search", "important", "-s", "master"])
        assert result.exit_code == 0
        assert "搜索结果" in result.output

    def test_list_master_source(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(cli, ["vocab", "list", "-s", "master"])
        assert result.exit_code == 0
        assert "词库浏览" in result.output

    def test_info_master_source(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(cli, ["vocab", "info", "-s", "master"])
        assert result.exit_code == 0
        assert "词库概览" in result.output
        assert "master" in result.output

    def test_info_curated_source(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(cli, ["vocab", "info", "-s", "curated"])
        assert result.exit_code == 0
        assert "curated" in result.output

    def test_default_source_is_master(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(cli, ["vocab", "random", "-n", "2"])
        assert result.exit_code == 0
        assert "大词库" in result.output

    def test_quiz_with_source(self, runner):
        from ielts_buddy.cli import cli
        result = runner.invoke(
            cli, ["vocab", "quiz", "-n", "1", "-s", "curated"], input="q\n"
        )
        assert result.exit_code == 0
        assert "词汇测验" in result.output
