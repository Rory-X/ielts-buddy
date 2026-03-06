"""plan 命令组：学习计划管理"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.plan_service import PlanService
from ielts_buddy.services.stats_service import StatsService

console = Console()


@click.group("plan", invoke_without_command=True)
@click.pass_context
def plan(ctx):
    """学习计划命令"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(show)


@plan.command()
def show():
    """显示今日学习计划"""
    plan_svc = PlanService()
    plan_data = plan_svc.get_plan()

    if plan_data is None:
        console.print("[yellow]尚未设置学习计划。[/yellow]")
        console.print("[dim]使用 ib plan set --band 7 --daily 30 设置计划[/dim]")
        return

    stats_svc = StatsService()
    due = stats_svc.due_count()
    today = stats_svc.today_stats()
    stats_svc.close()

    suggested_new = max(0, plan_data.daily_new - today["new_words"])
    days_left = plan_svc.days_until_exam()

    # 今日计划面板
    lines = []
    lines.append(f"  目标等级:   [bold cyan]Band {plan_data.target_band}[/bold cyan]")
    lines.append(f"  每日目标:   [bold]{plan_data.daily_new}[/bold] 个新词")

    if plan_data.exam_date:
        if days_left is not None and days_left > 0:
            lines.append(f"  考试日期:   [bold yellow]{plan_data.exam_date}[/bold yellow]  (还剩 {days_left} 天)")
        elif days_left == 0:
            lines.append(f"  考试日期:   [bold red]{plan_data.exam_date}[/bold red]  (就是今天!)")
        else:
            lines.append(f"  考试日期:   [dim]{plan_data.exam_date}[/dim]  (已过期)")

    console.print(Panel("\n".join(lines), title="[bold]学习计划[/bold]", border_style="blue"))

    # 今日进度
    progress_lines = []
    progress_lines.append(f"  今日新学:   [bold cyan]{today['new_words']}[/bold cyan] / {plan_data.daily_new}")
    progress_lines.append(f"  今日复习:   [bold green]{today['reviewed_words']}[/bold green]")
    progress_lines.append(f"  待复习:     [bold yellow]{due}[/bold yellow]")

    if suggested_new > 0:
        progress_lines.append(f"  建议新学:   [bold magenta]{suggested_new}[/bold magenta] 个")
    else:
        progress_lines.append("  [green]今日新词目标已完成![/green]")

    console.print(Panel("\n".join(progress_lines), title="[bold]今日进度[/bold]", border_style="green"))


@plan.command("set")
@click.option("--band", type=int, default=None, help="目标 Band 等级 (5-9)")
@click.option("--daily", type=int, default=None, help="每日新学单词数")
@click.option("--exam-date", type=str, default=None, help="考试日期 (YYYY-MM-DD)")
def set_plan(band: int | None, daily: int | None, exam_date: str | None):
    """设置学习计划"""
    if band is None and daily is None and exam_date is None:
        console.print("[yellow]请至少指定一个参数: --band, --daily, --exam-date[/yellow]")
        console.print("[dim]示例: ib plan set --band 7 --daily 30 --exam-date 2026-06-01[/dim]")
        return

    # 验证 exam_date 格式
    if exam_date is not None:
        from datetime import date
        try:
            date.fromisoformat(exam_date)
        except ValueError:
            console.print(f"[red]日期格式错误: '{exam_date}'，请使用 YYYY-MM-DD 格式[/red]")
            return

    plan_svc = PlanService()
    plan_data = plan_svc.set_plan(target_band=band, daily_new=daily, exam_date=exam_date)

    console.print("[green]学习计划已更新:[/green]")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("项目", style="bold")
    table.add_column("值")

    table.add_row("目标等级", f"Band {plan_data.target_band}")
    table.add_row("每日新词", f"{plan_data.daily_new} 个")
    if plan_data.exam_date:
        table.add_row("考试日期", plan_data.exam_date)

    console.print(table)
