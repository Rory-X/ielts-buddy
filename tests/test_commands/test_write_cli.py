"""测试 write CLI 命令"""

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


class TestWriteHelp:
    """测试 write 命令帮助"""

    def test_write_in_main_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "write" in result.output

    def test_write_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "--help"])
        assert result.exit_code == 0
        assert "topics" in result.output
        assert "templates" in result.output
        assert "synonyms" in result.output
        assert "vocab" in result.output


class TestWriteTopics:
    """测试 write topics 命令"""

    def test_topics_all(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "topics"])
        assert result.exit_code == 0
        assert "雅思写作" in result.output

    def test_topics_by_category(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "topics", "-c", "education"])
        assert result.exit_code == 0
        assert "教育" in result.output

    def test_topics_by_category_environment(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "topics", "-c", "environment"])
        assert result.exit_code == 0
        assert "环境" in result.output

    def test_topics_by_category_technology(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "topics", "-c", "technology"])
        assert result.exit_code == 0
        assert "科技" in result.output


class TestWriteTemplates:
    """测试 write templates 命令"""

    def test_templates_all(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "templates"])
        assert result.exit_code == 0
        assert "句型模板" in result.output

    def test_templates_introduction(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "templates", "-t", "introduction"])
        assert result.exit_code == 0
        assert "开头段" in result.output

    def test_templates_body(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "templates", "-t", "body"])
        assert result.exit_code == 0
        assert "主体段" in result.output

    def test_templates_conclusion(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "templates", "-t", "conclusion"])
        assert result.exit_code == 0
        assert "结尾段" in result.output

    def test_templates_transition(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "templates", "-t", "transition"])
        assert result.exit_code == 0
        assert "过渡句" in result.output


class TestWriteSynonyms:
    """测试 write synonyms 命令"""

    def test_synonyms_all(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "synonyms"])
        assert result.exit_code == 0
        assert "同义替换" in result.output

    def test_synonyms_by_word(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "synonyms", "important"])
        assert result.exit_code == 0
        assert "crucial" in result.output

    def test_synonyms_not_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "synonyms", "xyznonexistent"])
        assert result.exit_code == 0
        assert "没有找到" in result.output


class TestWriteVocab:
    """测试 write vocab 命令"""

    def test_vocab_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "vocab", "气候"])
        assert result.exit_code == 0
        assert "话题词汇" in result.output

    def test_vocab_not_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "vocab", "xyznonexistent"])
        assert result.exit_code == 0
        assert "没有找到" in result.output

    def test_vocab_english_keyword(self, runner: CliRunner):
        result = runner.invoke(cli, ["write", "vocab", "education"])
        assert result.exit_code == 0
        assert "话题词汇" in result.output
