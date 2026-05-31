"""Unified LLM client — OpenAI-compatible API gateway.

All LLM calls go through this module. Supports sync and async usage.
Primary model: deepseek-v4-pro (±10M tokens/min)
Fallback model: us.anthropic.claude-opus-4-6 (±20 RPM)

Env config:
  OPENAI_BASE_URL  — API endpoint (default: http://10.190.0.214:8080/v1)
  LLM_API_KEY      — Authentication key
  LLM_MODEL        — Primary model name (default: deepseek-v4-pro)
  LLM_FALLBACK_MODEL  — Fallback model (default: us.anthropic.claude-opus-4-6)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger(__name__)


# ── Config ──────────────────────────────────────────────────────────────────────

def get_llm_config() -> dict[str, str]:
    return {
        "base_url": os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "model": os.getenv("LLM_MODEL", "deepseek-v4-pro"),
        "fallback_model": os.getenv("LLM_FALLBACK_MODEL", "us.anthropic.claude-opus-4-6"),
    }


# ── Clients ─────────────────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    cfg = get_llm_config()
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])


def get_async_client() -> AsyncOpenAI:
    cfg = get_llm_config()
    return AsyncOpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])


# ── Sync helpers ────────────────────────────────────────────────────────────────

def llm_chat(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """Synchronous chat completion. Falls back to fallback_model on failure."""
    cfg = get_llm_config()
    client = get_client()
    model_name = model or cfg["model"]
    kwargs = {}

    try:
        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"[LLM] Primary model {model_name} failed: {e}")
        # Try fallback
        fallback = cfg["fallback_model"]
        if fallback and fallback != model_name:
            logger.info(f"[LLM] Falling back to {fallback}")
            try:
                kwargs["model"] = fallback
                resp = client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as e2:
                logger.error(f"[LLM] Fallback also failed: {e2}")
        raise


def llm_chat_json(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Sync chat completion that returns parsed JSON.
    Falls back to extracting JSON from text if json_mode fails.
    """
    try:
        raw = llm_chat(prompt, model=model, max_tokens=max_tokens, temperature=temperature, json_mode=True)
        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        # Fall back: try extracting JSON from text
        raw = llm_chat(prompt, model=model, max_tokens=max_tokens, temperature=temperature, json_mode=False)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not extract JSON from LLM response: {raw[:300]}")


# ── Async helpers ───────────────────────────────────────────────────────────────

async def llm_chat_async(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """Async chat completion. Falls back to fallback_model on failure."""
    cfg = get_llm_config()
    client = get_async_client()
    model_name = model or cfg["model"]
    kwargs = {}

    try:
        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"[LLM] Async primary model {model_name} failed: {e}")
        fallback = cfg["fallback_model"]
        if fallback and fallback != model_name:
            logger.info(f"[LLM] Async falling back to {fallback}")
            try:
                kwargs["model"] = fallback
                resp = await client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as e2:
                logger.error(f"[LLM] Async fallback also failed: {e2}")
        raise


async def llm_chat_json_async(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Async chat completion returning parsed JSON."""
    try:
        raw = await llm_chat_async(prompt, model=model, max_tokens=max_tokens, temperature=temperature, json_mode=True)
        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        raw = await llm_chat_async(prompt, model=model, max_tokens=max_tokens, temperature=temperature, json_mode=False)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not extract JSON from LLM response: {raw[:300]}")
