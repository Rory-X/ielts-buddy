"""测试 CLI 命令"""

from __future__ import annotations

import os
import tempfile

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


class TestCLIBasic:
    """测试基础 CLI 功能"""

    def test_version(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "IELTS Buddy" in result.output
        assert "vocab" in result.output
        assert "stats" in result.output

    def test_vocab_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "--help"])
        assert result.exit_code == 0
        assert "random" in result.output
        assert "quiz" in result.output
        assert "review" in result.output

    def test_stats_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output


class TestVocabRandom:
    """测试 vocab random 命令"""

    def test_random_default(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random"])
        assert result.exit_code == 0
        assert "随机单词" in result.output

    def test_random_count(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-n", "3"])
        assert result.exit_code == 0
        assert "共 3 个" in result.output

    def test_random_band5(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-n", "2", "-b", "5"])
        assert result.exit_code == 0

    def test_random_band6(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-n", "2", "-b", "6"])
        assert result.exit_code == 0

    def test_random_band7(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-n", "2", "-b", "7"])
        assert result.exit_code == 0

    def test_random_zero_count(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-n", "0"])
        assert result.exit_code == 0
        assert "没有找到匹配的单词" in result.output

    def test_random_unsupported_band(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-b", "8"])
        assert result.exit_code == 0
        assert "没有找到匹配的单词" in result.output


class TestVocabQuiz:
    """测试 vocab quiz 命令"""

    def test_quiz_immediate_quit(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "3"], input="q\n")
        assert result.exit_code == 0
        assert "词汇测验" in result.output

    def test_quiz_answer_and_quit(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "2"], input="随便\nq\n")
        assert result.exit_code == 0

    def test_quiz_eof(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "2"], input="")
        assert result.exit_code == 0


class TestVocabReview:
    """测试 vocab review 命令"""

    def test_review_no_due(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "review"])
        assert result.exit_code == 0
        assert "暂无需要复习的单词" in result.output


class TestStatsShow:
    """测试 stats show 命令"""

    def test_stats_show_empty(self, runner: CliRunner):
        result = runner.invoke(cli, ["stats", "show"])
        assert result.exit_code == 0
        assert "今日学习" in result.output
        assert "总体统计" in result.output

    def test_stats_show_after_learning(self, runner: CliRunner):
        # Learn some words via quiz first
        runner.invoke(cli, ["vocab", "quiz", "-n", "2"], input="测试\n测试\n")
        result = runner.invoke(cli, ["stats", "show"])
        assert result.exit_code == 0
