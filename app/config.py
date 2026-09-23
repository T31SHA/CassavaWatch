"""Runtime settings from environment variables (and an optional, never-committed .env)."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    qwen_base_url: str = "https://api-inference.modelscope.ai/v1"
    qwen_api_key: str = ""
    qwen_model: str = "Qwen-Ambassador/Qwen3.7-Max"
    qwen_timeout_s: float = 8.0
    advisory_mode: Optional[str] = None  # "template" | "llm"; default: llm iff a key is set

    database_url: Optional[str] = None
    seed_demo_data: bool = False
    model_url: Optional[str] = None

    @property
    def effective_advisory_mode(self) -> str:
        if not self.qwen_api_key.strip():
            return "template"
        return self.advisory_mode if self.advisory_mode in ("template", "llm") else "llm"


@lru_cache
def get_settings() -> Settings:
    return Settings()
