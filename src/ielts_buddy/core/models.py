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
