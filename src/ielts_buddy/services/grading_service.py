"""写作批改服务：调用 LLM 批改雅思作文，存储历史记录"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from ielts_buddy.core.config import get_db_path
from ielts_buddy.core.models import GradeDimension, GradeResult

GROK_PATH = "/home/node/clawd/tools/grok.py"

SYSTEM_PROMPT = """\
你是一位资深雅思考官，拥有 20 年评分经验。请严格按照 IELTS Writing Task 2 的四维评分标准批改作文。

你必须返回纯 JSON（不要包含 markdown 代码块），格式如下：
{
  "overall_score": 6.5,
  "task_response": {"score": 6.5, "comment": "..."},
  "coherence": {"score": 6.0, "comment": "..."},
  "lexical_resource": {"score": 7.0, "comment": "..."},
  "grammar": {"score": 6.5, "comment": "..."},
  "suggestions": ["建议1", "建议2", "建议3"],
  "rewrite": "高分改写示例（可选，200字以内）"
}

评分要求：
- overall_score 是四维平均分，四舍五入到 0.5
- 每个维度 score 范围 1-9，精确到 0.5
- comment 用中文，100字以内，指出具体问题
- suggestions 至少给出 3 条可操作的改进建议（中文）
- rewrite 提供一段高分改写示例（英文）"""

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
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def grade_essay(self, essay_text: str, topic: str | None = None) -> GradeResult:
        """调用 LLM 批改作文，返回 GradeResult"""
        prompt = self._build_prompt(essay_text, topic)
        raw = self._call_grok(prompt)
        result = self._parse_result(raw, essay_text, topic)
        self._save_history(result)
        return result

    def _build_prompt(self, essay_text: str, topic: str | None) -> str:
        parts = []
        if topic:
            parts.append(f"题目：{topic}")
        parts.append(f"作文内容：\n{essay_text}")
        return "\n\n".join(parts)

    def _call_grok(self, prompt: str) -> dict:
        """调用 grok.py，返回解析后的 JSON"""
        try:
            result = subprocess.run(
                ["python3", GROK_PATH, prompt, "-s", SYSTEM_PROMPT, "--json"],
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
        self, data: dict, essay_text: str, topic: str | None
    ) -> GradeResult:
        """将 LLM 返回的 JSON 解析为 GradeResult"""
        now = datetime.now().isoformat(timespec="seconds")
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
            graded_at=now,
        )

    def _save_history(self, result: GradeResult) -> None:
        """保存批改记录到数据库"""
        self._conn.execute(
            """INSERT INTO grade_history
               (essay_text, topic, overall_score,
                task_response_score, coherence_score, lexical_score, grammar_score,
                result_json, graded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.essay_text,
                result.topic,
                result.overall_score,
                result.task_response.score,
                result.coherence.score,
                result.lexical_resource.score,
                result.grammar.score,
                result.model_dump_json(),
                result.graded_at,
            ),
        )
        self._conn.commit()

    def get_history(self, limit: int = 20) -> list[GradeResult]:
        """获取历史批改记录"""
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
