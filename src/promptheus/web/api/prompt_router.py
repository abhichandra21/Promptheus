"""Prompt API router for Promptheus Web UI."""
import asyncio
import json
from typing import Dict, Any, Optional, Tuple

from fastapi import APIRouter, HTTPException
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

LOAD_ALL_MODELS_SENTINEL = "__load_all__"


router = APIRouter()


async def process_prompt_web(
    provider: LLMProvider,
    initial_prompt: str,
    answers: Optional[Dict[str, Any]], 
    mapping: Optional[Dict[str, str]],  # Maps question keys to question text
    skip_questions: bool,
    refine: bool,
    app_config: Config
) -> Tuple[str, str]:  # Returns (final_prompt, task_type)
    """
    Web-compatible prompt processing function that replicates the main logic
    but without CLI-specific features like terminal I/O.
    """
    from promptheus.utils import sanitize_error_message
    
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
                        initial_prompt, answers, mapping, GENERATION_SYSTEM_INSTRUCTION
                    )
                    return final_prompt, task_type
                elif not questions_json:
                    # No questions needed, apply light refinement
                    final_prompt = provider.light_refine(
                        initial_prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                    )
                    return final_prompt, task_type
                elif task_type == "analysis":
                    # Analysis task, apply light refinement
                    final_prompt = provider.light_refine(
                        initial_prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                    )
                    return final_prompt, task_type
                else:
                    # Task type is generation but no answers provided, return task info
                    raise HTTPException(status_code=400, detail="Answers required for clarifying questions")
            else:
                # Fallback to light refinement if no result from API
                final_prompt = provider.light_refine(
                    initial_prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                )
                return final_prompt, "analysis"
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            raise HTTPException(status_code=500, detail=f"Failed to generate questions: {sanitized}")
    else:
        # Skip questions mode - apply light refinement
        final_prompt = provider.light_refine(
            initial_prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
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
async def submit_prompt(request: PromptRequest):
    """Submit a prompt for processing."""
    try:
        # Create configuration
        app_config = Config()
        if request.provider:
            app_config.set_provider(request.provider)
        if request.model and request.model != LOAD_ALL_MODELS_SENTINEL:
            app_config.set_model(request.model)
        
        # Create provider instance
        provider_name = app_config.provider or "gemini"
        provider = get_provider(provider_name, app_config, app_config.get_model())
        
        # Create an argument-like object to pass to the processing function
        class Args:
            def __init__(self):
                self.skip_questions = request.skip_questions
                self.refine = request.refine
                self.copy = request.copy_to_clipboard
                self.output_format = request.output_format
                # Add other attributes that might be accessed
                self.file = None
                self.provider = request.provider
                self.model = None
                self.version = False
                self.verbose = False
        
        args = Args()
        
        # Create IO context for web (quiet mode to avoid terminal output)
        io = IOContext.create()
        io.quiet_output = True  # Don't output to terminal in web mode
        
        # Create a simple mapping from answers keys to question text (in real usage, this would come from the questions generation)
        # For now, if we have answers, we'll just use the keys as is
        mapping = request.question_mapping or {}
        if not mapping and request.answers:
            mapping = {key: key for key in request.answers.keys()}

        # Process the prompt using the web-compatible function
        final_prompt, task_type = await process_prompt_web(
            provider=provider,
            initial_prompt=request.prompt,
            answers=request.answers,
            mapping=mapping,
            skip_questions=request.skip_questions,
            refine=request.refine,
            app_config=app_config
        )
        
        # Save to history
        history = get_history(app_config)
        history.save_entry(
            original_prompt=request.prompt,
            refined_prompt=final_prompt,
            task_type=task_type,
            provider=provider_name,
            model=app_config.get_model()
        )

        return PromptResponse(
            success=True,
            original_prompt=request.prompt,
            refined_prompt=final_prompt,
            task_type=task_type,
            provider=provider_name,
            model=app_config.get_model(),
            questions=[],  # Don't return questions after processing
            follow_up_questions=[],
        )
    except Exception as e:
        return PromptResponse(
            success=False,
            original_prompt=request.prompt,
            refined_prompt="",
            task_type="",
            provider=request.provider or "gemini",
            model="",
            questions=[],
            follow_up_questions=[],
            error=str(e)
        )


@router.post("/prompt/tweak")
async def tweak_prompt(request: TweakRequest):
    """Tweak/refine an existing prompt based on user instructions."""
    try:
        # Create configuration
        app_config = Config()
        if request.provider:
            app_config.set_provider(request.provider)

        # Create provider instance
        provider_name = app_config.provider or "gemini"
        provider = get_provider(provider_name, app_config, app_config.get_model())

        # Tweak the prompt
        tweaked_prompt = provider.tweak_prompt(
            request.current_prompt,
            request.tweak_instruction,
            TWEAK_SYSTEM_INSTRUCTION
        )

        return {
            "success": True,
            "original_prompt": request.current_prompt,
            "tweaked_prompt": tweaked_prompt,
            "tweak_instruction": request.tweak_instruction
        }
    except Exception as e:
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
    model: Optional[str] = None
):
    """Stream prompt refinement using Server-Sent Events (SSE)."""
    async def event_generator():
        try:
            # Create configuration
            app_config = Config()
            if provider:
                app_config.set_provider(provider)
            if model and model != LOAD_ALL_MODELS_SENTINEL:
                app_config.set_model(model)

            # Create provider instance
            provider_name = app_config.provider or "gemini"
            provider_instance = get_provider(provider_name, app_config, app_config.get_model())

            # Process the prompt (skip questions in streaming mode)
            final_prompt, task_type = await process_prompt_web(
                provider=provider_instance,
                initial_prompt=prompt,
                answers=None,
                mapping=None,
                skip_questions=skip_questions,
                refine=refine,
                app_config=app_config
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
            error_data = {
                "type": "error",
                "content": str(e)
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
