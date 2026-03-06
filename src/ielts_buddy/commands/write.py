"""write 命令组：写作辅助（话题、句型、同义替换）"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.writing_service import WritingService

console = Console()

# 分类中英文映射
_CATEGORY_LABELS = {
    "education": "教育",
    "environment": "环境",
    "technology": "科技",
    "health": "健康",
    "society": "社会",
    "culture": "文化",
    "economy": "经济",
}

# 模板类型中英文映射
_TYPE_LABELS = {
    "introduction": "开头段",
    "body": "主体段",
    "conclusion": "结尾段",
    "transition": "过渡句",
}


@click.group("write")
def write():
    """写作辅助命令"""


@write.command()
@click.option(
    "-c", "--category",
    type=click.Choice(
        ["education", "environment", "technology", "health", "society", "culture", "economy"],
        case_sensitive=False,
    ),
    default=None,
    help="按分类筛选",
)
def topics(category: str | None):
    """浏览写作话题"""
    svc = WritingService()
    items = svc.get_topics(category)

    if not items:
        console.print("[yellow]没有找到匹配的话题。[/yellow]")
        return

    cat_label = _CATEGORY_LABELS.get(category, category) if category else "全部"
    table = Table(
        title=f"雅思写作 Task 2 话题 [{cat_label}] (共 {len(items)} 个)",
        show_lines=True,
    )
    table.add_column("#", justify="right", style="dim", min_width=3)
    table.add_column("话题", style="bold cyan", min_width=10)
    table.add_column("分类", style="magenta", justify="center", min_width=6)
    table.add_column("题目", style="white", min_width=30)

    # 需要找到全局索引
    all_topics = svc.get_topics()
    for item in items:
        idx = all_topics.index(item) + 1
        cat_cn = _CATEGORY_LABELS.get(item["category"], item["category"])
        table.add_row(str(idx), item["topic"], cat_cn, item["question"])

    console.print(table)
    console.print("\n[dim]提示: 使用 ib write vocab <话题名> 查看话题对应的高分词汇[/dim]")


@write.command()
@click.option(
    "-t", "--type",
    "template_type",
    type=click.Choice(["introduction", "body", "conclusion", "transition"], case_sensitive=False),
    default=None,
    help="按类型筛选",
)
def templates(template_type: str | None):
    """查看句型模板"""
    svc = WritingService()
    items = svc.get_templates(template_type)

    if not items:
        console.print("[yellow]没有找到匹配的模板。[/yellow]")
        return

    type_label = _TYPE_LABELS.get(template_type, template_type) if template_type else "全部"
    console.print(f"\n[bold]高分句型模板 [{type_label}][/bold]  共 {len(items)} 个\n")

    for i, item in enumerate(items, 1):
        type_cn = _TYPE_LABELS.get(item["type"], item["type"])
        parts = [
            f"[magenta][{type_cn}][/magenta]",
            f"[bold white]{item['template']}[/bold white]",
            f"[yellow]{item['translation']}[/yellow]",
            f"[dim italic]例: {item['example']}[/dim italic]",
        ]
        console.print(Panel("\n".join(parts), title=f"#{i}", border_style="blue"))


@write.command()
@click.argument("word", required=False)
def synonyms(word: str | None):
    """同义替换查询"""
    svc = WritingService()
    items = svc.get_synonyms(word)

    if not items:
        msg = f"没有找到 '{word}' 的同义替换。" if word else "没有找到同义替换数据。"
        console.print(f"[yellow]{msg}[/yellow]")
        return

    title = f"同义替换: '{word}'" if word else "常用词同义替换"
    table = Table(title=f"{title} (共 {len(items)} 组)", show_lines=True)
    table.add_column("常用词", style="bold red", min_width=12)
    table.add_column("高分替换", style="bold green", min_width=30)
    table.add_column("使用场景", style="yellow", min_width=20)

    for item in items:
        syn_str = " / ".join(item["synonyms"])
        table.add_row(item["common"], syn_str, item["context"])

    console.print(table)


@write.command()
@click.argument("topic")
def vocab(topic: str):
    """查看话题对应的高分词汇"""
    svc = WritingService()
    result = svc.get_writing_vocab(topic)

    if not result:
        console.print(f"[yellow]没有找到与 '{topic}' 相关的话题。[/yellow]")
        console.print("[dim]提示: 使用 ib write topics 查看所有可用话题[/dim]")
        return

    parts = [
        f"[bold cyan]{result['topic']}[/bold cyan]  [magenta][{_CATEGORY_LABELS.get(result['category'], result['category'])}][/magenta]",
        f"\n[white]{result['question']}[/white]",
        f"\n[bold]关键词:[/bold]  {', '.join(result['keywords'])}",
        f"[bold]高分词汇:[/bold]",
    ]
    for v in result["band7_vocab"]:
        parts.append(f"  [green]• {v}[/green]")

    console.print(Panel("\n".join(parts), title="话题词汇", border_style="cyan"))
