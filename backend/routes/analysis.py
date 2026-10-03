from fastapi import APIRouter, HTTPException

from backend.pipeline import analyze_query
from backend.schemas import AnalyzeRequest

router = APIRouter()


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        return analyze_query(req.query_id, req.sql)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Analysis failed: {exc}") from exc
