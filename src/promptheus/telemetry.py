"""
Lightweight telemetry for Promptheus.

Records anonymized performance and usage metrics to a local JSONL file.
Telemetry is independent from history persistence and can be disabled via
the PROMPTHEUS_TELEMETRY_ENABLED environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from promptheus.history import get_default_history_dir
from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)


TELEMETRY_ENABLED_ENV = "PROMPTHEUS_TELEMETRY_ENABLED"
TELEMETRY_FILE_ENV = "PROMPTHEUS_TELEMETRY_FILE"
TELEMETRY_SAMPLE_RATE_ENV = "PROMPTHEUS_TELEMETRY_SAMPLE_RATE"


@dataclass
class TelemetryEvent:
    """Represents a single telemetry event for a refined prompt."""

    timestamp: str
    event_type: str
    source: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    task_type: Optional[str]
    processing_latency_sec: Optional[float]
    clarifying_questions_count: Optional[int]
    skip_questions: Optional[bool]
    refine_mode: Optional[bool]
    success: Optional[bool]

    # New fields for schema and correlation
    schema_version: int = 1
    session_id: Optional[str] = None
    run_id: Optional[str] = None

    # New aggregated metrics
    input_chars: Optional[int] = None
    output_chars: Optional[int] = None
    llm_latency_sec: Optional[float] = None
    total_run_latency_sec: Optional[float] = None

    # Token usage metrics (when reported by provider)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Feature flags and environment
    quiet_mode: Optional[bool] = None
    history_enabled: Optional[bool] = None
    python_version: Optional[str] = None
    platform: Optional[str] = None
    interface: Optional[str] = None
    sanitized_error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to plain dictionary for JSON serialization."""
        return asdict(self)


_cached_enabled: Optional[bool] = None
_cached_sample_rate: Optional[float] = None


def _telemetry_enabled() -> bool:
    """
    Determine whether telemetry is enabled.

    Telemetry is enabled by default and can be disabled by setting
    PROMPTHEUS_TELEMETRY_ENABLED to 0, false, or off.
    """
    global _cached_enabled
    if _cached_enabled is not None:
        return _cached_enabled

    raw = os.getenv(TELEMETRY_ENABLED_ENV)
    if raw is None:
        _cached_enabled = True
    else:
        lowered = raw.strip().lower()
        _cached_enabled = lowered not in ("0", "false", "no", "off")
    return _cached_enabled


def _get_sample_rate() -> float:
    """Get the telemetry sample rate from environment variable."""
    global _cached_sample_rate
    if _cached_sample_rate is not None:
        return _cached_sample_rate

    raw = os.getenv(TELEMETRY_SAMPLE_RATE_ENV)
    if not raw:
        _cached_sample_rate = 1.0
        return _cached_sample_rate

    try:
        value = float(raw)
    except ValueError:
        _cached_sample_rate = 1.0
        return _cached_sample_rate

    if not (0.0 <= value <= 1.0):
        _cached_sample_rate = 1.0
    else:
        _cached_sample_rate = value
    return _cached_sample_rate


def _should_sample() -> bool:
    """Determine if this event should be sampled based on sample rate."""
    rate = _get_sample_rate()
    if rate <= 0.0:
        return False
    if rate >= 1.0:
        return True
    return random.random() <= rate


def _get_telemetry_path() -> Path:
    """
    Resolve the telemetry file path.

    Uses PROMPTHEUS_TELEMETRY_FILE when set; otherwise defaults to the same
    directory used for history (~/.promptheus) with filename telemetry.jsonl.
    """
    override = os.getenv(TELEMETRY_FILE_ENV)
    if override:
        return Path(override).expanduser()
    return get_default_history_dir() / "telemetry.jsonl"


def _write_event(event: TelemetryEvent) -> None:
    """
    Write a telemetry event to the JSONL file.
    
    This is the central low-level writer that all public functions should use.
    Handles sampling and error handling.
    """
    if not _telemetry_enabled():
        return
    if not _should_sample():
        return

    try:
        path = _get_telemetry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            json.dump(event.to_dict(), f)
            f.write("\n")
    except OSError as exc:
        # Telemetry must never break primary workflows; log at debug level only.
        logger.debug(
            "Failed to write telemetry event: %s",
            sanitize_error_message(str(exc)),
        )


