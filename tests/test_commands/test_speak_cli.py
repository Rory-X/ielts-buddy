"""测试 speak CLI 命令"""

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


class TestSpeakHelp:
    """测试 speak 命令帮助"""

    def test_speak_in_main_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "speak" in result.output

    def test_speak_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "--help"])
        assert result.exit_code == 0
        assert "topics" in result.output
        assert "practice" in result.output
        assert "vocab" in result.output


class TestSpeakTopics:
    """测试 speak topics 命令"""

    def test_topics_all(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "topics"])
        assert result.exit_code == 0
        assert "雅思口语话题" in result.output

    def test_topics_part1(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "topics", "--part", "1"])
        assert result.exit_code == 0
        assert "Part 1" in result.output

    def test_topics_part2(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "topics", "--part", "2"])
        assert result.exit_code == 0
        assert "Part 2" in result.output

    def test_topics_part3(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "topics", "--part", "3"])
        assert result.exit_code == 0
        assert "Part 3" in result.output


class TestSpeakPractice:
    """测试 speak practice 命令"""

    def test_practice_random(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "practice"])
        assert result.exit_code == 0
        assert "口语练习题" in result.output
        assert "参考答案" in result.output

    def test_practice_part1(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "practice", "--part", "1"])
        assert result.exit_code == 0
        assert "Part 1" in result.output

    def test_practice_part2(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "practice", "--part", "2"])
        assert result.exit_code == 0
        assert "Part 2" in result.output

    def test_practice_part3(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "practice", "--part", "3"])
        assert result.exit_code == 0
        assert "Part 3" in result.output

    def test_practice_shows_vocab(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "practice"])
        assert result.exit_code == 0
        assert "关键词汇" in result.output

    def test_practice_shows_tips(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "practice"])
        assert result.exit_code == 0
        assert "答题技巧" in result.output


class TestSpeakVocab:
    """测试 speak vocab 命令"""

    def test_vocab_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "vocab", "Hometown"])
        assert result.exit_code == 0
        assert "话题词汇" in result.output

    def test_vocab_case_insensitive(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "vocab", "hometown"])
        assert result.exit_code == 0
        assert "话题词汇" in result.output

    def test_vocab_not_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "vocab", "xyznonexistent"])
        assert result.exit_code == 0
        assert "没有找到" in result.output

    def test_vocab_shows_questions(self, runner: CliRunner):
        result = runner.invoke(cli, ["speak", "vocab", "Hometown"])
        assert result.exit_code == 0
        assert "相关问题" in result.output
