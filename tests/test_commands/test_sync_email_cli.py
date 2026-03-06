"""测试 sync 和 email CLI 命令"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from ielts_buddy.cli import cli


@pytest.fixture(autouse=True)
def _tmp_home(tmp_path):
    """每个测试使用独立的临时数据目录"""
    os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
    yield
    os.environ.pop("IELTS_BUDDY_HOME", None)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestSyncHelp:
    """测试 sync 命令帮助"""

    def test_sync_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["sync", "--help"])
        assert result.exit_code == 0
        assert "vocab" in result.output
        assert "records" in result.output
        assert "stats" in result.output
        assert "all" in result.output

    def test_sync_in_main_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "sync" in result.output


class TestSyncVocab:
    """测试 sync vocab 命令"""

    def test_sync_vocab(self, runner: CliRunner):
        result = runner.invoke(cli, ["sync", "vocab"])
        assert result.exit_code == 0
        assert "词库已导出" in result.output

    def test_sync_vocab_creates_file(self, runner: CliRunner, tmp_path):
        runner.invoke(cli, ["sync", "vocab"])
        sync_dir = Path(os.environ["IELTS_BUDDY_HOME"]) / "sync"
        assert (sync_dir / "vocab.json").exists()


class TestSyncRecords:
    """测试 sync records 命令"""

    def test_sync_records(self, runner: CliRunner):
        result = runner.invoke(cli, ["sync", "records"])
        assert result.exit_code == 0
        assert "学习记录已导出" in result.output


class TestSyncStats:
    """测试 sync stats 命令"""

    def test_sync_stats(self, runner: CliRunner):
        result = runner.invoke(cli, ["sync", "stats"])
        assert result.exit_code == 0
        assert "统计摘要已导出" in result.output


class TestSyncAll:
    """测试 sync all 命令"""

    def test_sync_all(self, runner: CliRunner):
        result = runner.invoke(cli, ["sync", "all"])
        assert result.exit_code == 0
        assert "全部数据已导出" in result.output

    def test_sync_all_creates_files(self, runner: CliRunner):
        runner.invoke(cli, ["sync", "all"])
        sync_dir = Path(os.environ["IELTS_BUDDY_HOME"]) / "sync"
        assert (sync_dir / "vocab.json").exists()
        assert (sync_dir / "records.json").exists()
        assert (sync_dir / "stats.json").exists()


class TestEmailHelp:
    """测试 email 命令帮助"""

    def test_email_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["email", "--help"])
        assert result.exit_code == 0
        assert "preview" in result.output
        assert "send" in result.output

    def test_email_in_main_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "email" in result.output


class TestEmailPreview:
    """测试 email preview 命令"""

    def test_email_preview(self, runner: CliRunner):
        result = runner.invoke(cli, ["email", "preview"])
        assert result.exit_code == 0
        assert "邮件已生成" in result.output
        assert "HTML 已保存到" in result.output

    def test_email_preview_creates_file(self, runner: CliRunner):
        runner.invoke(cli, ["email", "preview"])
        preview_path = Path(os.environ["IELTS_BUDDY_HOME"]) / "email_preview.html"
        assert preview_path.exists()
        content = preview_path.read_text(encoding="utf-8")
        assert "<html" in content


class TestEmailSend:
    """测试 email send 命令"""

    def test_email_send_no_config(self, runner: CliRunner):
        """无配置文件时应提示错误"""
        result = runner.invoke(cli, ["email", "send"])
        assert result.exit_code == 0
        assert "配置文件不存在" in result.output

    def test_email_send_with_config(self, runner: CliRunner):
        """有配置但 SMTP 不可达时应报错"""
        config_dir = Path(os.environ["IELTS_BUDDY_HOME"])
        config_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "smtp_host": "localhost",
            "smtp_port": 9999,
            "smtp_ssl": True,
            "username": "test",
            "password": "test",
            "from_addr": "test@test.com",
            "to_addr": "user@test.com",
        }
        (config_dir / "email.json").write_text(json.dumps(config), encoding="utf-8")
        result = runner.invoke(cli, ["email", "send"])
        assert result.exit_code == 0
        assert "发送失败" in result.output
