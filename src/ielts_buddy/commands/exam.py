"""exam 命令组：模拟考试"""

from __future__ import annotations

import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.exam_service import ExamService

console = Console()


@click.group("exam")
def exam():
    """模拟考试命令"""


@exam.command()
@click.option("-n", "--count", default=30, help="题目数量", show_default=True)
@click.option("-b", "--band", type=int, default=None, help="按 band 等级筛选 (5-9)")
@click.option("--time", "time_limit", default=20, help="考试时长（分钟）", show_default=True)
def start(count: int, band: int | None, time_limit: int):
    """开始模拟考试"""
    svc = ExamService()

    try:
        session = svc.create_exam(band=band, count=count, time_limit=time_limit)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        svc.close()
        return

    total = len(session.questions)
    band_label = f" Band {band}" if band else ""
    console.print(
        Panel(
            f"  题目数量: [bold cyan]{total}[/bold cyan]\n"
            f"  考试时长: [bold yellow]{time_limit}[/bold yellow] 分钟\n"
            f"  题型混合: 英译中 + 中译英{band_label}\n\n"
            f"  [dim]输入答案后按 Enter 提交，输入 q 提前结束[/dim]",
            title="[bold]模拟考试[/bold]",
            border_style="cyan",
        )
    )

    deadline = time.time() + time_limit * 60

    try:
        for i, q in enumerate(session.questions):
            remaining = deadline - time.time()
            if remaining <= 0:
                console.print("\n[bold red]时间到！考试自动提交。[/bold red]")
                break

            mins = int(remaining // 60)
            secs = int(remaining % 60)

            mode_label = "英→中" if q.mode == "en2zh" else "中→英"
            console.print(
                f"\n[bold cyan]({i + 1}/{total})[/bold cyan] [{mode_label}]  "
                f"[dim]剩余 {mins:02d}:{secs:02d}[/dim]"
            )
            console.print(f"  {q.prompt}")

            hint = "中文释义" if q.mode == "en2zh" else "英文单词"
            answer = input(f"  你的答案 ({hint}): ").strip()

            if answer.lower() == "q":
                console.print("[dim]提前结束考试[/dim]")
                break

            result = svc.submit_answer(session, i, answer)
            if result["correct"]:
                console.print("  [green]✓ 正确！[/green]")
            else:
                console.print(f"  [red]✗ 错误[/red]  正确答案: [yellow]{result['answer']}[/yellow]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]考试中断[/dim]")

    # 生成报告
    report = svc.finish_exam(session)
    svc.close()

    _show_report(report)


def _show_report(report):
    """显示考试报告"""
    if report.total == 0:
        console.print("[dim]未作答任何题目。[/dim]")
        return

    color = "green" if report.accuracy >= 0.8 else "yellow" if report.accuracy >= 0.6 else "red"
    mins = report.duration // 60
    secs = report.duration % 60

    info = (
        f"  得分: [bold {color}]{report.score}/{report.total}[/bold {color}]\n"
        f"  正确率: [bold {color}]{report.accuracy:.0%}[/bold {color}]\n"
        f"  用时: {mins} 分 {secs} 秒"
    )
    console.print(Panel(info, title="[bold]考试报告[/bold]", border_style=color))

    # Band 分布
    if report.band_breakdown:
        table = Table(title="Band 分布", show_lines=False)
        table.add_column("Band", justify="center", style="bold")
        table.add_column("正确", justify="right", style="green")
        table.add_column("错误", justify="right", style="red")
        table.add_column("正确率", justify="right")

        for band_level in sorted(report.band_breakdown):
            stats = report.band_breakdown[band_level]
            c = stats["correct"]
            w = stats["wrong"]
            t = c + w
            rate = c / t if t > 0 else 0.0
            rate_color = "green" if rate >= 0.8 else "yellow" if rate >= 0.6 else "red"
            table.add_row(
                str(band_level),
                str(c),
                str(w),
                f"[{rate_color}]{rate:.0%}[/{rate_color}]",
            )
        console.print(table)

    # 薄弱单词
    if report.weak_words:
        words_str = ", ".join(report.weak_words[:20])
        if len(report.weak_words) > 20:
            words_str += f" ...等 {len(report.weak_words)} 个"
        console.print(f"\n[bold]薄弱单词:[/bold] [yellow]{words_str}[/yellow]")


@exam.command()
@click.option("-n", "--count", default=10, help="显示条数", show_default=True)
def history(count: int):
    """查看考试历史记录"""
    svc = ExamService()
    reports = svc.get_exam_history(limit=count)
    svc.close()

    if not reports:
        console.print("[dim]暂无考试记录。[/dim]")
        return

    table = Table(title=f"考试历史 (最近 {len(reports)} 次)", show_lines=True)
    table.add_column("时间", style="dim", min_width=19)
    table.add_column("得分", justify="right", style="cyan")
    table.add_column("正确率", justify="right")
    table.add_column("用时", justify="right", style="dim")
    table.add_column("薄弱词", min_width=20)

    for r in reports:
        rate_color = "green" if r.accuracy >= 0.8 else "yellow" if r.accuracy >= 0.6 else "red"
        mins = r.duration // 60
        secs = r.duration % 60
        weak = ", ".join(r.weak_words[:5])
        if len(r.weak_words) > 5:
            weak += f" ...+{len(r.weak_words) - 5}"

        table.add_row(
            r.finished_at[:19] if r.finished_at else "-",
            f"{r.score}/{r.total}",
            f"[{rate_color}]{r.accuracy:.0%}[/{rate_color}]",
            f"{mins}:{secs:02d}",
            weak or "[green]全部正确[/green]",
        )

    console.print(table)
