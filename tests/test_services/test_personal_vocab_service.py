"""测试 PersonalVocabService"""

from __future__ import annotations

from pathlib import Path

import pytest

from ielts_buddy.core.models import PersonalWord, VocabCategory, Word
from ielts_buddy.services.personal_vocab_service import PersonalVocabService


# ---- Fixtures ----


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_personal.db"


@pytest.fixture
def svc(tmp_db: Path) -> PersonalVocabService:
    s = PersonalVocabService(db_path=tmp_db)
    yield s
    s.close()


@pytest.fixture
def sample_pw() -> PersonalWord:
    return PersonalWord(
        word="contribute",
        phonetic="/kənˈtrɪbjuːt/",
        meaning="贡献，促成",
        pos="v.",
        band=6,
        topic="society",
        example="Many factors contribute to success.",
        example_cn="很多因素促成了成功。",
        note="常用搭配: contribute to",
        source="manual",
    )


@pytest.fixture
def sample_word() -> Word:
    """内置词库格式的 Word"""
    return Word(
        word="analyze",
        phonetic="/ˈænəlaɪz/",
        meaning="分析",
        pos="v.",
        band=6,
        topic="education",
        example="We need to analyze the data.",
        example_cn="我们需要分析数据。",
    )


# ---- 初始化测试 ----


class TestInit:
    def test_creates_db_file(self, tmp_db: Path):
        svc = PersonalVocabService(db_path=tmp_db)
        assert tmp_db.exists()
        svc.close()

    def test_system_categories_created(self, svc: PersonalVocabService):
        cats = svc.list_categories()
        names = {c.name for c in cats}
        assert "favorites" in names
        assert "mistakes" in names

    def test_system_categories_marked(self, svc: PersonalVocabService):
        cats = svc.list_categories()
        for c in cats:
            if c.name in ("favorites", "mistakes"):
                assert c.is_system is True

    def test_idempotent_init(self, tmp_db: Path):
        """多次初始化不会报错或重复创建系统分类"""
        svc1 = PersonalVocabService(db_path=tmp_db)
        svc1.close()
        svc2 = PersonalVocabService(db_path=tmp_db)
        cats = svc2.list_categories()
        svc2.close()
        system_cats = [c for c in cats if c.is_system]
        assert len(system_cats) == 2


# ---- 单词 CRUD ----


class TestAddWord:
    def test_add_word_returns_with_id(self, svc, sample_pw):
        result = svc.add_word(sample_pw)
        assert result.id is not None
        assert result.word == "contribute"
        assert result.meaning == "贡献，促成"
        assert result.created_at is not None

    def test_add_word_duplicate_raises(self, svc, sample_pw):
        svc.add_word(sample_pw)
        with pytest.raises(ValueError, match="已存在"):
            svc.add_word(sample_pw)

    def test_add_word_minimal(self, svc):
        pw = PersonalWord(word="hello", meaning="你好")
        result = svc.add_word(pw)
        assert result.word == "hello"
        assert result.band == 5  # default

    def test_add_word_persists(self, svc, sample_pw):
        svc.add_word(sample_pw)
        fetched = svc.get_word("contribute")
        assert fetched is not None
        assert fetched.phonetic == "/kənˈtrɪbjuːt/"


class TestEditWord:
    def test_edit_meaning(self, svc, sample_pw):
        svc.add_word(sample_pw)
        result = svc.edit_word("contribute", meaning="贡献")
        assert result.meaning == "贡献"

    def test_edit_multiple_fields(self, svc, sample_pw):
        svc.add_word(sample_pw)
        result = svc.edit_word("contribute", meaning="新释义", note="新笔记", band=7)
        assert result.meaning == "新释义"
        assert result.note == "新笔记"
        assert result.band == 7

    def test_edit_nonexistent_raises(self, svc):
        with pytest.raises(ValueError, match="不在个人词库中"):
            svc.edit_word("nonexistent", meaning="test")

    def test_edit_no_changes(self, svc, sample_pw):
        svc.add_word(sample_pw)
        result = svc.edit_word("contribute")
        assert result.meaning == sample_pw.meaning

    def test_edit_updates_timestamp(self, svc, sample_pw):
        added = svc.add_word(sample_pw)
        import time; time.sleep(0.01)
        edited = svc.edit_word("contribute", note="updated")
        # updated_at should be >= created_at
        assert edited.updated_at >= added.created_at

    def test_edit_ignores_unknown_fields(self, svc, sample_pw):
        svc.add_word(sample_pw)
        result = svc.edit_word("contribute", unknown_field="ignored")
        assert result.meaning == sample_pw.meaning


