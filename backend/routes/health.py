import os
from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import get_settings
from backend.database import ping

router = APIRouter()


class GeminiConfigRequest(BaseModel):
    api_key: str
    model: str | None = None


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
    }


@router.post("/config/gemini")
def set_gemini_key(req: GeminiConfigRequest):
    cleaned_key = req.api_key.strip()
    os.environ["GEMINI_API_KEY"] = cleaned_key
    settings = get_settings()
    settings.gemini_api_key = cleaned_key
    if req.model:
        settings.gemini_model = req.model.strip()
    return {
        "status": "ok",
        "gemini": bool(cleaned_key),
        "gemini_model": settings.gemini_model,
    }
