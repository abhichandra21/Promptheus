"""
Telemetry summary tool for Promptheus.

Reads telemetry JSONL events and presents aggregate statistics
without exposing any sensitive content.
"""

import json
import logging
import os
import statistics
from collections import defaultdict, Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from promptheus.history import get_default_history_dir

logger = logging.getLogger(__name__)


@dataclass
class RunMetrics:
    """Aggregated metrics for prompt runs."""

    total_runs: int = 0
    successful_runs: int = 0
    total_latencies: List[float] = None
    llm_latencies: List[float] = None
    input_chars: List[int] = None
    output_chars: List[int] = None
    input_tokens: List[int] = None
    output_tokens: List[int] = None
    total_tokens: List[int] = None

    def __post_init__(self):
        if self.total_latencies is None:
            self.total_latencies = []
        if self.llm_latencies is None:
            self.llm_latencies = []
        if self.input_chars is None:
            self.input_chars = []
        if self.output_chars is None:
            self.output_chars = []
        if self.input_tokens is None:
            self.input_tokens = []
        if self.output_tokens is None:
            self.output_tokens = []
        if self.total_tokens is None:
            self.total_tokens = []

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100

    def avg_total_latency(self) -> Optional[float]:
        """Average total latency."""
        valid = [v for v in self.total_latencies if isinstance(v, (int, float)) and v > 0]
        return statistics.mean(valid) if valid else None

    def median_total_latency(self) -> Optional[float]:
        """Median total latency."""
        valid = [v for v in self.total_latencies if isinstance(v, (int, float)) and v > 0]
        return statistics.median(valid) if valid else None

    def avg_llm_latency(self) -> Optional[float]:
        """Average LLM latency."""
        valid = [v for v in self.llm_latencies if isinstance(v, (int, float)) and v > 0]
        return statistics.mean(valid) if valid else None

    def median_llm_latency(self) -> Optional[float]:
        """Median LLM latency."""
        valid = [v for v in self.llm_latencies if isinstance(v, (int, float)) and v > 0]
        return statistics.median(valid) if valid else None

    def avg_input_chars(self) -> Optional[float]:
        """Average input characters."""
        return statistics.mean(self.input_chars) if self.input_chars else None

    def avg_output_chars(self) -> Optional[float]:
        """Average output characters."""
        return statistics.mean(self.output_chars) if self.output_chars else None

    # Token aggregation
    def avg_input_tokens(self) -> Optional[float]:
        """Average input tokens."""
        valid = [v for v in self.input_tokens if isinstance(v, (int, float)) and v > 0]
        return statistics.mean(valid) if valid else None

    def avg_output_tokens(self) -> Optional[float]:
        """Average output tokens."""
        valid = [v for v in self.output_tokens if isinstance(v, (int, float)) and v > 0]
        return statistics.mean(valid) if valid else None

    def avg_total_tokens(self) -> Optional[float]:
        """Average total tokens."""
        valid = [v for v in self.total_tokens if isinstance(v, (int, float)) and v > 0]
        return statistics.mean(valid) if valid else None


@dataclass
class QuestionMetrics:
    """Metrics for clarifying questions."""

    runs_with_questions: int = 0
    total_runs: int = 0
    question_counts: List[int] = None

    def __post_init__(self):
        if self.question_counts is None:
            self.question_counts = []

    @property
    def percentage_with_questions(self) -> float:
        """Percentage of runs with questions."""
        if self.total_runs == 0:
            return 0.0
        return (self.runs_with_questions / self.total_runs) * 100

    def avg_questions_when_present(self) -> Optional[float]:
        """Average number of questions when questions were asked."""
        return statistics.mean(self.question_counts) if self.question_counts else None

    def distribution(self) -> Dict[str, int]:
        """Distribution of question counts by bucket."""
        buckets = {"0": 0, "1-3": 0, "4-7": 0, "8+": 0}

        # Count runs with 0 questions
        buckets["0"] = self.total_runs - self.runs_with_questions

        # Distribute runs with questions
        for count in self.question_counts:
            if 1 <= count <= 3:
                buckets["1-3"] += 1
            elif 4 <= count <= 7:
                buckets["4-7"] += 1
            elif count >= 8:
                buckets["8+"] += 1

        return buckets


