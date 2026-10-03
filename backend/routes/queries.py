from fastapi import APIRouter, HTTPException

from backend.pipeline import list_queries
from ingestion.catalog import DEMO_QUERIES

router = APIRouter()


@router.get("/queries")
def queries():
    return list_queries()


@router.get("/queries/{query_id}")
def query_detail(query_id: str):
    if query_id not in DEMO_QUERIES:
        raise HTTPException(status_code=404, detail="Unknown query_id")
    q = DEMO_QUERIES[query_id]
    return {
        "query_id": q.query_id,
        "title": q.title,
        "description": q.description,
        "problem_class": q.problem_class,
        "sql": q.sql,
    }
