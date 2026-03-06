"""IELTS Buddy CLI 入口"""

import click

from ielts_buddy.commands.stats import stats
from ielts_buddy.commands.vocab import vocab


@click.group()
@click.version_option(version="0.1.0", prog_name="ielts-buddy")
def cli():
    """IELTS Buddy - 雅思词汇学习助手"""


cli.add_command(vocab)
cli.add_command(stats)


if __name__ == "__main__":
    cli()
