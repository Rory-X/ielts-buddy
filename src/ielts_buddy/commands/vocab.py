"""vocab 命令组：随机单词、测验、复习、搜索、浏览"""

from __future__ import annotations

import math
import random as rand_mod

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.vocab_service import VocabService

console = Console()


def _load_vocab(source: str) -> VocabService:
    """根据 source 参数加载词库"""
    svc = VocabService()
    if source == "curated":
        svc.load_all()
    else:
        svc.load_master()
    return svc


# 共享的 --source 选项
_source_option = click.option(
    "-s", "--source",
    type=click.Choice(["master", "curated"], case_sensitive=False),
    default="master",
    help="词库来源: master=大词库(4485词), curated=精选(526词)",
    show_default=True,
)


@click.group("vocab")
def vocab():
    """词汇学习命令"""


@vocab.command()
@click.option("-n", "--count", default=5, help="抽取数量", show_default=True)
@click.option("-b", "--band", type=int, default=None, help="按 band 等级筛选 (5-9)")
@_source_option
def random(count: int, band: int | None, source: str):
    """随机抽取单词"""
    svc = _load_vocab(source)

    words = svc.random_words(count, band)
    if not words:
        console.print("[yellow]没有找到匹配的单词。[/yellow]")
        return

    source_label = "大词库" if source == "master" else "精选"
    table = Table(title=f"随机单词 (共 {len(words)} 个) [{source_label}]", show_lines=True)
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
@click.option(
    "-m", "--mode",
    type=click.Choice(["en2zh", "zh2en", "mix"], case_sensitive=False),
    default="en2zh",
    help="测验模式: en2zh=英译中, zh2en=中译英, mix=混合",
    show_default=True,
)
@_source_option
def quiz(count: int, band: int | None, mode: str, source: str):
    """词汇测验"""
    svc = _load_vocab(source)
    review = ReviewService()

    words = svc.random_words(count, band)
    if not words:
        console.print("[yellow]没有足够的单词进行测验。[/yellow]")
        return

    correct = 0
    total = len(words)

    mode_labels = {"en2zh": "英译中", "zh2en": "中译英", "mix": "混合模式"}
    mode_label = mode_labels[mode]

    if mode == "en2zh":
        console.print(f"\n[bold]词汇测验 ({mode_label})[/bold]  共 {total} 题，输入中文释义（输入 q 退出）\n")
    elif mode == "zh2en":
        console.print(f"\n[bold]词汇测验 ({mode_label})[/bold]  共 {total} 题，输入英文单词（输入 q 退出）\n")
    else:
        console.print(f"\n[bold]词汇测验 ({mode_label})[/bold]  共 {total} 题，随机英译中/中译英（输入 q 退出）\n")

    answered = 0
    try:
        for i, w in enumerate(words, 1):
            # 决定本题模式
            if mode == "mix":
                q_mode = rand_mod.choice(["en2zh", "zh2en"])
            else:
                q_mode = mode

            if q_mode == "en2zh":
                console.print(f"[bold cyan]({i}/{total}) {w.word}[/bold cyan]  {w.phonetic}  [{w.pos}]")
                answer = input("  你的答案 (中文): ").strip()
            else:
                console.print(
                    f"[bold cyan]({i}/{total})[/bold cyan]  "
                    f"[yellow]{w.meaning}[/yellow]  [{w.pos}]"
                )
                answer = input("  你的答案 (英文): ").strip()

            if answer.lower() == "q":
                total = answered
                break

            if q_mode == "en2zh":
                # 英译中：答案包含释义中的关键词即算对
                meanings = w.meaning.replace("；", "，").replace(",", "，").split("，")
                is_correct = any(
                    m.strip() in answer or answer in m.strip()
                    for m in meanings if m.strip()
                )
            else:
                # 中译英：忽略大小写和首尾空格
                is_correct = answer.lower() == w.word.lower()

            if is_correct:
                correct += 1
                console.print("  [green]✓ 正确！[/green]\n")
            else:
                if q_mode == "en2zh":
                    console.print(f"  [red]✗ 错误[/red]  正确答案: [yellow]{w.meaning}[/yellow]\n")
                else:
                    console.print(f"  [red]✗ 错误[/red]  正确答案: [yellow]{w.word}[/yellow]\n")

            # 记录学习结果
            review.record_learn(w, is_correct)
            answered += 1
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]测验中断[/dim]")
        total = answered

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


