from fastapi import APIRouter, HTTPException

from backend.pipeline import recommend_query
from backend.schemas import RecommendRequest

router = APIRouter()


@router.post("/recommend")
def recommend(req: RecommendRequest):
    try:
        return recommend_query(req.query_id, req.sql)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Recommend failed: {exc}") from exc
