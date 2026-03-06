"""测试同步服务"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.sync_service import SyncService


@pytest.fixture(autouse=True)
def _tmp_home(tmp_path):
    """每个测试使用独立的临时数据目录"""
    os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
    yield
    os.environ.pop("IELTS_BUDDY_HOME", None)


@pytest.fixture
def sync_service(tmp_path) -> SyncService:
    """使用临时输出目录的 SyncService"""
    return SyncService(output_dir=tmp_path / "sync_out")


@pytest.fixture
def sample_word() -> Word:
    return Word(
        word="example",
        phonetic="/ɪɡˈzæmpəl/",
        meaning="例子，实例",
        pos="n.",
        band=5,
        topic="education",
    )


class TestExportVocab:
    """测试词库导出"""

    def test_export_vocab_creates_file(self, sync_service: SyncService):
        """导出词库应创建 vocab.json"""
        path = sync_service.export_vocab()
        assert path.exists()
        assert path.name == "vocab.json"

    def test_export_vocab_valid_json(self, sync_service: SyncService):
        """导出的文件应为有效 JSON"""
        path = sync_service.export_vocab()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) > 0

    def test_export_vocab_has_word_fields(self, sync_service: SyncService):
        """每条记录应包含 word/meaning/band/mastery 字段"""
        path = sync_service.export_vocab()
        data = json.loads(path.read_text(encoding="utf-8"))
        item = data[0]
        assert "word" in item
        assert "meaning" in item
        assert "band" in item
        assert "mastery" in item

    def test_export_vocab_mastery_default(self, sync_service: SyncService):
        """未学过的单词 mastery.memory_level 应为 0"""
        path = sync_service.export_vocab()
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            assert item["mastery"]["memory_level"] == 0

    def test_export_vocab_with_learned_word(self, sync_service: SyncService):
        """学过的单词应有非零 mastery"""
        # 用内置词库中的单词
        from ielts_buddy.services.vocab_service import VocabService
        vocab_svc = VocabService()
        vocab_svc.load_band(5)
        word = vocab_svc.words[0]  # "important"

        review_svc = ReviewService()
        try:
            review_svc.record_learn(word, correct=True)
        finally:
            review_svc.close()

        path = sync_service.export_vocab()
        data = json.loads(path.read_text(encoding="utf-8"))
        learned = [d for d in data if d["word"] == word.word]
        assert len(learned) == 1
        assert learned[0]["mastery"]["memory_level"] >= 1

    def test_export_vocab_overwrites(self, sync_service: SyncService):
        """多次导出应覆盖旧文件"""
        path1 = sync_service.export_vocab()
        path2 = sync_service.export_vocab()
        assert path1 == path2


class TestExportRecords:
    """测试学习记录导出"""

    def test_export_records_empty(self, sync_service: SyncService):
        """无记录时导出空列表"""
        path = sync_service.export_records()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == []

    def test_export_records_after_learning(self, sync_service: SyncService, sample_word: Word):
        """学习后应有记录"""
        review_svc = ReviewService()
        try:
            review_svc.record_learn(sample_word, correct=True)
        finally:
            review_svc.close()

        path = sync_service.export_records()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["word"] == "example"
        assert data[0]["correct_count"] == 1

    def test_export_records_has_fields(self, sync_service: SyncService, sample_word: Word):
        """记录应包含所有字段"""
        review_svc = ReviewService()
        try:
            review_svc.record_learn(sample_word, correct=False)
        finally:
            review_svc.close()

        path = sync_service.export_records()
        data = json.loads(path.read_text(encoding="utf-8"))
        rec = data[0]
        assert "word" in rec
        assert "memory_level" in rec
        assert "next_review" in rec
        assert "learn_count" in rec
        assert "first_learned" in rec
        assert "is_starred" in rec

    def test_export_records_creates_file(self, sync_service: SyncService):
        """应创建 records.json"""
        path = sync_service.export_records()
        assert path.exists()
        assert path.name == "records.json"


class TestExportStats:
    """测试统计导出"""

    def test_export_stats_creates_file(self, sync_service: SyncService):
        """应创建 stats.json"""
        path = sync_service.export_stats()
        assert path.exists()
        assert path.name == "stats.json"

    def test_export_stats_valid_json(self, sync_service: SyncService):
        """导出的应为有效 JSON"""
        path = sync_service.export_stats()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_export_stats_has_sections(self, sync_service: SyncService):
        """统计摘要应包含各个部分"""
        path = sync_service.export_stats()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "exported_at" in data
        assert "total" in data
        assert "today" in data
        assert "due_count" in data
        assert "streak" in data
        assert "band_progress" in data

    def test_export_stats_band_progress(self, sync_service: SyncService):
        """band_progress 应包含各 band 信息"""
        path = sync_service.export_stats()
        data = json.loads(path.read_text(encoding="utf-8"))
        progress = data["band_progress"]
        assert isinstance(progress, list)
        assert len(progress) > 0
        assert "band" in progress[0]
        assert "total" in progress[0]
        assert "mastered" in progress[0]


class TestExportAll:
    """测试全部导出"""

    def test_export_all_returns_all_paths(self, sync_service: SyncService):
        """应返回 vocab/records/stats 三个路径"""
        paths = sync_service.export_all()
        assert "vocab" in paths
        assert "records" in paths
        assert "stats" in paths

    def test_export_all_files_exist(self, sync_service: SyncService):
        """所有导出文件应存在"""
        paths = sync_service.export_all()
        for name, path in paths.items():
            assert path.exists(), f"{name} 文件不存在: {path}"

    def test_export_all_creates_output_dir(self, tmp_path):
        """应自动创建输出目录"""
        output_dir = tmp_path / "new_dir" / "sync"
        svc = SyncService(output_dir=output_dir)
        svc.export_all()
        assert output_dir.exists()