def record_prompt_run_event(
    *,
    source: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    task_type: Optional[str],
    processing_latency_sec: Optional[float],
    clarifying_questions_count: Optional[int],
    skip_questions: Optional[bool],
    refine_mode: Optional[bool],
    success: Optional[bool],
    session_id: Optional[str],
    run_id: Optional[str],
    input_chars: Optional[int] = None,
    output_chars: Optional[int] = None,
    llm_latency_sec: Optional[float] = None,
    total_run_latency_sec: Optional[float] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    quiet_mode: Optional[bool] = None,
    history_enabled: Optional[bool] = None,
    python_version: Optional[str] = None,
    platform: Optional[str] = None,
    interface: Optional[str] = None,
) -> None:
    """
    Record a prompt refinement run telemetry event.
    
    This is the main event type that captures high-level metrics about a
    prompt refinement session without storing any actual prompt content.
    """
    event = TelemetryEvent(
        timestamp=datetime.now().isoformat(),
        event_type="prompt_run",
        source=source,
        provider=provider,
        model=model,
        task_type=task_type,
        processing_latency_sec=processing_latency_sec,
        clarifying_questions_count=clarifying_questions_count,
        skip_questions=skip_questions,
        refine_mode=refine_mode,
        success=success,
        session_id=session_id,
        run_id=run_id,
        input_chars=input_chars,
        output_chars=output_chars,
        llm_latency_sec=llm_latency_sec,
        total_run_latency_sec=total_run_latency_sec,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        quiet_mode=quiet_mode,
        history_enabled=history_enabled,
        python_version=python_version,
        platform=platform,
        interface=interface,
    )
    _write_event(event)


def record_clarifying_questions_summary(
    *,
    session_id: Optional[str],
    run_id: Optional[str],
    total_questions: int,
    history_enabled: Optional[bool],
) -> None:
    """
    Record a summary of clarifying questions asked during a refinement run.
    
    Privacy guard: This event is only recorded when history is enabled.
    Only the count is recorded, never the actual question text.
    """
    # Privacy guard: do not log question-level summaries if history is disabled.
    if history_enabled is False:
        return

    event = TelemetryEvent(
        timestamp=datetime.now().isoformat(),
        event_type="clarifying_questions_summary",
        source=None,
        provider=None,
        model=None,
        task_type=None,
        processing_latency_sec=None,
        clarifying_questions_count=total_questions,
        skip_questions=None,
        refine_mode=None,
        success=None,
        session_id=session_id,
        run_id=run_id,
        history_enabled=history_enabled,
    )
    _write_event(event)


def record_provider_error(
    *,
    provider: str,
    model: Optional[str],
    session_id: Optional[str],
    run_id: Optional[str],
    error_message: str,
) -> None:
    """
    Record a provider error event.
    
    Captures high-level error information without storing sensitive details.
    The error message is sanitized before recording.
    """
    event = TelemetryEvent(
        timestamp=datetime.now().isoformat(),
        event_type="provider_error",
        source=None,
        provider=provider,
        model=model,
        task_type=None,
        processing_latency_sec=None,
        clarifying_questions_count=None,
        skip_questions=None,
        refine_mode=None,
        success=False,
        session_id=session_id,
        run_id=run_id,
        sanitized_error=sanitize_error_message(error_message),
    )
    _write_event(event)


# Backward compatibility: keep the old function name working
def record_prompt_event(
    *,
    source: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    task_type: Optional[str],
    processing_latency_sec: Optional[float],
    clarifying_questions_count: Optional[int],
    skip_questions: Optional[bool],
    refine_mode: Optional[bool],
    success: Optional[bool],
) -> None:
    """
    Record a single prompt-level telemetry event (backward compatibility).
    
    This function is kept for backward compatibility and calls the new
    record_prompt_run_event with default values for new fields.
    """
    record_prompt_run_event(
        source=source,
        provider=provider,
        model=model,
        task_type=task_type,
        processing_latency_sec=processing_latency_sec,
        clarifying_questions_count=clarifying_questions_count,
        skip_questions=skip_questions,
        refine_mode=refine_mode,
        success=success,
        session_id=None,
        run_id=None,
        input_chars=None,
        output_chars=None,
        llm_latency_sec=None,
        total_run_latency_sec=None,
        quiet_mode=None,
        history_enabled=None,
        python_version=None,
        platform=None,
        interface=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
    )
