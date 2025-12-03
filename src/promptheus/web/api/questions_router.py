"""Questions API router for Promptheus Web UI."""
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from promptheus.config import Config
from promptheus.providers import get_provider
from promptheus.utils import get_user_email, get_device_category

router = APIRouter()
logger = logging.getLogger(__name__)

class QuestionsRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None


class QuestionsResponse(BaseModel):
    success: bool
    task_type: str
    questions: list
    error: Optional[str] = None


@router.post("/questions/generate", response_model=QuestionsResponse)
async def generate_questions(questions_request: QuestionsRequest, request: Request):
    """Generate clarifying questions for a prompt."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Create configuration
        app_config = Config()
        logger.debug(f"[generate_questions] Initial provider from config: {app_config.provider}")
        logger.debug(f"[generate_questions] Request provider: {questions_request.provider}")
        logger.debug(f"[generate_questions] Request model: {questions_request.model}")

        if questions_request.provider:
            app_config.set_provider(questions_request.provider)
            logger.debug(f"[generate_questions] Set provider from request: {questions_request.provider}")
        if questions_request.model:
            app_config.set_model(questions_request.model)
            logger.debug(f"[generate_questions] Set model from request: {questions_request.model}")

        # Create provider instance - use detected provider, no hardcoded fallback
        provider_name = app_config.provider
        if not provider_name:
            logger.error("[generate_questions] No provider detected! Check environment variables.")
            raise HTTPException(status_code=500, detail="No provider configured")

        logger.info(f"[generate_questions] Using provider: {provider_name}, model: {app_config.get_model()}")
        provider = get_provider(provider_name, app_config, app_config.get_model())

        # Import the system instruction from main module
        from promptheus.prompts import CLARIFICATION_SYSTEM_INSTRUCTION

        # Generate questions using the provider
        result = provider.generate_questions(questions_request.prompt, CLARIFICATION_SYSTEM_INSTRUCTION)

        if result is None:
            # Log failed user action
            logger.warning(
                "User questions generation failed - no result",
                extra={
                    "user": get_user_email(request),
                    "action": "questions_generate",
                    "provider": provider_name,
                    "prompt_length": len(questions_request.prompt),
                    "success": False,
                }
            )
            return QuestionsResponse(
                success=False,
                task_type="",
                questions=[],
                error="Failed to generate questions"
            )

        task_type = result.get("task_type", "generation")
        questions = result.get("questions", [])

        # Log successful user action
        logger.info(
            "User generated questions",
            extra={
                "user": get_user_email(request),
                "action": "questions_generate",
                "provider": provider_name,
                "model": app_config.get_model(),
                "task_type": task_type,
                "prompt_length": len(questions_request.prompt),
                "questions_count": len(questions),
                "device_category": get_device_category(request),
                "success": True,
            }
        )

        return QuestionsResponse(
            success=True,
            task_type=task_type,
            questions=questions,
        )
    except Exception as e:
        # Log failed user action
        logger.error(
            "User questions generation failed",
            extra={
                "user": get_user_email(request),
                "action": "questions_generate",
                "prompt_length": len(questions_request.prompt),
                "success": False,
            },
            exc_info=True
        )
        return QuestionsResponse(
            success=False,
            task_type="",
            questions=[],
            error=str(e)
        )
