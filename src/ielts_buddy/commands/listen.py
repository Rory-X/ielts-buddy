"""listen 命令组：听力资源浏览、听写模式"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.listening_service import ListeningService
from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.vocab_service import VocabService

console = Console()

# 难度中文标签
_DIFFICULTY_LABELS = {
    "beginner": "初级",
    "intermediate": "中级",
    "advanced": "高级",
}

# 类型中文标签
_TYPE_LABELS = {
    "podcast": "播客",
    "video": "视频",
    "course": "课程",
    "website": "网站",
}


@click.group("listen")
def listen():
    """听力练习命令"""


@listen.command()
@click.option(
    "-t", "--type",
    "res_type",
    type=click.Choice(["podcast", "video", "course", "website"], case_sensitive=False),
    default=None,
    help="按类型筛选",
)
@click.option(
    "-d", "--difficulty",
    type=click.Choice(["beginner", "intermediate", "advanced"], case_sensitive=False),
    default=None,
    help="按难度筛选",
)
def resources(res_type: str | None, difficulty: str | None):
    """浏览听力资源"""
    svc = ListeningService()
    items = svc.get_resources(type=res_type, difficulty=difficulty)

    if not items:
        console.print("[yellow]没有找到匹配的听力资源。[/yellow]")
        return

    # 筛选描述
    filter_parts = []
    if res_type:
        filter_parts.append(_TYPE_LABELS.get(res_type, res_type))
    if difficulty:
        filter_parts.append(_DIFFICULTY_LABELS.get(difficulty, difficulty))
    filter_str = " | ".join(filter_parts) if filter_parts else "全部"

    table = Table(
        title=f"听力资源 [{filter_str}] (共 {len(items)} 个)",
        show_lines=True,
    )
    table.add_column("#", justify="right", style="dim", min_width=3)
    table.add_column("名称", style="bold cyan", min_width=15)
    table.add_column("类型", style="green", justify="center")
    table.add_column("难度", justify="center")
    table.add_column("描述", style="yellow", min_width=20)
    table.add_column("免费", justify="center")

    # 使用全局索引
    all_items = svc.get_resources()
    for item in items:
        idx = all_items.index(item) + 1
        type_label = _TYPE_LABELS.get(item["type"], item["type"])
        diff_label = _DIFFICULTY_LABELS.get(item["difficulty"], item["difficulty"])
        free_str = "[green]是[/green]" if item["free"] else "[red]否[/red]"
        table.add_row(
            str(idx),
            item["title"],
            type_label,
            diff_label,
            item["description"],
            free_str,
        )

    console.print(table)
    console.print("\n[dim]提示: 使用 ib listen detail N 查看资源详情[/dim]")


@listen.command()
@click.argument("index", type=int)
def detail(index: int):
    """查看资源详情（按序号）"""
    svc = ListeningService()
    item = svc.get_resource_detail(index)

    if not item:
        total = len(svc.get_resources())
        console.print(f"[red]无效序号: {index}[/red]  有效范围: 1-{total}")
        return

    type_label = _TYPE_LABELS.get(item["type"], item["type"])
    diff_label = _DIFFICULTY_LABELS.get(item["difficulty"], item["difficulty"])
    free_str = "免费" if item["free"] else "付费"
    topics_str = ", ".join(item.get("topics", []))

    parts = [
        f"[bold cyan]{item['title']}[/bold cyan]",
        "",
        f"类型: [green]{type_label}[/green]",
        f"难度: {diff_label}",
        f"费用: {'[green]免费[/green]' if item['free'] else '[red]付费[/red]'}",
        f"话题: [magenta]{topics_str}[/magenta]",
        "",
        f"[yellow]{item['description']}[/yellow]",
        "",
        f"链接: [underline]{item['url']}[/underline]",
    ]

    console.print(Panel("\n".join(parts), title="资源详情", border_style="cyan"))


@listen.command()
@click.option("-n", "--count", default=10, help="题目数量", show_default=True)
@click.option("-b", "--band", type=int, default=None, help="按 band 等级筛选 (5-9)")
def dictation(count: int, band: int | None):
    """听写模式 — 根据音标和释义拼写单词"""
    # 加载词库
    vocab_svc = VocabService()
    vocab_svc.load_master()
    pool = vocab_svc.filter_by_band(band) if band else vocab_svc.words

    if not pool:
        console.print("[yellow]没有找到匹配的单词。[/yellow]")
        return

    # 生成听写题目
    listening_svc = ListeningService()
    questions = listening_svc.generate_dictation(pool, count)

    if not questions:
        console.print("[yellow]无法生成听写题目。[/yellow]")
        return

    total = len(questions)
    correct = 0
    answered = 0
    wrong_words: list[dict] = []

    # 记录复习
    review = ReviewService()

    console.print(f"\n[bold]听写模式[/bold]  共 {total} 题")
    console.print("[dim]根据音标和中文释义，输入正确的英文拼写（输入 q 退出）[/dim]\n")

    try:
        for i, q in enumerate(questions, 1):
            console.print(
                f"[bold cyan]({i}/{total})[/bold cyan]  "
                f"[dim]{q['phonetic']}[/dim]  "
                f"[yellow]{q['definition']}[/yellow]"
            )
            answer = input("  拼写: ").strip()

            if answer.lower() == "q":
                total = answered
                break

            is_correct = answer.lower() == q["word"].lower()

            if is_correct:
                correct += 1
                console.print("  [green]✓ 正确！[/green]\n")
            else:
                console.print(
                    f"  [red]✗ 错误[/red]  "
                    f"正确拼写: [bold]{q['word']}[/bold]\n"
                )
                wrong_words.append(q)

            # 记录学习结果
            word_obj = vocab_svc.get_word(q["word"])
            if word_obj:
                review.record_learn(word_obj, is_correct)
            answered += 1
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]听写中断[/dim]")
        total = answered

    review.close()

    # 显示结果
    if total > 0:
        rate = correct / total * 100
        color = "green" if rate >= 80 else "yellow" if rate >= 60 else "red"
        console.print(
            f"\n[bold]听写结束[/bold]  "
            f"正确 {correct}/{total}  "
            f"正确率 [{color}]{rate:.0f}%[/{color}]"
        )

    # 错词回顾
    if wrong_words:
        console.print("\n[bold]错词回顾:[/bold]")
        table = Table(show_lines=False, show_header=True)
        table.add_column("单词", style="bold red")
        table.add_column("音标", style="dim")
        table.add_column("释义", style="yellow")
        for w in wrong_words:
            table.add_row(w["word"], w["phonetic"], w["definition"])
        console.print(table)
