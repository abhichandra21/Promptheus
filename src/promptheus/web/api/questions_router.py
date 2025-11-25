"""Questions API router for Promptheus Web UI."""
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from promptheus.config import Config
from promptheus.providers import get_provider

router = APIRouter()

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
async def generate_questions(request: QuestionsRequest):
    """Generate clarifying questions for a prompt."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Create configuration
        app_config = Config()
        logger.debug(f"[generate_questions] Initial provider from config: {app_config.provider}")
        logger.debug(f"[generate_questions] Request provider: {request.provider}")
        logger.debug(f"[generate_questions] Request model: {request.model}")

        if request.provider:
            app_config.set_provider(request.provider)
            logger.debug(f"[generate_questions] Set provider from request: {request.provider}")
        if request.model:
            app_config.set_model(request.model)
            logger.debug(f"[generate_questions] Set model from request: {request.model}")

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
        result = provider.generate_questions(request.prompt, CLARIFICATION_SYSTEM_INSTRUCTION)
        
        if result is None:
            return QuestionsResponse(
                success=False,
                task_type="",
                questions=[],
                error="Failed to generate questions"
            )
        
        task_type = result.get("task_type", "generation")
        questions = result.get("questions", [])
        
        return QuestionsResponse(
            success=True,
            task_type=task_type,
            questions=questions,
        )
    except Exception as e:
        return QuestionsResponse(
            success=False,
            task_type="",
            questions=[],
            error=str(e)
        )
