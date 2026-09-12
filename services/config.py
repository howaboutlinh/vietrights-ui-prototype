"""Environment-backed configuration for VietRights RAG services."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(RuntimeError):
    """Raised when a service is missing required server-side configuration."""


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number.") from exc


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Secrets remain server-side and are never serialized."""

    gemini_api_key: str = ""
    chat_model: str = "gemini-3.8-flash"
    embedding_model: str = "gemini-embedding-001"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""
    match_count: int = 6
    match_threshold: float = 0.60
    embedding_dimension: int = 768
    request_timeout_seconds: int = 30
    crawl_max_depth: int = 2
    crawl_max_pages: int = 40

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            chat_model=os.getenv("GEMINI_CHAT_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash")).strip(),
            embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001").strip(),
            supabase_url=os.getenv("SUPABASE_URL", "").strip(),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
            database_url=os.getenv("DATABASE_URL", "").strip(),
            match_count=_int_env("RAG_MATCH_COUNT", 6),
            match_threshold=_float_env("RAG_MATCH_THRESHOLD", 0.60),
            embedding_dimension=_int_env("EMBEDDING_DIMENSION", 768),
            request_timeout_seconds=_int_env("HTTP_REQUEST_TIMEOUT_SECONDS", 30),
            crawl_max_depth=_int_env("CRAWL_MAX_DEPTH", 2),
            crawl_max_pages=_int_env("CRAWL_MAX_PAGES", 40),
        )

    def validate(self, fields: Iterable[str]) -> None:
        missing = [name for name in fields if not getattr(self, name, "")]
        if missing:
            env_names = {
                "gemini_api_key": "GEMINI_API_KEY",
                "supabase_url": "SUPABASE_URL",
                "supabase_service_role_key": "SUPABASE_SERVICE_ROLE_KEY",
                "database_url": "DATABASE_URL",
            }
            labels = ", ".join(env_names.get(name, name) for name in missing)
            raise ConfigurationError(f"Missing required environment variable(s): {labels}")
        if self.embedding_dimension != 768:
            raise ConfigurationError("EMBEDDING_DIMENSION must be 768 to match the database migration.")


def knowledge_sources() -> list[str]:
    """Return exactly four configured, non-empty knowledge-source roots."""
    values = [os.getenv(f"KNOWLEDGE_SOURCE_{index}", "").strip() for index in range(1, 5)]
    missing = [str(index) for index, value in enumerate(values, start=1) if not value]
    if missing:
        raise ConfigurationError(f"Missing KNOWLEDGE_SOURCE_{', KNOWLEDGE_SOURCE_'.join(missing)}")
    if len(set(values)) != 4:
        raise ConfigurationError("KNOWLEDGE_SOURCE_1 through KNOWLEDGE_SOURCE_4 must be four distinct URLs.")
    return values
