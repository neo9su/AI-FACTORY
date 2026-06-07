"""
Settings API for runtime configuration.

Allows reading and updating factory settings without restarting the server.
Settings are stored as environment variables and persisted to .env file.
"""
import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SettingsResponse(BaseModel):
    """Current factory settings."""
    llm_provider: str
    llm_model: str
    llm_fallback_model: str
    llm_base_url: str
    llm_api_key: str  # masked
    llm_anthropic_key: str  # masked
    llm_openai_key: str  # masked
    llm_gemini_key: str  # masked
    pipeline_timeout: int
    stage_timeout: int
    max_retry_count: int
    git_auto_push: bool
    webhook_url: str
    webhook_events: str


class SettingsUpdate(BaseModel):
    """Settings update payload (all fields optional)."""
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_fallback_model: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_anthropic_key: str | None = None
    llm_openai_key: str | None = None
    llm_gemini_key: str | None = None
    pipeline_timeout: int | None = None
    stage_timeout: int | None = None
    max_retry_count: int | None = None
    git_auto_push: bool | None = None
    webhook_url: str | None = None
    webhook_events: str | None = None


# Mapping from settings field names to environment variable names
_SETTINGS_ENV_MAP = {
    "llm_provider": "LLM_PROVIDER",
    "llm_model": "LLM_MODEL",
    "llm_fallback_model": "LLM_FALLBACK_MODEL",
    "llm_base_url": "OPENAI_BASE_URL",
    "llm_api_key": "LLM_API_KEY",
    "llm_anthropic_key": "ANTHROPIC_API_KEY",
    "llm_openai_key": "OPENAI_API_KEY",
    "llm_gemini_key": "GEMINI_API_KEY",
    "pipeline_timeout": "PIPELINE_TIMEOUT",
    "stage_timeout": "STAGE_TIMEOUT",
    "max_retry_count": "MAX_RETRY_COUNT",
    "git_auto_push": "GIT_AUTO_PUSH",
    "webhook_url": "WEBHOOK_URL",
    "webhook_events": "WEBHOOK_EVENTS",
}


@router.get("/settings")
async def get_settings() -> SettingsResponse:
    """Get current factory settings.

    API keys are masked in the response (show first 8 chars only).
    Returns:
        SettingsResponse: All configurable settings with current values
    """
    def _mask(key: str) -> str:
        if not key or len(key) < 12:
            return ""
        return key[:8] + "****"

    return SettingsResponse(
        llm_provider=os.getenv("LLM_PROVIDER", "openai_compatible"),
        llm_model=os.getenv("LLM_MODEL", "deepseek-v4-pro"),
        llm_fallback_model=os.getenv("LLM_FALLBACK_MODEL", "us.anthropic.claude-opus-4-6"),
        llm_base_url=os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1"),
        llm_api_key=_mask(os.getenv("LLM_API_KEY", "")),
        llm_anthropic_key=_mask(os.getenv("ANTHROPIC_API_KEY", "")),
        llm_openai_key=_mask(os.getenv("OPENAI_API_KEY", "")),
        llm_gemini_key=_mask(os.getenv("GEMINI_API_KEY", "")),
        pipeline_timeout=int(os.getenv("PIPELINE_TIMEOUT", "600")),
        stage_timeout=int(os.getenv("STAGE_TIMEOUT", "180")),
        max_retry_count=int(os.getenv("MAX_RETRY_COUNT", "3")),
        git_auto_push=os.getenv("GIT_AUTO_PUSH", "false").lower() == "true",
        webhook_url=os.getenv("WEBHOOK_URL", ""),
        webhook_events=os.getenv("WEBHOOK_EVENTS", ""),
    )


