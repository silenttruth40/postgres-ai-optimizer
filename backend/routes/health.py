from fastapi import APIRouter

from backend.database import ping

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "postgres": ping(False),
        "sandbox": ping(True),
    }
