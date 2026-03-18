"""写作批改服务：调用 LLM 批改雅思作文，存储历史记录"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from ielts_buddy.core.config import get_db_path
from ielts_buddy.core.models import (
    GradeDimension, GradeResult, ParagraphAnalysis, SentenceAnnotation,
)

GROK_PATH = "/home/node/clawd/tools/grok.py"

# 有效的 task_type 值
VALID_TASK_TYPES = {"task1_academic", "task1_general", "task2"}

_JSON_FORMAT = """\
你必须返回纯 JSON（不要包含 markdown 代码块），格式如下：
{
  "overall_score": 6.5,
  "task_response": {"score": 6.5, "comment": "..."},
  "coherence": {"score": 6.0, "comment": "..."},
  "lexical_resource": {"score": 7.0, "comment": "..."},
  "grammar": {"score": 6.5, "comment": "..."},
  "suggestions": ["建议1", "建议2", "建议3"],
  "rewrite": "高分改写示例（可选，200字以内）",
  "annotations": [
    {
      "sentence_index": 0,
      "original": "原句",
      "issue_type": "grammar",
      "severity": "minor",
      "comment": "问题说明（中文）",
      "suggestion": "修改建议（英文）"
    }
  ],
  "paragraphs": [
    {
      "para_index": 0,
      "role": "introduction",
      "has_topic_sentence": true,
      "structure_score": 7.0,
      "cohesion_devices": ["however", "therefore"],
      "comment": "段落评价（中文）"
    }
  ]
}

评分要求：
- overall_score 是四维平均分，四舍五入到 0.5
- 每个维度 score 范围 1-9，精确到 0.5
- comment 用中文，100字以内，指出具体问题
- suggestions 至少给出 3 条可操作的改进建议（中文）
- rewrite 提供一段高分改写示例（英文）
- annotations: 对每个有问题的句子做标注，issue_type 可选 grammar/vocabulary/coherence/style，severity 可选 minor/major/critical
- paragraphs: 对每段做结构分析，role 可选 introduction/body/conclusion"""

SYSTEM_PROMPT_TASK2 = f"""\
你是一位资深雅思考官，拥有 20 年评分经验。请严格按照 IELTS Writing Task 2 的四维评分标准批改作文。

{_JSON_FORMAT}"""

SYSTEM_PROMPT_TASK1_ACADEMIC = f"""\
你是一位资深雅思考官，拥有 20 年评分经验。请严格按照 IELTS Writing Task 1 (Academic) 的四维评分标准批改图表描述。

评估重点（Task 1 Academic 特有）：
- Task Achievement: 是否选取了关键特征？是否有清晰的 overview statement 概括主要趋势？数据描述是否准确？
- 是否避免了对每个数据点的简单罗列，而是有合理的分组和对比？
- 数据引用是否准确，是否包含具体数字支撑？

{_JSON_FORMAT}"""

SYSTEM_PROMPT_TASK1_GENERAL = f"""\
你是一位资深雅思考官，拥有 20 年评分经验。请严格按照 IELTS Writing Task 1 (General Training) 的四维评分标准批改信件。

评估重点（Task 1 General 特有）：
- Task Achievement: 信件目的是否清晰？是否涵盖了所有要点？
- 语气是否得当（formal/semi-formal/informal 取决于收信人）？
- 信件格式是否正确（称呼、结尾、段落组织）？
- 用语是否符合信件场景（如投诉信需要礼貌但坚定）？

{_JSON_FORMAT}"""

# 保持向后兼容的别名
SYSTEM_PROMPT = SYSTEM_PROMPT_TASK2

# task_type → system prompt 映射
_TASK_PROMPTS = {
    "task2": SYSTEM_PROMPT_TASK2,
    "task1_academic": SYSTEM_PROMPT_TASK1_ACADEMIC,
    "task1_general": SYSTEM_PROMPT_TASK1_GENERAL,
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS grade_history (
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
    error_summary_json TEXT DEFAULT '{}',
    graded_at TEXT NOT NULL
);
"""


