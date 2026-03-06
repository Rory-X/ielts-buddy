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
    current_streak, max_streak = svc.get_streak()

    svc.close()

    # 今日概览
    today_info = (
        f"  新学单词: [bold cyan]{today['new_words']}[/bold cyan]\n"
        f"  复习单词: [bold green]{today['reviewed_words']}[/bold green]\n"
        f"  待复习:   [bold yellow]{due}[/bold yellow]\n"
        f"  连续学习: [bold magenta]{current_streak}[/bold magenta] 天"
        f"  (最长 {max_streak} 天)"
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


@stats.command()
@click.option("-d", "--days", default=7, help="显示天数", show_default=True)
def trend(days: int):
    """显示每日学习趋势"""
    svc = StatsService()
    data = svc.get_daily_trend(days=days)
    svc.close()

    if not data or all(count == 0 for _, count, _ in data):
        console.print("[dim]暂无学习记录，无法显示趋势。[/dim]")
        return

    max_count = max(count for _, count, _ in data)

    table = Table(title=f"学习趋势 (最近 {days} 天)", show_lines=False)
    table.add_column("日期", style="dim", min_width=10)
    table.add_column("数量", justify="right", min_width=4)
    table.add_column("趋势", min_width=25)

    for d, count, _ in data:
        bar_len = int(count / max_count * 25) if max_count > 0 else 0
        bar = "█" * bar_len
        color = "green" if count > 0 else "dim"
        table.add_row(d, str(count), f"[{color}]{bar}[/{color}]")

    console.print(table)

    total = sum(count for _, count, _ in data)
    active_days = sum(1 for _, count, _ in data if count > 0)
    avg = total / active_days if active_days > 0 else 0
    console.print(f"\n[dim]合计: {total} 词  |  活跃天数: {active_days}  |  日均: {avg:.1f} 词[/dim]")


@stats.command()
def progress():
    """显示各 Band 掌握进度"""
    svc = StatsService()
    data = svc.get_band_progress()
    svc.close()

    table = Table(title="Band 掌握进度", show_lines=False)
    table.add_column("Band", justify="center", style="bold", min_width=6)
    table.add_column("进度", min_width=30)
    table.add_column("已掌握", justify="right", min_width=10)
    table.add_column("比例", justify="right", min_width=6)

    for band, total, mastered, ratio in data:
        # 进度条：已掌握部分用实心，剩余用空心
        bar_width = 25
        filled = int(ratio * bar_width)
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty
        color = "green" if ratio >= 0.8 else "yellow" if ratio >= 0.3 else "cyan"
        table.add_row(
            f"Band {band}",
            f"[{color}]{bar}[/{color}]",
            f"{mastered}/{total}",
            f"[{color}]{ratio:.0%}[/{color}]",
        )

    console.print(table)
    console.print("[dim]掌握标准: 记忆等级 >= 4 (7天间隔以上)[/dim]")


@stats.command()
@click.option("-n", "--days", default=7, help="显示天数", show_default=True)
def history(days: int):
    """查看最近的学习日志"""
    svc = StatsService()
    data = svc.get_history(days=days)
    svc.close()

    if not data or all(r["new_words"] == 0 and r["reviewed_words"] == 0 for r in data):
        console.print("[dim]暂无学习记录。[/dim]")
        return

    table = Table(title=f"学习历史 (最近 {days} 天)", show_lines=False)
    table.add_column("日期", style="dim", min_width=10)
    table.add_column("新学", justify="right", style="cyan", min_width=6)
    table.add_column("复习", justify="right", style="green", min_width=6)
    table.add_column("合计", justify="right", style="bold", min_width=6)

    total_new = 0
    total_review = 0
    for r in data:
        total_day = r["new_words"] + r["reviewed_words"]
        total_new += r["new_words"]
        total_review += r["reviewed_words"]

        if total_day == 0:
            table.add_row(r["date"], "-", "-", "[dim]0[/dim]")
        else:
            table.add_row(
                r["date"],
                str(r["new_words"]),
                str(r["reviewed_words"]),
                str(total_day),
            )

    table.add_row("", "", "", "")
    table.add_row(
        "[bold]合计[/bold]",
        f"[bold cyan]{total_new}[/bold cyan]",
        f"[bold green]{total_review}[/bold green]",
        f"[bold]{total_new + total_review}[/bold]",
    )

    console.print(table)