def get_telemetry_path() -> Path:
    """
    Get the telemetry file path.

    Uses PROMPTHEUS_TELEMETRY_FILE if set, otherwise defaults to
    get_default_history_dir() / "telemetry.jsonl".
    """
    override = os.getenv("PROMPTHEUS_TELEMETRY_FILE")
    if override:
        return Path(override).expanduser()
    return get_default_history_dir() / "telemetry.jsonl"


def read_telemetry_events(path: Path) -> List[dict]:
    """
    Read telemetry events from JSONL file.

    Ignores malformed lines and continues processing.
    """
    events = []

    if not path.exists():
        return events

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError as e:
                    logger.debug(
                        "Skipping malformed line %d in telemetry file: %s",
                        line_num,
                        str(e),
                    )
                    continue

    except OSError as e:
        logger.warning("Failed to read telemetry file: %s", str(e))

    return events


def aggregate_metrics(events: List[dict]) -> Tuple[
    RunMetrics,
    Dict[str, RunMetrics],
    QuestionMetrics,
    Dict[Tuple[str, str], RunMetrics],
    Counter,
    Dict[Tuple[str, str], int],
]:
    """
    Aggregate telemetry events into metrics.

    Returns:
        - overall: Overall run metrics
        - by_interface: Metrics grouped by interface
        - questions: Question metrics
        - by_provider: Metrics grouped by (provider, model)
        - error_messages: Counter of sanitized error messages
        - error_by_provider: Count of errors by (provider, model)
    """
    overall = RunMetrics()
    by_interface: Dict[str, RunMetrics] = defaultdict(RunMetrics)
    questions = QuestionMetrics()
    by_provider: Dict[Tuple[str, str], RunMetrics] = defaultdict(RunMetrics)
    error_messages: Counter = Counter()
    error_by_provider: Dict[Tuple[str, str], int] = defaultdict(int)

    for event in events:
        event_type = event.get("event_type")

        if event_type == "prompt_run":
            # Overall metrics
            overall.total_runs += 1
            questions.total_runs += 1

            success = event.get("success")
            if success is True:
                overall.successful_runs += 1

            # Latencies
            if event.get("total_run_latency_sec") is not None:
                overall.total_latencies.append(event["total_run_latency_sec"])
            elif event.get("processing_latency_sec") is not None:
                overall.total_latencies.append(event["processing_latency_sec"])

            if event.get("llm_latency_sec") is not None:
                overall.llm_latencies.append(event["llm_latency_sec"])

            # Character counts
            if event.get("input_chars") is not None:
                overall.input_chars.append(event["input_chars"])
            if event.get("output_chars") is not None:
                overall.output_chars.append(event["output_chars"])

            # Token counts
            if event.get("input_tokens") is not None:
                overall.input_tokens.append(event["input_tokens"])
            if event.get("output_tokens") is not None:
                overall.output_tokens.append(event["output_tokens"])
            if event.get("total_tokens") is not None:
                overall.total_tokens.append(event["total_tokens"])

            # By interface
            interface = event.get("interface") or "unknown"
            interface_metrics = by_interface[interface]
            interface_metrics.total_runs += 1
            if success is True:
                interface_metrics.successful_runs += 1

            if event.get("total_run_latency_sec") is not None:
                interface_metrics.total_latencies.append(event["total_run_latency_sec"])
            elif event.get("processing_latency_sec") is not None:
                interface_metrics.total_latencies.append(event["processing_latency_sec"])

            if event.get("llm_latency_sec") is not None:
                interface_metrics.llm_latencies.append(event["llm_latency_sec"])

            if event.get("input_chars") is not None:
                interface_metrics.input_chars.append(event["input_chars"])
            if event.get("output_chars") is not None:
                interface_metrics.output_chars.append(event["output_chars"])

            if event.get("input_tokens") is not None:
                interface_metrics.input_tokens.append(event["input_tokens"])
            if event.get("output_tokens") is not None:
                interface_metrics.output_tokens.append(event["output_tokens"])
            if event.get("total_tokens") is not None:
                interface_metrics.total_tokens.append(event["total_tokens"])

            # Questions
            q_count = event.get("clarifying_questions_count", 0)
            if q_count and q_count > 0:
                questions.runs_with_questions += 1
                questions.question_counts.append(q_count)

            # By provider/model
            provider = event.get("provider") or "unknown"
            model = event.get("model") or "unknown"
            provider_key = (provider, model)

            provider_metrics = by_provider[provider_key]
            provider_metrics.total_runs += 1
            if success is True:
                provider_metrics.successful_runs += 1

            if event.get("total_run_latency_sec") is not None:
                provider_metrics.total_latencies.append(event["total_run_latency_sec"])
            elif event.get("processing_latency_sec") is not None:
                provider_metrics.total_latencies.append(event["processing_latency_sec"])

            if event.get("llm_latency_sec") is not None:
                provider_metrics.llm_latencies.append(event["llm_latency_sec"])

            if event.get("input_tokens") is not None:
                provider_metrics.input_tokens.append(event["input_tokens"])
            if event.get("output_tokens") is not None:
                provider_metrics.output_tokens.append(event["output_tokens"])
            if event.get("total_tokens") is not None:
                provider_metrics.total_tokens.append(event["total_tokens"])

        elif event_type == "provider_error":
            # Error tracking
            sanitized_error = event.get("sanitized_error", "Unknown error")
            error_messages[sanitized_error] += 1

            provider = event.get("provider") or "unknown"
            model = event.get("model") or "unknown"
            provider_key = (provider, model)
            error_by_provider[provider_key] += 1

    return overall, dict(by_interface), questions, dict(by_provider), error_messages, dict(error_by_provider)


