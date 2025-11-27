"""
MCP Server implementation for Promptheus.
Exposes prompt refinement as an MCP tool.

Architecture:
- Provides a 'refine_prompt' tool via MCP protocol
- Supports two interaction modes:
  1. Interactive (when AskUserQuestion is available): Asks questions directly
  2. Structured (fallback): Returns JSON with questions for client to handle
- Feature detection: Uses an injected AskUserQuestion callable at runtime
- Cross-platform compatibility: Works with any MCP client

Response Format:
- Success (refined):
    {"type": "refined", "prompt": "..."}
- Clarification needed:
    {
      "type": "clarification_needed",
      "task_type": "analysis" | "generation",
      "message": "...",
      "questions_for_ask_user_question": [...],
      "answer_mapping": {"q0": "<question 0 text>", ...},
      "instructions": "..."
    }
- Error:
    {"type": "error", "error_type": "...", "message": "..."}
"""
import logging
import sys
from typing import Optional, Dict, Any, List, Union, Tuple

# FastMCP import with graceful fallback
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# Core Promptheus imports
from promptheus.config import Config
from promptheus.providers import get_provider
from promptheus.utils import sanitize_error_message
from promptheus.prompts import (
    CLARIFICATION_SYSTEM_INSTRUCTION,
    GENERATION_SYSTEM_INSTRUCTION,
    ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
)

# Initialize logger (configured once at module level)
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("promptheus.mcp")

# Initialize FastMCP
if FastMCP:
    mcp = FastMCP("Promptheus")
else:
    mcp = None

# AskUserQuestion injection point
# MCP clients can inject this function to enable interactive questioning
# Default: None (falls back to structured JSON responses)
_ask_user_question_fn = None


def set_ask_user_question(fn):
    """
    Inject an AskUserQuestion implementation for interactive mode.

    Args:
        fn: Callable that takes questions list and returns answers
            Expected signature: fn(questions: List[Dict]) -> Dict[str, str]
    """
    global _ask_user_question_fn
    _ask_user_question_fn = fn
    logger.info("AskUserQuestion function registered for interactive mode")


# Type aliases for clarity
QuestionMapping = Dict[str, str]  # Maps question IDs to question text
RefinedResponse = Dict[str, Any]
ClarificationResponse = Dict[str, Any]
ErrorResponse = Dict[str, Any]
RefineResult = Union[RefinedResponse, ClarificationResponse, ErrorResponse]

# Configuration
MAX_PROMPT_LENGTH = 50000  # characters


def _ensure_mcp_available():
    """Verify MCP package is installed."""
    if mcp is None:
        print(
            "Error: 'mcp' package is not installed. "
            "Please install it with 'pip install mcp'.",
            file=sys.stderr,
        )
        sys.exit(1)


NEXT_ACTION_HINT = (
    "Use this refined prompt as input to your main LLM or tool. "
    'For the Promptheus CLI, you can run: promptheus --skip-questions "<refined prompt here>".'
)


def _build_refined_response(refined_prompt: str) -> RefinedResponse:
    """
    Build a standard refined response payload with guidance for next steps.

    Args:
        refined_prompt: The final refined prompt text
    """
    return {
        "type": "refined",
        "prompt": refined_prompt,
        "next_action": NEXT_ACTION_HINT,
    }


def _validate_prompt(prompt: str) -> Optional[ErrorResponse]:
    """
    Validate prompt input.

    Returns:
        ErrorResponse if invalid, None if valid
    """
    if not prompt or not prompt.strip():
        return {
            "type": "error",
            "error_type": "ValidationError",
            "message": "Prompt cannot be empty",
        }

    if len(prompt) > MAX_PROMPT_LENGTH:
        return {
            "type": "error",
            "error_type": "ValidationError",
            "message": f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters",
        }

    return None


def _initialize_provider(
    provider: Optional[str], model: Optional[str]
) -> Tuple[Any, Optional[ErrorResponse]]:
    """
    Initialize and validate LLM provider.

    Returns:
        Tuple of (provider_instance, error_response)
        If error_response is not None, provider_instance will be None
    """
    try:
        config = Config()

        if provider:
            config.set_provider(provider)
        if model:
            config.set_model(model)

        if not config.validate():
            error_msgs = "\n".join(config.consume_error_messages())
            # Note: Config already sanitizes error messages
            return None, {
                "type": "error",
                "error_type": "ConfigurationError",
                "message": f"Configuration error: {error_msgs}",
            }

        provider_name = config.provider
        if not provider_name:
            return None, {
                "type": "error",
                "error_type": "ConfigurationError",
                "message": "No provider configured. Please set API keys in environment.",
            }

        llm_provider = get_provider(provider_name, config, config.get_model())
        return llm_provider, None

    except Exception as e:
        logger.exception("Failed to initialize provider")
        return None, {
            "type": "error",
            "error_type": type(e).__name__,
            "message": sanitize_error_message(str(e)),
        }


