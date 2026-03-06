"""recommend 命令组：智能学习推荐"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.recommend_service import RecommendService

console = Console()


@click.group("recommend")
def recommend():
    """智能学习推荐"""


@recommend.command("show")
def show():
    """显示今日智能推荐"""
    svc = RecommendService()

    suggestion = svc.get_study_suggestion()
    prediction = svc.predict_mastery(days=7)
    weak = svc.get_weak_words(limit=5)
    due = svc.get_due_words(limit=5)

    svc.close()

    # 综合建议面板
    info_parts = [
        f"  待复习: [bold yellow]{suggestion['due_count']}[/bold yellow] 个",
        f"  薄弱词: [bold red]{suggestion['weak_count']}[/bold red] 个",
        f"  建议新学: [bold cyan]{suggestion['suggested_new']}[/bold cyan] 个",
        f"  重点 Band: [bold magenta]{suggestion['priority_band']}[/bold magenta]",
    ]
    console.print(Panel(
        "\n".join(info_parts),
        title="[bold]今日学习建议[/bold]",
        border_style="cyan",
    ))
    console.print(f"[dim]{suggestion['message']}[/dim]\n")

    # 掌握率预测
    if prediction["total_words"] > 0:
        console.print(
            f"当前掌握率: [bold green]{prediction['current_mastery']:.0%}[/bold green]"
            f"  ({prediction['mastered_now']}/{prediction['total_words']})"
        )
        console.print(
            f"预测 7 天后: [bold cyan]{prediction['predicted_mastery']:.0%}[/bold cyan]"
            f"  ({prediction['predicted_mastered']}/{prediction['total_words']})\n"
        )

    # 薄弱词提醒
    if weak:
        table = Table(title="薄弱词 TOP 5", show_lines=False)
        table.add_column("单词", style="bold red", min_width=15)
        table.add_column("释义", style="yellow", min_width=15)
        table.add_column("Band", justify="center")
        table.add_column("错误率", justify="right", style="red")

        for w in weak[:5]:
            table.add_row(
                w["word"],
                w["meaning"],
                str(w["band"]),
                f"{w['error_rate']:.0%}",
            )
        console.print(table)

    # 到期词提醒
    if due:
        table = Table(title="到期复习 TOP 5", show_lines=False)
        table.add_column("单词", style="bold cyan", min_width=15)
        table.add_column("释义", style="yellow", min_width=15)
        table.add_column("逾期天数", justify="right", style="red")

        for w in due[:5]:
            table.add_row(
                w["word"],
                w["meaning"],
                f"{w['overdue_days']} 天" if w["overdue_days"] > 0 else "今天",
            )
        console.print(table)

    if not weak and not due:
        console.print("[green]暂无学习记录，开始学习后将生成个性化推荐。[/green]")


@recommend.command("weak")
@click.option("-n", "--count", default=20, help="显示数量", show_default=True)
def weak(count: int):
    """查看薄弱词（错误率最高的词）"""
    svc = RecommendService()
    words = svc.get_weak_words(limit=count)
    svc.close()

    if not words:
        console.print("[green]没有薄弱词，继续保持！[/green]")
        return

    table = Table(title=f"薄弱词列表 (共 {len(words)} 个)", show_lines=True)
    table.add_column("单词", style="bold red", min_width=15)
    table.add_column("释义", style="yellow", min_width=15)
    table.add_column("Band", justify="center")
    table.add_column("学习", justify="right")
    table.add_column("正确", justify="right", style="green")
    table.add_column("错误", justify="right", style="red")
    table.add_column("错误率", justify="right", style="bold red")

    for w in words:
        table.add_row(
            w["word"],
            w["meaning"],
            str(w["band"]),
            str(w["learn_count"]),
            str(w["correct_count"]),
            str(w["wrong_count"]),
            f"{w['error_rate']:.0%}",
        )

    console.print(table)


@recommend.command("new")
@click.option("-n", "--count", default=10, help="推荐数量", show_default=True)
@click.option("-b", "--band", type=int, default=None, help="指定 Band 等级 (5-9)")
def new(count: int, band: int | None):
    """推荐新词（排除已学过的词）"""
    svc = RecommendService()
    words = svc.get_recommended_new(band=band, count=count)
    svc.close()

    if not words:
        band_str = f" Band {band}" if band else ""
        console.print(f"[yellow]没有更多{band_str}新词可推荐。[/yellow]")
        return

    band_str = f" Band {band}" if band else ""
    table = Table(title=f"推荐新词{band_str} (共 {len(words)} 个)", show_lines=True)
    table.add_column("单词", style="bold cyan", min_width=15)
    table.add_column("音标", style="dim")
    table.add_column("释义", style="yellow", min_width=15)
    table.add_column("Band", justify="center")
    table.add_column("主题", style="magenta")

    for w in words:
        table.add_row(
            w["word"],
            w.get("phonetic", ""),
            w["meaning"],
            str(w["band"]),
            w.get("topic", ""),
        )

    console.print(table)
