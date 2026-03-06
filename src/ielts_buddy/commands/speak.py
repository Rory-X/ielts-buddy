"""speak 命令组：口语练习（话题浏览、随机抽题、话题词汇）"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.speaking_service import SpeakingService

console = Console()

# Part 中文标签
_PART_LABELS = {
    1: "Part 1 (日常话题)",
    2: "Part 2 (个人陈述)",
    3: "Part 3 (深入讨论)",
}


@click.group("speak")
def speak():
    """口语练习命令"""


@speak.command()
@click.option(
    "-p", "--part",
    type=click.Choice(["1", "2", "3"]),
    default=None,
    help="按 Part 筛选 (1/2/3)",
)
def topics(part: str | None):
    """浏览口语话题"""
    svc = SpeakingService()
    part_int = int(part) if part else None
    items = svc.get_topics(part_int)

    if not items:
        console.print("[yellow]没有找到匹配的话题。[/yellow]")
        return

    part_label = _PART_LABELS.get(part_int, "全部") if part_int else "全部"
    table = Table(
        title=f"雅思口语话题 [{part_label}] (共 {len(items)} 个)",
        show_lines=True,
    )
    table.add_column("#", justify="right", style="dim", min_width=3)
    table.add_column("Part", style="bold", justify="center", min_width=4)
    table.add_column("话题", style="bold cyan", min_width=10)
    table.add_column("问题数", justify="center", style="green")
    table.add_column("关键词汇", style="yellow", min_width=20)

    # 计算全局索引
    all_topics = svc.get_topics()
    for item in items:
        idx = all_topics.index(item) + 1
        vocab_str = ", ".join(item["vocab"][:3])
        if len(item["vocab"]) > 3:
            vocab_str += "..."
        table.add_row(
            str(idx),
            str(item["part"]),
            item["topic"],
            str(len(item["questions"])),
            vocab_str,
        )

    console.print(table)
    console.print("\n[dim]提示: 使用 ib speak practice --part N 随机抽题练习[/dim]")


@speak.command()
@click.option(
    "-p", "--part",
    type=click.Choice(["1", "2", "3"]),
    default=None,
    help="按 Part 筛选 (1/2/3)",
)
def practice(part: str | None):
    """随机抽题练习"""
    svc = SpeakingService()
    part_int = int(part) if part else None
    topic = svc.get_random_topic(part_int)

    if not topic:
        console.print("[yellow]没有找到匹配的话题。[/yellow]")
        return

    part_label = _PART_LABELS.get(topic["part"], f"Part {topic['part']}")

    # 题目和问题
    parts = [
        f"[magenta][{part_label}][/magenta]",
        f"\n[bold cyan]{topic['topic']}[/bold cyan]",
        "",
    ]
    for i, q in enumerate(topic["questions"], 1):
        parts.append(f"  [white]{i}. {q}[/white]")

    # 关键词汇
    parts.append(f"\n[bold]关键词汇:[/bold]  [yellow]{', '.join(topic['vocab'])}[/yellow]")

    console.print(Panel("\n".join(parts), title="口语练习题", border_style="cyan"))

    # 范文和技巧
    answer_parts = [
        "[bold]参考范文:[/bold]",
        f"[italic]{topic['sample_answer']}[/italic]",
        "",
        "[bold]答题技巧:[/bold]",
        f"[green]{topic['tips']}[/green]",
    ]

    console.print(Panel("\n".join(answer_parts), title="参考答案", border_style="green"))


@speak.command()
@click.argument("topic")
def vocab(topic: str):
    """查看话题关键词汇"""
    svc = SpeakingService()
    result = svc.get_speaking_vocab(topic)

    if not result:
        console.print(f"[yellow]没有找到与 '{topic}' 相关的话题。[/yellow]")
        console.print("[dim]提示: 使用 ib speak topics 查看所有可用话题[/dim]")
        return

    part_label = _PART_LABELS.get(result["part"], f"Part {result['part']}")

    parts = [
        f"[bold cyan]{result['topic']}[/bold cyan]  [magenta][{part_label}][/magenta]",
        "",
        "[bold]相关问题:[/bold]",
    ]
    for q in result["questions"]:
        parts.append(f"  [white]• {q}[/white]")

    parts.append(f"\n[bold]关键词汇:[/bold]")
    for v in result["vocab"]:
        parts.append(f"  [green]• {v}[/green]")

    console.print(Panel("\n".join(parts), title="话题词汇", border_style="cyan"))
