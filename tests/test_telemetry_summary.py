"""
Tests for telemetry summary functionality.
"""

import json
import tempfile
from pathlib import Path
from io import StringIO

import pytest
from rich.console import Console

from promptheus.telemetry_summary import (
    print_telemetry_summary,
    read_telemetry_events,
    aggregate_metrics,
    RunMetrics,
    QuestionMetrics,
)


class TestTelemetrySummary:
    """Test telemetry summary aggregation and display."""

    def create_test_telemetry_file(self, events: list) -> Path:
        """Create a temporary telemetry file with given events."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl')
        for event in events:
            json.dump(event, temp_file)
            temp_file.write('\n')
        temp_file.close()
        return Path(temp_file.name)

    def test_empty_file(self):
        """Test handling of empty telemetry file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl')
        temp_file.close()
        path = Path(temp_file.name)

        # Create a console that writes to string
        output = StringIO()
        console = Console(file=output, force_terminal=False)

        exit_code = print_telemetry_summary(console, path)

        assert exit_code == 0
        assert "No telemetry data found" in output.getvalue() or "No valid" in output.getvalue()

        # Cleanup
        path.unlink()

    def test_nonexistent_file(self):
        """Test handling of nonexistent telemetry file."""
        path = Path("/tmp/nonexistent_telemetry_file_xyz.jsonl")

        output = StringIO()
        console = Console(file=output, force_terminal=False)

        exit_code = print_telemetry_summary(console, path)

        assert exit_code == 0
        assert "No telemetry data found" in output.getvalue()

    def test_basic_aggregation(self):
        """Test basic metrics aggregation."""
        events = [
            {
                "timestamp": "2025-12-03T10:00:00",
                "event_type": "prompt_run",
                "schema_version": 1,
                "session_id": "session-1",
                "run_id": "run-1",
                "source": "cli",
                "provider": "anthropic",
                "model": "claude-3-haiku",
                "task_type": "analysis",
                "processing_latency_sec": 2.5,
                "llm_latency_sec": 2.0,
                "input_chars": 100,
                "output_chars": 500,
                "clarifying_questions_count": 0,
                "skip_questions": True,
                "refine_mode": False,
                "success": True,
                "interface": "cli",
            },
            {
                "timestamp": "2025-12-03T10:05:00",
                "event_type": "prompt_run",
                "schema_version": 1,
                "session_id": "session-1",
                "run_id": "run-2",
                "source": "cli",
                "provider": "anthropic",
                "model": "claude-3-haiku",
                "task_type": "generation",
                "processing_latency_sec": 3.0,
                "llm_latency_sec": 2.5,
                "input_chars": 150,
                "output_chars": 600,
                "clarifying_questions_count": 2,
                "skip_questions": False,
                "refine_mode": True,
                "success": True,
                "interface": "cli",
            },
        ]

        overall, by_interface, questions, by_provider, error_messages, error_by_provider = aggregate_metrics(events)

        # Check overall metrics
        assert overall.total_runs == 2
        assert overall.successful_runs == 2
        assert overall.success_rate == 100.0
        assert overall.avg_total_latency() == 2.75  # (2.5 + 3.0) / 2
        assert overall.avg_llm_latency() == 2.25  # (2.0 + 2.5) / 2
        assert overall.avg_input_chars() == 125  # (100 + 150) / 2
        assert overall.avg_output_chars() == 550  # (500 + 600) / 2

        # Check interface breakdown
        assert "cli" in by_interface
        assert by_interface["cli"].total_runs == 2
        assert by_interface["cli"].success_rate == 100.0

        # Check questions
        assert questions.total_runs == 2
        assert questions.runs_with_questions == 1
        assert questions.percentage_with_questions == 50.0
        assert questions.avg_questions_when_present() == 2.0

        # Check provider breakdown
        assert ("anthropic", "claude-3-haiku") in by_provider
        assert by_provider[("anthropic", "claude-3-haiku")].total_runs == 2

    def test_multiple_interfaces(self):
        """Test aggregation across multiple interfaces."""
        events = [
            {
                "event_type": "prompt_run",
                "session_id": "s1",
                "run_id": "r1",
                "interface": "cli",
                "provider": "anthropic",
                "model": "claude-3",
                "success": True,
                "processing_latency_sec": 1.0,
            },
            {
                "event_type": "prompt_run",
                "session_id": "s2",
                "run_id": "r2",
                "interface": "web",
                "provider": "google",
                "model": "gemini",
                "success": True,
                "processing_latency_sec": 2.0,
            },
            {
                "event_type": "prompt_run",
                "session_id": "s3",
                "run_id": "r3",
                "interface": "mcp",
                "provider": "openai",
                "model": "gpt-4",
                "success": False,
                "processing_latency_sec": 3.0,
            },
        ]

        overall, by_interface, questions, by_provider, _, _ = aggregate_metrics(events)

        assert overall.total_runs == 3
        assert overall.successful_runs == 2
        assert overall.success_rate == pytest.approx(66.67, rel=0.1)

        assert len(by_interface) == 3
        assert "cli" in by_interface
        assert "web" in by_interface
        assert "mcp" in by_interface

        assert by_interface["cli"].total_runs == 1
        assert by_interface["web"].total_runs == 1
        assert by_interface["mcp"].total_runs == 1
        assert by_interface["mcp"].successful_runs == 0

    def test_question_distribution(self):
        """Test question count distribution."""
        events = [
            {"event_type": "prompt_run", "session_id": "s1", "run_id": "r1", "clarifying_questions_count": 0},
            {"event_type": "prompt_run", "session_id": "s2", "run_id": "r2", "clarifying_questions_count": 0},
            {"event_type": "prompt_run", "session_id": "s3", "run_id": "r3", "clarifying_questions_count": 2},
            {"event_type": "prompt_run", "session_id": "s4", "run_id": "r4", "clarifying_questions_count": 5},
            {"event_type": "prompt_run", "session_id": "s5", "run_id": "r5", "clarifying_questions_count": 10},
        ]

        _, _, questions, _, _, _ = aggregate_metrics(events)

        dist = questions.distribution()

        assert dist["0"] == 2  # 2 runs with 0 questions
        assert dist["1-3"] == 1  # 1 run with 2 questions
        assert dist["4-7"] == 1  # 1 run with 5 questions
        assert dist["8+"] == 1  # 1 run with 10 questions

    def test_provider_errors(self):
        """Test provider error aggregation."""
        events = [
            {
                "event_type": "provider_error",
                "provider": "anthropic",
                "model": "claude-3",
                "session_id": "s1",
                "run_id": "r1",
                "sanitized_error": "API key invalid",
                "success": False,
            },
            {
                "event_type": "provider_error",
                "provider": "anthropic",
                "model": "claude-3",
                "session_id": "s2",
                "run_id": "r2",
                "sanitized_error": "API key invalid",
                "success": False,
            },
            {
                "event_type": "provider_error",
                "provider": "google",
                "model": "gemini",
                "session_id": "s3",
                "run_id": "r3",
                "sanitized_error": "Rate limit exceeded",
                "success": False,
            },
        ]

        _, _, _, _, error_messages, error_by_provider = aggregate_metrics(events)

        assert error_messages["API key invalid"] == 2
        assert error_messages["Rate limit exceeded"] == 1

        assert error_by_provider[("anthropic", "claude-3")] == 2
        assert error_by_provider[("google", "gemini")] == 1

    def test_missing_fields(self):
        """Test handling of events with missing fields."""
        events = [
            {
                "event_type": "prompt_run",
                "session_id": "s1",
                "run_id": "r1",
                # Missing many fields
            },
            {
                "event_type": "prompt_run",
                "session_id": "s2",
                "run_id": "r2",
                "success": True,
                # Missing latency, chars, etc.
            },
        ]

        overall, _, _, _, _, _ = aggregate_metrics(events)

        assert overall.total_runs == 2
        assert overall.successful_runs == 1
        assert overall.avg_total_latency() is None  # No latency data
        assert overall.avg_input_chars() is None  # No char data

    def test_malformed_lines(self):
        """Test handling of malformed JSON lines."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl')
        temp_file.write('{"event_type": "prompt_run", "session_id": "s1"}\n')
        temp_file.write('this is not json\n')
        temp_file.write('{"event_type": "prompt_run", "session_id": "s2"}\n')
        temp_file.write('\n')  # Empty line
        temp_file.write('{"event_type": "prompt_run", "session_id": "s3"}\n')
        temp_file.close()
        path = Path(temp_file.name)

        events = read_telemetry_events(path)

        # Should have 3 valid events, skipping malformed line and empty line
        assert len(events) == 3
        assert events[0]["session_id"] == "s1"
        assert events[1]["session_id"] == "s2"
        assert events[2]["session_id"] == "s3"

        # Cleanup
        path.unlink()

    def test_full_summary_output(self):
        """Test complete summary generation with realistic data."""
        events = [
            # CLI runs
            {
                "event_type": "prompt_run",
                "session_id": "s1",
                "run_id": "r1",
                "interface": "cli",
                "provider": "anthropic",
                "model": "claude-3-haiku",
                "success": True,
                "processing_latency_sec": 2.0,
                "llm_latency_sec": 1.8,
                "input_chars": 100,
                "output_chars": 500,
                "clarifying_questions_count": 0,
            },
            {
                "event_type": "prompt_run",
                "session_id": "s2",
                "run_id": "r2",
                "interface": "cli",
                "provider": "google",
                "model": "gemini-2.5-flash",
                "success": True,
                "processing_latency_sec": 3.0,
                "llm_latency_sec": 2.5,
                "input_chars": 150,
                "output_chars": 600,
                "clarifying_questions_count": 3,
            },
            # Web run
            {
                "event_type": "prompt_run",
                "session_id": "s3",
                "run_id": "r3",
                "interface": "web",
                "provider": "anthropic",
                "model": "claude-3-haiku",
                "success": True,
                "processing_latency_sec": 2.5,
                "llm_latency_sec": 2.2,
                "input_chars": 120,
                "output_chars": 550,
                "clarifying_questions_count": 0,
            },
            # Error
            {
                "event_type": "provider_error",
                "provider": "openai",
                "model": "gpt-4",
                "session_id": "s4",
                "run_id": "r4",
                "sanitized_error": "API key invalid",
                "success": False,
            },
        ]

        path = self.create_test_telemetry_file(events)

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=80)

        exit_code = print_telemetry_summary(console, path)

        assert exit_code == 0

        output_text = output.getvalue()

        # Check that key sections are present
        assert "Telemetry Summary" in output_text
        assert "Overview" in output_text
        assert "Total Runs" in output_text and "3" in output_text
        assert "Success Rate" in output_text and "100.0%" in output_text
        assert "By Interface" in output_text
        assert "cli" in output_text
        assert "web" in output_text
        assert "Clarifying Questions" in output_text
        assert "Providers / Models" in output_text
        assert "claude-3-haiku" in output_text
        assert "gemini-2.5-flash" in output_text
        assert "Provider Errors" in output_text
        assert "Total Errors" in output_text and "1" in output_text
        assert "API key invalid" in output_text

        # Cleanup
        path.unlink()

    def test_metrics_with_null_values(self):
        """Test metrics calculation when some values are None."""
        metrics = RunMetrics()
        metrics.total_runs = 3
        metrics.successful_runs = 2
        metrics.total_latencies = [1.0, 2.0]  # Only 2 out of 3 runs have latency

        assert metrics.success_rate == pytest.approx(66.67, rel=0.1)
        assert metrics.avg_total_latency() == 1.5
        assert metrics.median_total_latency() == 1.5

        # Empty lists
        empty_metrics = RunMetrics()
        assert empty_metrics.avg_total_latency() is None
        assert empty_metrics.median_total_latency() is None

    def test_unknown_provider_and_interface(self):
        """Test handling of missing provider/interface fields."""
        events = [
            {
                "event_type": "prompt_run",
                "session_id": "s1",
                "run_id": "r1",
                # No provider, model, or interface
                "success": True,
            },
        ]

        overall, by_interface, _, by_provider, _, _ = aggregate_metrics(events)

        assert overall.total_runs == 1
        assert "unknown" in by_interface
        assert ("unknown", "unknown") in by_provider


class TestRunMetrics:
    """Test RunMetrics dataclass."""

    def test_success_rate_calculation(self):
        """Test success rate percentage calculation."""
        metrics = RunMetrics()
        metrics.total_runs = 10
        metrics.successful_runs = 8

        assert metrics.success_rate == 80.0

        # Edge case: 0 runs
        empty_metrics = RunMetrics()
        assert empty_metrics.success_rate == 0.0

    def test_average_calculations(self):
        """Test average metric calculations."""
        metrics = RunMetrics()
        metrics.total_latencies = [1.0, 2.0, 3.0, 4.0]
        metrics.llm_latencies = [0.8, 1.8, 2.8]
        metrics.input_chars = [100, 200, 300]
        metrics.output_chars = [500, 600, 700, 800]

        assert metrics.avg_total_latency() == 2.5
        assert metrics.median_total_latency() == 2.5
        assert metrics.avg_llm_latency() == pytest.approx(1.8, rel=0.01)
        assert metrics.median_llm_latency() == 1.8
        assert metrics.avg_input_chars() == 200.0
        assert metrics.avg_output_chars() == 650.0


class TestQuestionMetrics:
    """Test QuestionMetrics dataclass."""

    def test_percentage_calculation(self):
        """Test percentage of runs with questions."""
        metrics = QuestionMetrics()
        metrics.total_runs = 100
        metrics.runs_with_questions = 30

        assert metrics.percentage_with_questions == 30.0

        # Edge case: 0 runs
        empty_metrics = QuestionMetrics()
        assert empty_metrics.percentage_with_questions == 0.0

    def test_average_when_present(self):
        """Test average question count when questions are asked."""
        metrics = QuestionMetrics()
        metrics.question_counts = [1, 2, 3, 4, 5]

        assert metrics.avg_questions_when_present() == 3.0

        # Empty list
        empty_metrics = QuestionMetrics()
        assert empty_metrics.avg_questions_when_present() is None

    def test_distribution_buckets(self):
        """Test question count distribution into buckets."""
        metrics = QuestionMetrics()
        metrics.total_runs = 10
        metrics.runs_with_questions = 6
        metrics.question_counts = [1, 2, 3, 5, 6, 10]

        dist = metrics.distribution()

        assert dist["0"] == 4  # 10 total - 6 with questions
        assert dist["1-3"] == 3  # 1, 2, 3
        assert dist["4-7"] == 2  # 5, 6
        assert dist["8+"] == 1  # 10
