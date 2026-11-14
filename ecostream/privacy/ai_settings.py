"""AI Provider Configuration & BYOK (Bring Your Own Key) Manager for EcoStream.

Allows users to plug in free tier LLM keys (Google Gemini 1.5/2.0 Flash) or OpenAI/Ollama
with local persistence in ~/.ecostream/ai_config.json (or fallback to ./runs/ai_config.json).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

PRIMARY_CONFIG_DIR = Path.home() / ".ecostream"
FALLBACK_CONFIG_DIR = Path(__file__).resolve().parents[2] / "runs"


def _get_active_config_path() -> Path:
    """Return writable config file path."""
    try:
        PRIMARY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return PRIMARY_CONFIG_DIR / "ai_config.json"
    except (PermissionError, OSError):
        FALLBACK_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return FALLBACK_CONFIG_DIR / "ai_config.json"


def get_ai_config() -> Dict[str, Any]:
    """Retrieve saved AI configuration, with fallback to environment variables."""
    default_config = {
        "provider": os.environ.get("ECOSTREAM_AI_PROVIDER", "offline"),  # gemini, openai, ollama, offline
        "api_key": os.environ.get("OPENAI_API_KEY", os.environ.get("GEMINI_API_KEY", "")),
        "base_url": os.environ.get("OPENAI_BASE_URL", ""),
        "model": os.environ.get("LLM_MODEL", ""),
        "configured": False,
    }

    config_path = _get_active_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_config.update(saved)
        except Exception:
            pass

    provider = default_config.get("provider", "offline")
    api_key = default_config.get("api_key", "")
    if provider in ("gemini", "openai") and api_key:
        default_config["configured"] = True
    elif provider == "ollama":
        default_config["configured"] = True

    return default_config


def save_ai_config(
    provider: str,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> Dict[str, Any]:
    """Save AI configuration locally on user machine."""
    config_path = _get_active_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    provider = provider.lower().strip()
    clean_key = api_key.strip()

    if provider == "gemini":
        default_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        default_model = model or "gemini-1.5-flash"
    elif provider == "openai":
        default_url = "https://api.openai.com/v1"
        default_model = model or "gpt-4o-mini"
    elif provider == "ollama":
        default_url = base_url or "http://127.0.0.1:11434/v1"
        default_model = model or "qwen2.5:7b"
        clean_key = "ollama-local"
    else:
        provider = "offline"
        default_url = ""
        default_model = ""

    config = {
        "provider": provider,
        "api_key": clean_key,
        "base_url": base_url or default_url,
        "model": default_model,
        "configured": bool(clean_key or provider == "ollama"),
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return config


def mask_key(key: str) -> str:
    """Mask key for display in UI (e.g. AIzaSy...9xAB)."""
    if not key or len(key) < 8:
        return ""
    return f"{key[:6]}...{key[-4:]}"
