"""Unified LLM client with multi-provider support.

Supports four provider types:
- openai_compatible — any OpenAI-compatible endpoint (gateway, vLLM, etc.)
- anthropic        — direct Anthropic API
- openai           — direct OpenAI API
- gemini           — Google Gemini API via google-generativeai

All calls go through the unified `chat()` / `chat_json()` functions.
Provider selection and credentials are read from env vars or passed explicitly.
"""
from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


# ── Provider registry ─────────────────────────────────────────────────────────

class BaseProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        ...

    async def chat_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Chat completion returning parsed JSON. Falls back to extracting from text."""
        try:
            raw = await self.chat(
                prompt, system_prompt=system_prompt, model=model,
                max_tokens=max_tokens, temperature=temperature, json_mode=True,
            )
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            raw = await self.chat(
                prompt, system_prompt=system_prompt, model=model,
                max_tokens=max_tokens, temperature=temperature, json_mode=False,
            )
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Could not extract JSON from response: {raw[:300]}")

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """Test provider connectivity. Returns {"status": "ok", "model": ...} or raises."""
        ...


# ── OpenAI-compatible (gateway, vLLM, etc.) ───────────────────────────────────

class OpenAICompatibleProvider(BaseProvider):
    """Provider for any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "http://10.190.0.214:8080/v1",
        default_model: str = "deepseek-v4-pro",
        fallback_model: str = "us.anthropic.claude-opus-4-6",
    ):
        from openai import AsyncOpenAI

        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1")
        self.default_model = default_model or os.getenv("LLM_MODEL", "deepseek-v4-pro")
        self.fallback_model = fallback_model or os.getenv("LLM_FALLBACK_MODEL", "us.anthropic.claude-opus-4-6")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = dict(
            model=model or self.default_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = await self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"[LLM] Primary model {model or self.default_model} failed: {e}")
            if self.fallback_model and self.fallback_model != (model or self.default_model):
                logger.info(f"[LLM] Falling back to {self.fallback_model}")
                kwargs["model"] = self.fallback_model
                resp = await self.client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            raise

    async def test_connection(self) -> dict[str, Any]:
        resp = await self.client.chat.completions.create(
            model=self.default_model,
            messages=[{"role": "user", "content": "Reply with just: ok"}],
            max_tokens=10,
        )
        return {"status": "ok", "model": self.default_model, "provider": "openai_compatible"}


# ── Direct Anthropic ──────────────────────────────────────────────────────────

class AnthropicProvider(BaseProvider):
    """Provider for direct Anthropic API."""

    def __init__(
        self,
        api_key: str = "",
        default_model: str = "claude-sonnet-4-20250514",
    ):
        import anthropic

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.default_model = default_model or "claude-sonnet-4-20250514"
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        kwargs: dict[str, Any] = dict(
            model=model or self.default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        resp = await self.client.messages.create(**kwargs)
        return resp.content[0].text if resp.content else ""

    async def test_connection(self) -> dict[str, Any]:
        resp = await self.client.messages.create(
            model=self.default_model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with just: ok"}],
        )
        return {"status": "ok", "model": self.default_model, "provider": "anthropic"}


# ── Direct OpenAI ─────────────────────────────────────────────────────────────

class OpenAIProvider(BaseProvider):
    """Provider for direct OpenAI API."""

    def __init__(
        self,
        api_key: str = "",
        default_model: str = "gpt-4o",
    ):
        from openai import AsyncOpenAI

        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.default_model = default_model or "gpt-4o"
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = dict(
            model=model or self.default_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = await self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def test_connection(self) -> dict[str, Any]:
        resp = await self.client.chat.completions.create(
            model=self.default_model,
            messages=[{"role": "user", "content": "Reply with just: ok"}],
            max_tokens=10,
        )
        return {"status": "ok", "model": self.default_model, "provider": "openai"}


# ── Google Gemini ─────────────────────────────────────────────────────────────

class GeminiProvider(BaseProvider):
    """Provider for Google Gemini API via google-generativeai."""

    def __init__(
        self,
        api_key: str = "",
        default_model: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.default_model = default_model or "gemini-2.5-flash"

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        try:
            import google.genai as genai
            from google.genai import types as genai_types
        except ImportError:
            raise ImportError("google-genai not installed. Run: pip install google-genai")

        client = genai.Client(api_key=self.api_key)
        config = genai_types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_prompt,
        )
        resp = client.models.generate_content(
            model=model or self.default_model,
            contents=prompt,
            config=config,
        )
        return resp.text if hasattr(resp, 'text') else ""

    async def test_connection(self) -> dict[str, Any]:
        try:
            import google.genai as genai
        except ImportError:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
        client = genai.Client(api_key=self.api_key)
        resp = client.models.generate_content(
            model=self.default_model,
            contents="Reply with just: ok",
        )
        return {"status": "ok", "model": self.default_model, "provider": "gemini"}


# ── Provider factory ──────────────────────────────────────────────────────────

PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "openai_compatible": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}

PROVIDER_MODELS: dict[str, list[dict[str, str]]] = {
    "openai_compatible": [
        {"id": "deepseek-chat", "name": "DeepSeek Chat", "description": "Fast, good for code"},
        {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "description": "Reasoning-focused"},
        {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro", "description": "Latest DeepSeek flagship"},
        {"id": "us.anthropic.claude-opus-4-6", "name": "Claude Opus 4", "description": "Most capable code model"},
        {"id": "us.anthropic.claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "description": "Balanced speed/quality"},
        {"id": "gpt-4o", "name": "GPT-4o", "description": "OpenAI flagship"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast, cost-effective"},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "description": "Best value for code"},
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "description": "Most capable"},
        {"id": "claude-haiku-3-5-20241022", "name": "Claude Haiku 3.5", "description": "Fastest, cheapest"},
    ],
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "description": "Flagship multimodal"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast, affordable"},
        {"id": "gpt-4.1", "name": "GPT-4.1", "description": "Latest code model"},
        {"id": "o3", "name": "o3", "description": "Reasoning model"},
    ],
    "gemini": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "Fast, cost-effective"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "Most capable Gemini"},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "description": "Legacy fast"},
    ],
}