@vocab.command("search")
@click.argument("keyword")
@_source_option
def search_cmd(keyword: str, source: str):
    """搜索单词（支持 word/释义/topic 模糊匹配）"""
    svc = _load_vocab(source)

    results = svc.search_words(keyword)
    if not results:
        console.print(f"[yellow]没有找到包含 '{keyword}' 的单词。[/yellow]")
        return

    source_label = "大词库" if source == "master" else "精选"
    table = Table(title=f"搜索结果: '{keyword}' (共 {len(results)} 个) [{source_label}]", show_lines=True)
    table.add_column("单词", style="bold cyan", min_width=15)
    table.add_column("音标", style="dim")
    table.add_column("词性", style="green", justify="center")
    table.add_column("释义", style="yellow", min_width=15)
    table.add_column("Band", justify="center")
    table.add_column("主题", style="magenta")

    for w in results:
        table.add_row(w.word, w.phonetic, w.pos, w.meaning, str(w.band), w.topic)

    console.print(table)


@vocab.command("list")
@click.option("-b", "--band", type=int, default=None, help="按 band 等级筛选 (5-9)")
@click.option("-t", "--topic", default=None, help="按主题筛选")
@click.option("-p", "--page", default=1, help="页码", show_default=True)
@click.option("--per-page", default=20, help="每页数量", show_default=True)
@_source_option
def list_cmd(band: int | None, topic: str | None, page: int, per_page: int, source: str):
    """浏览词库（支持 band/topic 筛选，分页显示）"""
    svc = _load_vocab(source)

    words, total = svc.list_words(band=band, topic=topic, page=page, per_page=per_page)
    if not words:
        console.print("[yellow]没有找到匹配的单词。[/yellow]")
        return

    total_pages = math.ceil(total / per_page)
    filter_desc = []
    if band is not None:
        filter_desc.append(f"Band {band}")
    if topic is not None:
        filter_desc.append(f"主题: {topic}")
    source_label = "大词库" if source == "master" else "精选"
    filter_desc.append(source_label)
    filter_str = " | ".join(filter_desc)

    table = Table(
        title=f"词库浏览 [{filter_str}]  第 {page}/{total_pages} 页  (共 {total} 个)",
        show_lines=True,
    )
    table.add_column("单词", style="bold cyan", min_width=15)
    table.add_column("音标", style="dim")
    table.add_column("词性", style="green", justify="center")
    table.add_column("释义", style="yellow", min_width=15)
    table.add_column("Band", justify="center")
    table.add_column("主题", style="magenta")

    for w in words:
        table.add_row(w.word, w.phonetic, w.pos, w.meaning, str(w.band), w.topic)

    console.print(table)

    if total_pages > 1:
        console.print(
            f"\n[dim]提示: 使用 --page N 翻页 (共 {total_pages} 页)[/dim]"
        )


@vocab.command("info")
@_source_option
def info_cmd(source: str):
    """显示词库概览（各 Band 数量、主题分布）"""
    svc = _load_vocab(source)

    stats = svc.get_vocab_stats()

    source_label = "大词库 (master)" if source == "master" else "精选 (curated)"

    # Band 分布
    band_table = Table(title=f"词库概览 [{source_label}]", show_lines=False)
    band_table.add_column("Band", justify="center", style="bold")
    band_table.add_column("数量", justify="right", style="cyan")
    band_table.add_column("分布", min_width=20)

    max_band = max(stats["bands"].values()) if stats["bands"] else 1
    for band_level, count in stats["bands"].items():
        bar_len = int(count / max_band * 25) if max_band > 0 else 0
        bar = "█" * bar_len
        band_table.add_row(str(band_level), str(count), f"[cyan]{bar}[/cyan]")

    band_table.add_row("", "", "")
    band_table.add_row("[bold]总计[/bold]", f"[bold]{stats['total']}[/bold]", "")
    console.print(band_table)

    # 主题分布
    topic_table = Table(title="主题分布", show_lines=False)
    topic_table.add_column("主题", style="magenta", min_width=15)
    topic_table.add_column("数量", justify="right", style="cyan")
    topic_table.add_column("分布", min_width=20)

    max_topic = max(stats["topics"].values()) if stats["topics"] else 1
    for topic_name, count in stats["topics"].items():
        bar_len = int(count / max_topic * 25) if max_topic > 0 else 0
        bar = "█" * bar_len
        topic_table.add_row(topic_name, str(count), f"[magenta]{bar}[/magenta]")

    console.print(topic_table)
