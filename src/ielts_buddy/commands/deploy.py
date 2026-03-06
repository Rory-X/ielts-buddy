"""deploy 命令组：GitHub Pages 部署"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.deploy_service import DeployService

console = Console()


@click.group("deploy")
def deploy():
    """GitHub Pages 部署命令"""


@deploy.command()
@click.option("--repo", required=True, help="GitHub 仓库地址")
def setup(repo: str):
    """初始化 GitHub Pages 部署"""
    svc = DeployService()
    try:
        site_dir = svc.setup_github_pages(repo)
        parts = [
            f"[green]初始化完成！[/green]",
            f"站点目录: {site_dir}",
            f"远程仓库: {repo}",
            "",
            "[dim]下一步: 运行 [bold]ib deploy push[/bold] 构建并推送报告[/dim]",
        ]
        console.print(Panel("\n".join(parts), title="GitHub Pages 配置", border_style="green"))
    except RuntimeError as e:
        console.print(f"[red]初始化失败: {e}[/red]")


@deploy.command()
def push():
    """构建报告并推送到 GitHub Pages"""
    svc = DeployService()

    status = svc.get_status()
    if not status["initialized"]:
        console.print("[yellow]尚未初始化，请先运行: ib deploy setup --repo <url>[/yellow]")
        return

    console.print("[bold]正在构建并推送...[/bold]")

    try:
        msg = svc.deploy_to_pages()
        console.print(f"[green]部署成功:[/green] {msg}")
        if status["remote_url"]:
            # 提取 GitHub Pages URL
            url = status["remote_url"]
            if url.endswith(".git"):
                url = url[:-4]
            if "github.com" in url:
                parts = url.split("github.com")[-1].strip("/").split("/")
                if len(parts) >= 2:
                    pages_url = f"https://{parts[0]}.github.io/{parts[1]}/"
                    console.print(f"[dim]预计地址: {pages_url}[/dim]")
    except RuntimeError as e:
        console.print(f"[red]部署失败: {e}[/red]")


@deploy.command()
def status():
    """查看部署状态"""
    svc = DeployService()
    info = svc.get_status()

    table = Table(title="GitHub Pages 部署状态", show_lines=True)
    table.add_column("项目", style="bold cyan", min_width=12)
    table.add_column("状态", min_width=30)

    init_status = "[green]已初始化[/green]" if info["initialized"] else "[yellow]未初始化[/yellow]"
    table.add_row("初始化", init_status)
    table.add_row("站点目录", info["site_dir"])
    table.add_row("远程仓库", info["remote_url"] or "[dim]未设置[/dim]")
    table.add_row("HTML 页面", str(info["html_count"]))
    table.add_row("最近提交", info["last_commit"] or "[dim]无[/dim]")

    console.print(table)

    if not info["initialized"]:
        console.print("\n[dim]使用 [bold]ib deploy setup --repo <url>[/bold] 初始化[/dim]")
