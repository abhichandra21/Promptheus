"""
Analyze Promptheus prompt history for performance and usage metrics.

This script reads ~/.promptheus/history.jsonl (via PromptHistory) and reports:
- Total entries
- Breakdown by task_type and source (cli, api_submit, api_stream)
- Latency statistics where available
- Clarifying question counts where available

Usage:
    python scripts/analyze_history.py
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional

from promptheus.history import PromptHistory


def _safe_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _safe_p95(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    index = int(0.95 * (len(sorted_vals) - 1))
    return sorted_vals[index]


def _format_float(value: Optional[float]) -> str:
    if value is None or math.isnan(value):
        return "-"
    return f"{value:.3f}"


def main() -> int:
    history = PromptHistory()
    entries = history.get_all()

    total = len(entries)
    print(f"Total history entries: {total}")
    if not entries:
        return 0

    by_task: Dict[str, List] = defaultdict(list)
    by_source: Dict[str, List] = defaultdict(list)

    latencies: List[float] = []
    question_counts: List[int] = []

    for entry in entries:
        task = entry.task_type or "unknown"
        source = entry.source or "unknown"

        by_task[task].append(entry)
        by_source[source].append(entry)

        if entry.processing_latency_sec is not None:
            latencies.append(entry.processing_latency_sec)
        if entry.clarifying_questions_count is not None:
            question_counts.append(entry.clarifying_questions_count)

    if latencies:
        print("\nOverall latency (processing_latency_sec):")
        print(f"  avg:  {_format_float(_safe_mean(latencies))} s")
        print(f"  p95:  {_format_float(_safe_p95(latencies))} s")

    if question_counts:
        print("\nClarifying questions across all entries:")
        print(f"  avg count: {_format_float(_safe_mean([float(c) for c in question_counts]))}")

    print("\nBy task_type:")
    for task, task_entries in sorted(by_task.items()):
        task_latencies = [
            e.processing_latency_sec for e in task_entries if e.processing_latency_sec is not None
        ]
        task_questions = [
            e.clarifying_questions_count
            for e in task_entries
            if e.clarifying_questions_count is not None
        ]
        print(f"  {task}: {len(task_entries)} entries")
        if task_latencies:
            print(
                f"    latency avg={_format_float(_safe_mean(task_latencies))} s "
                f"p95={_format_float(_safe_p95(task_latencies))} s"
            )
        if task_questions:
            print(
                f"    clarifying questions avg={_format_float(_safe_mean([float(c) for c in task_questions]))}"
            )

    print("\nBy source:")
    for source, source_entries in sorted(by_source.items()):
        source_latencies = [
            e.processing_latency_sec for e in source_entries if e.processing_latency_sec is not None
        ]
        print(f"  {source}: {len(source_entries)} entries")
        if source_latencies:
            print(
                f"    latency avg={_format_float(_safe_mean(source_latencies))} s "
                f"p95={_format_float(_safe_p95(source_latencies))} s"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

