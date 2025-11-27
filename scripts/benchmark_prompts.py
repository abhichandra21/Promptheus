"""
Benchmark the effectiveness and efficiency of prompt templates.

This script measures:
- Response time (wall and CPU time)
- Structural accuracy (JSON validity, schema correctness, task classification)
- Relevance (simple keyword-overlap heuristics)
- Resource usage (approximate memory deltas via ru_maxrss)

It exercises the four system instructions defined in promptheus.prompts:
- CLARIFICATION_SYSTEM_INSTRUCTION
- GENERATION_SYSTEM_INSTRUCTION
- TWEAK_SYSTEM_INSTRUCTION
- ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION

Usage:
    python scripts/benchmark_prompts.py

The script assumes that at least one provider is configured via .env in the
same way the main CLI expects. It uses the default provider/model selected
by Config.
"""

from __future__ import annotations

import json
import resource
import statistics
import string
import sys
import time
from typing import Any, Dict, List, Tuple

from promptheus.config import Config
from promptheus.providers import get_provider
from promptheus.prompts import (
    ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
    CLARIFICATION_SYSTEM_INSTRUCTION,
    GENERATION_SYSTEM_INSTRUCTION,
    TWEAK_SYSTEM_INSTRUCTION,
)


def _now_usage() -> Tuple[float, float, int]:
    """Return current CPU time, wall time, and max RSS."""
    wall = time.perf_counter()
    cpu = time.process_time()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return cpu, wall, usage.ru_maxrss


def _measure_call(func) -> Dict[str, Any]:
    """Execute func and capture timing and resource deltas."""
    cpu_before, wall_before, rss_before = _now_usage()
    error: str = ""
    result: Any = None
    success = True

    try:
        result = func()
    except Exception as exc:  # pragma: no cover - observational script
        success = False
        error = str(exc)

    cpu_after, wall_after, rss_after = _now_usage()
    return {
        "success": success,
        "result": result,
        "error": error,
        "wall_time_sec": wall_after - wall_before,
        "cpu_time_sec": cpu_after - cpu_before,
        "rss_kb_delta": rss_after - rss_before,
    }


def _tokenize(text: str) -> List[str]:
    """Very simple tokenizer for overlap heuristics."""
    if not text:
        return []
    table = str.maketrans({ch: " " for ch in string.punctuation})
    cleaned = text.lower().translate(table)
    tokens = [t for t in cleaned.split() if len(t) > 3]
    return tokens


def _keyword_overlap_score(source: str, target: str) -> float:
    """Return fraction of source keywords that appear in target."""
    source_tokens = set(_tokenize(source))
    if not source_tokens:
        return 0.0
    target_tokens = set(_tokenize(target))
    if not target_tokens:
        return 0.0
    matched = len(source_tokens.intersection(target_tokens))
    return matched / max(len(source_tokens), 1)


def benchmark_clarification(provider) -> Dict[str, Any]:
    """Benchmark CLARIFICATION_SYSTEM_INSTRUCTION behavior."""
    samples: List[Tuple[str, str]] = [
        (
            "analysis",
            "Explore this Python codebase and identify potential performance bottlenecks in the HTTP request pipeline.",
        ),
        (
            "analysis",
            "Investigate this error log from a production service and determine the most likely root cause categories.",
        ),
        (
            "generation",
            "Write a LinkedIn post about migrating a monolith to microservices for engineering leaders.",
        ),
        (
            "generation",
            "Generate a Python function that validates email addresses and logs failures with context.",
        ),
        (
            "generation",
            "Draft product release notes for a new AI-assisted code review feature.",
        ),
    ]

    wall_times: List[float] = []
    cpu_times: List[float] = []
    rss_deltas: List[int] = []

    json_successes = 0
    total_runs = 0
    correct_task_type = 0
    question_count_ok = 0
    relevance_scores: List[float] = []

    for expected_task_type, prompt in samples:
        total_runs += 1

        measurement = _measure_call(
            lambda p=prompt: provider.generate_questions(p, CLARIFICATION_SYSTEM_INSTRUCTION)
        )

        wall_times.append(measurement["wall_time_sec"])
        cpu_times.append(measurement["cpu_time_sec"])
        rss_deltas.append(measurement["rss_kb_delta"])

        payload = measurement["result"]
        if not measurement["success"] or payload is None:
            continue

        if not isinstance(payload, dict):
            continue

        json_successes += 1
        task_type = payload.get("task_type")
        if task_type == expected_task_type:
            correct_task_type += 1

        questions = payload.get("questions") or []
        if isinstance(questions, list):
            count = len(questions)
            if expected_task_type == "analysis":
                if 0 <= count <= 3:
                    question_count_ok += 1
            else:
                if 3 <= count <= 6:
                    question_count_ok += 1

            # Relevance: average overlap between prompt keywords and each question.
            if questions:
                overlaps: List[float] = []
                for q in questions:
                    if not isinstance(q, dict):
                        continue
                    text = q.get("question") or ""
                    overlaps.append(_keyword_overlap_score(prompt, text))
                if overlaps:
                    relevance_scores.append(sum(overlaps) / len(overlaps))

    def _safe_mean(values: List[float]) -> float:
        return float(statistics.mean(values)) if values else 0.0

    def _safe_p95(values: List[float]) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        index = int(0.95 * (len(sorted_vals) - 1))
        return float(sorted_vals[index])

    return {
        "total_runs": total_runs,
        "json_success_rate": json_successes / total_runs if total_runs else 0.0,
        "classification_accuracy": (correct_task_type / json_successes) if json_successes else 0.0,
        "question_count_ok_rate": (question_count_ok / json_successes) if json_successes else 0.0,
        "avg_relevance_score": _safe_mean(relevance_scores),
        "wall_time_sec_avg": _safe_mean(wall_times),
        "wall_time_sec_p95": _safe_p95(wall_times),
        "cpu_time_sec_avg": _safe_mean(cpu_times),
        "rss_kb_delta_max": max(rss_deltas) if rss_deltas else 0,
    }


