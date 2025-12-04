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
import time
import uuid
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
from promptheus.telemetry import (
    record_prompt_run_event,
    record_clarifying_questions_summary,
    record_provider_error,
)
from promptheus.prompts import (
    CLARIFICATION_SYSTEM_INSTRUCTION,
    GENERATION_SYSTEM_INSTRUCTION,
    ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
    TWEAK_SYSTEM_INSTRUCTION,
)

logger = logging.getLogger("promptheus.mcp")

# Session ID for telemetry - generated once per MCP process
SESSION_ID = str(uuid.uuid4())

# Initialize FastMCP
if FastMCP:
    mcp = FastMCP("Promptheus")
else:
    mcp = None

# Type aliases for clarity
QuestionMapping = Dict[str, str]  # Maps question IDs to question text
RefinedResponse = Dict[str, Any]
ClarificationResponse = Dict[str, Any]
ErrorResponse = Dict[str, Any]
RefineResult = Union[RefinedResponse, ClarificationResponse, ErrorResponse]
AskUserFn = Optional[
    # questions: list of question dicts; returns mapping from question id to answer
    # or a richer result dict that contains an "answers" mapping.
    Any
]

# AskUserQuestion injection point.
# MCP clients can inject this function to enable interactive questioning.
# Default: None (falls back to structured JSON responses).
# Integration summary:
# - Call set_ask_user_question(fn) once after loading the MCP server.
# - fn will be called as fn(questions: List[Dict[str, Any]]) where each dict includes:
#     {"id": "q0", "question": "...", "header": "Q1", "multiSelect": bool,
#      "required": bool, "options": [{"label": "...", "description": "..."}]}
# - fn must return either:
#     {"q0": "answer", "q1": ["a", "b"]} or {"answers": {...}}.
# - Missing or empty answers for required questions cause a fallback to
#   the structured clarification_needed response.
_ask_user_question_fn: AskUserFn = None


def set_ask_user_question(fn: Optional[Any]) -> None:
    """
    Inject an AskUserQuestion implementation for interactive mode.

    Contract:
    - The injected callable must accept a single argument:
        questions: List[Dict[str, Any]]
      Each question dict will have at least:
        {
            "id": "q0",                      # Stable question identifier
            "question": "<full question>",   # Human readable text
            "header": "Q1",                  # Short label
            "multiSelect": bool,             # True when checkbox-style
            "options": [                     # Optional
                {"label": "<option>", "description": "<option>"}
            ],
            "required": bool                 # Present for clarity
        }

    - The callable must return one of:
        1) A mapping of question ids to answers, for example:
           {"q0": "Answer text", "q1": ["opt-a", "opt-b"]}
        2) A dict with an "answers" key whose value is such a mapping.

      Answers may be strings or lists of strings. Optional questions may be
      omitted from the mapping. For required questions, missing or empty
      answers are treated as failure and cause a fallback to the structured
      clarification_needed response.

    Any exception or invalid return value from the callable is treated as a
    failure and will cause refine_prompt to return a clarification_needed
    payload instead of attempting interactive refinement.
    """
    global _ask_user_question_fn
    _ask_user_question_fn = fn
    if fn is not None:
        logger.info("AskUserQuestion function registered for interactive mode")
    else:
        logger.info("AskUserQuestion function cleared; interactive mode disabled")

# Configuration
MAX_PROMPT_LENGTH = 50000  # characters


def _ensure_mcp_available():
    """Verify MCP package is installed."""
    if mcp is None:
        raise ImportError(
            "The 'mcp' package is not installed. "
            "Please install it with 'pip install mcp'."
        )