def _build_question_mapping(questions: List[Dict[str, Any]]) -> QuestionMapping:
    """
    Build mapping from question IDs to question text.

    Args:
        questions: List of question dicts with 'question' key

    Returns:
        Dict mapping q0, q1, etc. to full question text
    """
    return {f"q{i}": q.get("question", f"Question {i}") for i, q in enumerate(questions)}


def _try_interactive_questions(
    questions: List[Dict[str, Any]]
) -> Optional[Dict[str, str]]:
    """
    Attempt to ask questions interactively using AskUserQuestion.

    Returns:
        Dict of answers if successful, None if AskUserQuestion unavailable or fails
    """
    if _ask_user_question_fn is None:
        logger.debug("AskUserQuestion not available, using fallback")
        return None

    try:
        logger.info("Using interactive AskUserQuestion mode")
        answers = {}

        for i, q in enumerate(questions):
            q_id = f"q{i}"
            q_text = q.get("question", f"Question {i}")
            q_type = q.get("type", "text")
            options = q.get("options", [])
            required = q.get("required", True)

            # Format question for AskUserQuestion
            question_data = {
                "question": q_text,
                "header": f"Q{i+1}",
                "multiSelect": q_type == "checkbox",
            }

            if q_type in ("radio", "checkbox") and options:
                question_data["options"] = [
                    {"label": opt, "description": opt} for opt in options
                ]

            # Call injected AskUserQuestion function
            result = _ask_user_question_fn([question_data])

            # Extract answer from result
            if result and isinstance(result, dict):
                # Handle dict response with question keys
                answer = result.get(q_text) or result.get(q_id)
                if answer:
                    # Handle list results (from multiselect)
                    if isinstance(answer, list):
                        answers[q_id] = ", ".join(str(a) for a in answer)
                    else:
                        answers[q_id] = str(answer)
            elif result and isinstance(result, list) and len(result) > 0:
                # Handle list response
                if isinstance(result[0], list):
                    # Multiselect: list of selected options
                    answers[q_id] = ", ".join(str(a) for a in result[0])
                else:
                    # Single select: first item
                    answers[q_id] = str(result[0])
            elif not required:
                # Skip optional questions with no answer
                logger.debug(f"Skipping optional question {q_id}")
            else:
                # Required question with no valid answer
                logger.warning(f"No valid answer for required question {q_id}")
                return None

        return answers

    except Exception as exc:
        logger.warning(f"AskUserQuestion failed: {exc}", exc_info=True)
        return None


def _format_clarification_response(
    questions: List[Dict[str, Any]],
    task_type: str,
    mapping: QuestionMapping,
) -> ClarificationResponse:
    """
    Format structured clarification response for non-interactive clients.

    Args:
        questions: List of question dicts
        task_type: "analysis" or "generation"
        mapping: Question ID to text mapping

    Returns:
        Structured clarification response with guidance for using AskUserQuestion
    """
    # Format questions for AskUserQuestion tool
    formatted_questions = []
    for i, q in enumerate(questions):
        q_data = {
            "question": q.get("question", f"Question {i}"),
            "header": f"Q{i+1}",
            "multiSelect": q.get("type") == "checkbox",
        }
        if q.get("type") in ("radio", "checkbox") and q.get("options"):
            q_data["options"] = [
                {"label": opt, "description": opt}
                for opt in q.get("options", [])
            ]
        formatted_questions.append(q_data)

    return {
        "type": "clarification_needed",
        "task_type": task_type,
        "message": (
            "To refine this prompt effectively, I need to ask the user some clarifying questions. "
            "Please use the AskUserQuestion tool with the questions provided below, "
            "then call this tool again with the answers."
        ),
        "questions_for_ask_user_question": formatted_questions,
        "answer_mapping": mapping,
        "instructions": (
            "After collecting answers using AskUserQuestion:\n"
            "1. Map each answer to its corresponding question ID (q0, q1, etc.)\n"
            "2. Call promptheus.refine_prompt with:\n"
            "   - prompt: <original prompt text>\n"
            "   - answers: {q0: <answer0>, q1: <answer1>, ...}"
        ),
    }