def benchmark_generation(provider) -> Dict[str, Any]:
    """Benchmark GENERATION_SYSTEM_INSTRUCTION via refine_from_answers."""
    scenarios: List[Dict[str, Any]] = [
        {
            "initial_prompt": "Write a blog post about observability best practices in microservices.",
            "answers": {
                "audience": "Senior backend engineers",
                "tone": "Professional and practical",
                "length": "1200-1500 words",
            },
            "question_mapping": {
                "audience": "Who is the target audience?",
                "tone": "Preferred tone and voice?",
                "length": "Preferred length?",
            },
            "expected_keywords": [
                "observability",
                "microservices",
                "backend",
                "engineers",
                "professional",
            ],
        },
        {
            "initial_prompt": "Create a system design interview question about rate limiting APIs.",
            "answers": {
                "seniority": "Senior engineer",
                "focus": "Tradeoffs between simplicity and robustness",
            },
            "question_mapping": {
                "seniority": "Candidate seniority?",
                "focus": "What aspect should the question emphasize?",
            },
            "expected_keywords": [
                "rate limiting",
                "APIs",
                "senior",
                "tradeoffs",
            ],
        },
    ]

    wall_times: List[float] = []
    cpu_times: List[float] = []
    rss_deltas: List[int] = []
    keyword_coverages: List[float] = []

    total_runs = 0
    success_runs = 0

    for scenario in scenarios:
        total_runs += 1
        initial_prompt = scenario["initial_prompt"]
        answers = scenario["answers"]
        question_mapping = scenario["question_mapping"]
        expected_keywords = scenario["expected_keywords"]

        measurement = _measure_call(
            lambda ip=initial_prompt, a=answers, qm=question_mapping: provider.refine_from_answers(
                ip,
                a,
                qm,
                GENERATION_SYSTEM_INSTRUCTION,
            )
        )

        wall_times.append(measurement["wall_time_sec"])
        cpu_times.append(measurement["cpu_time_sec"])
        rss_deltas.append(measurement["rss_kb_delta"])

        if not measurement["success"]:
            continue

        success_runs += 1
        refined = measurement["result"] or ""
        if not isinstance(refined, str):
            continue

        matches = 0
        for kw in expected_keywords:
            if kw.lower() in refined.lower():
                matches += 1
        if expected_keywords:
            keyword_coverages.append(matches / len(expected_keywords))

    def _safe_mean(values: List[float]) -> float:
        return float(statistics.mean(values)) if values else 0.0

    def _safe_p95(values: List[float]) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        index = int(0.95 * (len(sorted_vals) - 1))
        return float(sorted_vals[index])

    return {
        "total_runs": total_runs,
        "success_rate": success_runs / total_runs if total_runs else 0.0,
        "avg_keyword_coverage": _safe_mean(keyword_coverages),
        "wall_time_sec_avg": _safe_mean(wall_times),
        "wall_time_sec_p95": _safe_p95(wall_times),
        "cpu_time_sec_avg": _safe_mean(cpu_times),
        "rss_kb_delta_max": max(rss_deltas) if rss_deltas else 0,
    }


