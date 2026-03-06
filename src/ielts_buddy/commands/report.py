"""report 命令组：生成学习报告网页"""

from __future__ import annotations

import http.server
import os
import socketserver
import threading
from datetime import date

import click
from rich.console import Console

from ielts_buddy.services.report_service import ReportService, _get_site_dir

console = Console()


@click.group("report")
def report():
    """学习报告命令"""


@report.command()
@click.option("-d", "--date", "date_str", default=None, help="日期 (YYYY-MM-DD)，默认今天")
def daily(date_str: str | None):
    """生成某天的学习报告 HTML"""
    svc = ReportService()
    try:
        target = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        console.print(f"[red]无效日期格式: {date_str}，请使用 YYYY-MM-DD[/red]")
        return

    site_dir = _get_site_dir()
    site_dir.mkdir(parents=True, exist_ok=True)

    html = svc.render_daily_report(target)
    out_path = site_dir / f"{target.isoformat()}.html"
    out_path.write_text(html, encoding="utf-8")
    svc.close()

    console.print(f"[green]已生成报告:[/green] {out_path}")


@report.command()
def build():
    """生成全部报告（所有有数据的日期 + 首页）"""
    svc = ReportService()
    site_dir = svc.build_site()
    svc.close()

    # 统计生成的文件
    html_files = list(site_dir.glob("*.html"))
    console.print(f"[green]站点已生成:[/green] {site_dir}")
    console.print(f"  共 {len(html_files)} 个页面 (1 首页 + {len(html_files) - 1} 日报告)")


@report.command()
@click.option("-p", "--port", default=8080, help="端口号", show_default=True)
def serve(port: int):
    """本地预览报告站点"""
    site_dir = _get_site_dir()

    if not site_dir.exists() or not (site_dir / "index.html").exists():
        console.print("[yellow]站点尚未生成，正在自动构建...[/yellow]")
        svc = ReportService()
        svc.build_site()
        svc.close()

    os.chdir(site_dir)
    handler = http.server.SimpleHTTPRequestHandler

    console.print(f"[green]预览地址:[/green] http://localhost:{port}")
    console.print("[dim]按 Ctrl+C 停止[/dim]")

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[dim]服务已停止[/dim]")
    except OSError as e:
        console.print(f"[red]启动失败: {e}[/red]")
