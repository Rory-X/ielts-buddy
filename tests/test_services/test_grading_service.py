"""测试 GradingService"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ielts_buddy.core.models import (
    GradeDimension, GradeResult, ParagraphAnalysis, SentenceAnnotation,
)
from ielts_buddy.services.grading_service import (
    GradingService, SYSTEM_PROMPT, SYSTEM_PROMPT_TASK1_ACADEMIC,
    SYSTEM_PROMPT_TASK1_GENERAL, SYSTEM_PROMPT_TASK2, VALID_TASK_TYPES,
    _TASK_PROMPTS,
)


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


# ---- Tests: Task type support ----

class TestTaskType:

    def test_valid_task_types(self):
        assert "task2" in VALID_TASK_TYPES
        assert "task1_academic" in VALID_TASK_TYPES
        assert "task1_general" in VALID_TASK_TYPES

    def test_task_prompts_mapping(self):
        for tt in VALID_TASK_TYPES:
            assert tt in _TASK_PROMPTS
            assert len(_TASK_PROMPTS[tt]) > 100

    def test_task1_academic_prompt_content(self):
        assert "Task 1" in SYSTEM_PROMPT_TASK1_ACADEMIC
        assert "Academic" in SYSTEM_PROMPT_TASK1_ACADEMIC
        assert "overview" in SYSTEM_PROMPT_TASK1_ACADEMIC

    def test_task1_general_prompt_content(self):
        assert "Task 1" in SYSTEM_PROMPT_TASK1_GENERAL
        assert "General" in SYSTEM_PROMPT_TASK1_GENERAL
        assert "信件" in SYSTEM_PROMPT_TASK1_GENERAL

    def test_backward_compat_system_prompt(self):
        """SYSTEM_PROMPT 应该等于 SYSTEM_PROMPT_TASK2"""
        assert SYSTEM_PROMPT == SYSTEM_PROMPT_TASK2

    def test_grade_result_default_task_type(self):
        result = GradeResult(
            overall_score=5.0,
            task_response=GradeDimension(score=5.0),
            coherence=GradeDimension(score=5.0),
            lexical_resource=GradeDimension(score=5.0),
            grammar=GradeDimension(score=5.0),
        )
        assert result.task_type == "task2"

    def test_grade_result_task_type_serialization(self):
        result = GradeResult(
            overall_score=5.0,
            task_response=GradeDimension(score=5.0),
            coherence=GradeDimension(score=5.0),
            lexical_resource=GradeDimension(score=5.0),
            grammar=GradeDimension(score=5.0),
            task_type="task1_academic",
        )
        data = json.loads(result.model_dump_json())
        assert data["task_type"] == "task1_academic"

    def test_invalid_task_type_raises(self, grading_service: GradingService):
        with pytest.raises(ValueError, match="无效的 task_type"):
            grading_service.grade_essay("text", task_type="invalid")

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_task1_academic(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        result = grading_service.grade_essay("My report", task_type="task1_academic")
        assert result.task_type == "task1_academic"
        # 验证使用了正确的 system prompt
        call_args = mock_run.call_args[0][0]
        assert "-s" in call_args

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_grade_essay_task1_general(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        result = grading_service.grade_essay("Dear Sir", task_type="task1_general")
        assert result.task_type == "task1_general"

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_task_type_saved_in_history(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        grading_service.grade_essay("report", task_type="task1_academic")
        grading_service.grade_essay("essay", task_type="task2")

        # 全部历史
        all_history = grading_service.get_history()
        assert len(all_history) == 2

        # 按 task_type 筛选
        t1_history = grading_service.get_history(task_type="task1_academic")
        assert len(t1_history) == 1
        assert t1_history[0].task_type == "task1_academic"

    def test_parse_result_with_task_type(self, grading_service: GradingService):
        data = _mock_grok_response()
        result = grading_service._parse_result(data, "text", None, "task1_general")
        assert result.task_type == "task1_general"

    def test_migration_adds_task_type_column(self, tmp_path: Path):
        """模拟旧数据库（没有 task_type 列）"""
        import sqlite3
        db = tmp_path / "old.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""CREATE TABLE IF NOT EXISTS grade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            essay_text TEXT NOT NULL,
            topic TEXT DEFAULT '',
            overall_score REAL NOT NULL,
            task_response_score REAL,
            coherence_score REAL,
            lexical_score REAL,
            grammar_score REAL,
            result_json TEXT NOT NULL,
            graded_at TEXT NOT NULL
        )""")
        conn.commit()
        conn.close()

        svc = GradingService(db_path=db)
        # 应能正常使用 task_type
        row = svc._conn.execute("PRAGMA table_info(grade_history)").fetchall()
        columns = {r[1] for r in row}
        assert "task_type" in columns
        svc.close()


# ---- Tests: Sentence annotations & paragraph analysis ----

