"""Prompt API router for Promptheus Web UI."""
import asyncio
import json
from typing import Dict, Any, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from promptheus.config import Config
from promptheus.providers import get_provider, LLMProvider
from promptheus.io_context import IOContext
from promptheus.history import get_history
from promptheus.question_prompter import create_prompter
from promptheus.prompts import (
    ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
    CLARIFICATION_SYSTEM_INSTRUCTION,
    GENERATION_SYSTEM_INSTRUCTION,
    TWEAK_SYSTEM_INSTRUCTION,
)
from promptheus.utils import sanitize_error_message, get_user_email

LOAD_ALL_MODELS_SENTINEL = "__load_all__"


STYLE_INSTRUCTIONS = {
    "default": "",
    "bullets": "Format the final response as concise bullet points.",
    "steps": "Return a numbered, step-by-step plan.",
    "plain": "Use plain sentences without heavy formatting.",
    "concise": "Be brief and to the point while preserving key details.",
}


router = APIRouter()


async def process_prompt_web(
    provider: LLMProvider,
    initial_prompt: str,
    answers: Optional[Dict[str, Any]], 
    mapping: Optional[Dict[str, str]],  # Maps question keys to question text
    skip_questions: bool,
    refine: bool,
    app_config: Config,
    style: str = "default",
) -> Tuple[str, str]:  # Returns (final_prompt, task_type)
    """
    Web-compatible prompt processing function that replicates the main logic
    but without CLI-specific features like terminal I/O.
    """
    def _apply_style(system_instruction: str) -> str:
        suffix = STYLE_INSTRUCTIONS.get(style or "default", "")
        if not suffix:
            return system_instruction
        return f"{system_instruction}\n\nOutput formatting: {suffix}"

    def _is_rate_limit_error(message: str) -> bool:
        lowered = message.lower()
        return any(token in lowered for token in ["rate limit", "too many requests", "429"])

    # Import here to avoid circular imports
    should_ask_questions = (not skip_questions) or refine

    if should_ask_questions:
        # Generate questions first to determine task type
        try:
            result = provider.generate_questions(initial_prompt, CLARIFICATION_SYSTEM_INSTRUCTION)
            
            if result is not None:
                task_type = result.get("task_type", "generation")
                questions_json = result.get("questions", [])
                
                # If we have answers, use them for refinement
                if answers and mapping:
                    # Refine using the answers
                    final_prompt = provider.refine_from_answers(
                        initial_prompt, answers, mapping, _apply_style(GENERATION_SYSTEM_INSTRUCTION)
                    )
                    return final_prompt, task_type
                elif not questions_json:
                    # No questions needed, apply light refinement
                    final_prompt = provider.light_refine(
                        initial_prompt, _apply_style(ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION)
                    )
                    return final_prompt, task_type
                elif task_type == "analysis":
                    # Analysis task, apply light refinement
                    final_prompt = provider.light_refine(
                        initial_prompt, _apply_style(ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION)
                    )
                    return final_prompt, task_type
                else:
                    # Task type is generation but no answers provided, return task info
                    raise HTTPException(status_code=400, detail="Answers required for clarifying questions")
            else:
                # Fallback to light refinement if no result from API
                final_prompt = provider.light_refine(
                    initial_prompt, _apply_style(ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION)
                )
                return final_prompt, "analysis"
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            if _is_rate_limit_error(sanitized):
                raise HTTPException(status_code=429, detail=f"Rate limit encountered: {sanitized}")
            raise HTTPException(status_code=500, detail=f"Failed to generate questions: {sanitized}")
    else:
        # Skip questions mode - apply light refinement
        final_prompt = provider.light_refine(
            initial_prompt, _apply_style(ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION)
        )
        return final_prompt, "analysis"

class PromptRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None
    skip_questions: bool = False
    refine: bool = False
    copy_to_clipboard: bool = False
    output_format: str = "plain"
    answers: Optional[Dict[str, Any]] = None  # Answers to clarifying questions
    question_mapping: Optional[Dict[str, str]] = None
    style: str = "default"


class TweakRequest(BaseModel):
    current_prompt: str
    tweak_instruction: str
    provider: Optional[str] = None


