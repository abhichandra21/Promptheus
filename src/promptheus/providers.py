"""
LLM Provider abstraction layer.
Supports Gemini, Anthropic/Claude, OpenAI, Groq, Qwen, and GLM.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, cast

from promptheus.constants import (
    DEFAULT_CLARIFICATION_MAX_TOKENS,
    DEFAULT_PROVIDER_TIMEOUT,
    DEFAULT_REFINEMENT_MAX_TOKENS,
    DEFAULT_TWEAK_MAX_TOKENS,
)
from promptheus.utils import sanitize_error_message
from promptheus.exceptions import ProviderAPIError

logger = logging.getLogger(__name__)


def _print_user_error(message: str) -> None:
    """Print error message directly to stderr for user visibility."""
    print(f"  [!] {message}", file=sys.stderr)


if TYPE_CHECKING:  # pragma: no cover - typing support only
    from promptheus.config import Config


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_questions(self, initial_prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        """
        Generate clarifying questions based on initial prompt.
        Returns dict with 'task_type' and 'questions' keys.
        """

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models from the provider API.
        Returns list of model names.
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




_JSON_ONLY_SUFFIX = (
    "Respond ONLY with a valid JSON object using double-quoted keys. "
    "Include the fields specified in the instructions (for example, task_type and questions). "
    "Do not wrap the JSON in markdown code fences or add commentary."
)


def _build_chat_messages(system_instruction: str, prompt: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    return messages


def _coerce_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        fragments: List[str] = []
        for item in content:
            if isinstance(item, dict):
                text_value = item.get("text") or item.get("content") or item.get("value")
                if isinstance(text_value, str):
                    fragments.append(text_value)
        return "".join(fragments)
    if hasattr(content, "text"):
        value = getattr(content, "text")
        if isinstance(value, str):
            return value
    return str(content or "")


def _append_json_instruction(prompt: str) -> str:
    if not prompt:
        return _JSON_ONLY_SUFFIX
    if _JSON_ONLY_SUFFIX in prompt:
        return prompt
    suffix = "" if prompt.endswith("\n") else "\n\n"
    return f"{prompt}{suffix}{_JSON_ONLY_SUFFIX}"


def _parse_question_payload(provider_label: str, raw_text: str) -> Optional[Dict[str, Any]]:
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("%s returned invalid JSON: %s", provider_label, sanitize_error_message(str(exc)))
        return None

    if not isinstance(result, dict) or "task_type" not in result:
        logger.warning(
            "%s question payload missing task_type; falling back to static questions",
            provider_label,
        )
        return None

    result.setdefault("questions", [])
    return result


class AnthropicProvider(LLMProvider):
    """Anthropic/Claude provider (also supports Z.ai)."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-5-sonnet-20240620",
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
            raise ProviderAPIError(f"API call failed: {sanitized}") from exc

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
        response_text = self._generate_text(
            initial_prompt,
            system_instruction,
            max_tokens=DEFAULT_CLARIFICATION_MAX_TOKENS,
        )

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

    def get_available_models(self) -> List[str]:
        """Get available models from Anthropic API."""
        try:
            response = self.client.models.list()
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            logger.warning("Failed to fetch Anthropic models: %s", sanitized)
            raise RuntimeError(f"Failed to fetch Anthropic models: {sanitized}") from exc

        data = getattr(response, "data", None) or []
        models: List[str] = []
        for entry in data:
            model_id = getattr(entry, "id", None)
            if model_id is None and isinstance(entry, dict):
                model_id = entry.get("id") or entry.get("name")
            if model_id:
                models.append(str(model_id))

        return models


