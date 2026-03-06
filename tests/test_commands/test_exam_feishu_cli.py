"""测试 exam 和 feishu CLI 命令"""

from __future__ import annotations

import json
import os

import pytest
from click.testing import CliRunner

from ielts_buddy.cli import cli
from ielts_buddy.core.models import Word
from ielts_buddy.services.review_service import ReviewService


@pytest.fixture(autouse=True)
def _tmp_home(tmp_path):
    """每个测试使用独立的临时数据目录"""
    os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
    yield
    os.environ.pop("IELTS_BUDDY_HOME", None)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestExamCLI:
    """测试 exam 命令组"""

    def test_exam_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["exam", "--help"])
        assert result.exit_code == 0
        assert "模拟考试" in result.output
        assert "start" in result.output
        assert "history" in result.output

    def test_exam_start_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["exam", "start", "--help"])
        assert result.exit_code == 0
        assert "--count" in result.output or "-n" in result.output
        assert "--band" in result.output or "-b" in result.output
        assert "--time" in result.output

    def test_exam_history_empty(self, runner: CliRunner):
        result = runner.invoke(cli, ["exam", "history"])
        assert result.exit_code == 0
        assert "暂无考试记录" in result.output

    def test_exam_start_with_input(self, runner: CliRunner):
        """测试考试开始后立即退出"""
        result = runner.invoke(cli, ["exam", "start", "-n", "3"], input="q\n")
        assert result.exit_code == 0

    def test_exam_start_answer_questions(self, runner: CliRunner):
        """模拟回答几道题后退出"""
        # 提供足够的输入来回答题目
        inputs = "答案1\n答案2\nq\n"
        result = runner.invoke(cli, ["exam", "start", "-n", "3"], input=inputs)
        assert result.exit_code == 0

    def test_exam_history_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["exam", "history", "--help"])
        assert result.exit_code == 0
        assert "-n" in result.output or "--count" in result.output


class TestFeishuCLI:
    """测试 feishu 命令组"""

    def test_feishu_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["feishu", "--help"])
        assert result.exit_code == 0
        assert "飞书" in result.output or "Bitable" in result.output
        assert "sync" in result.output
        assert "stats" in result.output
        assert "setup" in result.output

    def test_feishu_sync_no_config(self, runner: CliRunner):
        """没有配置时提示用户"""
        result = runner.invoke(cli, ["feishu", "sync"])
        assert result.exit_code == 0
        assert "app-token" in result.output or "setup" in result.output

    def test_feishu_sync_with_tokens(self, runner: CliRunner):
        """使用参数直接同步"""
        result = runner.invoke(
            cli, ["feishu", "sync", "--app-token", "tok", "--table-id", "tbl"]
        )
        assert result.exit_code == 0
        # 没有数据也应该成功导出
        assert "导出" in result.output or "失败" not in result.output

    def test_feishu_stats_no_config(self, runner: CliRunner):
        result = runner.invoke(cli, ["feishu", "stats"])
        assert result.exit_code == 0
        assert "app-token" in result.output or "setup" in result.output

    def test_feishu_stats_with_tokens(self, runner: CliRunner):
        result = runner.invoke(
            cli, ["feishu", "stats", "--app-token", "tok", "--table-id", "tbl"]
        )
        assert result.exit_code == 0

    def test_feishu_setup_cancel(self, runner: CliRunner):
        """setup 取消"""
        result = runner.invoke(cli, ["feishu", "setup"], input="\n\n")
        assert result.exit_code == 0

    def test_feishu_setup_save(self, runner: CliRunner):
        """setup 保存配置"""
        result = runner.invoke(
            cli, ["feishu", "setup"], input="mytoken\nmytable\n"
        )
        assert result.exit_code == 0
        assert "保存" in result.output

    def test_feishu_schema(self, runner: CliRunner):
        result = runner.invoke(
            cli, ["feishu", "schema", "--app-token", "tok", "--table-id", "tbl"]
        )
        assert result.exit_code == 0
        assert "单词" in result.output
        assert "Band" in result.output

    def test_feishu_sync_with_saved_config(self, runner: CliRunner):
        """先 setup 保存配置，再 sync"""
        runner.invoke(cli, ["feishu", "setup"], input="token1\ntable1\n")
        result = runner.invoke(cli, ["feishu", "sync"])
        assert result.exit_code == 0
        assert "导出" in result.output

    def test_feishu_registered_in_cli(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert "feishu" in result.output

    def test_exam_registered_in_cli(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert "exam" in result.output