@router.put("/settings")
async def update_settings(updates: SettingsUpdate) -> dict[str, Any]:
    """
    Update factory settings at runtime.

    Updates environment variables in-process. For persistence across restarts,
    also writes to .env file.

    Args:
        updates: Settings to update (only non-None fields are applied)

    Returns:
        dict: Updated settings and confirmation
    """
    changes = {}

    for field_name, env_var in _SETTINGS_ENV_MAP.items():
        value = getattr(updates, field_name)
        if value is not None:
            # Convert to string for env var
            if isinstance(value, bool):
                str_value = "true" if value else "false"
            else:
                str_value = str(value)

            os.environ[env_var] = str_value
            changes[field_name] = str_value

    # Persist to .env file
    if changes:
        _persist_to_env_file(changes)

    return {
        "updated": changes,
        "message": f"Updated {len(changes)} setting(s)",
    }


@router.get("/settings/models")
async def list_available_models() -> dict[str, list[dict[str, str]]]:
    """List available LLM models grouped by provider.

    Returns:
        dict: provider -> list of {id, name, description}
    """
    from backend.core.llm import PROVIDER_MODELS

    return {
        "providers": [
            {
                "id": "openai_compatible",
                "name": "OpenAI 兼容",
                "description": "通过网关访问 DeepSeek / Claude / GPT 等",
                "models": PROVIDER_MODELS.get("openai_compatible", []),
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "description": "直接访问 Claude API",
                "models": PROVIDER_MODELS.get("anthropic", []),
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "description": "直接访问 OpenAI API",
                "models": PROVIDER_MODELS.get("openai", []),
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "description": "直接访问 Gemini API",
                "models": PROVIDER_MODELS.get("gemini", []),
            },
        ]
    }


@router.post("/settings/test-model")
async def test_model_connection(
    data: dict[str, str],
) -> dict[str, str]:
    """Test connection to a specific model/provider.

    Body:
        provider: Provider type (openai_compatible, anthropic, openai, gemini)
        model: Model ID to test
        api_key: Optional override API key
        base_url: Optional override base URL (for openai_compatible)

    Returns:
        dict: {status: "ok"|"error", message: ..., model: ...}
    """
    from backend.core.llm import get_provider

    provider_type = data.get("provider", "openai_compatible")
    model = data.get("model", "")
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "")

    overrides: dict[str, str] = {}
    if api_key and api_key != "****":
        overrides["api_key"] = api_key
    if base_url:
        overrides["base_url"] = base_url

    try:
        provider = get_provider(provider_type, **overrides)
        result = await provider.test_connection()
        return {
            "status": "ok",
            "message": f"✅ Connected to {result.get('model', model)} via {provider_type}",
            "model": model or result.get("model", ""),
        }
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower() or "api key" in error_msg.lower():
            return {"status": "error", "message": f"❌ API Key 无效或未配置: {error_msg[:100]}", "model": model}
        if "connect" in error_msg.lower() or "timeout" in error_msg.lower():
            return {"status": "error", "message": f"❌ 无法连接到服务: {error_msg[:100]}", "model": model}
        return {"status": "error", "message": f"❌ {error_msg[:200]}", "model": model}


def _persist_to_env_file(changes: dict[str, str]) -> None:
    """
    Persist environment variable changes to .env file.

    Reads existing .env, updates changed values, writes back.
    """
    from pathlib import Path

    env_path = Path(".env")
    existing_lines: list[str] = []

    if env_path.exists():
        existing_lines = env_path.read_text().splitlines()

    # Build env var -> line index mapping
    env_map: dict[str, int] = {}
    for i, line in enumerate(existing_lines):
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            env_map[key] = i

    # Apply changes
    for field_name, str_value in changes.items():
        env_var = _SETTINGS_ENV_MAP.get(field_name, "")
        if not env_var:
            continue

        new_line = f"{env_var}={str_value}"

        if env_var in env_map:
            existing_lines[env_map[env_var]] = new_line
        else:
            existing_lines.append(new_line)

    # Write back
    env_path.write_text("\n".join(existing_lines) + "\n")
