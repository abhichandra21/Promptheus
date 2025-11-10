"""Shell completion functionality."""

import logging
import os
import sys
from typing import Optional

from rich.console import Console

logger = logging.getLogger(__name__)


def load_completion_template(shell: str) -> str:
    """
    Load completion template from the templates directory.

    Args:
        shell: Shell type ('bash' or 'zsh')

    Returns:
        The completion script as a string

    Raises:
        FileNotFoundError: If the template file doesn't exist
        ValueError: If shell is not supported
    """
    try:
        from importlib.resources import files
    except ImportError:
        # Python < 3.9 fallback
        from importlib_resources import files

    template_file = f"{shell}.bash" if shell == "bash" else f"{shell}.zsh"

    try:
        template_path = files('promptheus.completions.templates') / template_file
        return template_path.read_text()
    except Exception as exc:
        logger.error("Failed to load completion template for %s: %s", shell, exc)
        raise


def generate_completion_script(shell: str):
    """Prints the completion script for the specified shell."""
    if not shell:
        logger.error("Shell type must be specified when not using --install")
        sys.exit(1)

    try:
        script = load_completion_template(shell)
        print(script)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to generate completion script for %s: %s", shell, exc)
        sys.exit(1)


def install_completion(shell: Optional[str], console: Console) -> None:
    """
    Automatically install shell completion by:
    1. Detecting the shell if not provided
    2. Finding the promptheus executable
    3. Creating a shell alias
    4. Installing the completion script
    5. Updating shell config
    """
    import subprocess
    import shutil
    from pathlib import Path

    # Detect shell if not provided
    if not shell:
        shell_path = os.getenv("SHELL", "")
        if "zsh" in shell_path:
            shell = "zsh"
        elif "bash" in shell_path:
            shell = "bash"
        else:
            console.print(f"[red]Could not detect shell from SHELL={shell_path}[/red]")
            console.print("Please specify shell explicitly: [cyan]promptheus completion --install bash[/cyan] or [cyan]zsh[/cyan]")
            sys.exit(1)

    console.print(f"[bold]Installing completion for {shell}...[/bold]\n")

    # Find promptheus executable
    try:
        # Try to find the actual promptheus script
        result = subprocess.run(
            ["which", "promptheus"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            promptheus_path = result.stdout.strip()
        else:
            # Fallback: check if we're in a poetry project
            if Path("pyproject.toml").exists():
                try:
                    result = subprocess.run(
                        ["poetry", "run", "which", "promptheus"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    promptheus_path = result.stdout.strip()
                except subprocess.CalledProcessError:
                    console.print("[red]Could not find promptheus executable[/red]")
                    console.print("Make sure promptheus is installed: [cyan]pip install -e .[/cyan]")
                    sys.exit(1)
            else:
                console.print("[red]Could not find promptheus executable[/red]")
                console.print("Make sure promptheus is installed: [cyan]pip install -e .[/cyan]")
                sys.exit(1)
    except Exception as exc:
        console.print(f"[red]Error finding promptheus: {exc}[/red]")
        sys.exit(1)

    console.print(f"[green]✓[/green] Found promptheus at: [cyan]{promptheus_path}[/cyan]")

    # Determine shell config file
    home = Path.home()
    if shell == "zsh":
        shell_config = home / ".zshrc"
        completion_dir = home / ".zsh" / "completions"
        completion_file = completion_dir / "_promptheus"
    else:  # bash
        shell_config = home / ".bashrc"
        completion_dir = home / ".bash_completion.d"
        completion_file = completion_dir / "promptheus.bash"

    # Create completion directory if it doesn't exist
    completion_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Completion directory: [cyan]{completion_dir}[/cyan]")

    # Load and save completion script
    try:
        template = load_completion_template(shell)
        completion_file.write_text(template)
        console.print(f"[green]✓[/green] Saved completion script to: [cyan]{completion_file}[/cyan]")
    except Exception as exc:
        console.print(f"[red]Error saving completion script: {exc}[/red]")
        sys.exit(1)

    # Check if already configured
    shell_config_content = shell_config.read_text() if shell_config.exists() else ""

    # Add alias if promptheus is not in a standard location
    needs_alias = "/site-packages/" not in promptheus_path and ".local/bin" not in promptheus_path

    config_lines = []
    config_lines.append(f"\n# Promptheus completion (added by promptheus completion --install)")

    if needs_alias:
        alias_line = f'alias promptheus="{promptheus_path}"'
        if alias_line not in shell_config_content:
            config_lines.append(alias_line)
            console.print(f"[green]✓[/green] Adding alias: [cyan]{alias_line}[/cyan]")

    # Add completion loading
    if shell == "zsh":
        # Only add fpath if this specific directory isn't already there
        if str(completion_dir) not in shell_config_content:
            config_lines.append(f'fpath=({completion_dir} $fpath)')

        # Force reload completion and register for alias
        config_lines.append('autoload -Uz compinit && compinit -i')
        if needs_alias:
            config_lines.append('compdef _promptheus promptheus')
    else:  # bash
        source_line = f'source {completion_file}'
        if source_line not in shell_config_content:
            config_lines.append(source_line)

    # Write to shell config
    if len(config_lines) > 1:  # More than just the comment
        with open(shell_config, "a") as f:
            f.write("\n".join(config_lines) + "\n")
        console.print(f"[green]✓[/green] Updated shell config: [cyan]{shell_config}[/cyan]")
    else:
        console.print(f"[yellow]→[/yellow] Shell config already configured")

    # Final instructions
    console.print("\n[bold green]Installation complete![/bold green]\n")
    console.print("To activate completion in your current shell, run:")
    console.print(f"  [cyan]source {shell_config}[/cyan]\n")
    console.print("Or simply open a new terminal window.\n")
    console.print("[dim]Test it by typing:[/dim] [cyan]promptheus <TAB>[/cyan]")