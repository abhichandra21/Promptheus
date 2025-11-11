"""
Command implementations for persona management.
"""

from rich.console import Console
from rich.table import Table

from promptheus.config import load_personas


def list_personas() -> None:
    """Loads and displays all available built-in and custom personas."""
    all_personas = load_personas()

    if not all_personas:
        print("No personas found.")
        return

    table = Table(title="Available Personas")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")

    for name, data in sorted(all_personas.items()):
        table.add_row(name, data.get("description", "No description."))

    console = Console()
    console.print(table)
