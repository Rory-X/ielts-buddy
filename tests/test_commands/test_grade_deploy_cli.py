"""测试 grade + deploy CLI 命令"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def _mock_grok_response() -> dict:
    return {
        "overall_score": 6.5,
        "task_response": {"score": 6.5, "comment": "观点表达较为清晰"},
        "coherence": {"score": 6.0, "comment": "段落衔接有待加强"},
        "lexical_resource": {"score": 7.0, "comment": "词汇使用较为丰富"},
        "grammar": {"score": 6.5, "comment": "语法基本准确"},
        "suggestions": ["多用复杂句式", "注意段落过渡", "丰富高级词汇"],
        "rewrite": "In contemporary society...",
    }


def _make_subprocess_result(data: dict) -> MagicMock:
    content = json.dumps(data, ensure_ascii=False)
    outer = json.dumps({"content": content, "model": "test", "usage": {}})
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = outer
    mock.stderr = ""
    return mock


# ---- Tests: grade 命令组 ----

class TestGradeCLI:

    def test_grade_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["grade", "--help"])
        assert result.exit_code == 0
        assert "essay" in result.output
        assert "file" in result.output
        assert "history" in result.output

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_eof(self, mock_run, runner: CliRunner):
        """直接 EOF 输入空文本"""
        result = runner.invoke(cli, ["grade", "essay"], input="")
        assert result.exit_code == 0
        assert "为空" in result.output

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_with_text(self, mock_run, runner: CliRunner):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        result = runner.invoke(cli, ["grade", "essay"], input="This is my essay about education.\n")
        assert result.exit_code == 0
        assert "批改结果" in result.output or "正在批改" in result.output

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_with_topic(self, mock_run, runner: CliRunner):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        result = runner.invoke(
            cli, ["grade", "essay", "-t", "Education is important"],
            input="My essay text here.\n",
        )
        assert result.exit_code == 0

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_file(self, mock_run, runner: CliRunner, tmp_path):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        essay_file = tmp_path / "essay.txt"
        essay_file.write_text("This is a test essay for grading.", encoding="utf-8")

        result = runner.invoke(cli, ["grade", "file", str(essay_file)])
        assert result.exit_code == 0
        assert "读取文件" in result.output

    def test_grade_file_empty(self, runner: CliRunner, tmp_path):
        essay_file = tmp_path / "empty.txt"
        essay_file.write_text("", encoding="utf-8")

        result = runner.invoke(cli, ["grade", "file", str(essay_file)])
        assert result.exit_code == 0
        assert "为空" in result.output

    def test_grade_file_not_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["grade", "file", "/nonexistent/file.txt"])
        assert result.exit_code != 0

    def test_grade_history_empty(self, runner: CliRunner):
        result = runner.invoke(cli, ["grade", "history"])
        assert result.exit_code == 0
        assert "暂无" in result.output

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_history_with_data(self, mock_run, runner: CliRunner):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        # 先批改一篇
        runner.invoke(cli, ["grade", "essay"], input="Some essay text.\n")

        result = runner.invoke(cli, ["grade", "history"])
        assert result.exit_code == 0
        assert "批改历史" in result.output

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_llm_failure(self, mock_run, runner: CliRunner):
        mock = MagicMock()
        mock.returncode = 1
        mock.stderr = "API error"
        mock.stdout = ""
        mock_run.return_value = mock

        result = runner.invoke(cli, ["grade", "essay"], input="Test essay.\n")
        assert result.exit_code == 0
        assert "失败" in result.output

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_shows_scores(self, mock_run, runner: CliRunner):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        result = runner.invoke(cli, ["grade", "essay"], input="Test essay text.\n")
        assert result.exit_code == 0
        # 应该显示四维评分
        assert "6.5" in result.output or "批改" in result.output

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_shows_suggestions(self, mock_run, runner: CliRunner):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        result = runner.invoke(cli, ["grade", "essay"], input="Test essay text.\n")
        assert result.exit_code == 0
        assert "改进建议" in result.output or "建议" in result.output


# ---- Tests: deploy 命令组 ----

class TestDeployCLI:

    def test_deploy_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "setup" in result.output
        assert "push" in result.output
        assert "status" in result.output

    def test_deploy_status_not_initialized(self, runner: CliRunner):
        result = runner.invoke(cli, ["deploy", "status"])
        assert result.exit_code == 0
        assert "未初始化" in result.output

    def test_deploy_push_not_initialized(self, runner: CliRunner):
        result = runner.invoke(cli, ["deploy", "push"])
        assert result.exit_code == 0
        assert "尚未初始化" in result.output

    @patch("ielts_buddy.services.deploy_service.subprocess.run")
    def test_deploy_setup(self, mock_run, runner: CliRunner):
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "get-url" in cmd:
                return MagicMock(returncode=1, stderr="not found", stdout="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        result = runner.invoke(cli, ["deploy", "setup", "--repo", "https://github.com/user/repo.git"])
        assert result.exit_code == 0
        assert "初始化完成" in result.output

    def test_deploy_setup_missing_repo(self, runner: CliRunner):
        result = runner.invoke(cli, ["deploy", "setup"])
        assert result.exit_code != 0


# ---- Tests: CLI 注册 ----

class TestCLIRegistration:

    def test_grade_in_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "grade" in result.output

    def test_deploy_in_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "deploy" in result.output
