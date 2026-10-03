import os
from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import get_settings
from backend.database import ping

router = APIRouter()


class GeminiConfigRequest(BaseModel):
    api_key: str
    model: str | None = None


class DatabaseSwitchRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 5432
    database: str
    user: str = "optimizer"
    password: str = ""
    sandbox_database: str | None = None


@router.get("/health")
def health():
    settings = get_settings()
    key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    return {
        "status": "ok",
        "postgres": ping(False),
        "sandbox": ping(True),
        "gemini": bool(key.strip()),
        "gemini_model": settings.gemini_model,
        "database": settings.postgres_db,
        "host": settings.postgres_host,
        "port": settings.postgres_port,
    }


@router.get("/config/database")
def get_database():
    settings = get_settings()
    from sandbox.manager import discover_tables
    from backend.database import get_connection

    tables = []
    try:
        with get_connection(sandbox=False) as conn:
            tables = discover_tables(conn)
    except Exception:
        pass

    return {
        "status": "connected" if ping(False) else "disconnected",
        "host": settings.postgres_host,
        "port": settings.postgres_port,
        "database": settings.postgres_db,
        "user": settings.postgres_user,
        "sandbox_database": settings.sandbox_postgres_db,
        "tables": tables,
        "table_count": len(tables),
    }


@router.post("/config/database")
def switch_database(req: DatabaseSwitchRequest):
    import psycopg
    from fastapi import HTTPException
    from sandbox.manager import discover_tables

    parts = [
        f"host={req.host.strip()}",
        f"port={req.port}",
        f"dbname={req.database.strip()}",
        f"user={req.user.strip()}",
        "connect_timeout=5",
    ]
    if req.password:
        parts.append(f"password={req.password}")
    dsn = " ".join(parts)

    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            tables = discover_tables(conn)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Database connection error: {exc}")

    # Update environment & settings
    os.environ["POSTGRES_HOST"] = req.host.strip()
    os.environ["POSTGRES_PORT"] = str(req.port)
    os.environ["POSTGRES_DB"] = req.database.strip()
    os.environ["POSTGRES_USER"] = req.user.strip()
    os.environ["POSTGRES_PASSWORD"] = req.password

    sb_db = req.sandbox_database.strip() if req.sandbox_database else req.database.strip()
    os.environ["SANDBOX_POSTGRES_HOST"] = req.host.strip()
    os.environ["SANDBOX_POSTGRES_PORT"] = str(req.port)
    os.environ["SANDBOX_POSTGRES_DB"] = sb_db
    os.environ["SANDBOX_POSTGRES_USER"] = req.user.strip()
    os.environ["SANDBOX_POSTGRES_PASSWORD"] = req.password

    get_settings.cache_clear()
    settings = get_settings()

    return {
        "status": "connected",
        "host": settings.postgres_host,
        "port": settings.postgres_port,
        "database": settings.postgres_db,
        "user": settings.postgres_user,
        "sandbox_database": settings.sandbox_postgres_db,
        "tables": tables,
        "table_count": len(tables),
    }


@router.post("/config/gemini")
def set_gemini_key(req: GeminiConfigRequest):
    cleaned_key = req.api_key.strip()
    os.environ["GEMINI_API_KEY"] = cleaned_key
    if req.model and req.model.strip():
        os.environ["GEMINI_MODEL"] = req.model.strip()
    get_settings.cache_clear()
    settings = get_settings()
    settings.gemini_api_key = cleaned_key
    if req.model and req.model.strip():
        settings.gemini_model = req.model.strip()
    return {
        "status": "ok",
        "gemini": bool(cleaned_key),
        "gemini_model": settings.gemini_model,
    }