class PromptResponse(BaseModel):
    success: bool
    original_prompt: str
    refined_prompt: str
    task_type: str
    provider: str
    model: str
    questions: Optional[list] = None  # Clarifying questions
    follow_up_questions: Optional[list] = None  # Follow-up questions after refinement
    error: Optional[str] = None


@router.post("/prompt/submit", response_model=PromptResponse)
async def submit_prompt(prompt_request: PromptRequest, request: Request):
    """Submit a prompt for processing."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Create configuration
        app_config = Config()
        logger.debug(f"[submit_prompt] Initial provider from config: {app_config.provider}")
        logger.debug(f"[submit_prompt] Request provider: {prompt_request.provider}")
        logger.debug(f"[submit_prompt] Request model: {prompt_request.model}")

        if prompt_request.provider:
            app_config.set_provider(prompt_request.provider)
            logger.debug(f"[submit_prompt] Set provider from request: {prompt_request.provider}")
        if prompt_request.model and prompt_request.model != LOAD_ALL_MODELS_SENTINEL:
            app_config.set_model(prompt_request.model)
            logger.debug(f"[submit_prompt] Set model from request: {prompt_request.model}")

        # Create provider instance - use detected provider, no hardcoded fallback
        provider_name = app_config.provider
        if not provider_name:
            logger.error("[submit_prompt] No provider detected! Check environment variables.")
            raise HTTPException(status_code=500, detail="No provider configured")

        logger.info(f"[submit_prompt] Using provider: {provider_name}, model: {app_config.get_model()}")
        provider = get_provider(provider_name, app_config, app_config.get_model())
        
        # Create an argument-like object to pass to the processing function
        class Args:
            def __init__(self):
                self.skip_questions = prompt_request.skip_questions
                self.refine = prompt_request.refine
                self.copy = prompt_request.copy_to_clipboard
                self.output_format = prompt_request.output_format
                # Add other attributes that might be accessed
                self.file = None
                self.provider = prompt_request.provider
                self.model = prompt_request.model
                self.version = False
                self.verbose = False

        args = Args()

        # Create IO context for web (quiet mode to avoid terminal output)
        io = IOContext.create()
        io.quiet_output = True  # Don't output to terminal in web mode

        # Create a simple mapping from answers keys to question text (in real usage, this would come from the questions generation)
        # For now, if we have answers, we'll just use the keys as is
        mapping = prompt_request.question_mapping or {}
        if not mapping and prompt_request.answers:
            mapping = {key: key for key in prompt_request.answers.keys()}

        # Process the prompt using the web-compatible function
        final_prompt, task_type = await process_prompt_web(
            provider=provider,
            initial_prompt=prompt_request.prompt,
            answers=prompt_request.answers,
            mapping=mapping,
            skip_questions=prompt_request.skip_questions,
            refine=prompt_request.refine,
            app_config=app_config,
            style=prompt_request.style,
        )

        # Save to history
        history = get_history(app_config)
        history.save_entry(
            original_prompt=prompt_request.prompt,
            refined_prompt=final_prompt,
            task_type=task_type,
            provider=provider_name,
            model=app_config.get_model()
        )

        # Log successful user action
        logger.info(
            "User submitted prompt",
            extra={
                "user": get_user_email(request),
                "action": "prompt_submit",
                "provider": provider_name,
                "model": app_config.get_model(),
                "task_type": task_type,
                "prompt_length": len(prompt_request.prompt),
                "skip_questions": prompt_request.skip_questions,
                "refine": prompt_request.refine,
                "success": True,
            }
        )

        return PromptResponse(
            success=True,
            original_prompt=prompt_request.prompt,
            refined_prompt=final_prompt,
            task_type=task_type,
            provider=provider_name,
            model=app_config.get_model(),
            questions=[],  # Don't return questions after processing
            follow_up_questions=[],
        )
    except Exception as e:
        logger.exception("[submit_prompt] Error processing prompt")
        # Try to get provider from config, fallback to request provider
        error_provider = "unknown"
        try:
            temp_config = Config()
            error_provider = temp_config.provider or prompt_request.provider or "unknown"
        except:
            error_provider = prompt_request.provider or "unknown"

        # Log failed user action
        logger.error(
            "User prompt submission failed",
            extra={
                "user": get_user_email(request),
                "action": "prompt_submit",
                "provider": error_provider,
                "prompt_length": len(prompt_request.prompt),
                "success": False,
            },
            exc_info=True
        )

        return PromptResponse(
            success=False,
            original_prompt=prompt_request.prompt,
            refined_prompt="",
            task_type="",
            provider=error_provider,
            model="",
            questions=[],
            follow_up_questions=[],
            error=str(e)
        )


@router.post("/prompt/tweak")
async def tweak_prompt(tweak_request: TweakRequest, request: Request):
    """Tweak/refine an existing prompt based on user instructions."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Create configuration
        app_config = Config()
        if tweak_request.provider:
            app_config.set_provider(tweak_request.provider)

        # Create provider instance - use detected provider, no hardcoded fallback
        provider_name = app_config.provider
        if not provider_name:
            logger.error("[tweak_prompt] No provider detected!")
            raise HTTPException(status_code=500, detail="No provider configured")

        logger.info(f"[tweak_prompt] Using provider: {provider_name}")
        provider = get_provider(provider_name, app_config, app_config.get_model())

        # Tweak the prompt
        tweaked_prompt = provider.tweak_prompt(
            tweak_request.current_prompt,
            tweak_request.tweak_instruction,
            TWEAK_SYSTEM_INSTRUCTION
        )

        # Log successful user action
        logger.info(
            "User tweaked prompt",
            extra={
                "user": get_user_email(request),
                "action": "prompt_tweak",
                "provider": provider_name,
                "model": app_config.get_model(),
                "tweak_instruction": tweak_request.tweak_instruction,
                "prompt_length": len(tweak_request.current_prompt),
                "success": True,
            }
        )

        return {
            "success": True,
            "original_prompt": tweak_request.current_prompt,
            "tweaked_prompt": tweaked_prompt,
            "tweak_instruction": tweak_request.tweak_instruction
        }
    except Exception as e:
        # Log failed user action
        logger.error(
            "User prompt tweak failed",
            extra={
                "user": get_user_email(request),
                "action": "prompt_tweak",
                "tweak_instruction": tweak_request.tweak_instruction,
                "prompt_length": len(tweak_request.current_prompt),
                "success": False,
            },
            exc_info=True
        )

        return {
            "success": False,
            "error": str(e)
        }


