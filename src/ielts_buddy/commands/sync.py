"""sync 命令组：数据导出同步"""

from __future__ import annotations

import click
from rich.console import Console

from ielts_buddy.services.sync_service import SyncService

console = Console()


@click.group("sync")
def sync():
    """数据同步/导出命令"""


@sync.command()
def vocab():
    """导出词库（含掌握状态）"""
    svc = SyncService()
    path = svc.export_vocab()
    console.print(f"[green]词库已导出:[/green] {path}")


@sync.command()
def records():
    """导出学习记录"""
    svc = SyncService()
    path = svc.export_records()
    console.print(f"[green]学习记录已导出:[/green] {path}")


@sync.command()
def stats():
    """导出统计摘要"""
    svc = SyncService()
    path = svc.export_stats()
    console.print(f"[green]统计摘要已导出:[/green] {path}")


@sync.command("all")
def sync_all():
    """导出全部数据"""
    svc = SyncService()
    paths = svc.export_all()
    console.print("[green]全部数据已导出:[/green]")
    for name, path in paths.items():
        console.print(f"  {name}: {path}")