NEXT_ACTION_HINT = (
    "This refined prompt is now ready to use. "
    "If the user asked you to execute/run the prompt, use this refined prompt directly with your own capabilities to generate the requested content. "
    "IMPORTANT: Do NOT call Promptheus again to execute - Promptheus only refines prompts, it does not generate content. "
    "Use this refined prompt to create the actual output with your native LLM capabilities. "
    "If the user only asked for refinement, present the refined prompt to them for review. "
    'For CLI usage: promptheus --skip-questions "<refined prompt here>"'
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

    Contract with injected AskUserQuestion:
        - Input: a list of question dicts, each with at least the keys
          "id", "question", "header", "multiSelect", and optional "options"
          and "required". This matches the format described in
          set_ask_user_question.
        - Output: either
            * A dict mapping question ids to answers, or
            * A dict with an "answers" key whose value is that mapping.

      Answers may be strings or lists. Missing answers for required questions
      or completely empty mappings are treated as a failure.

    Returns:
        Dict of answers keyed by question id if successful, or None if
        AskUserQuestion is unavailable or fails validation.
    """
    if _ask_user_question_fn is None:
        logger.debug("AskUserQuestion not available, using fallback")
        return None

    try:
        logger.info("Using interactive AskUserQuestion mode")
        answers: Dict[str, str] = {}

        for i, q in enumerate(questions):
            q_id = f"q{i}"
            q_text = q.get("question", f"Question {i}")
            q_type = q.get("type", "text")
            options = q.get("options", [])
            required = bool(q.get("required", True))

            # Format question for AskUserQuestion.
            question_data = {
                "id": q_id,
                "question": q_text,
                "header": f"Q{i+1}",
                "multiSelect": q_type == "checkbox",
                "required": required,
            }

            if q_type in ("radio", "checkbox") and options:
                question_data["options"] = [
                    {"label": opt, "description": opt} for opt in options
                ]

            # Call injected AskUserQuestion function for this single question.
            result = _ask_user_question_fn([question_data])

            # Normalize into a flat mapping.
            answer_value: Any = None
            if isinstance(result, dict):
                result_mapping = result.get("answers", result)
                if isinstance(result_mapping, dict):
                    answer_value = (
                        result_mapping.get(q_id)
                        or result_mapping.get(q_text)
                        or result_mapping.get(question_data["header"])
                    )
            elif isinstance(result, list) and result:
                # For list responses, use first element or the first list.
                if isinstance(result[0], list):
                    answer_value = result[0]
                else:
                    answer_value = result[0]

            if answer_value is None or (
                isinstance(answer_value, str) and not answer_value.strip()
            ):
                if not required:
                    logger.debug(f"Skipping optional question {q_id}")
                    continue
                logger.warning(f"No valid answer for required question {q_id}")
                return None

            # Normalize lists for multiselect; everything stored as comma-separated text.
            if isinstance(answer_value, list):
                if not answer_value and required:
                    logger.warning(f"No valid answer for required question {q_id}")
                    return None
                answers[q_id] = ", ".join(str(a) for a in answer_value)
            else:
                answers[q_id] = str(answer_value)

        if not answers:
            logger.warning("AskUserQuestion returned no usable answers")
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
        q_id = f"q{i}"
        q_data = {
            "id": q_id,
            "question": q.get("question", f"Question {i}"),
            "header": f"Q{i+1}",
            "multiSelect": q.get("type") == "checkbox",
            "required": q.get("required", True),
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
            "   - answers: {q0: <answer0>, q1: <answer1>, ...}\n"
            "   - answer_mapping: the 'answer_mapping' object from this response"
        ),
    }


if mcp:
    @mcp.tool()
    def refine_prompt(
        prompt: str,
        answers: Optional[Dict[str, str]] = None,
        answer_mapping: Optional[Dict[str, str]] = None,
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
        3. If response type is "refined":
           - If user asked to "execute" or "run" the prompt, use the refined prompt with your native capabilities to generate content
           - Otherwise, present the refined prompt to the user for review
           - Note: Promptheus only refines prompts, it does not execute them

        Args:
            prompt: The initial prompt to refine.
            answers: Optional dictionary mapping question IDs to answers.
            answer_mapping: Optional dictionary mapping question IDs to original
                question text. Recommended when providing answers.
            provider: Override provider (e.g. 'google').
            model: Override model name.

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
        # Generate run_id for this specific tool invocation
        run_id = str(uuid.uuid4())
        
        # Track timing metrics
        start_time = time.time()
        llm_start_time = None
        llm_end_time = None
        clarifying_questions_count = 0
        success = False
        
        logger.info(
            f"refine_prompt called: prompt_len={len(prompt)}, "
            f"has_answers={bool(answers)}, provider={provider}, model={model}"
        )

        # Validate input
        validation_error = _validate_prompt(prompt)
        if validation_error:
            # Record failure telemetry
            end_time = time.time()
            total_run_latency_sec = end_time - start_time
            
            record_prompt_run_event(
                source="mcp",
                provider=provider or "unknown",
                model=model or "unknown",
                task_type="unknown",
                processing_latency_sec=total_run_latency_sec,
                clarifying_questions_count=0,
                skip_questions=False,
                refine_mode=True,
                success=False,
                session_id=SESSION_ID,
                run_id=run_id,
                input_chars=len(prompt),
                output_chars=len(prompt),  # No refinement, return original
                llm_latency_sec=None,
                total_run_latency_sec=total_run_latency_sec,
                quiet_mode=False,  # MCP doesn't have quiet mode
                history_enabled=None,  # Will be set when we have config
                python_version=sys.version.split()[0],
                platform=sys.platform,
                interface="mcp",
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
            return validation_error

        # Initialize provider
        llm_provider, provider_error = _initialize_provider(provider, model)
        if provider_error:
            # Record provider error telemetry
            end_time = time.time()
            total_run_latency_sec = end_time - start_time
            
            record_provider_error(
                provider=provider or "unknown",
                model=model or "unknown",
                session_id=SESSION_ID,
                run_id=run_id,
                error_message=provider_error.get("message", "Unknown provider error"),
            )
            
            record_prompt_run_event(
                source="mcp",
                provider=provider or "unknown",
                model=model or "unknown",
                task_type="unknown",
                processing_latency_sec=total_run_latency_sec,
                clarifying_questions_count=0,
                skip_questions=False,
                refine_mode=True,
                success=False,
                session_id=SESSION_ID,
                run_id=run_id,
                input_chars=len(prompt),
                output_chars=len(prompt),
                llm_latency_sec=None,
                total_run_latency_sec=total_run_latency_sec,
                quiet_mode=False,
                history_enabled=None,
                python_version=sys.version.split()[0],
                platform=sys.platform,
                interface="mcp",
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
            return provider_error

        try:
            # Get config for history_enabled setting
            config = Config()
            history_enabled = config.history_enabled
            
            # Case 1: Answers provided -> Generate final refined prompt
            if answers:
                logger.info(f"Refining with {len(answers)} answers")
                clarifying_questions_count = 0  # No new questions asked
                llm_start_time = time.time()

                # Prefer caller-provided mapping so the provider can see the original
                # question text; fall back to generic labels for backward compatibility.
                if answer_mapping:
                    mapping = answer_mapping
                else:
                    mapping = {key: f"Question: {key}" for key in answers.keys()}

                refined = llm_provider.refine_from_answers(
                    prompt, answers, mapping, GENERATION_SYSTEM_INSTRUCTION
                )
                llm_end_time = time.time()
                
                # Calculate timing metrics
                end_time = time.time()
                total_run_latency_sec = end_time - start_time
                llm_latency_sec = llm_end_time - llm_start_time
                
                input_tokens = getattr(llm_provider, "last_input_tokens", None)
                output_tokens = getattr(llm_provider, "last_output_tokens", None)
                total_tokens = getattr(llm_provider, "last_total_tokens", None)

                # Record successful telemetry
                record_prompt_run_event(
                    source="mcp",
                    provider=llm_provider.name if hasattr(llm_provider, 'name') else (provider or "unknown"),
                    model=model or config.get_model(),
                    task_type="generation",  # When answers are provided, it's generation
                    processing_latency_sec=total_run_latency_sec,
                    clarifying_questions_count=clarifying_questions_count,
                    skip_questions=True,  # We already have answers
                    refine_mode=True,
                    success=True,
                    session_id=SESSION_ID,
                    run_id=run_id,
                    input_chars=len(prompt),
                    output_chars=len(refined),
                    llm_latency_sec=llm_latency_sec,
                    total_run_latency_sec=total_run_latency_sec,
                    quiet_mode=False,
                    history_enabled=history_enabled,
                    python_version=sys.version.split()[0],
                    platform=sys.platform,
                    interface="mcp",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                )

                return _build_refined_response(refined)

            # Case 2: No answers -> Determine if questions are needed
            logger.info("Analyzing prompt for clarification needs")
            llm_start_time = time.time()
            analysis = llm_provider.generate_questions(
                prompt, CLARIFICATION_SYSTEM_INSTRUCTION
            )
            llm_end_time = time.time()
            questions_llm_latency_sec = llm_end_time - llm_start_time

            if not analysis:
                # Analysis failed, do light refinement
                logger.warning("Question generation failed, doing light refinement")
                llm_start_time = time.time()
                refined = llm_provider.light_refine(
                    prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                )
                llm_end_time = time.time()
                
                # Calculate timing metrics
                end_time = time.time()
                total_run_latency_sec = end_time - start_time
                refine_llm_latency_sec = llm_end_time - llm_start_time
                llm_latency_sec = questions_llm_latency_sec + refine_llm_latency_sec

                input_tokens = getattr(llm_provider, "last_input_tokens", None)
                output_tokens = getattr(llm_provider, "last_output_tokens", None)
                total_tokens = getattr(llm_provider, "last_total_tokens", None)
                
                # Record successful telemetry
                record_prompt_run_event(
                    source="mcp",
                    provider=llm_provider.name if hasattr(llm_provider, 'name') else (provider or "unknown"),
                    model=model or config.get_model(),
                    task_type="analysis",
                    processing_latency_sec=total_run_latency_sec,
                    clarifying_questions_count=0,
                    skip_questions=False,
                    refine_mode=False,  # Light refinement
                    success=True,
                    session_id=SESSION_ID,
                    run_id=run_id,
                    input_chars=len(prompt),
                    output_chars=len(refined),
                    llm_latency_sec=llm_latency_sec,
                    total_run_latency_sec=total_run_latency_sec,
                    quiet_mode=False,
                    history_enabled=history_enabled,
                    python_version=sys.version.split()[0],
                    platform=sys.platform,
                    interface="mcp",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                )
                
                return _build_refined_response(refined)

            task_type = analysis.get("task_type", "analysis")
            questions = analysis.get("questions", [])
            clarifying_questions_count = len(questions)

            logger.info(f"Task type: {task_type}, questions: {len(questions)}")

            # If questions generated, attempt to ask them
            if questions:
                mapping = _build_question_mapping(questions)

                # Try interactive mode first
                interactive_answers = _try_interactive_questions(questions)

                if interactive_answers:
                    # Got answers interactively, refine immediately
                    logger.info("Interactive answers received, refining")
                    llm_start_time = time.time()
                    refined = llm_provider.refine_from_answers(
                        prompt,
                        interactive_answers,
                        mapping,
                        GENERATION_SYSTEM_INSTRUCTION,
                    )
                    llm_end_time = time.time()
                    
                    # Calculate timing metrics
                    end_time = time.time()
                    total_run_latency_sec = end_time - start_time
                    refine_llm_latency_sec = llm_end_time - llm_start_time
                    llm_latency_sec = questions_llm_latency_sec + refine_llm_latency_sec

                    input_tokens = getattr(llm_provider, "last_input_tokens", None)
                    output_tokens = getattr(llm_provider, "last_output_tokens", None)
                    total_tokens = getattr(llm_provider, "last_total_tokens", None)
                    
                    # Record successful telemetry
                    record_prompt_run_event(
                        source="mcp",
                        provider=llm_provider.name if hasattr(llm_provider, 'name') else (provider or "unknown"),
                        model=model or config.get_model(),
                        task_type=task_type,
                        processing_latency_sec=total_run_latency_sec,
                        clarifying_questions_count=clarifying_questions_count,
                        skip_questions=False,
                        refine_mode=True,
                        success=True,
                        session_id=SESSION_ID,
                        run_id=run_id,
                        input_chars=len(prompt),
                        output_chars=len(refined),
                        llm_latency_sec=llm_latency_sec,
                        total_run_latency_sec=total_run_latency_sec,
                        quiet_mode=False,
                        history_enabled=history_enabled,
                        python_version=sys.version.split()[0],
                        platform=sys.platform,
                        interface="mcp",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                    )
                    
                    # Record clarifying questions summary
                    record_clarifying_questions_summary(
                        session_id=SESSION_ID,
                        run_id=run_id,
                        total_questions=clarifying_questions_count,
                        history_enabled=history_enabled,
                    )
                    
                    return _build_refined_response(refined)

                # Interactive mode unavailable or failed, return structured response
                logger.info("Returning structured clarification response")
                return _format_clarification_response(questions, task_type, mapping)

            # No questions needed, do light refinement
            logger.info("No questions needed, doing light refinement")
            llm_start_time = time.time()
            refined = llm_provider.light_refine(
                prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
            )
            llm_end_time = time.time()
            
            # Calculate timing metrics
            end_time = time.time()
            total_run_latency_sec = end_time - start_time
            llm_latency_sec = llm_end_time - llm_start_time

            input_tokens = getattr(llm_provider, "last_input_tokens", None)
            output_tokens = getattr(llm_provider, "last_output_tokens", None)
            total_tokens = getattr(llm_provider, "last_total_tokens", None)
            
            # Record successful telemetry
            record_prompt_run_event(
                source="mcp",
                provider=llm_provider.name if hasattr(llm_provider, 'name') else (provider or "unknown"),
                model=model or config.get_model(),
                task_type=task_type,
                processing_latency_sec=total_run_latency_sec,
                clarifying_questions_count=0,
                skip_questions=False,
                refine_mode=False,  # Light refinement
                success=True,
                session_id=SESSION_ID,
                run_id=run_id,
                input_chars=len(prompt),
                output_chars=len(refined),
                llm_latency_sec=llm_latency_sec,
                total_run_latency_sec=total_run_latency_sec,
                quiet_mode=False,
                history_enabled=history_enabled,
                python_version=sys.version.split()[0],
                platform=sys.platform,
                interface="mcp",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )
            
            return _build_refined_response(refined)

        except Exception as e:
            logger.exception("Error during prompt refinement")
            
            # Get config for history_enabled setting
            config = Config()
            history_enabled = config.history_enabled
            
            # Record provider error telemetry
            end_time = time.time()
            total_run_latency_sec = end_time - start_time
            
            record_provider_error(
                provider=provider or "unknown",
                model=model or config.get_model(),
                session_id=SESSION_ID,
                run_id=run_id,
                error_message=str(e),
            )
            
            # Record failed prompt run telemetry
            record_prompt_run_event(
                source="mcp",
                provider=provider or "unknown",
                model=model or config.get_model(),
                task_type="unknown",
                processing_latency_sec=total_run_latency_sec,
                clarifying_questions_count=clarifying_questions_count,
                skip_questions=False,
                refine_mode=True,
                success=False,
                session_id=SESSION_ID,
                run_id=run_id,
                input_chars=len(prompt),
                output_chars=len(prompt),  # No refinement, return original
                llm_latency_sec=None,
                total_run_latency_sec=total_run_latency_sec,
                quiet_mode=False,
                history_enabled=history_enabled,
                python_version=sys.version.split()[0],
                platform=sys.platform,
                interface="mcp",
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
            )
            
            return {
                "type": "error",
                "error_type": type(e).__name__,
                "message": sanitize_error_message(str(e)),
            }


    @mcp.tool()
    def tweak_prompt(
        prompt: str,
        modification: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> RefineResult:
        """
        Make a specific modification to an existing prompt.

        This tool applies surgical edits to prompts without changing their core intent.
        Use this when you have a refined prompt and want to make targeted adjustments.

        Args:
            prompt: The current prompt to modify.
            modification: Description of what to change (e.g. "make it shorter").
            provider: Override provider.
            model: Override model name.

        Returns:
            {"type": "refined", "prompt": "..."} - Modified prompt
            {"type": "error", ...} - If modification fails

        Examples:
            tweak_prompt(
                prompt="Write a technical blog post about Docker",
                modification="make it more beginner-friendly"
            )
        """
        logger.info(f"tweak_prompt called: modification='{modification[:50]}...'")

        # Validate inputs
        validation_error = _validate_prompt(prompt)
        if validation_error:
            return validation_error

        if not modification or not modification.strip():
            return {
                "type": "error",
                "error_type": "ValidationError",
                "message": "Modification description cannot be empty",
            }

        # Initialize provider
        llm_provider, provider_error = _initialize_provider(provider, model)
        if provider_error:
            return provider_error

        try:
            tweaked = llm_provider.tweak_prompt(
                prompt, modification, TWEAK_SYSTEM_INSTRUCTION
            )

            return {
                "type": "refined",
                "prompt": tweaked,
            }

        except Exception as e:
            logger.exception("Error during prompt tweaking")
            return {
                "type": "error",
                "error_type": type(e).__name__,
                "message": sanitize_error_message(str(e)),
            }

    @mcp.tool()
    def list_models(
        providers: Optional[List[str]] = None,
        limit: int = 20,
        include_nontext: bool = False,
    ) -> Dict[str, Any]:
        """
        List available models from configured AI providers.

        Shows which models are available for each provider you have API keys for.
        Useful for discovering new models or checking model availability.

        Args:
            providers: List of provider names to query (e.g. ["google"]).
                Queries all if not specified.
            limit: Max models per provider (default: 20).
            include_nontext: Include non-text models (default: False).

        Returns:
            {
                "type": "success",
                "providers": {
                    "google": {
                        "available": true,
                        "models": [{"id": "...", "name": "..."}],
                        "total_count": 15,
                        "showing": 10
                    },
                    ...
                }
            }

        Examples:
            list_models()  # All providers, text models only
            list_models(providers=["google", "openai"], limit=10)
            list_models(include_nontext=True)  # Include vision/embedding models
        """
        logger.info(
            f"list_models called: providers={providers}, limit={limit}, "
            f"include_nontext={include_nontext}"
        )

        try:
            from promptheus.commands.providers import get_models_data

            config = Config()
            provider_list = providers if providers else None

            models_data = get_models_data(
                config, provider_list, include_nontext=include_nontext, limit=limit
            )

            return {
                "type": "success",
                "providers": models_data,
            }

        except Exception as e:
            logger.exception("Error listing models")
            return {
                "type": "error",
                "error_type": type(e).__name__,
                "message": sanitize_error_message(str(e)),
            }

    @mcp.tool()
    def list_providers() -> Dict[str, Any]:
        """
        List all configured AI providers and their status.

        Shows which providers have valid API keys configured and are ready to use.
        Use this to check your environment setup before calling other tools.

        Returns:
            {
                "type": "success",
                "providers": {
                    "google": {"configured": true, "model": "gemini-2.0-flash-exp"},
                    "openai": {"configured": false, "error": "No API key found"},
                    ...
                }
            }

        Example:
            list_providers()  # Check which providers are ready
        """
        logger.info("list_providers called")

        try:
            config = Config()
            provider_status: Dict[str, Any] = {}

            from promptheus.config import SUPPORTED_PROVIDER_IDS

            for provider_id in SUPPORTED_PROVIDER_IDS:
                # Try to get provider instance; handle per-provider failures so one
                # misconfigured provider does not break the entire response.
                try:
                    config.set_provider(provider_id)

                    if config.validate():
                        get_provider(provider_id, config, config.get_model())
                        provider_status[provider_id] = {
                            "configured": True,
                            "model": config.get_model(),
                        }
                    else:
                        errors = config.consume_error_messages()
                        provider_status[provider_id] = {
                            "configured": False,
                            "error": errors[0] if errors else "Configuration invalid",
                        }
                except Exception as e:
                    provider_status[provider_id] = {
                        "configured": False,
                        "error": sanitize_error_message(str(e)),
                    }

            return {
                "type": "success",
                "providers": provider_status,
            }

        except Exception as e:
            logger.exception("Error listing providers")
            return {
                "type": "error",
                "error_type": type(e).__name__,
                "message": sanitize_error_message(str(e)),
            }

    @mcp.tool()
    def validate_environment(
        providers: Optional[List[str]] = None,
        test_connection: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate environment configuration and optionally test API connections.

        Checks that API keys are configured correctly and can connect to provider APIs.
        Use this for troubleshooting configuration issues.

        Args:
            providers: List of provider names to validate.
                Validates all if not specified.
            test_connection: Whether to test API connectivity (default: False).

        Returns:
            {
                "type": "success",
                "validation": {
                    "google": {
                        "configured": true,
                        "connection_test": "passed" (if test_connection=True)
                    },
                    ...
                }
            }

        Examples:
            validate_environment()  # Quick config check
            validate_environment(test_connection=True)  # Full API test
            validate_environment(providers=["openai"], test_connection=True)
        """
        logger.info(
            f"validate_environment called: providers={providers}, "
            f"test_connection={test_connection}"
        )

        try:
            from promptheus.commands.providers import get_validation_data

            config = Config()
            provider_list = providers if providers else None

            validation_data = get_validation_data(
                config, provider_list, test_connection
            )

            return {
                "type": "success",
                "validation": validation_data,
            }

        except Exception as e:
            logger.exception("Error validating environment")
            return {
                "type": "error",
                "error_type": type(e).__name__,
                "message": sanitize_error_message(str(e)),
            }


def run_mcp_server():
    """Entry point for the MCP server."""
    # Configure basic logging only when running the MCP server directly to avoid
    # overriding application-wide logging when imported as a module.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    _ensure_mcp_available()
    logger.info("Starting Promptheus MCP server")

    if mcp:
        mcp.run()
    else:
        print("Error: FastMCP not initialized.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        run_mcp_server()
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
