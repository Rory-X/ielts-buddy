"""feishu 命令组：飞书 Bitable 数据同步"""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.feishu_service import FeishuService

console = Console()


@click.group("feishu")
def feishu():
    """飞书 Bitable 数据同步命令"""


@feishu.command("sync")
@click.option("--app-token", default=None, help="飞书 Bitable App Token")
@click.option("--table-id", default=None, help="飞书 Bitable Table ID")
def sync_vocab(app_token: str | None, table_id: str | None):
    """同步词汇学习数据到飞书 Bitable（导出 JSON）"""
    svc = FeishuService()
    app_token, table_id = _resolve_tokens(svc, app_token, table_id)
    if not app_token or not table_id:
        return

    try:
        filepath = svc.sync_to_bitable(app_token, table_id)
        console.print(f"[green]词汇数据已导出:[/green] {filepath}")
        console.print("[dim]请参考同目录下的 sync_instructions.md 完成导入[/dim]")
    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")


@feishu.command("stats")
@click.option("--app-token", default=None, help="飞书 Bitable App Token")
@click.option("--table-id", default=None, help="飞书 Bitable Table ID")
def sync_stats(app_token: str | None, table_id: str | None):
    """同步统计数据到飞书 Bitable（导出 JSON）"""
    svc = FeishuService()
    app_token, table_id = _resolve_tokens(svc, app_token, table_id)
    if not app_token or not table_id:
        return

    try:
        filepath = svc.sync_stats_to_bitable(app_token, table_id)
        console.print(f"[green]统计数据已导出:[/green] {filepath}")
    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")


@feishu.command("setup")
def setup():
    """交互式配置飞书 Bitable 连接参数"""
    svc = FeishuService()

    # 加载已有配置
    existing = svc.load_config()
    if existing:
        console.print(
            Panel(
                f"  App Token: [cyan]{existing.get('app_token', '')}[/cyan]\n"
                f"  Table ID:  [cyan]{existing.get('table_id', '')}[/cyan]\n"
                f"  更新时间:  [dim]{existing.get('updated_at', '')}[/dim]",
                title="[bold]当前配置[/bold]",
                border_style="cyan",
            )
        )

    try:
        default_token = existing.get("app_token", "") if existing else ""
        default_table = existing.get("table_id", "") if existing else ""

        app_token = input(f"  App Token [{default_token}]: ").strip() or default_token
        table_id = input(f"  Table ID [{default_table}]: ").strip() or default_table

        if not app_token or not table_id:
            console.print("[yellow]App Token 和 Table ID 不能为空[/yellow]")
            return

        config_path = svc.save_config(app_token, table_id)
        console.print(f"[green]配置已保存:[/green] {config_path}")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]配置取消[/dim]")


@feishu.command("schema")
@click.option("--app-token", default=None, help="飞书 Bitable App Token")
@click.option("--table-id", default=None, help="飞书 Bitable Table ID")
def schema(app_token: str | None, table_id: str | None):
    """显示推荐的 Bitable 表结构"""
    svc = FeishuService()
    app_token, table_id = _resolve_tokens(svc, app_token, table_id)
    if not app_token or not table_id:
        return

    schema_data = svc.create_bitable_schema(app_token, table_id)

    table = Table(title="推荐表结构", show_lines=True)
    table.add_column("字段名", style="bold cyan")
    table.add_column("类型", justify="center")
    table.add_column("说明", style="dim")

    type_map = {1: "文本", 2: "数字", 5: "日期"}
    for field in schema_data["fields"]:
        table.add_row(
            field["field_name"],
            type_map.get(field["type"], str(field["type"])),
            field["description"],
        )

    console.print(table)
    console.print(f"\n[dim]App Token: {app_token}  |  Table ID: {table_id}[/dim]")


def _resolve_tokens(
    svc: FeishuService, app_token: str | None, table_id: str | None
) -> tuple[str | None, str | None]:
    """从参数或配置文件解析 app_token 和 table_id"""
    if app_token and table_id:
        return app_token, table_id

    config = svc.load_config()
    if config:
        app_token = app_token or config.get("app_token")
        table_id = table_id or config.get("table_id")

    if not app_token or not table_id:
        console.print(
            "[yellow]请提供 --app-token 和 --table-id 参数，"
            "或先运行 `ib feishu setup` 配置[/yellow]"
        )
        return None, None

    return app_token, table_id