class GradingService:
    """AI 写作批改服务"""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._migrate_add_task_type()
        self._conn.commit()

    def _migrate_add_task_type(self) -> None:
        """为已有 grade_history 表添加 task_type 和 error_summary_json 列（幂等）"""
        cursor = self._conn.execute("PRAGMA table_info(grade_history)")
        columns = {row[1] for row in cursor.fetchall()}
        if "task_type" not in columns:
            self._conn.execute(
                "ALTER TABLE grade_history ADD COLUMN task_type TEXT DEFAULT 'task2'"
            )
        if "error_summary_json" not in columns:
            self._conn.execute(
                "ALTER TABLE grade_history ADD COLUMN error_summary_json TEXT DEFAULT '{}'"
            )

    def close(self) -> None:
        self._conn.close()

    def grade_essay(
        self,
        essay_text: str,
        topic: str | None = None,
        task_type: str = "task2",
    ) -> GradeResult:
        """调用 LLM 批改作文，返回 GradeResult

        Args:
            essay_text: 作文正文
            topic: 题目（可选）
            task_type: 题型 (task1_academic / task1_general / task2)
        """
        if task_type not in VALID_TASK_TYPES:
            raise ValueError(
                f"无效的 task_type: '{task_type}'，"
                f"可选: {', '.join(sorted(VALID_TASK_TYPES))}"
            )
        prompt = self._build_prompt(essay_text, topic)
        system_prompt = _TASK_PROMPTS[task_type]
        raw = self._call_grok(prompt, system_prompt)
        result = self._parse_result(raw, essay_text, topic, task_type)
        self._save_history(result)
        return result

    def _build_prompt(self, essay_text: str, topic: str | None) -> str:
        parts = []
        if topic:
            parts.append(f"题目：{topic}")
        parts.append(f"作文内容：\n{essay_text}")
        return "\n\n".join(parts)

    def _call_grok(self, prompt: str, system_prompt: str | None = None) -> dict:
        """调用 grok.py，返回解析后的 JSON"""
        sp = system_prompt or SYSTEM_PROMPT
        try:
            result = subprocess.run(
                ["python3", GROK_PATH, prompt, "-s", sp, "--json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"grok.py 返回错误: {result.stderr}")

            outer = json.loads(result.stdout)
            content = outer.get("content", "")
            # content 可能被 markdown 代码块包裹
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                # 去掉首尾的 ``` 行
                lines = [l for l in lines if not l.strip().startswith("```")]
                content = "\n".join(lines)
            return json.loads(content)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e

    def _parse_result(
        self, data: dict, essay_text: str, topic: str | None, task_type: str = "task2"
    ) -> GradeResult:
        """将 LLM 返回的 JSON 解析为 GradeResult"""
        now = datetime.now().isoformat(timespec="seconds")

        # 解析句级标注
        annotations = []
        for ann in data.get("annotations", []):
            try:
                annotations.append(SentenceAnnotation(**ann))
            except Exception:
                continue

        # 解析段落分析
        paragraphs = []
        for para in data.get("paragraphs", []):
            try:
                paragraphs.append(ParagraphAnalysis(**para))
            except Exception:
                continue

        # 从标注中聚合错误类型分布
        error_summary: dict[str, int] = {}
        for ann in annotations:
            error_summary[ann.issue_type] = error_summary.get(ann.issue_type, 0) + 1

        return GradeResult(
            overall_score=float(data.get("overall_score", 5.0)),
            task_response=GradeDimension(**data.get("task_response", {"score": 5.0, "comment": ""})),
            coherence=GradeDimension(**data.get("coherence", {"score": 5.0, "comment": ""})),
            lexical_resource=GradeDimension(**data.get("lexical_resource", {"score": 5.0, "comment": ""})),
            grammar=GradeDimension(**data.get("grammar", {"score": 5.0, "comment": ""})),
            suggestions=data.get("suggestions", []),
            rewrite=data.get("rewrite", ""),
            essay_text=essay_text,
            topic=topic or "",
            task_type=task_type,
            annotations=annotations,
            paragraphs=paragraphs,
            error_summary=error_summary,
            graded_at=now,
        )

    def _save_history(self, result: GradeResult) -> None:
        """保存批改记录到数据库"""
        self._conn.execute(
            """INSERT INTO grade_history
               (essay_text, topic, overall_score,
                task_response_score, coherence_score, lexical_score, grammar_score,
                result_json, task_type, error_summary_json, graded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.essay_text,
                result.topic,
                result.overall_score,
                result.task_response.score,
                result.coherence.score,
                result.lexical_resource.score,
                result.grammar.score,
                result.model_dump_json(),
                result.task_type,
                json.dumps(result.error_summary, ensure_ascii=False),
                result.graded_at,
            ),
        )
        self._conn.commit()

    def get_history(self, limit: int = 20, task_type: str | None = None) -> list[GradeResult]:
        """获取历史批改记录，可按 task_type 筛选"""
        if task_type:
            rows = self._conn.execute(
                """SELECT result_json FROM grade_history
                   WHERE task_type = ?
                   ORDER BY id DESC LIMIT ?""",
                (task_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT result_json FROM grade_history
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        results = []
        for row in rows:
            try:
                data = json.loads(row["result_json"])
                results.append(GradeResult(**data))
            except (json.JSONDecodeError, Exception):
                continue
        return results

    def get_history_count(self) -> int:
        """获取批改记录总数"""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM grade_history").fetchone()
        return row["cnt"]

    def get_average_score(self) -> float:
        """获取历史平均分"""
        row = self._conn.execute(
            "SELECT AVG(overall_score) as avg_score FROM grade_history"
        ).fetchone()
        return row["avg_score"] or 0.0

    def get_error_stats(self) -> dict[str, int]:
        """聚合所有批改记录的错误类型分布"""
        rows = self._conn.execute(
            "SELECT error_summary_json FROM grade_history WHERE error_summary_json != '{}'"
        ).fetchall()
        totals: dict[str, int] = {}
        for row in rows:
            try:
                summary = json.loads(row["error_summary_json"])
                for err_type, count in summary.items():
                    totals[err_type] = totals.get(err_type, 0) + count
            except (json.JSONDecodeError, TypeError):
                continue
        return totals

    def get_error_trend(self, limit: int = 10) -> list[dict]:
        """获取最近 N 次批改的错误类型趋势

        Returns:
            [{graded_at, overall_score, error_summary}, ...]
            按时间正序排列（从旧到新）
        """
        rows = self._conn.execute(
            """SELECT graded_at, overall_score, error_summary_json
               FROM grade_history
               ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        result = []
        for row in reversed(rows):  # 反转为正序
            try:
                summary = json.loads(row["error_summary_json"])
            except (json.JSONDecodeError, TypeError):
                summary = {}
            result.append({
                "graded_at": row["graded_at"],
                "overall_score": row["overall_score"],
                "error_summary": summary,
            })
        return result

    @staticmethod
    def extract_vocab_from_result(result: GradeResult) -> list[dict[str, str]]:
        """从批改结果中提取可加入词库的单词

        从 vocabulary 类型的标注中提取 suggestion 中的替换词，
        返回 [{"word": "...", "context": "原句", "suggestion": "修改建议"}, ...]
        """
        vocab_items = []
        for ann in result.annotations:
            if ann.issue_type == "vocabulary" and ann.suggestion:
                # 提取 suggestion 中可能的替换词（取第一个英文单词序列）
                words_in_suggestion = []
                for token in ann.suggestion.split():
                    clean = token.strip(".,;:!?\"'()[]")
                    if clean.isalpha() and len(clean) > 2:
                        words_in_suggestion.append(clean)
                vocab_items.append({
                    "word": " ".join(words_in_suggestion[:5]) if words_in_suggestion else ann.suggestion[:50],
                    "context": ann.original,
                    "suggestion": ann.suggestion,
                    "comment": ann.comment,
                })
        return vocab_items
