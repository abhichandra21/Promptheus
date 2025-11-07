from promptheus.main import QuestionPlan, ask_clarifying_questions


class _StaticPrompt:
    """Simple helper that mimics questionary prompt objects."""

    def __init__(self, reply):
        self._reply = reply

    def ask(self):
        return self._reply


def test_required_question_reprompts_until_answer(monkeypatch):
    """Ensure required questions are re-asked when empty responses are provided."""
    replies = iter(["   ", "", "Ship it"])

    def fake_text(*args, **kwargs):
        return _StaticPrompt(next(replies))

    monkeypatch.setattr("promptheus.main.questionary.text", fake_text)

    messages = []
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

    answers = ask_clarifying_questions(plan, messages.append)

    assert answers["goal"] == "Ship it"
    assert any("required" in msg.lower() for msg in messages)