def _mock_grok_response_with_annotations() -> dict:
    """模拟包含句级标注和段落分析的 LLM 返回"""
    base = _mock_grok_response()
    base["annotations"] = [
        {
            "sentence_index": 0,
            "original": "Education is important for everyone.",
            "issue_type": "grammar",
            "severity": "minor",
            "comment": "主语过于简单",
            "suggestion": "Education plays a crucial role for everyone.",
        },
        {
            "sentence_index": 2,
            "original": "I think this is good.",
            "issue_type": "vocabulary",
            "severity": "major",
            "comment": "用词过于口语化",
            "suggestion": "It is widely acknowledged that this is beneficial.",
        },
        {
            "sentence_index": 5,
            "original": "And then we can see.",
            "issue_type": "coherence",
            "severity": "minor",
            "comment": "缺少逻辑衔接",
        },
    ]
    base["paragraphs"] = [
        {
            "para_index": 0,
            "role": "introduction",
            "has_topic_sentence": True,
            "structure_score": 7.0,
            "cohesion_devices": ["however", "in my opinion"],
            "comment": "开头段结构清晰",
        },
        {
            "para_index": 1,
            "role": "body",
            "has_topic_sentence": True,
            "structure_score": 6.0,
            "cohesion_devices": ["furthermore", "for example"],
            "comment": "论证需要更多展开",
        },
        {
            "para_index": 2,
            "role": "conclusion",
            "has_topic_sentence": False,
            "structure_score": 5.5,
            "cohesion_devices": ["in conclusion"],
            "comment": "结尾段过于简短",
        },
    ]
    return base


class TestSentenceAnnotationModel:

    def test_create_annotation(self):
        ann = SentenceAnnotation(
            sentence_index=0,
            original="Test sentence.",
            issue_type="grammar",
            comment="语法问题",
        )
        assert ann.sentence_index == 0
        assert ann.severity == "minor"  # default
        assert ann.suggestion == ""  # default

    def test_annotation_with_all_fields(self):
        ann = SentenceAnnotation(
            sentence_index=3,
            original="She go to school.",
            issue_type="grammar",
            severity="major",
            comment="主谓不一致",
            suggestion="She goes to school.",
        )
        assert ann.severity == "major"
        assert ann.suggestion == "She goes to school."

    def test_annotation_serialization(self):
        ann = SentenceAnnotation(
            sentence_index=0,
            original="Test.",
            issue_type="vocabulary",
            comment="用词问题",
        )
        data = json.loads(ann.model_dump_json())
        assert data["issue_type"] == "vocabulary"


class TestParagraphAnalysisModel:

    def test_create_paragraph(self):
        para = ParagraphAnalysis(
            para_index=0,
            role="introduction",
            comment="ok",
        )
        assert para.has_topic_sentence is False  # default
        assert para.structure_score == 5.0  # default
        assert para.cohesion_devices == []

    def test_paragraph_with_all_fields(self):
        para = ParagraphAnalysis(
            para_index=1,
            role="body",
            has_topic_sentence=True,
            structure_score=7.5,
            cohesion_devices=["however", "moreover"],
            comment="论证充分",
        )
        assert para.has_topic_sentence is True
        assert len(para.cohesion_devices) == 2

    def test_paragraph_score_range(self):
        with pytest.raises(Exception):
            ParagraphAnalysis(para_index=0, role="body", structure_score=0.5)
        with pytest.raises(Exception):
            ParagraphAnalysis(para_index=0, role="body", structure_score=9.5)


class TestParseAnnotations:

    def test_parse_with_annotations(self, grading_service: GradingService):
        data = _mock_grok_response_with_annotations()
        result = grading_service._parse_result(data, "essay", "topic")
        assert len(result.annotations) == 3
        assert result.annotations[0].issue_type == "grammar"
        assert result.annotations[1].severity == "major"

    def test_parse_with_paragraphs(self, grading_service: GradingService):
        data = _mock_grok_response_with_annotations()
        result = grading_service._parse_result(data, "essay", "topic")
        assert len(result.paragraphs) == 3
        assert result.paragraphs[0].role == "introduction"
        assert result.paragraphs[0].has_topic_sentence is True
        assert "however" in result.paragraphs[0].cohesion_devices

    def test_error_summary_aggregated(self, grading_service: GradingService):
        data = _mock_grok_response_with_annotations()
        result = grading_service._parse_result(data, "essay", "topic")
        assert result.error_summary == {"grammar": 1, "vocabulary": 1, "coherence": 1}

    def test_parse_without_annotations(self, grading_service: GradingService):
        """没有标注时默认空列表"""
        data = _mock_grok_response()
        result = grading_service._parse_result(data, "essay", "topic")
        assert result.annotations == []
        assert result.paragraphs == []
        assert result.error_summary == {}

    def test_parse_invalid_annotation_skipped(self, grading_service: GradingService):
        """无效标注被跳过，不影响其他"""
        data = _mock_grok_response()
        data["annotations"] = [
            {"invalid": "data"},
            {
                "sentence_index": 0,
                "original": "Valid.",
                "issue_type": "grammar",
                "comment": "ok",
            },
        ]
        result = grading_service._parse_result(data, "essay", "topic")
        assert len(result.annotations) == 1

    def test_annotations_in_history(self, grading_service: GradingService):
        """标注通过 result_json 持久化到 DB 并正确恢复"""
        data = _mock_grok_response_with_annotations()
        result = grading_service._parse_result(data, "essay", "topic")
        grading_service._save_history(result)

        history = grading_service.get_history()
        assert len(history) == 1
        restored = history[0]
        assert len(restored.annotations) == 3
        assert len(restored.paragraphs) == 3
        assert restored.error_summary == {"grammar": 1, "vocabulary": 1, "coherence": 1}

    def test_grade_result_backward_compat(self):
        """旧的 GradeResult JSON（无标注字段）反序列化正常"""
        old_data = {
            "overall_score": 6.0,
            "task_response": {"score": 6.0, "comment": ""},
            "coherence": {"score": 6.0, "comment": ""},
            "lexical_resource": {"score": 6.0, "comment": ""},
            "grammar": {"score": 6.0, "comment": ""},
        }
        result = GradeResult(**old_data)
        assert result.annotations == []
        assert result.paragraphs == []
        assert result.error_summary == {}
        assert result.task_type == "task2"

    def test_prompt_mentions_annotations(self):
        """prompt 中应包含 annotations 和 paragraphs 的说明"""
        from ielts_buddy.services.grading_service import SYSTEM_PROMPT_TASK2
        assert "annotations" in SYSTEM_PROMPT_TASK2
        assert "paragraphs" in SYSTEM_PROMPT_TASK2
        assert "issue_type" in SYSTEM_PROMPT_TASK2


