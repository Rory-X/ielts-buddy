"""测试飞书 Bitable 数据导出服务 (Phase 6 新增方法)"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ielts_buddy.core.models import Word
from ielts_buddy.services.feishu_service import FeishuService
from ielts_buddy.services.review_service import ReviewService


@pytest.fixture(autouse=True)
def _tmp_home(tmp_path):
    """使用临时目录"""
    os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
    yield
    os.environ.pop("IELTS_BUDDY_HOME", None)


@pytest.fixture
def feishu_service(tmp_db: Path) -> FeishuService:
    return FeishuService(db_path=tmp_db)


@pytest.fixture
def feishu_with_data(tmp_db: Path) -> FeishuService:
    """带有学习记录的 feishu service"""
    review_svc = ReviewService(db_path=tmp_db)
    words = [
        Word(word="example", meaning="例子", band=5, topic="test"),
        Word(word="develop", meaning="发展", band=6, topic="economy"),
        Word(word="analyze", meaning="分析", band=7, topic="education"),
    ]
    for w in words:
        review_svc.record_learn(w, correct=True)
    review_svc.record_learn(words[2], correct=False)  # analyze 答错一次
    review_svc.close()
    return FeishuService(db_path=tmp_db)


class TestSyncToBitable:
    """测试 sync_to_bitable 方法"""

    def test_sync_creates_file(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_to_bitable("token123", "table456")
        assert filepath.exists()

    def test_sync_json_format(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_to_bitable("token123", "table456")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 3

    def test_sync_json_fields(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_to_bitable("token123", "table456")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        record = data[0]
        assert "单词" in record
        assert "Band" in record
        assert "掌握等级" in record
        assert "正确次数" in record
        assert "错误次数" in record
        assert "上次复习" in record
        assert "下次复习" in record

    def test_sync_correct_data(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_to_bitable("t", "id")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        words = {r["单词"] for r in data}
        assert "example" in words
        assert "develop" in words
        assert "analyze" in words

    def test_sync_generates_instructions(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_to_bitable("token", "table")
        instructions = filepath.parent / "sync_instructions.md"
        assert instructions.exists()
        content = instructions.read_text(encoding="utf-8")
        assert "token" in content
        assert "table" in content

    def test_sync_empty_db(self, feishu_service: FeishuService):
        """空数据库时也能正常导出（空列表）"""
        filepath = feishu_service.sync_to_bitable("t", "id")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data == []

    def test_sync_filename_contains_tokens(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_to_bitable("mytoken", "mytable")
        assert "mytoken" in filepath.name
        assert "mytable" in filepath.name

    def test_sync_to_feishu_subdir(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_to_bitable("t", "id")
        assert "feishu" in str(filepath)


class TestCreateBitableSchema:
    """测试 create_bitable_schema 方法"""

    def test_schema_basic(self, feishu_service: FeishuService):
        schema = feishu_service.create_bitable_schema("token", "table")
        assert schema["app_token"] == "token"
        assert schema["table_id"] == "table"
        assert "fields" in schema

    def test_schema_fields(self, feishu_service: FeishuService):
        schema = feishu_service.create_bitable_schema("t", "id")
        field_names = [f["field_name"] for f in schema["fields"]]
        assert "单词" in field_names
        assert "Band" in field_names
        assert "掌握等级" in field_names
        assert "正确次数" in field_names
        assert "错误次数" in field_names

    def test_schema_field_types(self, feishu_service: FeishuService):
        schema = feishu_service.create_bitable_schema("t", "id")
        # 文本类型是 1
        word_field = next(f for f in schema["fields"] if f["field_name"] == "单词")
        assert word_field["type"] == 1
        # 数字类型是 2
        band_field = next(f for f in schema["fields"] if f["field_name"] == "Band")
        assert band_field["type"] == 2


class TestSyncStatsToBitable:
    """测试 sync_stats_to_bitable 方法"""

    def test_stats_creates_file(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_stats_to_bitable("token", "table")
        assert filepath.exists()

    def test_stats_json_format(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_stats_to_bitable("t", "id")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 30  # 30 天历史

    def test_stats_json_fields(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_stats_to_bitable("t", "id")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        record = data[0]
        assert "日期" in record
        assert "学习量" in record
        assert "正确率" in record
        assert "新学" in record
        assert "复习" in record
        assert "streak" in record

    def test_stats_empty_db(self, feishu_service: FeishuService):
        filepath = feishu_service.sync_stats_to_bitable("t", "id")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert isinstance(data, list)

    def test_stats_filename_contains_tokens(self, feishu_with_data: FeishuService):
        filepath = feishu_with_data.sync_stats_to_bitable("tok", "tbl")
        assert "tok" in filepath.name
        assert "tbl" in filepath.name


class TestFeishuConfig:
    """测试配置管理"""

    def test_save_and_load_config(self, feishu_service: FeishuService):
        feishu_service.save_config("mytoken", "mytable")
        config = feishu_service.load_config()
        assert config is not None
        assert config["app_token"] == "mytoken"
        assert config["table_id"] == "mytable"
        assert "updated_at" in config

    def test_load_config_not_exists(self, feishu_service: FeishuService):
        config = feishu_service.load_config()
        assert config is None

    def test_save_config_returns_path(self, feishu_service: FeishuService):
        path = feishu_service.save_config("t", "id")
        assert path.exists()
        assert path.name == "feishu.json"

    def test_save_config_overwrites(self, feishu_service: FeishuService):
        feishu_service.save_config("old", "old")
        feishu_service.save_config("new", "new")
        config = feishu_service.load_config()
        assert config["app_token"] == "new"
