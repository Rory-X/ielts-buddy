"""差异对比服务：将原文与改写版本做 diff，生成 Rich 富文本标记"""

from __future__ import annotations

import difflib

from rich.text import Text


def diff_texts(original: str, rewrite: str) -> Text:
    """将原文与改写做 diff，返回带颜色标记的 Rich Text

    颜色规则：
    - 红色删除线: 原文中被删除的部分
    - 绿色: 改写中新增的部分
    - 黄色: 被替换的部分（原文）
    - 默认: 未改动的部分

    Args:
        original: 原文
        rewrite: 改写版本

    Returns:
        Rich Text 对象，可直接传给 console.print()
    """
    result = Text()
    matcher = difflib.SequenceMatcher(None, original, rewrite)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append(original[i1:i2])
        elif tag == "delete":
            result.append(original[i1:i2], style="red strike")
        elif tag == "insert":
            result.append(rewrite[j1:j2], style="green bold")
        elif tag == "replace":
            result.append(original[i1:i2], style="red strike")
            result.append(rewrite[j1:j2], style="green bold")

    return result


def diff_lines(original: str, rewrite: str) -> list[tuple[str, str, str]]:
    """逐行 diff，返回 [(标记, 原文行, 改写行), ...]

    标记: "equal" / "delete" / "insert" / "replace"
    """
    orig_lines = original.splitlines()
    rewrite_lines = rewrite.splitlines()
    matcher = difflib.SequenceMatcher(None, orig_lines, rewrite_lines)

    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in orig_lines[i1:i2]:
                result.append(("equal", line, line))
        elif tag == "delete":
            for line in orig_lines[i1:i2]:
                result.append(("delete", line, ""))
        elif tag == "insert":
            for line in rewrite_lines[j1:j2]:
                result.append(("insert", "", line))
        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                orig = orig_lines[i1 + k] if i1 + k < i2 else ""
                rewr = rewrite_lines[j1 + k] if j1 + k < j2 else ""
                result.append(("replace", orig, rewr))

    return result


def diff_summary(original: str, rewrite: str) -> dict[str, int]:
    """统计差异摘要：新增/删除/替换/保留的字符数"""
    matcher = difflib.SequenceMatcher(None, original, rewrite)
    stats = {"equal": 0, "delete": 0, "insert": 0, "replace_old": 0, "replace_new": 0}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            stats["equal"] += i2 - i1
        elif tag == "delete":
            stats["delete"] += i2 - i1
        elif tag == "insert":
            stats["insert"] += j2 - j1
        elif tag == "replace":
            stats["replace_old"] += i2 - i1
            stats["replace_new"] += j2 - j1

    return stats
