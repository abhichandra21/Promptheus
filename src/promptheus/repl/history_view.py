"""History viewing functionality for the REPL."""

import logging

from rich.console import Console
from rich.table import Table

from promptheus.history import get_history

logger = logging.getLogger(__name__)


def display_history(console: Console, notify, limit: int = 20) -> None:
    """Display recent history entries."""
    history = get_history()
    entries = history.get_recent(limit)
    logger.debug("Displaying %d history entries (limit was %d)", len(entries), limit)

    if not entries:
        notify("[yellow]No history entries found.[/yellow]")
        return

    table = Table(title="Prompt History", show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Date", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Original → Refined", style="white")

    for idx, entry in enumerate(entries, 1):
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(entry.timestamp)
            timestamp_str = dt.strftime("%m-%d %H:%M")
        except Exception:  # pragma: no cover - defensive
            timestamp_str = entry.timestamp[5:16]

        original = entry.original_prompt[:60] + "..." if len(entry.original_prompt) > 60 else entry.original_prompt
        refined = entry.refined_prompt[:60] + "..." if len(entry.refined_prompt) > 60 else entry.refined_prompt

        original = original.replace("\n", " ")
        refined = refined.replace("\n", " ")

        task_type = entry.task_type or "unknown"
        combined = f"[white]{original}[/white]\n[dim]→[/dim] [yellow]{refined}[/yellow]"

        table.add_row(str(idx), timestamp_str, task_type, combined)

    console.print()
    console.print(table)
    console.print()
    notify("[dim]Use '/load <number>' to load a prompt from history[/dim]")