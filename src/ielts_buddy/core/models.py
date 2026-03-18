"""Pydantic 数据模型定义"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Word(BaseModel):
    """词库单词模型"""

    id: Optional[int] = None
    word: str
    phonetic: str = ""
    meaning: str
    pos: str = ""  # 词性: n., v., adj., adv. 等
    band: int = Field(ge=5, le=9)  # 雅思 Band 5-9
    topic: str = ""  # 主题: education, environment, ...
    example: str = ""  # 英文例句
    example_cn: str = ""  # 例句中文翻译
    collocations: list[str] = Field(default_factory=list)  # 常用搭配
    synonyms: list[str] = Field(default_factory=list)  # 同义词
    etymology: str = ""  # 词根词缀/助记
    is_custom: bool = False  # 是否用户自定义
    created_at: Optional[str] = None

    def collocations_json(self) -> str:
        """序列化搭配为 JSON 字符串"""
        return json.dumps(self.collocations, ensure_ascii=False)

    def synonyms_json(self) -> str:
        """序列化同义词为 JSON 字符串"""
        return json.dumps(self.synonyms, ensure_ascii=False)

    @staticmethod
    def parse_json_field(value: str | None) -> list[str]:
        """从 JSON 字符串解析列表字段"""
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


class LearningRecord(BaseModel):
    """学习记录模型"""

    id: Optional[int] = None
    word_id: int
    memory_level: int = Field(default=0, ge=0, le=6)  # 记忆等级 0-6
    next_review: Optional[str] = None  # ISO 日期 YYYY-MM-DD
    learn_count: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    first_learned: Optional[str] = None  # ISO datetime
    last_reviewed: Optional[str] = None  # ISO datetime
    is_starred: bool = False
    is_difficult: bool = False


class TestSession(BaseModel):
    """测试会话模型"""

    id: Optional[int] = None
    session_id: str
    test_date: str  # ISO datetime
    test_mode: str  # spelling / meaning / choice / context
    total_count: int
    correct_count: int
    wrong_words: list[str] = Field(default_factory=list)  # 错误的单词列表
    duration: Optional[int] = None  # 秒
    band_filter: Optional[int] = None
    topic_filter: Optional[str] = None

    def wrong_words_json(self) -> str:
        """序列化错误单词为 JSON 字符串"""
        return json.dumps(self.wrong_words, ensure_ascii=False)

    @property
    def accuracy(self) -> float:
        """正确率"""
        if self.total_count == 0:
            return 0.0
        return self.correct_count / self.total_count


class DailySummary(BaseModel):
    """每日学习摘要模型"""

    id: Optional[int] = None
    date: str  # YYYY-MM-DD
    new_words: int = 0
    reviewed_words: int = 0
    test_accuracy: Optional[float] = None
    study_minutes: int = 0
    streak_days: int = 0


class StudyPlan(BaseModel):
    """学习计划模型"""

    target_band: int = Field(default=7, ge=5, le=9)
    daily_new: int = Field(default=30, ge=1)
    exam_date: Optional[str] = None  # YYYY-MM-DD
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ExamQuestion(BaseModel):
    """模拟考试单题模型"""

    index: int  # 题号 (0-based)
    word: str  # 原始单词
    mode: str  # "en2zh" 或 "zh2en"
    prompt: str  # 题目显示文本
    answer: str  # 正确答案
    band: int = 5  # 单词 band 等级
    user_answer: Optional[str] = None  # 用户的回答
    is_correct: Optional[bool] = None  # 是否正确


class ExamSession(BaseModel):
    """模拟考试会话模型"""

    id: str  # UUID
    questions: list[ExamQuestion] = Field(default_factory=list)
    time_limit: int = 20  # 分钟
    started_at: str = ""  # ISO datetime
    finished_at: Optional[str] = None  # ISO datetime
    band_filter: Optional[int] = None


class ExamReport(BaseModel):
    """模拟考试报告模型"""

    session_id: str
    score: int = 0
    total: int = 0
    accuracy: float = 0.0
    band_breakdown: dict[int, dict[str, int]] = Field(default_factory=dict)
    weak_words: list[str] = Field(default_factory=list)
    duration: int = 0  # 秒
    finished_at: str = ""


class PersonalWord(BaseModel):
    """个人词库单词模型"""

    id: Optional[int] = None
    word: str
    phonetic: str = ""
    meaning: str = ""
    pos: str = ""
    band: int = Field(default=5, ge=5, le=9)
    topic: str = ""
    example: str = ""
    example_cn: str = ""
    note: str = ""  # 用户笔记
    source: str = "manual"  # manual / quiz_mistake / grading / import
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VocabCategory(BaseModel):
    """词库分类模型"""

    id: Optional[int] = None
    name: str
    description: str = ""
    is_system: bool = False  # 系统内置分类不可删除
    word_count: int = 0
    created_at: Optional[str] = None


class GradeDimension(BaseModel):
    """写作批改单维度评分"""

    score: float = Field(ge=1.0, le=9.0)
    comment: str = ""


class SentenceAnnotation(BaseModel):
    """句级标注：标记单句的具体问题"""

    sentence_index: int  # 句子序号（从 0 开始）
    original: str  # 原句
    issue_type: str  # grammar / vocabulary / coherence / style
    severity: str = "minor"  # minor / major / critical
    comment: str  # 问题说明（中文）
    suggestion: str = ""  # 修改建议（英文）


class ParagraphAnalysis(BaseModel):
    """段落结构分析"""

    para_index: int  # 段落序号（从 0 开始）
    role: str  # introduction / body / conclusion
    has_topic_sentence: bool = False
    structure_score: float = Field(default=5.0, ge=1.0, le=9.0)
    cohesion_devices: list[str] = Field(default_factory=list)  # 检测到的衔接词
    comment: str = ""


class GradeResult(BaseModel):
    """AI 写作批改结果"""

    overall_score: float = Field(ge=1.0, le=9.0)
    task_response: GradeDimension
    coherence: GradeDimension
    lexical_resource: GradeDimension
    grammar: GradeDimension
    suggestions: list[str] = Field(default_factory=list)
    rewrite: str = ""
    essay_text: str = ""
    topic: str = ""
    task_type: str = "task2"  # task1_academic / task1_general / task2
    annotations: list[SentenceAnnotation] = Field(default_factory=list)
    paragraphs: list[ParagraphAnalysis] = Field(default_factory=list)
    error_summary: dict[str, int] = Field(default_factory=dict)  # {"grammar": 5, ...}
    graded_at: Optional[str] = None
