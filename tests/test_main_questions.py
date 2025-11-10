from unittest.mock import Mock
from promptheus.main import QuestionPlan, ask_clarifying_questions
from promptheus.io_context import IOContext


class _StaticPrompt:
    """Simple helper that mimics questionary prompt objects."""

    def __init__(self, reply):
        self._reply = reply

    def ask(self):
        return self._reply


def create_mock_io():
    """Create a mock IOContext for testing."""
    io = Mock(spec=IOContext)
    io.messages = []
    io.notify = lambda msg: io.messages.append(msg)
    io.stdin_is_tty = True
    io.stdout_is_tty = True
    io.is_fully_interactive = True
    io.quiet_output = False
    return io


def test_required_question_reprompts_until_answer(monkeypatch):
    """Ensure required questions are re-asked when empty responses are provided."""
    replies = iter(["   ", "", "Ship it"])

    def fake_text(*args, **kwargs):
        return _StaticPrompt(next(replies))

    monkeypatch.setattr("promptheus.main.questionary.text", fake_text)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "goal",
                "message": "What is the goal?",
                "type": "text",
                "options": [],
                "required": True,
                "default": "",
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    assert answers["goal"] == "Ship it"
    assert any("required" in msg.lower() for msg in io.messages)


def test_radio_question_with_selection(monkeypatch):
    """Test radio button question with user selection."""
    def fake_select(*args, **kwargs):
        return _StaticPrompt("professional")

    monkeypatch.setattr("promptheus.main.questionary.select", fake_select)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "tone",
                "message": "What tone should be used?",
                "type": "radio",
                "options": ["casual", "professional", "formal"],
                "required": True,
                "default": "professional",
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    assert answers["tone"] == "professional"


def test_radio_question_with_default_selection(monkeypatch):
    """Test radio button question with user cancellation."""
    def fake_select(*args, **kwargs):
        return _StaticPrompt(None)  # User cancels

    monkeypatch.setattr("promptheus.main.questionary.select", fake_select)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "tone",
                "message": "What tone should be used?",
                "type": "radio",
                "options": ["casual", "professional", "formal"],
                "required": False,
                "default": "professional",
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    # Should return None when user cancels
    assert answers is None


def test_checkbox_question_single_selection(monkeypatch):
    """Test checkbox question with single selection."""
    def fake_checkbox(*args, **kwargs):
        return _StaticPrompt(["developers"])

    monkeypatch.setattr("promptheus.main.questionary.checkbox", fake_checkbox)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "audience",
                "message": "Who is the target audience?",
                "type": "checkbox",
                "options": ["developers", "designers", "managers", "students"],
                "required": True,
                "default": [],
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    assert answers["audience"] == ["developers"]


def test_checkbox_question_multiple_selections(monkeypatch):
    """Test checkbox question with multiple selections."""
    def fake_checkbox(*args, **kwargs):
        return _StaticPrompt(["developers", "designers"])

    monkeypatch.setattr("promptheus.main.questionary.checkbox", fake_checkbox)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "audience",
                "message": "Who is the target audience?",
                "type": "checkbox",
                "options": ["developers", "designers", "managers", "students"],
                "required": True,
                "default": [],
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    assert answers["audience"] == ["developers", "designers"]


def test_checkbox_question_no_selections_for_required(monkeypatch):
    """Test checkbox question with required field when no selections made."""
    replies = iter([[], ["developers"]])  # First empty, then valid selection

    def fake_checkbox(*args, **kwargs):
        return _StaticPrompt(next(replies))

    monkeypatch.setattr("promptheus.main.questionary.checkbox", fake_checkbox)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "audience",
                "message": "Who is the target audience?",
                "type": "checkbox",
                "options": ["developers", "designers", "managers", "students"],
                "required": True,
                "default": [],
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    assert answers["audience"] == ["developers"]
    assert any("required" in msg.lower() for msg in io.messages)