if mcp:
    @mcp.tool()
    def refine_prompt(
        prompt: str,
        answers: Optional[Dict[str, str]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> RefineResult:
        """
        Refine a user prompt using AI-powered prompt engineering.

        Use the AskUserQuestion tool to clarify requirements when this tool returns
        type="clarification_needed". The response includes formatted questions ready
        to pass to AskUserQuestion.

        Workflow:
        1. Call refine_prompt with just the prompt parameter
        2. If response type is "clarification_needed":
           - Use the AskUserQuestion tool with the questions from "questions_for_ask_user_question"
           - Map the user's answers to question IDs (q0, q1, q2, etc.)
           - Call refine_prompt again with both prompt and answers dict
        3. If response type is "refined", return the prompt to the user

        Args:
            prompt: The initial prompt to refine (required)
            answers: Dict of {question_id: answer} if responding to questions (optional)
            provider: Override provider (e.g., 'google', 'anthropic') (optional)
            model: Override model name (optional)

        Returns:
            One of:
            - {"type": "refined", "prompt": "..."} - Success
            - {"type": "clarification_needed", "questions_for_ask_user_question": [...], ...} - Need answers
            - {"type": "error", "error_type": "...", "message": "..."} - Error

        Examples:
            # Simple refinement
            result = refine_prompt("Write a blog post about AI")
            # May return refined prompt or request clarification

            # With clarification
            result1 = refine_prompt("Write a blog post")
            # Returns: {"type": "clarification_needed", ...}
            # Then use AskUserQuestion and:
            result2 = refine_prompt(
                "Write a blog post",
                answers={"q0": "Technical audience", "q1": "Professional tone"}
            )
            # Returns: {"type": "refined", "prompt": "..."}
        """
        logger.info(
            f"refine_prompt called: prompt_len={len(prompt)}, "
            f"has_answers={bool(answers)}, provider={provider}, model={model}"
        )

        # Validate input
        validation_error = _validate_prompt(prompt)
        if validation_error:
            return validation_error

        # Initialize provider
        llm_provider, provider_error = _initialize_provider(provider, model)
        if provider_error:
            return provider_error

        try:
            # Case 1: Answers provided -> Generate final refined prompt
            if answers:
                logger.info(f"Refining with {len(answers)} answers")

                # Build question mapping from answer keys
                # (Ideally we'd preserve original mapping, but we reconstruct from keys)
                mapping = {key: f"Question: {key}" for key in answers.keys()}

                refined = llm_provider.refine_from_answers(
                    prompt, answers, mapping, GENERATION_SYSTEM_INSTRUCTION
                )

                return _build_refined_response(refined)

            # Case 2: No answers -> Determine if questions are needed
            logger.info("Analyzing prompt for clarification needs")

            analysis = llm_provider.generate_questions(
                prompt, CLARIFICATION_SYSTEM_INSTRUCTION
            )

            if not analysis:
                # Analysis failed, do light refinement
                logger.warning("Question generation failed, doing light refinement")
                refined = llm_provider.light_refine(
                    prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                )
                return _build_refined_response(refined)

            task_type = analysis.get("task_type", "analysis")
            questions = analysis.get("questions", [])

            logger.info(f"Task type: {task_type}, questions: {len(questions)}")

            # If questions generated, attempt to ask them
            if questions:
                mapping = _build_question_mapping(questions)

                # Try interactive mode first
                interactive_answers = _try_interactive_questions(questions)

                if interactive_answers:
                    # Got answers interactively, refine immediately
                    logger.info("Interactive answers received, refining")
                    refined = llm_provider.refine_from_answers(
                        prompt,
                        interactive_answers,
                        mapping,
                        GENERATION_SYSTEM_INSTRUCTION,
                    )
                    return _build_refined_response(refined)

                # Interactive mode unavailable or failed, return structured response
                logger.info("Returning structured clarification response")
                return _format_clarification_response(questions, task_type, mapping)

            # No questions needed, do light refinement
            logger.info("No questions needed, doing light refinement")
            refined = llm_provider.light_refine(
                prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
            )
            return _build_refined_response(refined)

        except Exception as e:
            logger.exception("Error during prompt refinement")
            return {
                "type": "error",
                "error_type": type(e).__name__,
                "message": sanitize_error_message(str(e)),
            }


def run_mcp_server():
    """Entry point for the MCP server."""
    _ensure_mcp_available()
    logger.info("Starting Promptheus MCP server")

    if mcp:
        mcp.run()
    else:
        print("Error: FastMCP not initialized.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_mcp_server()
