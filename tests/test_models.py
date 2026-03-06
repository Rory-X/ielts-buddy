"""测试 Pydantic 数据模型"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from ielts_buddy.core.models import (
    DailySummary,
    LearningRecord,
    TestSession,
    Word,
)


class TestWordModel:
    """测试 Word 模型"""

    def test_basic_creation(self):
        w = Word(word="test", meaning="测试", band=5)
        assert w.word == "test"
        assert w.meaning == "测试"
        assert w.band == 5

    def test_all_fields(self):
        w = Word(
            word="analyze",
            phonetic="/ˈænəlaɪz/",
            meaning="分析",
            pos="v.",
            band=6,
            topic="education",
            example="Scientists analyze data.",
            example_cn="科学家分析数据。",
            collocations=["analyze data", "analyze results"],
            synonyms=["examine", "study"],
            etymology="ana- + lyze",
            is_custom=False,
        )
        assert w.phonetic == "/ˈænəlaɪz/"
        assert w.pos == "v."
        assert w.topic == "education"
        assert len(w.collocations) == 2
        assert len(w.synonyms) == 2

    def test_default_values(self):
        w = Word(word="test", meaning="测试", band=5)
        assert w.id is None
        assert w.phonetic == ""
        assert w.pos == ""
        assert w.topic == ""
        assert w.example == ""
        assert w.example_cn == ""
        assert w.collocations == []
        assert w.synonyms == []
        assert w.etymology == ""
        assert w.is_custom is False
        assert w.created_at is None

    def test_band_validation_min(self):
        with pytest.raises(ValidationError):
            Word(word="test", meaning="测试", band=4)

    def test_band_validation_max(self):
        with pytest.raises(ValidationError):
            Word(word="test", meaning="测试", band=10)

    def test_band_boundaries(self):
        w5 = Word(word="a", meaning="x", band=5)
        w9 = Word(word="b", meaning="y", band=9)
        assert w5.band == 5
        assert w9.band == 9

    def test_collocations_json(self):
        w = Word(
            word="test", meaning="测试", band=5,
            collocations=["test case", "test data"]
        )
        result = w.collocations_json()
        parsed = json.loads(result)
        assert parsed == ["test case", "test data"]

    def test_synonyms_json(self):
        w = Word(
            word="test", meaning="测试", band=5,
            synonyms=["exam", "quiz"]
        )
        result = w.synonyms_json()
        parsed = json.loads(result)
        assert parsed == ["exam", "quiz"]

    def test_empty_collocations_json(self):
        w = Word(word="test", meaning="测试", band=5)
        result = w.collocations_json()
        assert json.loads(result) == []

    def test_parse_json_field_valid(self):
        result = Word.parse_json_field('["a", "b"]')
        assert result == ["a", "b"]

    def test_parse_json_field_empty(self):
        assert Word.parse_json_field("") == []
        assert Word.parse_json_field(None) == []

    def test_parse_json_field_invalid(self):
        assert Word.parse_json_field("not json") == []

    def test_model_dump_json_roundtrip(self):
        w = Word(
            word="test",
            phonetic="/test/",
            meaning="测试",
            band=5,
            collocations=["a", "b"],
        )
        json_str = w.model_dump_json()
        w2 = Word(**json.loads(json_str))
        assert w2.word == w.word
        assert w2.collocations == w.collocations

    def test_chinese_in_meaning(self):
        w = Word(word="environment", meaning="环境；周围的事物", band=5)
        assert "环境" in w.meaning
        assert "；" in w.meaning


class TestLearningRecordModel:
    """测试 LearningRecord 模型"""

    def test_basic_creation(self):
        rec = LearningRecord(word_id=1)
        assert rec.word_id == 1
        assert rec.memory_level == 0
        assert rec.learn_count == 0

    def test_default_values(self):
        rec = LearningRecord(word_id=1)
        assert rec.id is None
        assert rec.memory_level == 0
        assert rec.next_review is None
        assert rec.learn_count == 0
        assert rec.correct_count == 0
        assert rec.wrong_count == 0
        assert rec.first_learned is None
        assert rec.last_reviewed is None
        assert rec.is_starred is False
        assert rec.is_difficult is False

    def test_memory_level_bounds(self):
        rec = LearningRecord(word_id=1, memory_level=0)
        assert rec.memory_level == 0
        rec = LearningRecord(word_id=1, memory_level=6)
        assert rec.memory_level == 6

    def test_memory_level_too_low(self):
        with pytest.raises(ValidationError):
            LearningRecord(word_id=1, memory_level=-1)

    def test_memory_level_too_high(self):
        with pytest.raises(ValidationError):
            LearningRecord(word_id=1, memory_level=7)


class TestTestSessionModel:
    """测试 TestSession 模型"""

    def test_basic_creation(self):
        ts = TestSession(
            session_id="s1",
            test_date="2026-03-06T10:00:00",
            test_mode="meaning",
            total_count=10,
            correct_count=8,
        )
        assert ts.total_count == 10
        assert ts.correct_count == 8

    def test_accuracy(self):
        ts = TestSession(
            session_id="s1",
            test_date="2026-03-06",
            test_mode="spelling",
            total_count=10,
            correct_count=7,
        )
        assert ts.accuracy == pytest.approx(0.7)

    def test_accuracy_zero_total(self):
        ts = TestSession(
            session_id="s1",
            test_date="2026-03-06",
            test_mode="meaning",
            total_count=0,
            correct_count=0,
        )
        assert ts.accuracy == 0.0

    def test_accuracy_perfect(self):
        ts = TestSession(
            session_id="s1",
            test_date="2026-03-06",
            test_mode="meaning",
            total_count=5,
            correct_count=5,
        )
        assert ts.accuracy == 1.0

    def test_wrong_words_json(self):
        ts = TestSession(
            session_id="s1",
            test_date="2026-03-06",
            test_mode="meaning",
            total_count=10,
            correct_count=8,
            wrong_words=["word1", "word2"],
        )
        parsed = json.loads(ts.wrong_words_json())
        assert parsed == ["word1", "word2"]


class TestDailySummaryModel:
    """测试 DailySummary 模型"""

    def test_basic_creation(self):
        ds = DailySummary(date="2026-03-06")
        assert ds.date == "2026-03-06"
        assert ds.new_words == 0
        assert ds.reviewed_words == 0

    def test_full_data(self):
        ds = DailySummary(
            date="2026-03-06",
            new_words=50,
            reviewed_words=30,
            test_accuracy=0.85,
            study_minutes=45,
            streak_days=12,
        )
        assert ds.new_words == 50
        assert ds.streak_days == 12
