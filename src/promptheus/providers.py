"""
LLM Provider abstraction layer.
Supports Gemini, Anthropic/Claude, OpenAI, Groq, Qwen, GLM, and OpenRouter.
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
from promptheus.config import SUPPORTED_PROVIDER_IDS
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
                "Edit the prompt below. Preserve all line breaks, bullets, indentation, headings, and section order unless the user explicitly asks to change formatting.",
                "Keep all sections; do not drop content. Keep length within ±10% unless the user requests a length change.",
                "Return only the modified prompt text. No fences, no commentary.",
                "",
                "<<<CURRENT_PROMPT>>>",
                current_prompt,
                "<<<END_CURRENT_PROMPT>>>",
                "",
                "<<<TWEAK_REQUEST>>>",
                tweak_instruction,
                "<<<END_TWEAK_REQUEST>>>",
                "",
                "Now return the tweaked prompt:",
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
        # Reset token usage for this call
        self.last_input_tokens = None  # type: ignore[attr-defined]
        self.last_output_tokens = None  # type: ignore[attr-defined]
        self.last_total_tokens = None  # type: ignore[attr-defined]
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

        # Capture token usage when available
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                input_tokens = getattr(usage, "input_tokens", None)
                output_tokens = getattr(usage, "output_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
                if total_tokens is None and isinstance(input_tokens, int) and isinstance(output_tokens, int):
                    total_tokens = input_tokens + output_tokens
                self.last_input_tokens = input_tokens  # type: ignore[attr-defined]
                self.last_output_tokens = output_tokens  # type: ignore[attr-defined]
                self.last_total_tokens = total_tokens  # type: ignore[attr-defined]
        except Exception:
            # Token accounting is best-effort only
            self.last_input_tokens = None  # type: ignore[attr-defined]
            self.last_output_tokens = None  # type: ignore[attr-defined]
            self.last_total_tokens = None  # type: ignore[attr-defined]

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
            # Reset token usage for this call
            self.last_input_tokens = None  # type: ignore[attr-defined]
            self.last_output_tokens = None  # type: ignore[attr-defined]
            self.last_total_tokens = None  # type: ignore[attr-defined]

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

            # Capture token usage when available (field names vary by SDK version)
            try:
                usage = getattr(response, "usage_metadata", None)
                if usage is None and isinstance(response, dict):
                    usage = response.get("usage_metadata")
                if usage is not None:
                    def _get(name_candidates):
                        if isinstance(usage, dict):
                            for name in name_candidates:
                                value = usage.get(name)
                                if isinstance(value, (int, float)):
                                    return int(value)
                        else:
                            for name in name_candidates:
                                value = getattr(usage, name, None)
                                if isinstance(value, (int, float)):
                                    return int(value)
                        return None

                    input_tokens = _get(["input_tokens", "prompt_tokens", "prompt_token_count"])
                    output_tokens = _get(["output_tokens", "candidates_token_count", "completion_tokens"])
                    total_tokens = _get(["total_tokens", "total_token_count"])
                    if total_tokens is None and input_tokens is not None and output_tokens is not None:
                        total_tokens = input_tokens + output_tokens

                    self.last_input_tokens = input_tokens  # type: ignore[attr-defined]
                    self.last_output_tokens = output_tokens  # type: ignore[attr-defined]
                    self.last_total_tokens = total_tokens  # type: ignore[attr-defined]
            except Exception:
                self.last_input_tokens = None  # type: ignore[attr-defined]
                self.last_output_tokens = None  # type: ignore[attr-defined]
                self.last_total_tokens = None  # type: ignore[attr-defined]

            if hasattr(response, "text") and response.text:
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
        # Reset token usage for this call
        self.last_input_tokens = None  # type: ignore[attr-defined]
        self.last_output_tokens = None  # type: ignore[attr-defined]
        self.last_total_tokens = None  # type: ignore[attr-defined]

        messages = _build_chat_messages(
            system_instruction,
            _append_json_instruction(prompt) if json_mode else prompt,
        )

        limit = max_tokens or DEFAULT_REFINEMENT_MAX_TOKENS

        response_mode = "chat"

        def _call_chat() -> Any:
            params: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": limit,
            }
            if json_mode:
                params["response_format"] = {"type": "json_object"}
            return self.client.chat.completions.create(**params)

        def _call_responses() -> Any:
            params: Dict[str, Any] = {
                "model": self.model_name,
                "input": messages,
                "max_output_tokens": limit,
            }
            if json_mode:
                params["response_format"] = {"type": "json_object"}

            current_params = params
            dropped_max = False
            dropped_response_format = False
            last_exc: Optional[BaseException] = None

            for _ in range(3):
                try:
                    return self.client.responses.create(**current_params)
                except TypeError as te:
                    last_exc = te
                    message = str(te)
                    if "max_output_tokens" in message and not dropped_max:
                        current_params = {k: v for k, v in current_params.items() if k != "max_output_tokens"}
                        dropped_max = True
                        continue
                    if "response_format" in message and not dropped_response_format:
                        current_params = {k: v for k, v in current_params.items() if k != "response_format"}
                        dropped_response_format = True
                        continue
                    raise
                except Exception as exc:  # pragma: no cover - network failures
                    last_exc = exc
                    break

            if last_exc:
                raise last_exc
            raise RuntimeError("Failed to invoke Responses API with provided parameters")

        try:
            response = _call_chat()
        except Exception as exc:  # pragma: no cover - network failures
            sanitized_first = sanitize_error_message(str(exc))
            lower_msg = sanitized_first.lower()
            fallback_triggers = (
                "responses api",
                "max_output_tokens",
                "max_tokens",
                "unexpected keyword argument",
                "use the responses api",
                "unrecognized request argument",
                "unsupported parameter",
            )
            if any(trigger in lower_msg for trigger in fallback_triggers):
                logger.info("%s chat API rejected parameters; retrying via Responses API", self._provider_label)
                try:
                    response = _call_responses()
                    response_mode = "responses"
                except Exception as exc_responses:
                    sanitized_second = sanitize_error_message(str(exc_responses))
                    logger.warning("%s Responses API call failed after chat fallback: %s", self._provider_label, sanitized_second)
                    raise ProviderAPIError(f"API call failed: {sanitized_second}") from exc_responses
            else:
                logger.warning("%s API call failed: %s", self._provider_label, sanitized_first)
                raise ProviderAPIError(f"API call failed: {sanitized_first}") from exc

        # Capture token usage when available
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                input_tokens = getattr(usage, "prompt_tokens", None)
                if input_tokens is None:
                    input_tokens = getattr(usage, "input_tokens", None)
                output_tokens = getattr(usage, "completion_tokens", None)
                if output_tokens is None:
                    output_tokens = getattr(usage, "output_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
                if total_tokens is None and isinstance(input_tokens, int) and isinstance(output_tokens, int):
                    total_tokens = input_tokens + output_tokens
                self.last_input_tokens = input_tokens  # type: ignore[attr-defined]
                self.last_output_tokens = output_tokens  # type: ignore[attr-defined]
                self.last_total_tokens = total_tokens  # type: ignore[attr-defined]
        except Exception:
            self.last_input_tokens = None  # type: ignore[attr-defined]
            self.last_output_tokens = None  # type: ignore[attr-defined]
            self.last_total_tokens = None  # type: ignore[attr-defined]

        if response_mode == "responses":
            text = getattr(response, "output_text", None)
            if not text:
                output = getattr(response, "output", None) or getattr(response, "outputs", None)
                if isinstance(output, list) and output:
                    first_output = output[0]
                    content = getattr(first_output, "content", None)
                    if content is None and isinstance(first_output, dict):
                        content = first_output.get("content")
                    text = _coerce_message_content(content)
        else:
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


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter provider using the OpenAI-compatible API surface.

    OpenRouter is a unified API gateway that provides access to hundreds of AI models
    from various providers (OpenAI, Anthropic, Google, Meta, etc.) through a single endpoint.

    Key differences from other providers:
    - Model availability is API-key specific (depends on user's credits and permissions)
    - Uses a special 'openrouter/auto' model for intelligent routing
    - Model names include provider prefix (e.g., 'openai/gpt-4', 'anthropic/claude-3-opus')
    - Has its own /api/v1/models endpoint that returns models available to the specific API key
    """

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model_name: str = "openrouter/auto", base_url: Optional[str] = None) -> None:
        # For OpenRouter, the OpenAI-compatible client created by the base class is kept for
        # structural consistency (shared helpers and type expectations), but all text generation
        # and model listing use the direct HTTP path implemented below rather than the OpenAI
        # compatibility surface.
        self._api_key = api_key
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url or self.DEFAULT_BASE_URL,
            provider_label="OpenRouter",
        )

    def _generate_text(
        self,
        prompt: str,
        system_instruction: str,
        *,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Use a direct OpenRouter call to avoid provider selection failures when JSON mode is unsupported.
        We avoid response_format and rely on an embedded JSON-only instruction when needed.
        """
        import httpx

        user_prompt = _append_json_instruction(prompt) if json_mode else prompt
        messages = _build_chat_messages(system_instruction, user_prompt)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self._base_url}/chat/completions"

        # Reset token usage for this call
        self.last_input_tokens = None  # type: ignore[attr-defined]
        self.last_output_tokens = None  # type: ignore[attr-defined]
        self.last_total_tokens = None  # type: ignore[attr-defined]

        def _post_with_model(model_name: str) -> httpx.Response:
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens or DEFAULT_REFINEMENT_MAX_TOKENS,
            }
            return httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=DEFAULT_PROVIDER_TIMEOUT,
            )

        try:
            response = _post_with_model("openrouter/auto")
            if response.status_code == 404 and "No allowed providers" in response.text:
                fallback_model = os.getenv("OPENROUTER_FALLBACK_MODEL", "mistralai/mistral-nemo")
                response = _post_with_model(fallback_model)
        except httpx.TimeoutException as exc:
            logger.warning("OpenRouter API call timed out")
            raise ProviderAPIError("API call failed: OpenRouter request timed out") from exc
        except Exception as exc:  # pragma: no cover - network failures
            sanitized_error = sanitize_error_message(str(exc))
            logger.warning("OpenRouter API call failed: %s", sanitized_error)
            raise ProviderAPIError(f"API call failed: {sanitized_error}") from exc

        if response.status_code != 200:
            sanitized_body = sanitize_error_message(response.text or f"Status {response.status_code}")
            logger.warning("OpenRouter returned non-200 status %s: %s", response.status_code, sanitized_body)
            # Provide basic guidance for common authentication and permission errors
            if response.status_code in (401, 403):
                logger.warning(
                    "OpenRouter authentication or permission error detected. "
                    "Check the OpenRouter dashboard, ensure the key is valid, and that at least one provider/model is enabled."
                )
            raise ProviderAPIError(f"API call failed: Status {response.status_code} - {sanitized_body}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderAPIError("API call failed: Invalid JSON response from OpenRouter") from exc

        if isinstance(data, dict) and "error" in data:
            sanitized_error = sanitize_error_message(str(data.get("error")))
            logger.warning("OpenRouter returned error payload: %s", sanitized_error)
            raise ProviderAPIError(f"API call failed: {sanitized_error}")

        # Capture token usage when available
        try:
            if isinstance(data, dict):
                usage = data.get("usage")
                if isinstance(usage, dict):
                    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
                    output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
                    total_tokens = usage.get("total_tokens")
                    if total_tokens is None and isinstance(input_tokens, int) and isinstance(output_tokens, int):
                        total_tokens = input_tokens + output_tokens
                    self.last_input_tokens = input_tokens  # type: ignore[attr-defined]
                    self.last_output_tokens = output_tokens  # type: ignore[attr-defined]
                    self.last_total_tokens = total_tokens  # type: ignore[attr-defined]
        except Exception:
            self.last_input_tokens = None  # type: ignore[attr-defined]
            self.last_output_tokens = None  # type: ignore[attr-defined]
            self.last_total_tokens = None  # type: ignore[attr-defined]

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise ProviderAPIError("API call failed: OpenRouter response missing choices")

        message = choices[0].get("message", {})
        text = _coerce_message_content(message.get("content"))
        if not text:
            raise ProviderAPIError("API call failed: OpenRouter response missing text output")
        return str(text)

    def get_available_models(self) -> List[str]:
        """Get recommended models for OpenRouter.

        OpenRouter's special characteristics:
        1. It's an aggregator providing access to hundreds of models from multiple providers
        2. The /api/v1/models endpoint returns the ENTIRE catalog (not user-specific)
        3. Model availability is determined at request time based on credits/permissions
        4. The 'openrouter/auto' model intelligently routes to the best available model

        Since OpenRouter returns all platform models (not account-specific), we return
        a curated list with 'openrouter/auto' as the recommended option. Users can
        still specify any model manually if they have access.

        Returns:
            List containing the recommended 'openrouter/auto' model. Users can manually
            specify any model from https://openrouter.ai/models if they have access.

        Raises:
            RuntimeError: If there's a critical configuration error
        """
        # For OpenRouter, recommend using the auto-routing model
        # This intelligently selects the best available model based on the user's
        # prompt and their account permissions/credits
        logger.debug("Returning recommended model for OpenRouter: openrouter/auto")
        return ["openrouter/auto"]


def get_provider(provider_name: str, config: Config, model_name: Optional[str] = None) -> LLMProvider:
    """Factory function to get the appropriate provider."""
    provider_config = config.get_provider_config()
    model_to_use = model_name or config.get_model()

    # OpenRouter should always rely on its auto-routing model to avoid per-model permission errors
    if provider_name == "openrouter":
        model_to_use = "openrouter/auto"

    if provider_name in ("google", "gemini"):
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
    if provider_name == "openrouter":
        return OpenRouterProvider(
            api_key=provider_config["api_key"],
            model_name=model_to_use,
            base_url=provider_config.get("base_url"),
        )
    raise ValueError(f"Unknown provider: {provider_name}")


def get_available_providers(config) -> Dict[str, Any]:
    """Get available providers and their status."""
    from promptheus.config import SUPPORTED_PROVIDER_IDS
    config_data = config._ensure_provider_config()
    providers_data = config_data.get("providers", {})
    
    available_providers = {}
    for provider_id in SUPPORTED_PROVIDER_IDS:
        provider_info = providers_data.get(provider_id, {})
        if not provider_info:
            continue

        # Check if this provider has API key configured
        api_key_env = provider_info.get("api_key_env")
        keys = api_key_env if isinstance(api_key_env, list) else [api_key_env]
        is_configured = any(os.getenv(key_env) for key_env in keys if key_env)
        
        available_providers[provider_id] = {
            "name": provider_info.get("display_name", provider_info.get("name", provider_id.title())),
            "available": is_configured,
            "default_model": provider_info.get("default_model", "")
        }
    
    return available_providers


def validate_provider(provider_id: str, config) -> bool:
    """Validate if a provider is available and properly configured."""
    from promptheus.config import SUPPORTED_PROVIDER_IDS
    if provider_id not in SUPPORTED_PROVIDER_IDS:
        return False

    config_data = config._ensure_provider_config()
    provider_info = config_data.get("providers", {}).get(provider_id)
    if not provider_info:
        return False

    api_key_env = provider_info.get("api_key_env")
    if isinstance(api_key_env, list):
        return any(os.getenv(key_env) for key_env in api_key_env)
    if api_key_env:
        return bool(os.getenv(api_key_env))
    return False


__all__ = [
    "LLMProvider",
    "get_provider",
    "get_available_providers",
    "validate_provider",
    "GeminiProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GroqProvider",
    "QwenProvider",
    "GLMProvider",
    "OpenRouterProvider",
]