def benchmark_tweak(provider) -> Dict[str, Any]:
    """Benchmark TWEAK_SYSTEM_INSTRUCTION behavior."""
    scenarios: List[Dict[str, Any]] = [
        {
            "current_prompt": (
                "Act as a senior backend engineer. Design an API for processing imaging studies for {TENANT_NAME} "
                "and output a step-by-step migration plan by [DATE_PLACEHOLDER]."
            ),
            "tweak_instruction": "Make the tone more concise and formal.",
            "placeholders": ["{TENANT_NAME}", "[DATE_PLACEHOLDER]"],
        }
    ]

    wall_times: List[float] = []
    cpu_times: List[float] = []
    rss_deltas: List[int] = []

    placeholder_preservation_scores: List[float] = []
    relevance_scores: List[float] = []

    total_runs = 0
    success_runs = 0

    for scenario in scenarios:
        total_runs += 1
        current_prompt = scenario["current_prompt"]
        tweak_instruction = scenario["tweak_instruction"]
        placeholders = scenario["placeholders"]

        measurement = _measure_call(
            lambda cp=current_prompt, ti=tweak_instruction: provider.tweak_prompt(
                cp,
                ti,
                TWEAK_SYSTEM_INSTRUCTION,
            )
        )

        wall_times.append(measurement["wall_time_sec"])
        cpu_times.append(measurement["cpu_time_sec"])
        rss_deltas.append(measurement["rss_kb_delta"])

        if not measurement["success"]:
            continue

        success_runs += 1
        tweaked = measurement["result"] or ""
        if not isinstance(tweaked, str):
            continue

        # Placeholder preservation: fraction of placeholders preserved exactly.
        preserved = 0
        for ph in placeholders:
            if ph in tweaked:
                preserved += 1
        if placeholders:
            placeholder_preservation_scores.append(preserved / len(placeholders))

        # Relevance: overlap between original prompt and tweaked version.
        relevance_scores.append(_keyword_overlap_score(current_prompt, tweaked))

    def _safe_mean(values: List[float]) -> float:
        return float(statistics.mean(values)) if values else 0.0

    return {
        "total_runs": total_runs,
        "success_rate": success_runs / total_runs if total_runs else 0.0,
        "avg_placeholder_preservation": _safe_mean(placeholder_preservation_scores),
        "avg_relevance_score": _safe_mean(relevance_scores),
        "wall_time_sec_avg": _safe_mean(wall_times),
        "cpu_time_sec_avg": _safe_mean(cpu_times),
        "rss_kb_delta_max": max(rss_deltas) if rss_deltas else 0,
    }


def benchmark_analysis_refinement(provider) -> Dict[str, Any]:
    """Benchmark ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION via light_refine."""
    prompts = [
        "Analyze this system design for a multi-tenant PACS platform and identify scalability risks.",
        "Review this incident summary and propose 3 hypotheses for the underlying cause.",
    ]

    wall_times: List[float] = []
    cpu_times: List[float] = []
    rss_deltas: List[int] = []
    relevance_scores: List[float] = []

    total_runs = 0
    success_runs = 0

    for prompt in prompts:
        total_runs += 1
        measurement = _measure_call(
            lambda p=prompt: provider.light_refine(
                p,
                ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
            )
        )

        wall_times.append(measurement["wall_time_sec"])
        cpu_times.append(measurement["cpu_time_sec"])
        rss_deltas.append(measurement["rss_kb_delta"])

        if not measurement["success"]:
            continue

        success_runs += 1
        refined = measurement["result"] or ""
        if not isinstance(refined, str):
            continue

        relevance_scores.append(_keyword_overlap_score(prompt, refined))

    def _safe_mean(values: List[float]) -> float:
        return float(statistics.mean(values)) if values else 0.0

    def _safe_p95(values: List[float]) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        index = int(0.95 * (len(sorted_vals) - 1))
        return float(sorted_vals[index])

    return {
        "total_runs": total_runs,
        "success_rate": success_runs / total_runs if total_runs else 0.0,
        "avg_relevance_score": _safe_mean(relevance_scores),
        "wall_time_sec_avg": _safe_mean(wall_times),
        "wall_time_sec_p95": _safe_p95(wall_times),
        "cpu_time_sec_avg": _safe_mean(cpu_times),
        "rss_kb_delta_max": max(rss_deltas) if rss_deltas else 0,
    }


def main() -> int:
    config = Config()
    if not config.validate():
        print("Provider configuration invalid; cannot run benchmark.", file=sys.stderr)
        return 1

    provider_name = config.provider or "google"
    provider = get_provider(provider_name, config)

    results = {
        "provider": provider_name,
        "clarification": benchmark_clarification(provider),
        "generation": benchmark_generation(provider),
        "tweak": benchmark_tweak(provider),
        "analysis_refinement": benchmark_analysis_refinement(provider),
    }

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

