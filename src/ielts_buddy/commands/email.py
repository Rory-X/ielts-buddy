"""email 命令组：邮件预览与发送"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

from ielts_buddy.services.email_service import EmailService

console = Console()


@click.group("email")
def email():
    """每日邮件命令"""


@email.command()
def preview():
    """预览每日邮件内容（终端输出 HTML 摘要）"""
    svc = EmailService()
    html = svc.generate_daily_email()

    # 在终端显示简要摘要（Rich 不支持完整 HTML，显示文字版）
    console.print(Panel(
        "[bold cyan]每日邮件已生成[/bold cyan]\n\n"
        f"HTML 长度: {len(html)} 字符",
        title="[bold]邮件预览[/bold]",
        border_style="blue",
    ))

    # 保存到临时文件方便浏览器打开
    from ielts_buddy.core.config import get_app_dir
    preview_path = get_app_dir() / "email_preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(html, encoding="utf-8")
    console.print(f"\n[green]HTML 已保存到:[/green] {preview_path}")
    console.print("[dim]可用浏览器打开查看完整效果[/dim]")


@email.command()
def send():
    """发送每日邮件"""
    try:
        from ielts_buddy.services.email_service import load_email_config
        config = load_email_config()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        console.print("\n[dim]配置文件格式 (~/.ielts-buddy/email.json):[/dim]")
        console.print('[dim]{"smtp_host": "smtp.example.com", "smtp_port": 465, '
                       '"smtp_ssl": true, "username": "...", "password": "...", '
                       '"from_addr": "...", "to_addr": "..."}[/dim]')
        return

    svc = EmailService()
    console.print("[dim]正在生成邮件内容...[/dim]")
    html = svc.generate_daily_email()

    console.print("[dim]正在发送邮件...[/dim]")
    try:
        svc.send_email(html, config)
        console.print(f"[green]邮件已发送至 {config['to_addr']}[/green]")
    except Exception as e:
        console.print(f"[red]邮件发送失败: {e}[/red]")
