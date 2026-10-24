"""Runtime configuration, read from environment variables and a local .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    gemini_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    agent_provider: Literal["gemini", "groq"] = "gemini"
    agent_model: str = ""  # empty = provider default

    search_backend: Literal["local", "live", "replay"] = "local"
    rail_rag_data_dir: Path = REPO_ROOT.parent / "rail-regulation-rag" / "data"
    rail_api_url: str = "https://rail-rag.calmcliff-0073b8b6.switzerlandnorth.azurecontainerapps.io"
    search_cache_dir: Path = REPO_ROOT / "eval" / ".cache" / "search"

    def api_key(self, provider: str) -> str:
        secret = getattr(self, f"{provider}_api_key", None)
        return secret.get_secret_value() if secret else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
