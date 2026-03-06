"""vocab 命令组：随机单词、测验、复习"""

from __future__ import annotations

import random

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.vocab_service import VocabService

console = Console()


@click.group("vocab")
def vocab():
    """词汇学习命令"""


@vocab.command()
@click.option("-n", "--count", default=5, help="抽取数量", show_default=True)
@click.option("-b", "--band", type=int, default=None, help="按 band 等级筛选 (5/6/7)")
def random(count: int, band: int | None):
    """随机抽取单词"""
    svc = VocabService()
    svc.load_all()

    words = svc.random_words(count, band)
    if not words:
        console.print("[yellow]没有找到匹配的单词。[/yellow]")
        return

    table = Table(title=f"随机单词 (共 {len(words)} 个)", show_lines=True)
    table.add_column("单词", style="bold cyan", min_width=15)
    table.add_column("音标", style="dim")
    table.add_column("词性", style="green", justify="center")
    table.add_column("释义", style="yellow", min_width=15)
    table.add_column("Band", justify="center")
    table.add_column("主题", style="magenta")

    for w in words:
        table.add_row(w.word, w.phonetic, w.pos, w.meaning, str(w.band), w.topic)

    console.print(table)

    # 显示详情
    for w in words:
        parts = []
        parts.append(f"[bold cyan]{w.word}[/bold cyan]  {w.phonetic}  [green]{w.pos}[/green]")
        parts.append(f"[yellow]{w.meaning}[/yellow]")
        if w.example:
            parts.append(f"\n[italic]例: {w.example}[/italic]")
            if w.example_cn:
                parts.append(f"[dim]    {w.example_cn}[/dim]")
        if w.collocations:
            parts.append(f"\n搭配: {', '.join(w.collocations)}")
        if w.synonyms:
            parts.append(f"同义: {', '.join(w.synonyms)}")
        if w.etymology:
            parts.append(f"词源: {w.etymology}")

        console.print(Panel("\n".join(parts), border_style="blue"))


@vocab.command()
@click.option("-n", "--count", default=10, help="题目数量", show_default=True)
@click.option("-b", "--band", type=int, default=None, help="按 band 等级筛选")
def quiz(count: int, band: int | None):
    """词汇测验（英译中）"""
    svc = VocabService()
    svc.load_all()
    review = ReviewService()

    words = svc.random_words(count, band)
    if not words:
        console.print("[yellow]没有足够的单词进行测验。[/yellow]")
        return

    correct = 0
    total = len(words)

    console.print(f"\n[bold]词汇测验[/bold]  共 {total} 题，输入中文释义（输入 q 退出）\n")

    try:
        for i, w in enumerate(words, 1):
            console.print(f"[bold cyan]({i}/{total}) {w.word}[/bold cyan]  {w.phonetic}  [{w.pos}]")
            answer = input("  你的答案: ").strip()

            if answer.lower() == "q":
                total = i - 1
                break

            # 简单匹配：答案包含释义中的关键词即算对
            meanings = w.meaning.replace("；", "，").replace(",", "，").split("，")
            is_correct = any(m.strip() in answer or answer in m.strip() for m in meanings if m.strip())

            if is_correct:
                correct += 1
                console.print("  [green]✓ 正确！[/green]\n")
            else:
                console.print(f"  [red]✗ 错误[/red]  正确答案: [yellow]{w.meaning}[/yellow]\n")

            # 记录学习结果
            review.record_learn(w, is_correct)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]测验中断[/dim]")
        total = max(i - 1, 0)

    review.close()

    if total > 0:
        rate = correct / total * 100
        color = "green" if rate >= 80 else "yellow" if rate >= 60 else "red"
        console.print(f"\n[bold]测验结束[/bold]  正确 {correct}/{total}  正确率 [{color}]{rate:.0f}%[/{color}]")


@vocab.command()
@click.option("-n", "--count", default=20, help="复习数量上限", show_default=True)
def review(count: int):
    """复习到期单词"""
    svc = ReviewService()
    due = svc.get_due_words(limit=count)

    if not due:
        console.print("[green]暂无需要复习的单词，继续保持！[/green]")
        svc.close()
        return

    console.print(f"\n[bold]复习模式[/bold]  共 {len(due)} 个待复习单词\n")
    console.print("[dim]看到单词后回忆释义，按 Enter 查看答案，输入 y=记得 n=忘了 q=退出[/dim]\n")

    correct = 0
    total = 0

    try:
        for i, item in enumerate(due, 1):
            w = item["word_data"]
            rec = item["record"]

            console.print(
                f"[bold cyan]({i}/{len(due)}) {w.word}[/bold cyan]  "
                f"[dim]记忆等级: {rec.memory_level}  已学: {rec.learn_count}次[/dim]"
            )
            input("  按 Enter 查看答案...")

            console.print(f"  释义: [yellow]{w.meaning}[/yellow]  [{w.pos}]")
            if w.example:
                console.print(f"  [italic]例: {w.example}[/italic]")

            answer = input("  记得吗？(y/n/q): ").strip().lower()
            if answer == "q":
                break

            is_correct = answer == "y"
            if is_correct:
                correct += 1
                console.print("  [green]继续保持！[/green]\n")
            else:
                console.print("  [red]加油，下次会记住的！[/red]\n")

            svc.record_learn(w, is_correct)
            total += 1
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]复习中断[/dim]")

    svc.close()

    if total > 0:
        rate = correct / total * 100
        console.print(f"\n[bold]复习结束[/bold]  记住 {correct}/{total}  正确率 {rate:.0f}%")
