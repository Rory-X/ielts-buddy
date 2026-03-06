"""grade 命令组：AI 写作批改"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from ielts_buddy.services.grading_service import GradingService

console = Console()

# 评分颜色映射
def _score_color(score: float) -> str:
    if score >= 7.0:
        return "green"
    if score >= 5.5:
        return "yellow"
    return "red"


def _score_bar(label: str, score: float, comment: str) -> str:
    """生成单维度评分展示"""
    color = _score_color(score)
    filled = int(score / 9 * 20)
    bar = "█" * filled + "░" * (20 - filled)
    return f"[bold]{label}[/bold]  [{color}]{bar}  {score:.1f}[/{color}]\n  [dim]{comment}[/dim]"


@click.group("grade")
def grade():
    """AI 写作批改命令"""


@grade.command()
@click.option("-t", "--topic", default=None, help="指定写作话题")
def essay(topic: str | None):
    """交互式输入作文并批改（输入完毕后按 Ctrl-D 提交）"""
    console.print("[bold cyan]请输入你的作文[/bold cyan] (输入完毕后按 Ctrl-D 提交)：")
    if topic:
        console.print(f"[dim]话题: {topic}[/dim]\n")

    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
    except KeyboardInterrupt:
        console.print("\n[dim]已取消[/dim]")
        return

    essay_text = "\n".join(lines).strip()
    if not essay_text:
        console.print("[yellow]作文内容为空，已取消。[/yellow]")
        return

    _do_grade(essay_text, topic)


@grade.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-t", "--topic", default=None, help="指定写作话题")
def file(path: str, topic: str | None):
    """从文件读取作文并批改"""
    file_path = Path(path)
    essay_text = file_path.read_text(encoding="utf-8").strip()
    if not essay_text:
        console.print("[yellow]文件内容为空。[/yellow]")
        return

    console.print(f"[dim]读取文件: {file_path} ({len(essay_text)} 字符)[/dim]")
    _do_grade(essay_text, topic)


@grade.command()
@click.option("-n", "--limit", default=10, help="显示条数", show_default=True)
def history(limit: int):
    """查看历史批改记录"""
    svc = GradingService()
    records = svc.get_history(limit)
    total = svc.get_history_count()
    avg = svc.get_average_score()
    svc.close()

    if not records:
        console.print("[yellow]暂无批改记录。[/yellow]")
        return

    console.print(f"\n[bold]批改历史[/bold]  共 {total} 条 | 平均分: [bold]{avg:.1f}[/bold]\n")

    table = Table(show_lines=True)
    table.add_column("#", justify="right", style="dim", min_width=3)
    table.add_column("时间", style="cyan", min_width=16)
    table.add_column("总分", justify="center", min_width=5)
    table.add_column("TR", justify="center", min_width=4)
    table.add_column("CC", justify="center", min_width=4)
    table.add_column("LR", justify="center", min_width=4)
    table.add_column("GRA", justify="center", min_width=4)
    table.add_column("话题", style="dim", min_width=10)

    for i, r in enumerate(records, 1):
        color = _score_color(r.overall_score)
        table.add_row(
            str(i),
            (r.graded_at or "")[:16],
            f"[{color}]{r.overall_score:.1f}[/{color}]",
            f"{r.task_response.score:.1f}",
            f"{r.coherence.score:.1f}",
            f"{r.lexical_resource.score:.1f}",
            f"{r.grammar.score:.1f}",
            (r.topic or "—")[:20],
        )

    console.print(table)


def _do_grade(essay_text: str, topic: str | None) -> None:
    """执行批改并展示结果"""
    console.print("\n[bold]正在批改...[/bold] 请稍候\n")

    svc = GradingService()
    try:
        result = svc.grade_essay(essay_text, topic)
    except RuntimeError as e:
        console.print(f"[red]批改失败: {e}[/red]")
        svc.close()
        return
    svc.close()

    # 总分展示
    color = _score_color(result.overall_score)
    score_text = f"[bold {color}]  ★ 总分: {result.overall_score:.1f} / 9.0  [/bold {color}]"
    console.print(Panel(score_text, border_style=color, title="批改结果"))

    # 四维评分
    dims = [
        ("Task Response (审题回应)", result.task_response),
        ("Coherence & Cohesion (连贯衔接)", result.coherence),
        ("Lexical Resource (词汇资源)", result.lexical_resource),
        ("Grammatical Range (语法)", result.grammar),
    ]
    dim_lines = []
    for label, dim in dims:
        dim_lines.append(_score_bar(label, dim.score, dim.comment))

    console.print(Panel("\n\n".join(dim_lines), title="四维评分", border_style="blue"))

    # 改进建议
    if result.suggestions:
        suggestions = "\n".join(f"  [bold]{i}.[/bold] {s}" for i, s in enumerate(result.suggestions, 1))
        console.print(Panel(suggestions, title="改进建议", border_style="yellow"))

    # 高分改写
    if result.rewrite:
        console.print(Panel(result.rewrite, title="高分改写示例", border_style="green"))
