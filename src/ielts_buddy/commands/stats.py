"""stats 命令组：学习统计"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.stats_service import StatsService

console = Console()

LEVEL_LABELS = {
    0: "未掌握",
    1: "刚学习",
    2: "初记忆",
    3: "短期记忆",
    4: "中期记忆",
    5: "长期记忆",
    6: "已掌握",
}

LEVEL_BARS = "░▒▓█"


@click.group("stats")
def stats():
    """学习统计命令"""


@stats.command()
def show():
    """显示学习统计概览"""
    svc = StatsService()

    total = svc.total_stats()
    today = svc.today_stats()
    due = svc.due_count()
    levels = svc.level_distribution()

    svc.close()

    # 今日概览
    today_info = (
        f"  新学单词: [bold cyan]{today['new_words']}[/bold cyan]\n"
        f"  复习单词: [bold green]{today['reviewed_words']}[/bold green]\n"
        f"  待复习:   [bold yellow]{due}[/bold yellow]"
    )
    console.print(Panel(today_info, title="[bold]今日学习[/bold]", border_style="cyan"))

    # 总体统计
    total_table = Table(show_header=False, box=None, padding=(0, 2))
    total_table.add_column("指标", style="bold")
    total_table.add_column("数值", justify="right")

    total_table.add_row("已学单词", f"[cyan]{total['total_words']}[/cyan]")
    total_table.add_row("总复习次数", f"[green]{total['total_reviews']}[/green]")
    total_table.add_row("总正确次数", f"[green]{total['total_correct']}[/green]")
    total_table.add_row("总错误次数", f"[red]{total['total_wrong']}[/red]")
    total_table.add_row("总正确率", f"[yellow]{total['accuracy']:.1%}[/yellow]")
    total_table.add_row("已掌握 (Lv5+)", f"[bold green]{total['mastered']}[/bold green]")

    console.print(Panel(total_table, title="[bold]总体统计[/bold]", border_style="green"))

    # 记忆等级分布
    if levels:
        level_table = Table(title="记忆等级分布", show_lines=False)
        level_table.add_column("等级", justify="center", min_width=4)
        level_table.add_column("描述", min_width=10)
        level_table.add_column("数量", justify="right", min_width=6)
        level_table.add_column("分布", min_width=20)

        max_count = max(levels.values()) if levels else 1
        for lv in range(7):
            cnt = levels.get(lv, 0)
            label = LEVEL_LABELS.get(lv, f"等级{lv}")
            bar_len = int(cnt / max_count * 20) if max_count > 0 else 0
            bar = "█" * bar_len
            color = "red" if lv <= 1 else "yellow" if lv <= 3 else "green"
            level_table.add_row(str(lv), label, str(cnt), f"[{color}]{bar}[/{color}]")

        console.print(level_table)
    else:
        console.print("[dim]暂无学习记录，开始学习后将显示统计数据。[/dim]")
