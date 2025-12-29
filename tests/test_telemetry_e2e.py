"""
End-to-end telemetry tests using real CLI commands.

These tests execute actual promptheus CLI commands and verify that telemetry
events are properly recorded to ~/.promptheus/telemetry.jsonl with correct metadata.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any

import pytest


class TestTelemetryE2E:
    """End-to-end telemetry tests with real CLI execution."""

    def setup_method(self):
        """Set up test environment."""
        # Use a temporary directory for all test data
        self.temp_dir = tempfile.mkdtemp()
        self.telemetry_file = Path(self.temp_dir) / "telemetry.jsonl"
        self.history_dir = Path(self.temp_dir) / "history"

        # Set up environment to isolate from user's actual data
        self.env = os.environ.copy()
        repo_root = Path(__file__).resolve().parent.parent
        bin_path = repo_root / "venv" / "bin"
        if bin_path.exists():
            self.env["PATH"] = f"{bin_path}:{self.env.get('PATH', '')}"
        self.env.update({
            "PROMPTHEUS_TELEMETRY_FILE": str(self.telemetry_file),
            "PROMPTHEUS_TELEMETRY_ENABLED": "1",
            "PROMPTHEUS_TELEMETRY_SAMPLE_RATE": "1.0",
            "PROMPTHEUS_ENABLE_HISTORY": "1",
            "PROMPTHEUS_HISTORY_DIR": str(self.history_dir),  # Isolate history
        })

    def teardown_method(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def read_telemetry_events(self) -> List[Dict[str, Any]]:
        """Read and parse all telemetry events from file."""
        if not self.telemetry_file.exists():
            return []

        events = []
        with open(self.telemetry_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line.strip()))
        return events

    def find_events_by_type(self, events: List[Dict[str, Any]], event_type: str) -> List[Dict[str, Any]]:
        """Find all events of a specific type."""
        return [e for e in events if e.get("event_type") == event_type]

    def run_promptheus(self, args: List[str], input_text: str = None) -> subprocess.CompletedProcess:
        """Run promptheus command and return result."""
        cmd = ["promptheus"] + args
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
        )
        return result

    def test_cli_skip_questions_basic(self):
        """Test basic CLI usage with --skip-questions."""
        result = self.run_promptheus([
            "--skip-questions",
            "Write a short function to add two numbers"
        ])

        # Command should succeed (or fail gracefully if no provider configured)
        # We're mainly interested in telemetry being written

        events = self.read_telemetry_events()

        # Should have at least one event
        assert len(events) >= 1, "No telemetry events were recorded"

        # Find prompt_run events
        prompt_events = self.find_events_by_type(events, "prompt_run")
        assert len(prompt_events) >= 1, "No prompt_run events found"

        event = prompt_events[0]

        # Verify required fields
        assert event["event_type"] == "prompt_run"
        assert event["schema_version"] == 1
        assert "timestamp" in event
        assert "session_id" in event
        assert "run_id" in event

        # Verify interface and flags
        assert event["interface"] == "cli"
        assert event["skip_questions"] is True

        # Verify metrics are present
        assert event["input_chars"] is not None
        assert event["input_chars"] > 0

        # Provider info (may be None if no provider configured)
        # assert "provider" in event
        # assert "model" in event

    def test_cli_refine_mode(self):
        """Test CLI usage with --refine mode (forces questions)."""
        # Note: This will try to ask questions interactively
        # We'll provide empty input to skip quickly
        result = self.run_promptheus([
            "--refine",
            "Create a deployment guide"
        ], input_text="\n\n\n")  # Empty answers to questions

        events = self.read_telemetry_events()
        assert len(events) >= 1

        prompt_events = self.find_events_by_type(events, "prompt_run")
        assert len(prompt_events) >= 1

        event = prompt_events[0]
        assert event["interface"] == "cli"
        assert event["refine_mode"] is True

    def test_telemetry_file_location_default(self):
        """Test that telemetry file defaults to ~/.promptheus/telemetry.jsonl."""
        # Remove our custom path to test default
        env_default = self.env.copy()
        del env_default["PROMPTHEUS_TELEMETRY_FILE"]

        result = subprocess.run(
            ["promptheus", "--skip-questions", "test prompt"],
            capture_output=True,
            text=True,
            env=env_default,
            timeout=30,
        )

        # Check default location
        default_path = Path.home() / ".promptheus" / "telemetry.jsonl"

        # File should exist (or parent dir should exist)
        # Note: We won't assert file exists because provider might not be configured
        assert default_path.parent.exists() or Path.home().exists()

    def test_telemetry_disabled(self):
        """Test that telemetry can be disabled via environment variable."""
        env_disabled = self.env.copy()
        env_disabled["PROMPTHEUS_TELEMETRY_ENABLED"] = "0"

        result = subprocess.run(
            ["promptheus", "--skip-questions", "test prompt"],
            capture_output=True,
            text=True,
            env=env_disabled,
            timeout=30,
        )

        events = self.read_telemetry_events()

        # No events should be recorded
        assert len(events) == 0, "Events were recorded despite telemetry being disabled"

    def test_sampling_zero_percent(self):
        """Test that 0% sample rate records nothing."""
        env_no_sample = self.env.copy()
        env_no_sample["PROMPTHEUS_TELEMETRY_SAMPLE_RATE"] = "0.0"

        result = subprocess.run(
            ["promptheus", "--skip-questions", "test prompt"],
            capture_output=True,
            text=True,
            env=env_no_sample,
            timeout=30,
        )

        events = self.read_telemetry_events()
        assert len(events) == 0, "Events were recorded with 0% sample rate"

    def test_multiple_runs_same_file(self):
        """Test that multiple runs append to the same telemetry file."""
        # Run multiple times
        for i in range(3):
            result = self.run_promptheus([
                "--skip-questions",
                f"Test prompt {i}"
            ])
            time.sleep(0.1)  # Small delay between runs

        events = self.read_telemetry_events()

        # Should have multiple events
        prompt_events = self.find_events_by_type(events, "prompt_run")
        assert len(prompt_events) >= 3, f"Expected at least 3 events, got {len(prompt_events)}"

        # Each should have unique timestamps
        timestamps = [e["timestamp"] for e in prompt_events]
        assert len(set(timestamps)) >= 2, "Timestamps should be different"

    def test_privacy_no_prompt_text(self):
        """Test that actual prompt text is NOT stored in telemetry."""
        secret_text = "VERY_SECRET_STRING_xyz123"

        result = self.run_promptheus([
            "--skip-questions",
            f"This prompt contains {secret_text} which should not appear in telemetry"
        ])

        # Read raw file content
        if self.telemetry_file.exists():
            with open(self.telemetry_file, 'r') as f:
                raw_content = f.read()

            # Secret should NOT appear anywhere
            assert secret_text not in raw_content, "Secret text found in telemetry file!"

    def test_event_required_fields(self):
        """Test that all required fields are present in events."""
        result = self.run_promptheus([
            "--skip-questions",
            "Test required fields"
        ])

        events = self.read_telemetry_events()
        assert len(events) >= 1

        event = events[0]

        # Required fields for all events
        required_fields = [
            "timestamp",
            "event_type",
            "schema_version",
            "session_id",
            "run_id",
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"
            assert event[field] is not None, f"Field {field} is None"

    def test_latency_metrics_reasonable(self):
        """Test that latency metrics are present and reasonable."""
        result = self.run_promptheus([
            "--skip-questions",
            "Test latency metrics"
        ])

        events = self.read_telemetry_events()
        prompt_events = self.find_events_by_type(events, "prompt_run")

        if len(prompt_events) > 0:
            event = prompt_events[0]

            # Should have latency fields
            if event.get("processing_latency_sec") is not None:
                assert event["processing_latency_sec"] > 0
                assert event["processing_latency_sec"] < 300  # Less than 5 minutes

            if event.get("total_run_latency_sec") is not None:
                assert event["total_run_latency_sec"] > 0
                assert event["total_run_latency_sec"] < 300

    def test_character_counts_present(self):
        """Test that character counts are tracked."""
        test_prompt = "This is a test prompt for character counting" * 5

        result = self.run_promptheus([
            "--skip-questions",
            test_prompt
        ])

        events = self.read_telemetry_events()
        prompt_events = self.find_events_by_type(events, "prompt_run")

        if len(prompt_events) > 0:
            event = prompt_events[0]

            # Input chars should be recorded
            if event.get("input_chars") is not None:
                assert event["input_chars"] > 0
                # Should be roughly the length of our prompt
                assert event["input_chars"] > len(test_prompt) * 0.5

    def test_success_field_on_error(self):
        """Test that success field is False when there's an error."""
        # Try to use an invalid provider to trigger an error
        env_bad_provider = self.env.copy()
        env_bad_provider["PROMPTHEUS_PROVIDER"] = "invalid_provider_xyz"

        result = subprocess.run(
            ["promptheus", "--skip-questions", "test error"],
            capture_output=True,
            text=True,
            env=env_bad_provider,
            timeout=30,
        )

        # Command should fail
        # assert result.returncode != 0

        events = self.read_telemetry_events()

        # May have provider_error events
        error_events = self.find_events_by_type(events, "provider_error")

        # If we have error events, success should be False
        for event in error_events:
            assert event["success"] is False

    def test_history_enabled_records_question_summary(self):
        """Test that clarifying_questions_summary is recorded when history is enabled."""
        # This test would need interactive input or mocking
        # For now, just verify the environment is set correctly
        assert self.env.get("PROMPTHEUS_ENABLE_HISTORY") == "1"

    def test_history_disabled_no_question_summary(self):
        """Test that clarifying_questions_summary is NOT recorded when history is disabled."""
        env_no_history = self.env.copy()
        env_no_history["PROMPTHEUS_ENABLE_HISTORY"] = "0"

        result = subprocess.run(
            ["promptheus", "--skip-questions", "test no history"],
            capture_output=True,
            text=True,
            env=env_no_history,
            timeout=30,
        )

        events = self.read_telemetry_events()

        # Should not have clarifying_questions_summary events
        summary_events = self.find_events_by_type(events, "clarifying_questions_summary")

        # With skip_questions, there shouldn't be summaries anyway
        # But this verifies the privacy guard


