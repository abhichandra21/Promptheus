"""Promptheus - AI-powered prompt engineering CLI tool."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

__version__ = "0.3.1"

__all__ = ["__version__", "refine_prompt", "refine_prompt_async"]


async def refine_prompt_async(
    prompt: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    answers: Optional[Dict[str, Any]] = None,
    question_mapping: Optional[Dict[str, str]] = None,
    skip_questions: bool = False,
    refine: bool = False,
    style: str = "default",
) -> Dict[str, Any]:
    """
    Programmatic async API for prompt refinement.
    Returns dict with refined_prompt, task_type, provider, and model.
    """
    from promptheus.config import Config
    from promptheus.providers import get_provider
    from promptheus.web.api.prompt_router import LOAD_ALL_MODELS_SENTINEL, process_prompt_web

    cfg = Config()
    if provider:
        cfg.set_provider(provider)
    if model and model != LOAD_ALL_MODELS_SENTINEL:
        cfg.set_model(model)

    provider_name = cfg.provider
    if not provider_name:
        raise RuntimeError("No provider configured. Set API keys or pass provider/model explicitly.")

    provider_instance = get_provider(provider_name, cfg, cfg.get_model())

    mapping = question_mapping or {}
    if not mapping and answers:
        mapping = {key: key for key in answers.keys()}

    refined, task_type = await process_prompt_web(
        provider=provider_instance,
        initial_prompt=prompt,
        answers=answers,
        mapping=mapping,
        skip_questions=skip_questions,
        refine=refine,
        app_config=cfg,
        style=style,
    )

    return {
        "refined_prompt": refined,
        "task_type": task_type,
        "provider": provider_name,
        "model": cfg.get_model(),
    }


def refine_prompt(
    prompt: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    answers: Optional[Dict[str, Any]] = None,
    question_mapping: Optional[Dict[str, str]] = None,
    skip_questions: bool = False,
    refine: bool = False,
    style: str = "default",
) -> Dict[str, Any]:
    """
    Synchronous wrapper for refine_prompt_async.
    Raises if called from within a running event loop (use refine_prompt_async instead).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            refine_prompt_async(
                prompt,
                provider=provider,
                model=model,
                answers=answers,
                question_mapping=question_mapping,
                skip_questions=skip_questions,
                refine=refine,
                style=style,
            )
        )

    raise RuntimeError("refine_prompt cannot run inside an active event loop; use refine_prompt_async instead.")