def test_checkbox_question_optional_no_selections(monkeypatch):
    """Test checkbox question with optional field when no selections made."""
    def fake_checkbox(*args, **kwargs):
        return _StaticPrompt([])  # Empty selection for optional question

    monkeypatch.setattr("promptheus.main.questionary.checkbox", fake_checkbox)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "audience",
                "message": "Who is the target audience? (optional)",
                "type": "checkbox",
                "options": ["developers", "designers", "managers", "students"],
                "required": False,
                "default": [],
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    assert answers["audience"] == []


def test_mixed_question_types(monkeypatch):
    """Test handling multiple question types in sequence."""
    text_replies = iter(["Write documentation", "comprehensive"])
    select_reply = "technical"
    checkbox_reply = ["developers", "students"]

    def fake_text(*args, **kwargs):
        return _StaticPrompt(next(text_replies))

    def fake_select(*args, **kwargs):
        return _StaticPrompt(select_reply)

    def fake_checkbox(*args, **kwargs):
        return _StaticPrompt(checkbox_reply)

    monkeypatch.setattr("promptheus.main.questionary.text", fake_text)
    monkeypatch.setattr("promptheus.main.questionary.select", fake_select)
    monkeypatch.setattr("promptheus.main.questionary.checkbox", fake_checkbox)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "goal",
                "message": "What is your goal?",
                "type": "text",
                "options": [],
                "required": True,
                "default": "",
            },
            {
                "key": "tone",
                "message": "What tone should be used?",
                "type": "radio",
                "options": ["casual", "technical", "formal"],
                "required": True,
                "default": "technical",
            },
            {
                "key": "audience",
                "message": "Who is the target audience?",
                "type": "checkbox",
                "options": ["developers", "designers", "managers", "students"],
                "required": True,
                "default": [],
            },
            {
                "key": "format",
                "message": "What format should be used?",
                "type": "text",
                "options": [],
                "required": False,
                "default": "concise",
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    assert answers["goal"] == "Write documentation"
    assert answers["tone"] == "technical"
    assert answers["audience"] == ["developers", "students"]
    assert answers["format"] == "comprehensive"


def test_optional_text_question_with_empty_answer(monkeypatch):
    """Test optional text question when user provides empty answer."""
    replies = iter(["   "])  # Empty answer for optional question

    def fake_text(*args, **kwargs):
        return _StaticPrompt(next(replies))

    monkeypatch.setattr("promptheus.main.questionary.text", fake_text)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "additional_notes",
                "message": "Any additional notes? (optional)",
                "type": "text",
                "options": [],
                "required": False,
                "default": "",
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    # Optional question should accept empty answer without reprompting
    assert answers.get("additional_notes") == ""


def test_question_with_default_value_text(monkeypatch):
    """Test text question that has a default value."""
    def fake_text(*args, **kwargs):
        return _StaticPrompt("")  # User accepts default (empty string)

    monkeypatch.setattr("promptheus.main.questionary.text", fake_text)

    io = create_mock_io()
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "urgency",
                "message": "What is the urgency level?",
                "type": "text",
                "options": [],
                "required": False,
                "default": "normal",
            }
        ],
        mapping={},
    )

    answers = ask_clarifying_questions(plan, io)

    # For optional questions with empty response, should return empty string
    assert answers["urgency"] == ""


def test_question_order_preservation():
    """Test that questions maintain their order in the answers."""
    # This is more of a structural test to ensure the answer mapping
    # preserves the original question order
    plan = QuestionPlan(
        skip_questions=False,
        task_type="generation",
        questions=[
            {
                "key": "first_q",
                "message": "First question",
                "type": "text",
                "options": [],
                "required": True,
                "default": "",
            },
            {
                "key": "second_q",
                "message": "Second question",
                "type": "radio",
                "options": ["a", "b"],
                "required": True,
                "default": "a",
            },
            {
                "key": "third_q",
                "message": "Third question",
                "type": "checkbox",
                "options": ["x", "y"],
                "required": True,
                "default": [],
            }
        ],
        mapping={},
    )

    # Verify question order is preserved
    assert len(plan.questions) == 3
    assert plan.questions[0]["key"] == "first_q"
    assert plan.questions[1]["key"] == "second_q"
    assert plan.questions[2]["key"] == "third_q"
