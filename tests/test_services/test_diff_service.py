"""测试 diff_service"""

from __future__ import annotations

from rich.text import Text

from ielts_buddy.services.diff_service import diff_lines, diff_summary, diff_texts


class TestDiffTexts:

    def test_identical_texts(self):
        result = diff_texts("hello world", "hello world")
        assert isinstance(result, Text)
        assert result.plain == "hello world"

    def test_completely_different(self):
        result = diff_texts("abc", "xyz")
        assert isinstance(result, Text)
        # 应包含原文和改写
        assert "abc" in result.plain
        assert "xyz" in result.plain

    def test_insertion(self):
        result = diff_texts("hello", "hello world")
        assert isinstance(result, Text)
        assert "hello" in result.plain
        assert "world" in result.plain

    def test_deletion(self):
        result = diff_texts("hello world", "hello")
        assert isinstance(result, Text)
        assert "hello" in result.plain

    def test_replacement(self):
        result = diff_texts("I think this is good.", "I believe this is excellent.")
        plain = result.plain
        # diff 输出应包含原文和改写的混合内容
        assert len(plain) > 0
        # 共同部分应被保留
        assert "I " in plain
        assert "this is " in plain

    def test_empty_original(self):
        result = diff_texts("", "new text")
        assert result.plain == "new text"

    def test_empty_rewrite(self):
        result = diff_texts("old text", "")
        assert result.plain == "old text"

    def test_both_empty(self):
        result = diff_texts("", "")
        assert result.plain == ""

    def test_multiline_diff(self):
        original = "First line.\nSecond line.\nThird line."
        rewrite = "First line.\nModified second.\nThird line."
        result = diff_texts(original, rewrite)
        assert isinstance(result, Text)
        assert "First line." in result.plain


class TestDiffLines:

    def test_identical_lines(self):
        result = diff_lines("line1\nline2", "line1\nline2")
        assert all(tag == "equal" for tag, _, _ in result)
        assert len(result) == 2

    def test_added_line(self):
        result = diff_lines("line1", "line1\nline2")
        tags = [tag for tag, _, _ in result]
        assert "insert" in tags

    def test_deleted_line(self):
        result = diff_lines("line1\nline2", "line1")
        tags = [tag for tag, _, _ in result]
        assert "delete" in tags

    def test_replaced_line(self):
        result = diff_lines("old line", "new line")
        tags = [tag for tag, _, _ in result]
        assert "replace" in tags

    def test_empty_original(self):
        result = diff_lines("", "new")
        assert len(result) >= 1

    def test_mixed_changes(self):
        original = "keep\ndelete_me\nkeep2"
        rewrite = "keep\nadd_me\nkeep2"
        result = diff_lines(original, rewrite)
        assert len(result) >= 3


class TestDiffSummary:

    def test_identical(self):
        stats = diff_summary("same text", "same text")
        assert stats["equal"] == len("same text")
        assert stats["delete"] == 0
        assert stats["insert"] == 0
        assert stats["replace_old"] == 0
        assert stats["replace_new"] == 0

    def test_pure_insertion(self):
        stats = diff_summary("abc", "abcdef")
        assert stats["insert"] > 0

    def test_pure_deletion(self):
        stats = diff_summary("abcdef", "abc")
        assert stats["delete"] > 0

    def test_replacement(self):
        stats = diff_summary("old text", "new text")
        assert stats["replace_old"] > 0 or stats["delete"] > 0

    def test_empty_both(self):
        stats = diff_summary("", "")
        assert all(v == 0 for v in stats.values())

    def test_essay_diff(self):
        """模拟实际作文对比"""
        original = "Education is important. I think everyone should study."
        rewrite = "Education plays a crucial role. It is widely acknowledged that everyone should pursue academic studies."
        stats = diff_summary(original, rewrite)
        # 应有一些保留和变化
        assert stats["equal"] > 0 or stats["replace_old"] > 0 or stats["insert"] > 0
