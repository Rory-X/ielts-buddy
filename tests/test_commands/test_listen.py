"""测试 listen 命令组"""

from __future__ import annotations

import os

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


class TestListenHelp:
    """测试 listen 命令组基础功能"""

    def test_listen_in_main_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "listen" in result.output

    def test_listen_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "--help"])
        assert result.exit_code == 0
        assert "resources" in result.output
        assert "dictation" in result.output
        assert "detail" in result.output


class TestListenResources:
    """测试 listen resources 命令"""

    def test_resources_default(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "resources"])
        assert result.exit_code == 0
        assert "听力资源" in result.output

    def test_resources_filter_type_podcast(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "resources", "-t", "podcast"])
        assert result.exit_code == 0
        assert "播客" in result.output

    def test_resources_filter_type_video(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "resources", "-t", "video"])
        assert result.exit_code == 0
        assert "视频" in result.output

    def test_resources_filter_difficulty(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "resources", "-d", "beginner"])
        assert result.exit_code == 0
        assert "初级" in result.output

    def test_resources_filter_combined(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "resources", "-t", "podcast", "-d", "intermediate"])
        assert result.exit_code == 0
        assert "播客" in result.output
        assert "中级" in result.output


class TestListenDetail:
    """测试 listen detail 命令"""

    def test_detail_valid_index(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "detail", "1"])
        assert result.exit_code == 0
        assert "资源详情" in result.output

    def test_detail_invalid_index(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "detail", "9999"])
        assert result.exit_code == 0
        assert "无效序号" in result.output

    def test_detail_zero_index(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "detail", "0"])
        assert result.exit_code == 0
        assert "无效序号" in result.output


class TestListenDictation:
    """测试 listen dictation 命令"""

    def test_dictation_immediate_quit(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "dictation", "-n", "3"], input="q\n")
        assert result.exit_code == 0
        assert "听写模式" in result.output

    def test_dictation_answer_and_quit(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "dictation", "-n", "2"], input="wrong\nq\n")
        assert result.exit_code == 0

    def test_dictation_eof(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "dictation", "-n", "2"], input="")
        assert result.exit_code == 0

    def test_dictation_with_band(self, runner: CliRunner):
        result = runner.invoke(cli, ["listen", "dictation", "-n", "2", "-b", "5"], input="q\n")
        assert result.exit_code == 0
        assert "听写模式" in result.output
