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
    llm_model: str
    llm_fallback_model: str
    llm_base_url: str
    pipeline_timeout: int
    stage_timeout: int
    max_retry_count: int
    git_auto_push: bool
    webhook_url: str
    webhook_events: str


class SettingsUpdate(BaseModel):
    """Settings update payload (all fields optional)."""
    llm_model: str | None = None
    llm_fallback_model: str | None = None
    llm_base_url: str | None = None
    pipeline_timeout: int | None = None
    stage_timeout: int | None = None
    max_retry_count: int | None = None
    git_auto_push: bool | None = None
    webhook_url: str | None = None
    webhook_events: str | None = None


# Mapping from settings field names to environment variable names
_SETTINGS_ENV_MAP = {
    "llm_model": "LLM_MODEL",
    "llm_fallback_model": "LLM_FALLBACK_MODEL",
    "llm_base_url": "OPENAI_BASE_URL",
    "pipeline_timeout": "PIPELINE_TIMEOUT",
    "stage_timeout": "STAGE_TIMEOUT",
    "max_retry_count": "MAX_RETRY_COUNT",
    "git_auto_push": "GIT_AUTO_PUSH",
    "webhook_url": "WEBHOOK_URL",
    "webhook_events": "WEBHOOK_EVENTS",
}


@router.get("/settings")
async def get_settings() -> SettingsResponse:
    """
    Get current factory settings.

    Returns:
        SettingsResponse: All configurable settings with current values
    """
    return SettingsResponse(
        llm_model=os.getenv("LLM_MODEL", "deepseek-chat"),
        llm_fallback_model=os.getenv("LLM_FALLBACK_MODEL", "us.anthropic.claude-opus-4-6"),
        llm_base_url=os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1"),
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
async def list_available_models() -> list[dict[str, str]]:
    """
    List available LLM models.

    Returns a curated list of models known to work with the internal gateway.
    """
    return [
        {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek", "description": "Fast, good for code generation"},
        {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "provider": "deepseek", "description": "Reasoning-focused model"},
        {"id": "us.anthropic.claude-opus-4-6", "name": "Claude Opus 4", "provider": "anthropic", "description": "Most capable, best code quality"},
        {"id": "us.anthropic.claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "provider": "anthropic", "description": "Balanced speed/quality"},
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "description": "OpenAI flagship multimodal"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "description": "Fast and cost-effective"},
    ]


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