class GeminiProvider(LLMProvider):
    """Google Gemini provider using the unified google-genai SDK.

    Supports both Gemini Developer API (AIza... keys) and Vertex AI (AQ... keys).
    Automatically detects API key type and routes to appropriate endpoint."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-flash",
    ) -> None:
        from google import genai

        # Detect API key type and use appropriate endpoint
        # AQ.* keys are Vertex AI, AIza.* keys are Gemini Developer API
        is_vertex_ai_key = api_key.startswith('AQ.')

        self.client = genai.Client(
            api_key=api_key,
            vertexai=is_vertex_ai_key,  # Use Vertex AI for AQ.* keys, Gemini API for AIza.* keys
        )
        self.model_name = model_name

    def _generate_text(
        self,
        prompt: str,
        system_instruction: str,
        *,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using the new google-genai SDK."""
        from google.genai import types

        try:
            config_params: Dict[str, Any] = {
                "system_instruction": system_instruction,
            }
            if max_tokens is not None:
                config_params["max_output_tokens"] = max_tokens
            if json_mode:
                config_params["response_mime_type"] = "application/json"

            config = types.GenerateContentConfig(**config_params)

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            if hasattr(response, 'text') and response.text:
                return str(response.text)
            raise RuntimeError("Gemini response did not include text content")

        except Exception as exc:
            error_msg = str(exc)
            sanitized = sanitize_error_message(error_msg)
            logger.warning("Gemini model %s failed: %s", self.model_name, sanitized)

            # Provide helpful context for common errors
            if "401" in error_msg or "403" in error_msg or "Unauthorized" in error_msg or "UNAUTHENTICATED" in error_msg:
                _print_user_error("Authentication failed: Please check your API key")
                _print_user_error("Ensure your GOOGLE_API_KEY or GEMINI_API_KEY is valid and active")
                _print_user_error("Get your API key at: https://makersuite.google.com/app/apikey")
            elif "404" in error_msg:
                _print_user_error(f"Model not found: The model '{self.model_name}' may not exist or be available")

            raise ProviderAPIError(f"API call failed: {sanitized}") from exc

    def generate_questions(self, initial_prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        """Generate clarifying questions using Gemini."""
        response_text = self._generate_text(
            initial_prompt,
            system_instruction,
            json_mode=True,
        )

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

    def get_available_models(self) -> List[str]:
        """Get available models from Gemini API."""
        try:
            model_iterable = self.client.models.list()
            models: List[str] = []
            for model in model_iterable:
                name = getattr(model, "name", None)
                if name is None and isinstance(model, dict):
                    name = model.get("name")
                if not name:
                    continue
                models.append(name.split("/")[-1])

            return models
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            logger.warning("Failed to fetch Gemini models: %s", sanitized)
            raise RuntimeError(
                "Gemini model listing via API requires OAuth credentials. "
                "Refer to https://ai.google.dev/gemini-api/docs/models for the latest list."
            ) from exc


class OpenAICompatibleProvider(LLMProvider):
    """Base provider for APIs that implement the OpenAI chat/completions surface."""

    PROVIDER_LABEL = "OpenAI"

    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        timeout: int = DEFAULT_PROVIDER_TIMEOUT,
        provider_label: Optional[str] = None,
        **client_kwargs: Any,
    ) -> None:
        from openai import OpenAI

        client_kwargs: Dict[str, Any] = {
            "api_key": api_key,
            "timeout": timeout,
            **client_kwargs,
        }
        if base_url:
            client_kwargs["base_url"] = base_url
        if organization:
            client_kwargs["organization"] = organization
        if project:
            client_kwargs["project"] = project
        self.client = OpenAI(**client_kwargs)
        self.model_name = model_name
        self._provider_label = provider_label or self.PROVIDER_LABEL

    def _generate_text(
        self,
        prompt: str,
        system_instruction: str,
        *,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> str:
        messages = _build_chat_messages(
            system_instruction,
            _append_json_instruction(prompt) if json_mode else prompt,
        )
        params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens or DEFAULT_REFINEMENT_MAX_TOKENS,
        }
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**params)
        except Exception as exc:  # pragma: no cover - network failures
            sanitized = sanitize_error_message(str(exc))
            logger.warning("%s API call failed: %s", self._provider_label, sanitized)
            raise ProviderAPIError(f"API call failed: {sanitized}") from exc

        if not response.choices:
            raise RuntimeError(f"{self._provider_label} API returned no choices")
        choice = response.choices[0]
        message = getattr(choice, "message", None)
        text = _coerce_message_content(getattr(message, "content", None))
        if not text:
            raise RuntimeError(f"{self._provider_label} API response did not include text output")
        return str(text)

    def generate_questions(self, initial_prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        response_text = self._generate_text(
            initial_prompt,
            system_instruction,
            json_mode=True,
            max_tokens=DEFAULT_CLARIFICATION_MAX_TOKENS,
        )
        return _parse_question_payload(self._provider_label, response_text)

    def get_available_models(self) -> List[str]:
        """Get available models from the OpenAI-compatible API."""
        try:
            models_response = self.client.models.list()
            return [model.id for model in models_response.data]
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            logger.warning("Failed to fetch %s models: %s", self._provider_label, sanitized)
            raise RuntimeError(f"Failed to fetch {self._provider_label} models: {sanitized}") from exc


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider backed by the official openai-python client."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        *,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            organization=organization,
            project=project,
            provider_label="OpenAI",
        )


class GroqProvider(OpenAICompatibleProvider):
    """Groq provider using the OpenAI-compatible API surface."""

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str, model_name: str = "llama3-70b-8192", base_url: Optional[str] = None) -> None:
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url or self.DEFAULT_BASE_URL,
            provider_label="Groq",
        )


class QwenProvider(OpenAICompatibleProvider):
    """Qwen provider using DashScope's OpenAI-compatible endpoint."""

    DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    def __init__(self, api_key: str, model_name: str = "qwen-turbo") -> None:
        base_url = os.getenv("DASHSCOPE_HTTP_BASE_URL", self.DEFAULT_BASE_URL)
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            provider_label="Qwen",
        )


class GLMProvider(OpenAICompatibleProvider):
    """Zhipu GLM provider using the OpenAI-compatible API surface."""

    DEFAULT_BASE_URL = "https://api.z.ai/api/paas/v4"

    def __init__(self, api_key: str, model_name: str = "glm-4", base_url: Optional[str] = None) -> None:
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url or self.DEFAULT_BASE_URL,
            provider_label="GLM",
        )


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
    if provider_name == "openai":
        return OpenAIProvider(
            api_key=provider_config["api_key"],
            model_name=model_to_use,
            base_url=provider_config.get("base_url"),
            organization=provider_config.get("organization"),
            project=provider_config.get("project"),
        )
    if provider_name == "groq":
        return GroqProvider(
            api_key=provider_config["api_key"],
            model_name=model_to_use,
        )
    if provider_name == "qwen":
        return QwenProvider(
            api_key=provider_config["api_key"],
            model_name=model_to_use,
        )
    if provider_name == "glm":
        return GLMProvider(
            api_key=provider_config["api_key"],
            model_name=model_to_use,
            base_url=provider_config.get("base_url"),
        )
    raise ValueError(f"Unknown provider: {provider_name}")

__all__ = [
    "LLMProvider",
    "get_provider",
    "GeminiProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GroqProvider",
    "QwenProvider",
    "GLMProvider",
]
