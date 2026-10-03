from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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

    def dsn(self, sandbox: bool = False) -> str:
        if sandbox:
            return (
                f"host={self.sandbox_postgres_host} port={self.sandbox_postgres_port} "
                f"dbname={self.sandbox_postgres_db} user={self.sandbox_postgres_user} "
                f"password={self.sandbox_postgres_password} connect_timeout=3"
            )
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password} connect_timeout=3"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
