"""
LLM Provider abstraction layer.
Supports multiple AI providers: Gemini, Anthropic.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from promptheus.constants import (
    DEFAULT_CLARIFICATION_MAX_TOKENS,
    DEFAULT_PROVIDER_TIMEOUT,
    DEFAULT_REFINEMENT_MAX_TOKENS,
    DEFAULT_TWEAK_MAX_TOKENS,
)
from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - typing support only
    from google.generativeai.types.generation_types import GenerationConfigType

    from promptheus.config import Config
else:
    GenerationConfigType = Any  # type: ignore[misc,assignment]


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_questions(self, initial_prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        """
        Generate clarifying questions based on initial prompt.
        Returns dict with 'task_type' and 'questions' keys.
        """

    @abstractmethod
    def _generate_text(
        self,
        prompt: str,
        system_instruction: str,
        *,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Execute a provider call and return the raw text output.

        Implementations may leverage model fallbacks, retries, or provider-specific
        configuration.  They should raise a RuntimeError with a sanitized message
        if all attempts fail.
        """

    def refine_from_answers(
        self,
        initial_prompt: str,
        answers: Dict[str, Any],
        question_mapping: Dict[str, str],
        system_instruction: str,
    ) -> str:
        payload = self._format_refinement_payload(initial_prompt, answers, question_mapping)
        return self._generate_text(
            payload,
            system_instruction,
            json_mode=False,
            max_tokens=DEFAULT_REFINEMENT_MAX_TOKENS,
        )

    def generate_refined_prompt(  # pragma: no cover - backwards compatibility shim
        self,
        initial_prompt: str,
        answers: Dict[str, Any],
        system_instruction: str,
    ) -> str:
        """
        Deprecated wrapper maintained for compatibility with older integrations/tests.
        Falls back to using the raw answer keys as question text.
        """
        logger.debug("generate_refined_prompt is deprecated; use refine_from_answers instead.")
        return self.refine_from_answers(initial_prompt, answers, {}, system_instruction)

    def tweak_prompt(
        self,
        current_prompt: str,
        tweak_instruction: str,
        system_instruction: str,
    ) -> str:
        payload = self._format_tweak_payload(current_prompt, tweak_instruction)
        return self._generate_text(
            payload,
            system_instruction,
            json_mode=False,
            max_tokens=DEFAULT_TWEAK_MAX_TOKENS,
        )

    def light_refine(self, prompt: str, system_instruction: str) -> str:
        """
        Performs a non-interactive refinement of a prompt.
        This is a default implementation that can be overridden by providers
        if a more specific implementation is needed.
        """
        return self._generate_text(
            prompt,
            system_instruction,
            json_mode=False,
            max_tokens=DEFAULT_REFINEMENT_MAX_TOKENS,
        )

    # ------------------------------------------------------------------ #
    # Formatting helpers shared across providers
    # ------------------------------------------------------------------ #
    def _format_refinement_payload(
        self,
        initial_prompt: str,
        answers: Dict[str, Any],
        question_mapping: Dict[str, str],
    ) -> str:
        lines: List[str] = [
            f"Initial Prompt: {initial_prompt}",
            "",
            "User's Answers to Clarifying Questions:",
        ]
        for key, value in answers.items():
            if isinstance(value, list):
                value_str = ", ".join(value) if value else "None selected"
            else:
                value_str = value or "None provided"
            question_text = question_mapping.get(key, key)
            lines.append(f"- {question_text}: {value_str}")

        lines.extend(
            [
                "",
                "Please generate a refined, optimized prompt based on this information.",
            ]
        )
        return "\n".join(lines)

    def _format_tweak_payload(self, current_prompt: str, tweak_instruction: str) -> str:
        return "\n".join(
            [
                "Current Prompt:",
                current_prompt,
                "",
                "User's Modification Request:",
                tweak_instruction,
                "",
                "Return the tweaked prompt:",
            ]
        )


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str, model_name: str = "gemini-pro") -> None:
        import google.generativeai as genai
        try:
            from google.api_core import exceptions as google_exceptions  # type: ignore[attr-defined]
            self._fatal_exceptions: Tuple[type[Exception], ...] = (
                google_exceptions.PermissionDenied,
                google_exceptions.InvalidArgument,
                google_exceptions.ResourceExhausted,
            )
        except Exception:  # pragma: no cover - optional dependency
            self._fatal_exceptions = ()

        genai.configure(api_key=api_key)
        self.genai = genai
        self.model_name = model_name
        self._model_cache: Dict[Tuple[str, str, bool], Any] = {}

    def _get_model(self, model_name: str, system_instruction: str, json_mode: bool) -> Any:
        cache_key = (model_name, system_instruction, json_mode)
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        generation_config: Optional[GenerationConfigType] = None
        if json_mode:
            generation_config = cast(
                GenerationConfigType,
                {"response_mime_type": "application/json"},
            )

        model = self.genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config=generation_config,
        )
        self._model_cache[cache_key] = model
        return model

    def _generate_text(
        self,
        prompt: str,
        system_instruction: str,
        *,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,  # noqa: ARG002 - Gemini config handled via generation_config
    ) -> str:
        """Try multiple models until one succeeds, caching model instances."""
        models_to_try = [self.model_name] + [m for m in config.get_provider_config()["models"] if m != self.model_name]
        last_error: Optional[Exception] = None

        for model_name in models_to_try:
            try:
                model = self._get_model(model_name, system_instruction, json_mode)
                response = model.generate_content(prompt)
                text = getattr(response, "text", None)
                if text is None and hasattr(response, "candidates"):
                    candidates = getattr(response, "candidates", [])
                    if candidates:
                        first_candidate = candidates[0]
                        parts = getattr(first_candidate, "content", [])
                        if parts:
                            text = getattr(parts[0], "text", None)
                if text is None and hasattr(response, "result"):
                    text = getattr(response.result, "text", None)
                if text is None:
                    raise RuntimeError("Gemini response did not include text content")
                return str(text)
            except Exception as exc:  # pragma: no cover - network failures
                last_error = exc
                sanitized = sanitize_error_message(str(exc))
                logger.warning("Gemini model %s failed: %s", model_name, sanitized)
                if self._fatal_exceptions and isinstance(exc, self._fatal_exceptions):
                    # Fatal auth/argument errors – stop immediately
                    break
                if "401" in str(exc) and model_name != models_to_try[-1]:
                    continue

        if last_error:
            sanitized = sanitize_error_message(str(last_error))
            raise RuntimeError(f"Gemini API call failed: {sanitized}") from last_error
        raise RuntimeError("Gemini API call failed: unknown error")

    def generate_questions(self, initial_prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        """Generate clarifying questions using Gemini."""
        try:
            response_text = self._generate_text(
                initial_prompt,
                system_instruction,
                json_mode=True,
            )
        except Exception as exc:
            logger.warning("Gemini question generation failed: %s", sanitize_error_message(str(exc)))
            return None

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini returned invalid JSON: %s", sanitize_error_message(str(exc)))
            return None

        if not isinstance(result, dict) or "task_type" not in result:
            logger.warning("Gemini question payload missing task_type; falling back to static questions")
            return None

        result.setdefault("questions", [])
        return result


class AnthropicProvider(LLMProvider):
    """Anthropic/Claude provider (also supports Z.ai)."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-5-sonnet-20241022",
        base_url: Optional[str] = None,
    ) -> None:
        import anthropic

        client_args = {"api_key": api_key, "timeout": DEFAULT_PROVIDER_TIMEOUT}
        if base_url:
            client_args["base_url"] = base_url

        self.client = anthropic.Anthropic(**client_args)
        self.model_name = model_name

    def _generate_text(
        self,
        prompt: str,
        system_instruction: str,
        *,
        json_mode: bool = False,  # noqa: ARG002 - unused for Anthropic
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens or DEFAULT_REFINEMENT_MAX_TOKENS,
                system=system_instruction,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # pragma: no cover - network failures
            sanitized = sanitize_error_message(str(exc))
            logger.warning("Anthropic API call failed: %s", sanitized)
            raise RuntimeError(f"Anthropic API call failed: {sanitized}") from exc

        if not response.content:
            raise RuntimeError("Anthropic API returned no content")

        first_block = response.content[0]
        text = getattr(first_block, "text", None)
        if text is None:
            text = getattr(first_block, "value", None)
        if text is None:
            text = str(first_block)
        return str(text)

    @staticmethod
    def _extract_json_block(text: str) -> str:
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        return text

    def generate_questions(self, initial_prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        """Generate clarifying questions using Claude."""
        try:
            response_text = self._generate_text(
                initial_prompt,
                system_instruction,
                max_tokens=DEFAULT_CLARIFICATION_MAX_TOKENS,
            )
        except Exception as exc:
            logger.warning(
                "Anthropic question generation failed: %s", sanitize_error_message(str(exc))
            )
            return None

        cleaned = self._extract_json_block(response_text)
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("Anthropic returned invalid JSON: %s", sanitize_error_message(str(exc)))
            return None

        if not isinstance(result, dict) or "task_type" not in result:
            logger.warning("Anthropic question payload missing task_type; falling back to static questions")
            return None

        result.setdefault("questions", [])
        return result


def get_provider(provider_name: str, config: Config, model_name: Optional[str] = None) -> LLMProvider:
    """Factory function to get the appropriate provider."""
    provider_config = config.get_provider_config()
    model_to_use = model_name or config.get_model()

    if provider_name == "gemini":
        return GeminiProvider(
            api_key=provider_config["api_key"],
            model_name=model_to_use,
        )
    if provider_name == "anthropic":
        return AnthropicProvider(
            api_key=provider_config["api_key"],
            model_name=model_to_use,
            base_url=provider_config.get("base_url"),
        )
    raise ValueError(f"Unknown provider: {provider_name}")

__all__ = ["LLMProvider", "get_provider", "GeminiProvider", "AnthropicProvider"]