# For backward compatibility — legacy env-only config
PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai_compatible": {
        "api_key": "LLM_API_KEY",
        "base_url": "OPENAI_BASE_URL",
        "default_model": "LLM_MODEL",
        "fallback_model": "LLM_FALLBACK_MODEL",
    },
    "anthropic": {
        "api_key": "ANTHROPIC_API_KEY",
        "default_model": "ANTHROPIC_MODEL",
    },
    "openai": {
        "api_key": "OPENAI_API_KEY",
        "default_model": "OPENAI_MODEL",
    },
    "gemini": {
        "api_key": "GEMINI_API_KEY",
        "default_model": "GEMINI_MODEL",
    },
}


def get_provider(provider_type: str | None = None, **overrides: str) -> BaseProvider:
    """Get a provider instance by type.

    Args:
        provider_type: One of: openai_compatible, anthropic, openai, gemini.
                       Defaults to LLM_PROVIDER env var, then openai_compatible.
        **overrides: Override specific config values (api_key, base_url, etc.)

    Returns:
        BaseProvider instance
    """
    provider_type = provider_type or os.getenv("LLM_PROVIDER", "openai_compatible")
    cls = PROVIDER_REGISTRY.get(provider_type)
    if not cls:
        logger.warning(f"Unknown provider '{provider_type}', falling back to openai_compatible")
        cls = OpenAICompatibleProvider

    # Build kwargs from env vars + overrides
    kwargs: dict[str, str] = {}
    defaults = PROVIDER_DEFAULTS.get(provider_type, {})

    for param, env_var in defaults.items():
        kwargs[param] = os.getenv(env_var, "")

    kwargs.update(overrides)

    return cls(**kwargs)


# ── Backward-compatible helpers ──────────────────────────────────────────────

def get_llm_config() -> dict[str, str]:
    """Get current LLM configuration from env vars."""
    provider_type = os.getenv("LLM_PROVIDER", "openai_compatible")
    return {
        "provider": provider_type,
        "base_url": os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "model": os.getenv("LLM_MODEL", "deepseek-v4-pro"),
        "fallback_model": os.getenv("LLM_FALLBACK_MODEL", "us.anthropic.claude-opus-4-6"),
    }


def get_client() -> Any:
    """Get sync OpenAI client (backward compat)."""
    from openai import OpenAI
    cfg = get_llm_config()
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])


def get_async_client() -> Any:
    """Get async OpenAI client (backward compat)."""
    from openai import AsyncOpenAI
    cfg = get_llm_config()
    return AsyncOpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])


async def llm_chat_async(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """Async chat completion using configured provider."""
    provider = get_provider()
    return await provider.chat(
        prompt, model=model, max_tokens=max_tokens,
        temperature=temperature, json_mode=json_mode,
    )


async def llm_chat_json_async(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Async chat completion returning parsed JSON."""
    provider = get_provider()
    return await provider.chat_json(
        prompt, model=model, max_tokens=max_tokens, temperature=temperature,
    )
