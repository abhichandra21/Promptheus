"""
Tests for extended telemetry functionality with privacy preservation.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from promptheus.telemetry import (
    TelemetryEvent,
    record_prompt_run_event,
    record_clarifying_questions_summary,
    record_provider_error,
    record_prompt_event,  # backward compatibility
    _get_sample_rate,
    _should_sample,
    TELEMETRY_SAMPLE_RATE_ENV,
)


class TestTelemetryExtended:
    """Test the extended telemetry functionality."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.telemetry_file = Path(self.temp_dir) / "telemetry.jsonl"
        
        # Reset telemetry module caches
        import promptheus.telemetry as telemetry_module
        telemetry_module._cached_enabled = None
        telemetry_module._cached_sample_rate = None
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            "PROMPTHEUS_TELEMETRY_FILE": str(self.telemetry_file),
            "PROMPTHEUS_TELEMETRY_ENABLED": "1",
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Clean up after each test method."""
        self.env_patcher.stop()
        # Reset telemetry module caches
        import promptheus.telemetry as telemetry_module
        telemetry_module._cached_enabled = None
        telemetry_module._cached_sample_rate = None
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def read_telemetry_events(self):
        """Helper to read and parse telemetry events from file."""
        if not self.telemetry_file.exists():
            return []
        
        events = []
        with open(self.telemetry_file, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line.strip()))
        return events

    def test_telemetry_event_schema_version(self):
        """Test that schema_version is included in events."""
        record_prompt_run_event(
            source="test",
            provider="openai",
            model="gpt-4",
            task_type="code",
            processing_latency_sec=1.5,
            clarifying_questions_count=2,
            skip_questions=False,
            refine_mode=True,
            success=True,
            session_id="test-session-123",
            run_id="test-run-456",
        )

        events = self.read_telemetry_events()
        assert len(events) == 1
        event = events[0]
        
        assert event["schema_version"] == 1
        assert event["session_id"] == "test-session-123"
        assert event["run_id"] == "test-run-456"
        assert event["event_type"] == "prompt_run"

    def test_extended_metrics_fields(self):
        """Test that extended metrics fields are properly recorded."""
        record_prompt_run_event(
            source="test",
            provider="openai",
            model="gpt-4",
            task_type="code",
            processing_latency_sec=1.5,
            clarifying_questions_count=2,
            skip_questions=False,
            refine_mode=True,
            success=True,
            session_id="test-session",
            run_id="test-run",
            input_chars=100,
            output_chars=200,
            llm_latency_sec=0.8,
            total_run_latency_sec=2.5,
            quiet_mode=True,
            history_enabled=True,
            python_version="3.9.0",
            platform="linux",
            interface="cli",
        )

        events = self.read_telemetry_events()
        assert len(events) == 1
        event = events[0]
        
        # Check extended metrics
        assert event["input_chars"] == 100
        assert event["output_chars"] == 200
        assert event["llm_latency_sec"] == 0.8
        assert event["total_run_latency_sec"] == 2.5
        assert event["quiet_mode"] is True
        assert event["history_enabled"] is True
        assert event["python_version"] == "3.9.0"
        assert event["platform"] == "linux"
        assert event["interface"] == "cli"

    def test_clarifying_questions_summary_with_history_enabled(self):
        """Test that clarifying questions summary is recorded when history is enabled."""
        record_clarifying_questions_summary(
            session_id="test-session",
            run_id="test-run",
            total_questions=3,
            history_enabled=True,
        )

        events = self.read_telemetry_events()
        assert len(events) == 1
        event = events[0]
        
        assert event["event_type"] == "clarifying_questions_summary"
        assert event["session_id"] == "test-session"
        assert event["run_id"] == "test-run"
        assert event["clarifying_questions_count"] == 3
        assert event["history_enabled"] is True

    def test_clarifying_questions_summary_with_history_disabled(self):
        """Test that clarifying questions summary is NOT recorded when history is disabled."""
        record_clarifying_questions_summary(
            session_id="test-session",
            run_id="test-run",
            total_questions=3,
            history_enabled=False,
        )

        events = self.read_telemetry_events()
        assert len(events) == 0  # No events should be recorded

    def test_clarifying_questions_summary_with_history_none(self):
        """Test that clarifying questions summary is recorded when history_enabled is None."""
        record_clarifying_questions_summary(
            session_id="test-session",
            run_id="test-run",
            total_questions=3,
            history_enabled=None,
        )

        events = self.read_telemetry_events()
        assert len(events) == 1  # Should be recorded when None

    def test_provider_error_event(self):
        """Test that provider error events are properly recorded."""
        record_provider_error(
            provider="openai",
            model="gpt-4",
            session_id="test-session",
            run_id="test-run",
            error_message="API rate limit exceeded",
        )

        events = self.read_telemetry_events()
        assert len(events) == 1
        event = events[0]
        
        assert event["event_type"] == "provider_error"
        assert event["provider"] == "openai"
        assert event["model"] == "gpt-4"
        assert event["session_id"] == "test-session"
        assert event["run_id"] == "test-run"
        assert event["success"] is False
        assert event["sanitized_error"] == "API rate limit exceeded"

    def test_backward_compatibility(self):
        """Test that the old record_prompt_event function still works."""
        record_prompt_event(
            source="test",
            provider="openai",
            model="gpt-4",
            task_type="code",
            processing_latency_sec=1.5,
            clarifying_questions_count=2,
            skip_questions=False,
            refine_mode=True,
            success=True,
        )

        events = self.read_telemetry_events()
        assert len(events) == 1
        event = events[0]
        
        # Should have schema_version and new fields with None defaults
        assert event["schema_version"] == 1
        assert event["session_id"] is None
        assert event["run_id"] is None
        assert event["event_type"] == "prompt_run"
        # Extended fields should be None for backward compatibility
        assert event["input_chars"] is None
        assert event["output_chars"] is None
        assert event["llm_latency_sec"] is None
        assert event["total_run_latency_sec"] is None
        assert event["quiet_mode"] is None
        assert event["history_enabled"] is None
        assert event["python_version"] is None
        assert event["platform"] is None
        assert event["interface"] is None

    def test_sample_rate_parsing(self):
        """Test that sample rate parsing works correctly."""
        # Test default (no env var)
        with patch.dict(os.environ, {}, clear=True):
            # Force reset of cached sample rate
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            assert _get_sample_rate() == 1.0

        # Test valid values
        with patch.dict(os.environ, {TELEMETRY_SAMPLE_RATE_ENV: "0.5"}):
            # Force reset of cached sample rate
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            assert _get_sample_rate() == 0.5

        with patch.dict(os.environ, {TELEMETRY_SAMPLE_RATE_ENV: "1.0"}):
            # Force reset of cached sample rate
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            assert _get_sample_rate() == 1.0

        # Test invalid values
        with patch.dict(os.environ, {TELEMETRY_SAMPLE_RATE_ENV: "invalid"}):
            # Force reset of cached sample rate
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            assert _get_sample_rate() == 1.0

        with patch.dict(os.environ, {TELEMETRY_SAMPLE_RATE_ENV: "2.0"}):  # > 1.0
            # Force reset of cached sample rate
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            assert _get_sample_rate() == 1.0

        with patch.dict(os.environ, {TELEMETRY_SAMPLE_RATE_ENV: "0"}):  # == 0 (valid - no sampling)
            # Force reset of cached sample rate
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            assert _get_sample_rate() == 0.0  # 0.0 is now valid (no sampling)

        with patch.dict(os.environ, {TELEMETRY_SAMPLE_RATE_ENV: "-0.1"}):  # < 0 (invalid)
            # Force reset of cached sample rate
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            assert _get_sample_rate() == 1.0  # Invalid negative value

    def test_sampling_behavior(self):
        """Test that sampling behavior works as expected."""
        # Test with 0% sample rate - should never record
        import os
        from promptheus.telemetry import TELEMETRY_SAMPLE_RATE_ENV
        original_value = os.environ.get(TELEMETRY_SAMPLE_RATE_ENV)
        os.environ[TELEMETRY_SAMPLE_RATE_ENV] = "0.0"
        
        try:
            # Force reset of cached sample rate and telemetry enabled
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            telemetry_module._cached_enabled = None
            
            # Debug: check the actual sample rate and environment
            from promptheus.telemetry import _get_sample_rate, TELEMETRY_SAMPLE_RATE_ENV
            print(f"Environment variable {TELEMETRY_SAMPLE_RATE_ENV}: {os.environ.get(TELEMETRY_SAMPLE_RATE_ENV)}")
            print(f"Cached sample rate before reset: {telemetry_module._cached_sample_rate}")
            sample_rate = _get_sample_rate()
            print(f"Sample rate after reset: {sample_rate}")
            assert sample_rate == 0.0, f"Expected 0.0, got {sample_rate}"

            with patch('random.random', return_value=0.5):  # Always above 0.0
                record_prompt_run_event(
                    source="test",
                    provider="openai",
                    model="gpt-4",
                    task_type="code",
                    processing_latency_sec=1.5,
                    clarifying_questions_count=2,
                    skip_questions=False,
                    refine_mode=True,
                    success=True,
                    session_id="test-session",
                    run_id="test-run",
                )

            events = self.read_telemetry_events()
            assert len(events) == 0, f"Expected 0 events with 0% sample rate, got {len(events)}. Sample rate was {sample_rate}"
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop(TELEMETRY_SAMPLE_RATE_ENV, None)
            else:
                os.environ[TELEMETRY_SAMPLE_RATE_ENV] = original_value

        # Test with 100% sample rate - should always record
        with patch.dict(os.environ, {TELEMETRY_SAMPLE_RATE_ENV: "1.0"}):
            # Force reset of cached sample rate and telemetry enabled
            import promptheus.telemetry as telemetry_module
            telemetry_module._cached_sample_rate = None
            telemetry_module._cached_enabled = None
            
            with patch('random.random', return_value=0.5):
                record_prompt_run_event(
                    source="test",
                    provider="openai",
                    model="gpt-4",
                    task_type="code",
                    processing_latency_sec=1.5,
                    clarifying_questions_count=2,
                    skip_questions=False,
                    refine_mode=True,
                    success=True,
                    session_id="test-session",
                    run_id="test-run",
                )

            events = self.read_telemetry_events()
            assert len(events) == 1  # Should be recorded

    def test_telemetry_disabled(self):
        """Test that telemetry is not recorded when disabled."""
        # Force reset of cached telemetry enabled
        import promptheus.telemetry as telemetry_module
        telemetry_module._cached_enabled = None
        
        with patch.dict(os.environ, {"PROMPTHEUS_TELEMETRY_ENABLED": "0"}):
            # Force reset again inside the context
            telemetry_module._cached_enabled = None
            
            record_prompt_run_event(
                source="test",
                provider="openai",
                model="gpt-4",
                task_type="code",
                processing_latency_sec=1.5,
                clarifying_questions_count=2,
                skip_questions=False,
                refine_mode=True,
                success=True,
                session_id="test-session",
                run_id="test-run",
            )

            events = self.read_telemetry_events()
            assert len(events) == 0  # Should not be recorded

    def test_error_handling(self):
        """Test that telemetry errors are gracefully handled."""
        # Make the telemetry file directory read-only to cause an error
        os.chmod(self.temp_dir, 0o444)
        
        try:
            # This should not raise an exception
            record_prompt_run_event(
                source="test",
                provider="openai",
                model="gpt-4",
                task_type="code",
                processing_latency_sec=1.5,
                clarifying_questions_count=2,
                skip_questions=False,
                refine_mode=True,
                success=True,
                session_id="test-session",
                run_id="test-run",
            )
            
            # Should not have crashed the test
            assert True
        finally:
            # Restore permissions for cleanup
            os.chmod(self.temp_dir, 0o755)

    def test_optional_fields(self):
        """Test that optional fields can be omitted."""
        record_prompt_run_event(
            source="test",
            provider="openai",
            model="gpt-4",
            task_type="code",
            processing_latency_sec=1.5,
            clarifying_questions_count=2,
            skip_questions=False,
            refine_mode=True,
            success=True,
            session_id="test-session",
            run_id="test-run",
            # Omit optional fields
        )

        events = self.read_telemetry_events()
        assert len(events) == 1
        event = events[0]
        
        # Required fields should be present
        assert event["source"] == "test"
        assert event["provider"] == "openai"
        assert event["model"] == "gpt-4"
        
        # Optional fields should be None
        assert event["input_chars"] is None
        assert event["output_chars"] is None
        assert event["llm_latency_sec"] is None
        assert event["total_run_latency_sec"] is None
        assert event["quiet_mode"] is None
        assert event["history_enabled"] is None
        assert event["python_version"] is None
        assert event["platform"] is None
        assert event["interface"] is None

    def test_multiple_event_types(self):
        """Test recording multiple different event types."""
        # Record a prompt run
        record_prompt_run_event(
            source="test",
            provider="openai",
            model="gpt-4",
            task_type="code",
            processing_latency_sec=1.5,
            clarifying_questions_count=2,
            skip_questions=False,
            refine_mode=True,
            success=True,
            session_id="session-1",
            run_id="run-1",
        )

        # Record a clarifying questions summary (history enabled)
        record_clarifying_questions_summary(
            session_id="session-1",
            run_id="run-1",
            total_questions=3,
            history_enabled=True,
        )

        # Record a provider error
        record_provider_error(
            provider="anthropic",
            model="claude-3",
            session_id="session-1",
            run_id="run-2",
            error_message="Connection timeout",
        )

        events = self.read_telemetry_events()
        assert len(events) == 3

        # Check event types
        event_types = [event["event_type"] for event in events]
        assert "prompt_run" in event_types
        assert "clarifying_questions_summary" in event_types
        assert "provider_error" in event_types

        # Verify session/run IDs and sanitized errors are preserved
        for event in events:
            if event["event_type"] != "clarifying_questions_summary":
                assert event["session_id"] == "session-1"
            if event["event_type"] == "provider_error":
                assert event["run_id"] == "run-2"
                assert event["sanitized_error"] == "Connection timeout"
            else:
                assert event["run_id"] in ["run-1", "run-2"]