@router.get("/prompt/stream")
async def stream_prompt(
    prompt: str,
    skip_questions: bool = False,
    refine: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    style: str = "default"
):
    """Stream prompt refinement using Server-Sent Events (SSE)."""
    import logging
    logger = logging.getLogger(__name__)

    async def event_generator():
        try:
            # Create configuration
            app_config = Config()
            if provider:
                app_config.set_provider(provider)
            if model and model != LOAD_ALL_MODELS_SENTINEL:
                app_config.set_model(model)

            # Create provider instance - use detected provider, no hardcoded fallback
            provider_name = app_config.provider
            if not provider_name:
                logger.error("[stream_prompt] No provider detected!")
                error_data = {
                    "type": "error",
                    "content": "No provider configured"
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                return

            logger.info(f"[stream_prompt] Using provider: {provider_name}")
            provider_instance = get_provider(provider_name, app_config, app_config.get_model())

            # Process the prompt (skip questions in streaming mode)
            final_prompt, task_type = await process_prompt_web(
                provider=provider_instance,
                initial_prompt=prompt,
                answers=None,
                mapping=None,
                skip_questions=skip_questions,
                refine=refine,
                app_config=app_config,
                style=style,
            )

            # Save to history
            history = get_history(app_config)
            history.save_entry(
                original_prompt=prompt,
                refined_prompt=final_prompt,
                task_type=task_type,
                provider=provider_name,
                model=app_config.get_model()
            )

            # Stream the response character by character for effect
            for char in final_prompt:
                event_data = {
                    "type": "token",
                    "content": char
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(0.01)  # Small delay for visual effect

            # Send completion event
            completion_data = {
                "type": "done",
                "content": ""
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            sanitized = sanitize_error_message(str(e))
            msg = sanitized
            if "rate limit" in sanitized.lower() or "429" in sanitized.lower() or "too many requests" in sanitized.lower():
                msg = f"Rate limit detected. Retry after a pause or switch provider. Details: {sanitized}"
            error_data = {
                "type": "error",
                "content": msg
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