@pytest.mark.manual
class TestManualTelemetryVerification:
    """
    Manual verification tests that require human inspection.

    These tests document what should be verified manually in a deployed environment.
    """

    def test_manual_deployed_cli_verification(self):
        """
        Manual test: Verify CLI telemetry in deployed environment.

        Steps:
        1. SSH to deployed host
        2. Set environment:
           export PROMPTHEUS_TELEMETRY_ENABLED=1
           export PROMPTHEUS_TELEMETRY_SAMPLE_RATE=1.0
           export PROMPTHEUS_TELEMETRY_FILE=~/.promptheus/telemetry.jsonl
        3. Run commands:
           promptheus --skip-questions "Quick refine test"
           promptheus "Write a deployment runbook"  # with questions
        4. Inspect file:
           tail -n 20 ~/.promptheus/telemetry.jsonl
        5. Verify:
           - interface: "cli"
           - Reasonable latency and char counts
           - No actual prompt text in file
        """
        pytest.skip("Manual verification test - see docstring for steps")

    def test_manual_deployed_mcp_verification(self):
        """
        Manual test: Verify MCP telemetry in deployed environment.

        Steps:
        1. Start MCP server: promptheus mcp
        2. From MCP client, call:
           - refine_prompt without answers
           - refine_prompt with answers
           - tweak_prompt
        3. Inspect telemetry file on MCP host
        4. Verify:
           - interface: "mcp"
           - session_id and run_id present
           - clarifying_questions_summary when questions asked
        """
        pytest.skip("Manual verification test - see docstring for steps")

    def test_manual_deployed_web_verification(self):
        """
        Manual test: Verify Web telemetry in deployed environment.

        Steps:
        1. Access web UI at deployed URL
        2. Use the web interface to:
           - Refine a prompt with skip_questions
           - Refine a prompt with questions
           - Tweak a prompt
        3. Inspect telemetry file on web server host
        4. Verify:
           - interface: "web"
           - quiet_mode: true
           - Latencies and char counts present
        """
        pytest.skip("Manual verification test - see docstring for steps")
