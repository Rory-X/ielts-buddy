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
        result = runner.invoke(cli, ["vocab", "random", "-b", "4"])
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

    def test_quiz_en2zh_mode(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "1", "-m", "en2zh"], input="q\n")
        assert result.exit_code == 0
        assert "英译中" in result.output

    def test_quiz_zh2en_mode(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "1", "-m", "zh2en"], input="q\n")
        assert result.exit_code == 0
        assert "中译英" in result.output

    def test_quiz_mix_mode(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "1", "-m", "mix"], input="q\n")
        assert result.exit_code == 0
        assert "混合模式" in result.output

    def test_quiz_zh2en_correct_answer(self, runner: CliRunner):
        """中译英：输入正确英文单词"""
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "1", "-m", "zh2en", "-b", "5"], input="important\n")
        assert result.exit_code == 0
        # 可能对也可能错（随机出题），但不应 crash

    def test_quiz_zh2en_case_insensitive(self, runner: CliRunner):
        """中译英：大小写不敏感"""
        result = runner.invoke(cli, ["vocab", "quiz", "-n", "1", "-m", "zh2en"], input="IMPORTANT\n")
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


class TestVocabSearch:
    """测试 vocab search 命令"""

    def test_search_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "search", "important"])
        assert result.exit_code == 0
        assert "搜索结果" in result.output
        assert "important" in result.output

    def test_search_not_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "search", "xyznonexistent"])
        assert result.exit_code == 0
        assert "没有找到" in result.output

    def test_search_by_topic(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "search", "education"])
        assert result.exit_code == 0
        assert "搜索结果" in result.output

    def test_search_by_chinese(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "search", "重要"])
        assert result.exit_code == 0
        assert "搜索结果" in result.output

    def test_search_in_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output


class TestVocabList:
    """测试 vocab list 命令"""

    def test_list_default(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "list"])
        assert result.exit_code == 0
        assert "词库浏览" in result.output

    def test_list_by_band(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "list", "-b", "5"])
        assert result.exit_code == 0
        assert "Band 5" in result.output

    def test_list_by_topic(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "list", "-t", "education"])
        assert result.exit_code == 0
        assert "education" in result.output

    def test_list_pagination(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "list", "--per-page", "5", "-p", "1"])
        assert result.exit_code == 0
        assert "第 1/" in result.output

    def test_list_page2(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "list", "--per-page", "5", "-p", "2"])
        assert result.exit_code == 0
        assert "第 2/" in result.output

    def test_list_empty_band(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "list", "-b", "4"])
        assert result.exit_code == 0
        assert "没有找到匹配的单词" in result.output

    def test_list_in_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output


class TestVocabInfo:
    """测试 vocab info 命令"""

    def test_info_show(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "info"])
        assert result.exit_code == 0
        assert "词库概览" in result.output
        assert "主题分布" in result.output

    def test_info_has_band_counts(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "info"])
        assert result.exit_code == 0
        # 应该显示各 band 的数量
        for band in ["5", "6", "7", "8", "9"]:
            assert band in result.output

    def test_info_in_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "--help"])
        assert result.exit_code == 0
        assert "info" in result.output


class TestVocabRandomBand8and9:
    """测试 Band 8/9 词库随机"""

    def test_random_band8(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-n", "2", "-b", "8"])
        assert result.exit_code == 0
        assert "随机单词" in result.output

    def test_random_band9(self, runner: CliRunner):
        result = runner.invoke(cli, ["vocab", "random", "-n", "2", "-b", "9"])
        assert result.exit_code == 0
        assert "随机单词" in result.output
