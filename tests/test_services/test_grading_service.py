"""测试 GradingService"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ielts_buddy.core.models import GradeDimension, GradeResult
from ielts_buddy.services.grading_service import GradingService, SYSTEM_PROMPT


# ---- Fixtures ----

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_data.db"


@pytest.fixture
def grading_service(tmp_db: Path) -> GradingService:
    svc = GradingService(db_path=tmp_db)
    yield svc
    svc.close()


def _mock_grok_response() -> dict:
    """模拟 grok.py 正常返回的 JSON"""
    return {
        "overall_score": 6.5,
        "task_response": {"score": 6.5, "comment": "观点表达较为清晰"},
        "coherence": {"score": 6.0, "comment": "段落衔接有待加强"},
        "lexical_resource": {"score": 7.0, "comment": "词汇使用较为丰富"},
        "grammar": {"score": 6.5, "comment": "语法基本准确"},
        "suggestions": ["多用复杂句式", "注意段落过渡", "丰富高级词汇"],
        "rewrite": "In contemporary society, the debate surrounding...",
    }


def _make_subprocess_result(data: dict, returncode: int = 0) -> MagicMock:
    """构造 subprocess.run 的 mock 返回值"""
    content = json.dumps(data, ensure_ascii=False)
    outer = json.dumps({"content": content, "model": "test", "usage": {}})
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = outer
    mock.stderr = ""
    return mock


# ---- Tests: GradeResult model ----

class TestGradeResultModel:

    def test_create_grade_dimension(self):
        dim = GradeDimension(score=7.0, comment="很好")
        assert dim.score == 7.0
        assert dim.comment == "很好"

    def test_grade_dimension_min_score(self):
        dim = GradeDimension(score=1.0, comment="")
        assert dim.score == 1.0

    def test_grade_dimension_max_score(self):
        dim = GradeDimension(score=9.0, comment="")
        assert dim.score == 9.0

    def test_grade_dimension_invalid_score_low(self):
        with pytest.raises(Exception):
            GradeDimension(score=0.5, comment="")

    def test_grade_dimension_invalid_score_high(self):
        with pytest.raises(Exception):
            GradeDimension(score=9.5, comment="")

    def test_create_grade_result(self):
        result = GradeResult(
            overall_score=6.5,
            task_response=GradeDimension(score=6.5, comment="ok"),
            coherence=GradeDimension(score=6.0, comment="ok"),
            lexical_resource=GradeDimension(score=7.0, comment="ok"),
            grammar=GradeDimension(score=6.5, comment="ok"),
            suggestions=["a", "b"],
            rewrite="rewrite text",
            essay_text="my essay",
            topic="education",
        )
        assert result.overall_score == 6.5
        assert result.task_response.score == 6.5
        assert len(result.suggestions) == 2
        assert result.essay_text == "my essay"

    def test_grade_result_defaults(self):
        result = GradeResult(
            overall_score=5.0,
            task_response=GradeDimension(score=5.0),
            coherence=GradeDimension(score=5.0),
            lexical_resource=GradeDimension(score=5.0),
            grammar=GradeDimension(score=5.0),
        )
        assert result.suggestions == []
        assert result.rewrite == ""
        assert result.essay_text == ""
        assert result.topic == ""

    def test_grade_result_serialization(self):
        result = GradeResult(
            overall_score=7.0,
            task_response=GradeDimension(score=7.0, comment="好"),
            coherence=GradeDimension(score=7.0, comment="好"),
            lexical_resource=GradeDimension(score=7.0, comment="好"),
            grammar=GradeDimension(score=7.0, comment="好"),
        )
        data = json.loads(result.model_dump_json())
        assert data["overall_score"] == 7.0
        assert data["task_response"]["score"] == 7.0

    def test_grade_result_deserialization(self):
        data = {
            "overall_score": 6.0,
            "task_response": {"score": 6.0, "comment": ""},
            "coherence": {"score": 6.0, "comment": ""},
            "lexical_resource": {"score": 6.0, "comment": ""},
            "grammar": {"score": 6.0, "comment": ""},
        }
        result = GradeResult(**data)
        assert result.overall_score == 6.0


# ---- Tests: GradingService._build_prompt ----

class TestBuildPrompt:

    def test_prompt_without_topic(self, grading_service: GradingService):
        prompt = grading_service._build_prompt("My essay text", None)
        assert "My essay text" in prompt
        assert "题目" not in prompt

    def test_prompt_with_topic(self, grading_service: GradingService):
        prompt = grading_service._build_prompt("My essay", "Education is important")
        assert "Education is important" in prompt
        assert "My essay" in prompt
        assert "题目" in prompt


# ---- Tests: GradingService._parse_result ----

class TestParseResult:

    def test_parse_normal(self, grading_service: GradingService):
        data = _mock_grok_response()
        result = grading_service._parse_result(data, "essay text", "topic")
        assert result.overall_score == 6.5
        assert result.task_response.score == 6.5
        assert result.coherence.score == 6.0
        assert result.lexical_resource.score == 7.0
        assert result.grammar.score == 6.5
        assert len(result.suggestions) == 3
        assert result.essay_text == "essay text"
        assert result.topic == "topic"
        assert result.graded_at is not None

    def test_parse_missing_fields(self, grading_service: GradingService):
        data = {"overall_score": 5.0}
        result = grading_service._parse_result(data, "text", None)
        assert result.overall_score == 5.0
        assert result.task_response.score == 5.0
        assert result.topic == ""

    def test_parse_with_rewrite(self, grading_service: GradingService):
        data = _mock_grok_response()
        result = grading_service._parse_result(data, "text", None)
        assert "contemporary" in result.rewrite


# ---- Tests: GradingService._call_grok ----

class TestCallGrok:

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_call_grok_success(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        result = grading_service._call_grok("test prompt")
        assert result["overall_score"] == 6.5
        mock_run.assert_called_once()

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_call_grok_with_markdown_wrapper(self, mock_run, grading_service: GradingService):
        """grok 返回内容被 markdown 代码块包裹"""
        data = _mock_grok_response()
        content = "```json\n" + json.dumps(data) + "\n```"
        outer = json.dumps({"content": content, "model": "test", "usage": {}})
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = outer
        mock.stderr = ""
        mock_run.return_value = mock

        result = grading_service._call_grok("test")
        assert result["overall_score"] == 6.5

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_call_grok_error(self, mock_run, grading_service: GradingService):
        mock = MagicMock()
        mock.returncode = 1
        mock.stderr = "API error"
        mock.stdout = ""
        mock_run.return_value = mock

        with pytest.raises(RuntimeError, match="grok.py 返回错误"):
            grading_service._call_grok("test")

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_call_grok_timeout(self, mock_run, grading_service: GradingService):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=120)

        with pytest.raises(RuntimeError, match="LLM 调用失败"):
            grading_service._call_grok("test")

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_call_grok_invalid_json(self, mock_run, grading_service: GradingService):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "not json"
        mock.stderr = ""
        mock_run.return_value = mock

        with pytest.raises(RuntimeError, match="LLM 调用失败"):
            grading_service._call_grok("test")


# ---- Tests: GradingService.grade_essay (integration with mock) ----

class TestGradeEssay:

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_success(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        result = grading_service.grade_essay("My essay about education", "Education topic")
        assert result.overall_score == 6.5
        assert result.essay_text == "My essay about education"
        assert result.topic == "Education topic"

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_no_topic(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        result = grading_service.grade_essay("My essay")
        assert result.topic == ""

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_saves_history(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        grading_service.grade_essay("Essay 1")
        grading_service.grade_essay("Essay 2")

        history = grading_service.get_history()
        assert len(history) == 2

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_failure(self, mock_run, grading_service: GradingService):
        mock = MagicMock()
        mock.returncode = 1
        mock.stderr = "error"
        mock.stdout = ""
        mock_run.return_value = mock

        with pytest.raises(RuntimeError):
            grading_service.grade_essay("text")


# ---- Tests: history ----

class TestGradeHistory:

    def test_empty_history(self, grading_service: GradingService):
        assert grading_service.get_history() == []
        assert grading_service.get_history_count() == 0

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_history_order(self, mock_run, grading_service: GradingService):
        """历史记录按时间倒序"""
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        grading_service.grade_essay("Essay 1")
        grading_service.grade_essay("Essay 2")

        history = grading_service.get_history()
        assert len(history) == 2
        # 最新的在前面
        assert history[0].essay_text == "Essay 2"
        assert history[1].essay_text == "Essay 1"

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_history_limit(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        for i in range(5):
            grading_service.grade_essay(f"Essay {i}")

        history = grading_service.get_history(limit=3)
        assert len(history) == 3

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_history_count(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        for i in range(3):
            grading_service.grade_essay(f"Essay {i}")

        assert grading_service.get_history_count() == 3

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_average_score(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())

        grading_service.grade_essay("Essay")

        avg = grading_service.get_average_score()
        assert avg == 6.5

    def test_average_score_empty(self, grading_service: GradingService):
        assert grading_service.get_average_score() == 0.0


# ---- Tests: system prompt ----

class TestSystemPrompt:

    def test_system_prompt_contains_json_format(self):
        assert "overall_score" in SYSTEM_PROMPT
        assert "task_response" in SYSTEM_PROMPT
        assert "suggestions" in SYSTEM_PROMPT

    def test_system_prompt_mentions_ielts(self):
        assert "雅思" in SYSTEM_PROMPT or "IELTS" in SYSTEM_PROMPT