class TestDeleteWord:
    def test_delete_existing(self, svc, sample_pw):
        svc.add_word(sample_pw)
        assert svc.delete_word("contribute") is True
        assert svc.get_word("contribute") is None

    def test_delete_nonexistent(self, svc):
        assert svc.delete_word("nonexistent") is False

    def test_delete_removes_from_categories(self, svc, sample_pw):
        """删除单词时级联删除分类关联"""
        svc.add_word(sample_pw)
        svc.add_word_to_category("contribute", "favorites")
        svc.delete_word("contribute")
        words, total = svc.list_words(category="favorites")
        assert total == 0


class TestGetWord:
    def test_get_existing(self, svc, sample_pw):
        svc.add_word(sample_pw)
        result = svc.get_word("contribute")
        assert result is not None
        assert result.word == "contribute"

    def test_get_nonexistent(self, svc):
        assert svc.get_word("nonexistent") is None


class TestListWords:
    def test_list_empty(self, svc):
        words, total = svc.list_words()
        assert words == []
        assert total == 0

    def test_list_all(self, svc):
        for i in range(5):
            svc.add_word(PersonalWord(word=f"word{i}", meaning=f"释义{i}"))
        words, total = svc.list_words()
        assert total == 5
        assert len(words) == 5

    def test_list_pagination(self, svc):
        for i in range(10):
            svc.add_word(PersonalWord(word=f"word{i:02d}", meaning=f"释义{i}"))
        words_p1, total = svc.list_words(page=1, per_page=3)
        assert total == 10
        assert len(words_p1) == 3
        words_p2, _ = svc.list_words(page=2, per_page=3)
        assert len(words_p2) == 3
        # 不同页内容不重叠
        assert set(w.word for w in words_p1) & set(w.word for w in words_p2) == set()

    def test_list_by_category(self, svc):
        svc.add_word(PersonalWord(word="apple", meaning="苹果"))
        svc.add_word(PersonalWord(word="banana", meaning="香蕉"))
        svc.add_word_to_category("apple", "favorites")
        words, total = svc.list_words(category="favorites")
        assert total == 1
        assert words[0].word == "apple"

    def test_list_nonexistent_category(self, svc):
        words, total = svc.list_words(category="nonexistent")
        assert words == []
        assert total == 0

    def test_get_word_count(self, svc):
        assert svc.get_word_count() == 0
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        assert svc.get_word_count() == 1


# ---- 分类管理 ----


class TestCreateCategory:
    def test_create(self, svc):
        cat = svc.create_category("writing", "写作高频词")
        assert cat.name == "writing"
        assert cat.description == "写作高频词"
        assert cat.is_system is False
        assert cat.id is not None

    def test_create_duplicate_raises(self, svc):
        svc.create_category("writing")
        with pytest.raises(ValueError, match="已存在"):
            svc.create_category("writing")

    def test_create_system_name_raises(self, svc):
        """不能创建与系统分类同名的分类"""
        with pytest.raises(ValueError, match="已存在"):
            svc.create_category("favorites")


class TestDeleteCategory:
    def test_delete_user_category(self, svc):
        svc.create_category("writing")
        assert svc.delete_category("writing") is True

    def test_delete_system_raises(self, svc):
        with pytest.raises(ValueError, match="不可删除"):
            svc.delete_category("favorites")

    def test_delete_nonexistent_raises(self, svc):
        with pytest.raises(ValueError, match="不存在"):
            svc.delete_category("nonexistent")