def format_latency(value: Optional[float]) -> str:
    """Format latency value for display."""
    if value is None:
        return "n/a"
    return f"{value:.2f}s"


def format_chars(value: Optional[float]) -> str:
    """Format character count for display."""
    if value is None:
        return "n/a"
    return f"{int(value)}"


def format_tokens(value: Optional[float]) -> str:
    """Format token count for display."""
    if value is None:
        return "n/a"
    return f"{int(value)}"


def format_percentage(value: float) -> str:
    """Format percentage for display."""
    return f"{value:.1f}%"


def print_telemetry_summary(console: Console, path: Optional[Path] = None) -> int:
    """
    Print telemetry summary to console with rich formatting.

    Args:
        console: Rich console for output
        path: Optional path to telemetry file (uses default if None)

    Returns:
        Exit code (0 for success)
    """
    if path is None:
        path = get_telemetry_path()

    # Check if file exists and has content
    if not path.exists() or path.stat().st_size == 0:
        console.print("\n[yellow]📊 No telemetry data found[/yellow]")
        console.print(f"[dim]Looking for telemetry at: {path}[/dim]\n")
        return 0

    # Read events
    events = read_telemetry_events(path)

    if not events:
        console.print("\n[yellow]📊 No valid telemetry events found[/yellow]\n")
        return 0

    # Aggregate metrics
    overall, by_interface, questions, by_provider, error_messages, error_by_provider = aggregate_metrics(events)

    # Header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]📊 Promptheus Telemetry Summary[/bold cyan]",
        border_style="cyan"
    ))

    # Overview Section
    overview_table = Table(show_header=False, box=None, padding=(0, 2))
    overview_table.add_column("Metric", style="cyan")
    overview_table.add_column("Value", style="bold white")

    overview_table.add_row("Total Runs", str(overall.total_runs))
    overview_table.add_row("Success Rate", format_percentage(overall.success_rate))
    overview_table.add_row("Avg Latency",
                           f"{format_latency(overall.avg_total_latency())} (median: {format_latency(overall.median_total_latency())})")
    overview_table.add_row("Avg LLM Latency",
                           f"{format_latency(overall.avg_llm_latency())} (median: {format_latency(overall.median_llm_latency())})")
    overview_table.add_row("Avg Input", f"{format_chars(overall.avg_input_chars())} chars")
    overview_table.add_row("Avg Output", f"{format_chars(overall.avg_output_chars())} chars")
    overview_table.add_row(
        "Avg Tokens",
        f"{format_tokens(overall.avg_total_tokens())} total "
        f"(in: {format_tokens(overall.avg_input_tokens())}, "
        f"out: {format_tokens(overall.avg_output_tokens())})",
    )

    console.print(Panel(overview_table, title="[bold]Overview[/bold]", border_style="blue"))

    # By Interface Section
    if by_interface:
        interface_table = Table(show_header=True, box=None)
        interface_table.add_column("Interface", style="cyan")
        interface_table.add_column("Runs", justify="right")
        interface_table.add_column("Success", justify="right")
        interface_table.add_column("Avg Latency", justify="right")
        interface_table.add_column("Avg LLM", justify="right")
        interface_table.add_column("Avg Tokens", justify="right")

        for interface in sorted(by_interface.keys()):
            metrics = by_interface[interface]
            interface_table.add_row(
                interface,
                str(metrics.total_runs),
                format_percentage(metrics.success_rate),
                format_latency(metrics.avg_total_latency()),
                format_latency(metrics.avg_llm_latency()),
                format_tokens(metrics.avg_total_tokens()),
            )

        console.print(Panel(interface_table, title="[bold]By Interface[/bold]", border_style="green"))

    # Questions Section
    if questions.total_runs > 0:
        questions_table = Table(show_header=False, box=None, padding=(0, 2))
        questions_table.add_column("Metric", style="cyan")
        questions_table.add_column("Value", style="bold white")

        questions_table.add_row(
            "Runs with Questions",
            f"{questions.runs_with_questions}/{questions.total_runs} ({format_percentage(questions.percentage_with_questions)})"
        )

        avg_q = questions.avg_questions_when_present()
        if avg_q is not None:
            questions_table.add_row("Avg Questions", f"{avg_q:.1f}")

        # Distribution
        dist = questions.distribution()
        dist_text = " | ".join([f"{bucket}: {count}" for bucket, count in sorted(dist.items())])
        questions_table.add_row("Distribution", dist_text)

        console.print(Panel(questions_table, title="[bold]Clarifying Questions[/bold]", border_style="magenta"))

    # Providers Section
    if by_provider:
        provider_table = Table(show_header=True, box=None)
        provider_table.add_column("Provider", style="cyan")
        provider_table.add_column("Model", style="dim")
        provider_table.add_column("Runs", justify="right")
        provider_table.add_column("Success", justify="right")
        provider_table.add_column("Avg Latency", justify="right")
        provider_table.add_column("Avg Tokens", justify="right")

        # Sort by number of runs (descending)
        sorted_providers = sorted(
            by_provider.items(),
            key=lambda x: x[1].total_runs,
            reverse=True,
        )

        for (provider, model), metrics in sorted_providers[:10]:  # Top 10
            provider_table.add_row(
                provider,
                model,
                str(metrics.total_runs),
                format_percentage(metrics.success_rate),
                format_latency(metrics.avg_total_latency()),
                format_tokens(metrics.avg_total_tokens()),
            )

        title = "[bold]Providers / Models[/bold]"
        if len(sorted_providers) > 10:
            title += f" [dim](showing top 10 of {len(sorted_providers)})[/dim]"

        console.print(Panel(provider_table, title=title, border_style="yellow"))

    # Errors Section
    total_errors = sum(error_by_provider.values())
    if total_errors > 0:
        error_table = Table(show_header=False, box=None, padding=(0, 2))
        error_table.add_column("", style="red")
        error_table.add_column("", style="white")

        error_table.add_row("Total Errors", str(total_errors))

        if error_by_provider:
            sorted_errors = sorted(
                error_by_provider.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for (provider, model), count in sorted_errors[:5]:
                error_table.add_row(f"{provider} / {model}", str(count))

        console.print(Panel(error_table, title="[bold red]Provider Errors[/bold red]", border_style="red"))

        # Top error messages
        if error_messages:
            error_msg_table = Table(show_header=True, box=None)
            error_msg_table.add_column("Count", justify="right", style="red")
            error_msg_table.add_column("Error Message", style="dim")

            for error_msg, count in error_messages.most_common(5):
                error_msg_table.add_row(f"{count}x", error_msg)

            console.print(Panel(error_msg_table, title="[bold]Top Errors[/bold]", border_style="red"))

    console.print()
    return 0
