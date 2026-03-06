"""IELTS Buddy CLI 入口"""

import click
from rich.console import Console

from ielts_buddy.commands.deploy import deploy
from ielts_buddy.commands.email import email
from ielts_buddy.commands.exam import exam
from ielts_buddy.commands.feishu import feishu
from ielts_buddy.commands.grade import grade
from ielts_buddy.commands.recommend import recommend
from ielts_buddy.commands.listen import listen
from ielts_buddy.commands.plan import plan
from ielts_buddy.commands.report import report
from ielts_buddy.commands.speak import speak
from ielts_buddy.commands.stats import stats
from ielts_buddy.commands.sync import sync
from ielts_buddy.commands.vocab import vocab
from ielts_buddy.commands.write import write


def _show_daily_reminder():
    """显示每日学习提醒（仅在设置了学习计划时显示）"""
    try:
        from ielts_buddy.core.config import get_app_dir

        plan_path = get_app_dir() / "plan.json"
        if not plan_path.exists():
            return

        from ielts_buddy.services.plan_service import PlanService
        from ielts_buddy.services.stats_service import StatsService

        plan_svc = PlanService()
        plan_data = plan_svc.get_plan()
        if plan_data is None:
            return

        stats_svc = StatsService()
        due = stats_svc.due_count()
        today = stats_svc.today_stats()
        stats_svc.close()

        suggested = max(0, plan_data.daily_new - today["new_words"])
        parts = []
        if due > 0:
            parts.append(f"待复习: {due}")
        if suggested > 0:
            parts.append(f"建议新学: {suggested}")

        if parts:
            console = Console(stderr=True)
            console.print(f"[dim]-- {' | '.join(parts)} --[/dim]")
    except Exception:
        pass  # 静默失败，不影响正常使用


@click.group()
@click.version_option(version="0.1.0", prog_name="ielts-buddy")
@click.pass_context
def cli(ctx):
    """IELTS Buddy - 雅思词汇学习助手"""
    if ctx.invoked_subcommand is not None:
        _show_daily_reminder()


cli.add_command(vocab)
cli.add_command(stats)
cli.add_command(plan)
cli.add_command(sync)
cli.add_command(email)
cli.add_command(write)
cli.add_command(speak)
cli.add_command(report)
cli.add_command(listen)
cli.add_command(grade)
cli.add_command(deploy)
cli.add_command(exam)
cli.add_command(feishu)
cli.add_command(recommend)


if __name__ == "__main__":
    cli()