class TestListCategories:
    def test_default_categories(self, svc):
        cats = svc.list_categories()
        assert len(cats) >= 2

    def test_includes_word_count(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        svc.add_word_to_category("test", "favorites")
        cats = svc.list_categories()
        fav = next(c for c in cats if c.name == "favorites")
        assert fav.word_count == 1

    def test_system_first(self, svc):
        """系统分类排在前面"""
        svc.create_category("zzz_custom")
        cats = svc.list_categories()
        system_indices = [i for i, c in enumerate(cats) if c.is_system]
        custom_indices = [i for i, c in enumerate(cats) if not c.is_system]
        if system_indices and custom_indices:
            assert max(system_indices) < min(custom_indices)


# ---- 分类关联 ----


class TestCategoryWords:
    def test_add_to_category(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        assert svc.add_word_to_category("test", "favorites") is True

    def test_add_duplicate_returns_false(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        svc.add_word_to_category("test", "favorites")
        assert svc.add_word_to_category("test", "favorites") is False

    def test_add_nonexistent_word_raises(self, svc):
        with pytest.raises(ValueError, match="不在个人词库中"):
            svc.add_word_to_category("nonexistent", "favorites")

    def test_add_to_nonexistent_category_raises(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        with pytest.raises(ValueError, match="不存在"):
            svc.add_word_to_category("test", "nonexistent")

    def test_remove_from_category(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        svc.add_word_to_category("test", "favorites")
        assert svc.remove_word_from_category("test", "favorites") is True

    def test_remove_not_in_category(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        assert svc.remove_word_from_category("test", "favorites") is False

    def test_get_word_categories(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        svc.add_word_to_category("test", "favorites")
        svc.add_word_to_category("test", "mistakes")
        cats = svc.get_word_categories("test")
        names = {c.name for c in cats}
        assert "favorites" in names
        assert "mistakes" in names

    def test_get_categories_nonexistent_word(self, svc):
        assert svc.get_word_categories("nonexistent") == []

    def test_word_in_multiple_categories(self, svc):
        svc.add_word(PersonalWord(word="test", meaning="测试"))
        svc.create_category("custom1")
        svc.add_word_to_category("test", "favorites")
        svc.add_word_to_category("test", "custom1")
        cats = svc.get_word_categories("test")
        assert len(cats) == 2


# ---- 错词收录 ----


class TestAddMistake:
    def test_add_mistake_from_word(self, svc, sample_word):
        result = svc.add_mistake(sample_word)
        assert result.word == "analyze"
        assert result.source == "quiz_mistake"
        # 应在 mistakes 分类中
        cats = svc.get_word_categories("analyze")
        assert any(c.name == "mistakes" for c in cats)

    def test_add_mistake_fills_fields(self, svc, sample_word):
        result = svc.add_mistake(sample_word)
        assert result.phonetic == "/ˈænəlaɪz/"
        assert result.meaning == "分析"
        assert result.band == 6

    def test_add_mistake_dedup(self, svc, sample_word):
        """重复答错不会创建多个词库条目"""
        r1 = svc.add_mistake(sample_word)
        r2 = svc.add_mistake(sample_word)
        assert r1.id == r2.id
        assert svc.get_word_count() == 1

    def test_add_mistake_existing_word(self, svc):
        """已在个人词库的词只添加到 mistakes 分类"""
        svc.add_word(PersonalWord(word="hello", meaning="你好"))
        word = Word(word="hello", meaning="你好", band=5)
        result = svc.add_mistake(word)
        assert result.word == "hello"
        cats = svc.get_word_categories("hello")
        assert any(c.name == "mistakes" for c in cats)

    def test_add_mistake_custom_source(self, svc, sample_word):
        result = svc.add_mistake(sample_word, source="exam_mistake")
        assert result.source == "exam_mistake"


# ---- PersonalWord → Word 转换 ----


class TestToWord:
    def test_converts_correctly(self, svc, sample_pw):
        added = svc.add_word(sample_pw)
        w = svc.to_word(added)
        assert isinstance(w, Word)
        assert w.word == "contribute"
        assert w.meaning == "贡献，促成"
        assert w.is_custom is True
        assert w.band == 6

    def test_converts_minimal(self, svc):
        pw = PersonalWord(word="test", meaning="测试")
        added = svc.add_word(pw)
        w = svc.to_word(added)
        assert w.word == "test"
        assert w.meaning == "测试"
        assert w.band == 5


# ---- 批量导入导出 ----


class TestImportJSON:
    def test_import_json(self, svc, tmp_path):
        data = [
            {"word": "apple", "meaning": "苹果", "band": 5},
            {"word": "banana", "meaning": "香蕉", "band": 6},
        ]
        f = tmp_path / "words.json"
        import json
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = svc.import_words(f)
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert svc.get_word_count() == 2

    def test_import_json_dedup(self, svc, tmp_path):
        svc.add_word(PersonalWord(word="apple", meaning="苹果"))
        data = [{"word": "apple", "meaning": "苹果"}, {"word": "new", "meaning": "新"}]
        f = tmp_path / "words.json"
        import json
        f.write_text(json.dumps(data), encoding="utf-8")

        result = svc.import_words(f)
        assert result["imported"] == 1
        assert result["skipped"] == 1

    def test_import_json_invalid(self, svc, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json", encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 0

    def test_import_json_empty_list(self, svc, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]", encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 0

    def test_import_json_source_set(self, svc, tmp_path):
        data = [{"word": "test", "meaning": "测试"}]
        f = tmp_path / "words.json"
        import json
        f.write_text(json.dumps(data), encoding="utf-8")
        svc.import_words(f)
        w = svc.get_word("test")
        assert w.source == "import"


class TestImportCSV:
    def test_import_csv(self, svc, tmp_path):
        f = tmp_path / "words.csv"
        f.write_text("word,meaning,band\napple,苹果,5\nbanana,香蕉,6\n", encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 2
        assert svc.get_word("apple").meaning == "苹果"

    def test_import_csv_extra_columns(self, svc, tmp_path):
        f = tmp_path / "words.csv"
        f.write_text("word,meaning,pos,note\nhello,你好,n.,重要\n", encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 1
        w = svc.get_word("hello")
        assert w.note == "重要"

    def test_import_csv_invalid_band(self, svc, tmp_path):
        f = tmp_path / "words.csv"
        f.write_text("word,meaning,band\ntest,测试,99\n", encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 1
        w = svc.get_word("test")
        assert w.band == 9  # clamped to max


class TestImportPlain:
    def test_import_plain_no_vocab_service(self, svc, tmp_path):
        f = tmp_path / "words.txt"
        f.write_text("apple\nbanana\n", encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 2
        w = svc.get_word("apple")
        assert w.meaning == ""  # no builtin match

    def test_import_plain_with_vocab_service(self, svc, tmp_path):
        from unittest.mock import MagicMock
        mock_vocab = MagicMock()
        mock_vocab.get_word.return_value = Word(
            word="contribute", meaning="贡献", band=6,
            phonetic="/kənˈtrɪbjuːt/", pos="v.",
        )
        f = tmp_path / "words.txt"
        f.write_text("contribute\n", encoding="utf-8")
        result = svc.import_words(f, vocab_service=mock_vocab)
        assert result["imported"] == 1
        w = svc.get_word("contribute")
        assert w.meaning == "贡献"
        assert w.phonetic == "/kənˈtrɪbjuːt/"

    def test_import_plain_empty_lines_skipped(self, svc, tmp_path):
        f = tmp_path / "words.txt"
        f.write_text("apple\n\n\nbanana\n", encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 2

    def test_import_empty_file(self, svc, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        result = svc.import_words(f)
        assert result == {"imported": 0, "skipped": 0, "failed": 0}


class TestExport:
    def test_export_json_empty(self, svc):
        content = svc.export_words(fmt="json")
        assert content == "[]"

    def test_export_json(self, svc):
        import json
        svc.add_word(PersonalWord(word="apple", meaning="苹果", band=5))
        svc.add_word(PersonalWord(word="banana", meaning="香蕉", band=6))
        content = svc.export_words(fmt="json")
        data = json.loads(content)
        assert len(data) == 2
        words = {d["word"] for d in data}
        assert "apple" in words
        assert "banana" in words

    def test_export_csv(self, svc):
        svc.add_word(PersonalWord(word="apple", meaning="苹果"))
        content = svc.export_words(fmt="csv")
        assert "word" in content  # header
        assert "apple" in content
        assert "苹果" in content

    def test_export_csv_empty(self, svc):
        content = svc.export_words(fmt="csv")
        assert content == ""

    def test_export_by_category(self, svc):
        import json
        svc.add_word(PersonalWord(word="apple", meaning="苹果"))
        svc.add_word(PersonalWord(word="banana", meaning="香蕉"))
        svc.add_word_to_category("apple", "favorites")

        content = svc.export_words(fmt="json", category="favorites")
        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["word"] == "apple"

    def test_roundtrip_json(self, svc, tmp_path):
        """导出再导入应保持数据一致"""
        import json
        svc.add_word(PersonalWord(word="apple", meaning="苹果", band=6, note="好吃"))
        exported = svc.export_words(fmt="json")

        # 删除后重新导入
        svc.delete_word("apple")
        assert svc.get_word_count() == 0

        f = tmp_path / "roundtrip.json"
        f.write_text(exported, encoding="utf-8")
        result = svc.import_words(f)
        assert result["imported"] == 1
        w = svc.get_word("apple")
        assert w.meaning == "苹果"
        assert w.band == 6
        assert w.note == "好吃"


# ---- 写作批改联动 ----


class TestAddFromGrading:
    def test_add_from_grading(self, svc):
        result = svc.add_from_grading(
            word="beneficial",
            context="This is good for health.",
            suggestion="This is beneficial for health.",
            comment="用词过于口语化",
        )
        assert result.word == "beneficial"
        assert result.source == "grading"
        assert result.example == "This is good for health."
        assert result.example_cn == "This is beneficial for health."
        assert result.note == "用词过于口语化"

    def test_add_from_grading_dedup(self, svc):
        svc.add_word(PersonalWord(word="beneficial", meaning="有益的"))
        result = svc.add_from_grading(word="beneficial")
        assert result.meaning == "有益的"  # 返回已有的
        assert svc.get_word_count() == 1

    def test_add_from_grading_minimal(self, svc):
        result = svc.add_from_grading(word="elaborate")
        assert result.word == "elaborate"
        assert result.source == "grading"


class TestExtractVocabFromResult:
    def test_extract_vocab_words(self):
        from ielts_buddy.core.models import GradeDimension, GradeResult, SentenceAnnotation
        from ielts_buddy.services.grading_service import GradingService

        result = GradeResult(
            overall_score=6.0,
            task_response=GradeDimension(score=6.0),
            coherence=GradeDimension(score=6.0),
            lexical_resource=GradeDimension(score=6.0),
            grammar=GradeDimension(score=6.0),
            annotations=[
                SentenceAnnotation(
                    sentence_index=0,
                    original="I think this is good.",
                    issue_type="vocabulary",
                    comment="用词过于口语化",
                    suggestion="It is widely acknowledged that this is beneficial.",
                ),
                SentenceAnnotation(
                    sentence_index=1,
                    original="She go to school.",
                    issue_type="grammar",
                    comment="主谓不一致",
                    suggestion="She goes to school.",
                ),
            ],
        )

        items = GradingService.extract_vocab_from_result(result)
        assert len(items) == 1  # 只有 vocabulary 类型
        assert items[0]["context"] == "I think this is good."
        assert "acknowledged" in items[0]["word"] or "beneficial" in items[0]["word"]

    def test_extract_no_vocab_annotations(self):
        from ielts_buddy.core.models import GradeDimension, GradeResult, SentenceAnnotation
        from ielts_buddy.services.grading_service import GradingService

        result = GradeResult(
            overall_score=6.0,
            task_response=GradeDimension(score=6.0),
            coherence=GradeDimension(score=6.0),
            lexical_resource=GradeDimension(score=6.0),
            grammar=GradeDimension(score=6.0),
            annotations=[
                SentenceAnnotation(
                    sentence_index=0,
                    original="Test.",
                    issue_type="grammar",
                    comment="test",
                    suggestion="fix",
                ),
            ],
        )
        assert GradingService.extract_vocab_from_result(result) == []

    def test_extract_empty_annotations(self):
        from ielts_buddy.core.models import GradeDimension, GradeResult
        from ielts_buddy.services.grading_service import GradingService

        result = GradeResult(
            overall_score=6.0,
            task_response=GradeDimension(score=6.0),
            coherence=GradeDimension(score=6.0),
            lexical_resource=GradeDimension(score=6.0),
            grammar=GradeDimension(score=6.0),
        )
        assert GradingService.extract_vocab_from_result(result) == []


# ---- 统计方法 ----


class TestCategoryStats:
    def test_category_stats_default(self, svc):
        stats = svc.get_category_stats()
        assert len(stats) >= 2  # favorites + mistakes
        names = {s["name"] for s in stats}
        assert "favorites" in names
        assert "mistakes" in names

    def test_category_stats_with_words(self, svc):
        svc.add_word(PersonalWord(word="apple", meaning="苹果"))
        svc.add_word_to_category("apple", "favorites")
        stats = svc.get_category_stats()
        fav = next(s for s in stats if s["name"] == "favorites")
        assert fav["word_count"] == 1

    def test_source_distribution_empty(self, svc):
        assert svc.get_source_distribution() == {}

    def test_source_distribution(self, svc):
        svc.add_word(PersonalWord(word="a", meaning="1", source="manual"))
        svc.add_word(PersonalWord(word="b", meaning="2", source="manual"))
        svc.add_word(PersonalWord(word="c", meaning="3", source="grading"))
        dist = svc.get_source_distribution()
        assert dist["manual"] == 2
        assert dist["grading"] == 1

    def test_band_distribution_empty(self, svc):
        assert svc.get_band_distribution() == {}

    def test_band_distribution(self, svc):
        svc.add_word(PersonalWord(word="a", meaning="1", band=5))
        svc.add_word(PersonalWord(word="b", meaning="2", band=6))
        svc.add_word(PersonalWord(word="c", meaning="3", band=6))
        dist = svc.get_band_distribution()
        assert dist[5] == 1
        assert dist[6] == 2
