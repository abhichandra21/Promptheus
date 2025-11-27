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
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from promptheus.history import get_default_history_dir
from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)


TELEMETRY_ENABLED_ENV = "PROMPTHEUS_TELEMETRY_ENABLED"
TELEMETRY_FILE_ENV = "PROMPTHEUS_TELEMETRY_FILE"


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

    def to_dict(self) -> dict:
        """Convert to plain dictionary for JSON serialization."""
        return asdict(self)


_cached_enabled: Optional[bool] = None


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
    Record a single prompt-level telemetry event.

    This function is intentionally tolerant: any failure to write telemetry
    is logged and then ignored so that it never affects user workflows.
    """
    if not _telemetry_enabled():
        return

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
    )

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

