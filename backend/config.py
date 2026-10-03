from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "optimizer"
    postgres_user: str = "optimizer"
    postgres_password: str = "optimizer"

    sandbox_postgres_host: str = "localhost"
    sandbox_postgres_port: int = 5433
    sandbox_postgres_db: str = "optimizer_sandbox"
    sandbox_postgres_user: str = "optimizer"
    sandbox_postgres_password: str = "optimizer"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"

    streamlit_port: int = 8501
    demo_scale: str = "small"
    demo_seed: int = 42
    benchmark_timeout_seconds: int = 90
    benchmark_repeat: int = 1
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"


    def dsn(self, sandbox: bool = False) -> str:
        if sandbox:
            parts = [
                f"host={self.sandbox_postgres_host}",
                f"port={self.sandbox_postgres_port}",
                f"dbname={self.sandbox_postgres_db}",
                f"user={self.sandbox_postgres_user}",
                "connect_timeout=5",
            ]
            if self.sandbox_postgres_password:
                parts.append(f"password={self.sandbox_postgres_password}")
            return " ".join(parts)
        parts = [
            f"host={self.postgres_host}",
            f"port={self.postgres_port}",
            f"dbname={self.postgres_db}",
            f"user={self.postgres_user}",
            "connect_timeout=5",
        ]
        if self.postgres_password:
            parts.append(f"password={self.postgres_password}")
        return " ".join(parts)


@lru_cache
def get_settings() -> Settings:
    return Settings()