# ---- Tests: Error classification statistics (Feature 1.4) ----


class TestErrorStats:

    def test_get_error_stats_empty(self, grading_service: GradingService):
        assert grading_service.get_error_stats() == {}

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_get_error_stats_aggregated(self, mock_run, grading_service: GradingService):
        """多次批改的错误类型应正确聚合"""
        data = _mock_grok_response_with_annotations()
        mock_run.return_value = _make_subprocess_result(data)

        grading_service.grade_essay("Essay 1")
        grading_service.grade_essay("Essay 2")

        stats = grading_service.get_error_stats()
        # 每篇都有 grammar:1, vocabulary:1, coherence:1
        assert stats["grammar"] == 2
        assert stats["vocabulary"] == 2
        assert stats["coherence"] == 2

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_error_stats_no_annotations(self, mock_run, grading_service: GradingService):
        """无标注的批改不影响统计"""
        mock_run.return_value = _make_subprocess_result(_mock_grok_response())
        grading_service.grade_essay("Essay without annotations")
        assert grading_service.get_error_stats() == {}

    def test_get_error_trend_empty(self, grading_service: GradingService):
        assert grading_service.get_error_trend() == []

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_get_error_trend(self, mock_run, grading_service: GradingService):
        data = _mock_grok_response_with_annotations()
        mock_run.return_value = _make_subprocess_result(data)

        grading_service.grade_essay("Essay 1")
        grading_service.grade_essay("Essay 2")

        trend = grading_service.get_error_trend()
        assert len(trend) == 2
        # 正序排列（Essay 1 先）
        assert trend[0]["overall_score"] == 6.5
        assert trend[0]["error_summary"] == {"grammar": 1, "vocabulary": 1, "coherence": 1}
        assert "graded_at" in trend[0]

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_get_error_trend_limit(self, mock_run, grading_service: GradingService):
        mock_run.return_value = _make_subprocess_result(_mock_grok_response_with_annotations())
        for i in range(5):
            grading_service.grade_essay(f"Essay {i}")

        trend = grading_service.get_error_trend(limit=3)
        assert len(trend) == 3

    @patch("ielts_buddy.services.grading_service.subprocess.run")
    def test_error_summary_persisted_in_column(self, mock_run, grading_service: GradingService):
        """error_summary_json 列应正确存储"""
        mock_run.return_value = _make_subprocess_result(_mock_grok_response_with_annotations())
        grading_service.grade_essay("Test essay")

        row = grading_service._conn.execute(
            "SELECT error_summary_json FROM grade_history"
        ).fetchone()
        summary = json.loads(row["error_summary_json"])
        assert summary == {"grammar": 1, "vocabulary": 1, "coherence": 1}

    def test_migration_adds_error_summary_column(self, tmp_path: Path):
        """旧数据库迁移后应包含 error_summary_json 列"""
        import sqlite3
        db = tmp_path / "old_v2.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""CREATE TABLE IF NOT EXISTS grade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            essay_text TEXT NOT NULL,
            topic TEXT DEFAULT '',
            overall_score REAL NOT NULL,
            task_response_score REAL,
            coherence_score REAL,
            lexical_score REAL,
            grammar_score REAL,
            result_json TEXT NOT NULL,
            task_type TEXT DEFAULT 'task2',
            graded_at TEXT NOT NULL
        )""")
        conn.commit()
        conn.close()

        svc = GradingService(db_path=db)
        row = svc._conn.execute("PRAGMA table_info(grade_history)").fetchall()
        columns = {r[1] for r in row}
        assert "error_summary_json" in columns
        svc.close()
