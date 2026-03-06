"""共享 pytest fixtures"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.stats_service import StatsService
from ielts_buddy.services.vocab_service import VocabService


@pytest.fixture
def sample_word() -> Word:
    """创建一个示例单词"""
    return Word(
        word="example",
        phonetic="/ɪɡˈzæmpəl/",
        meaning="例子，实例",
        pos="n.",
        band=5,
        topic="education",
        example="This is an example sentence.",
        example_cn="这是一个例句。",
        collocations=["for example", "set an example"],
        synonyms=["instance", "sample"],
        etymology="ex- (出) + ample (取) → 取出来看 → 例子",
    )


@pytest.fixture
def sample_words() -> list[Word]:
    """创建一组示例单词"""
    return [
        Word(word="important", meaning="重要的", pos="adj.", band=5, topic="education"),
        Word(word="develop", meaning="发展，开发", pos="v.", band=5, topic="economy"),
        Word(word="analyze", meaning="分析", pos="v.", band=6, topic="education"),
        Word(word="benefit", meaning="好处；受益", pos="n./v.", band=6, topic="society"),
        Word(word="acknowledge", meaning="承认；确认", pos="v.", band=7, topic="education"),
    ]


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """临时 SQLite 数据库路径"""
    return tmp_path / "test_data.db"


@pytest.fixture
def review_service(tmp_db: Path) -> ReviewService:
    """创建使用临时数据库的 ReviewService"""
    svc = ReviewService(db_path=tmp_db)
    yield svc
    svc.close()


@pytest.fixture
def stats_service(tmp_db: Path) -> StatsService:
    """创建使用临时数据库的 StatsService"""
    svc = StatsService(db_path=tmp_db)
    yield svc
    svc.close()


@pytest.fixture
def vocab_service() -> VocabService:
    """创建 VocabService 实例"""
    return VocabService()


@pytest.fixture
def custom_vocab_file(tmp_path: Path) -> Path:
    """创建一个自定义词库 JSON 文件"""
    words = [
        {
            "word": "custom_word_1",
            "meaning": "自定义词1",
            "band": 5,
            "topic": "test",
        },
        {
            "word": "custom_word_2",
            "meaning": "自定义词2",
            "band": 6,
            "topic": "test",
        },
    ]
    file_path = tmp_path / "custom_vocab.json"
    file_path.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return file_path
