from fastapi import APIRouter, HTTPException

from backend.pipeline import benchmark_query, results_for, run_demo
from backend.schemas import BenchmarkRequest, DemoRequest
from privacy.anonymizer import privacy_demo_pair

router = APIRouter()


@router.post("/benchmark")
def benchmark(req: BenchmarkRequest):
    try:
        return benchmark_query(req.query_id, req.candidate_id, req.sql)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Benchmark failed: {exc}") from exc


@router.get("/results/{query_id}")
def results(query_id: str):
    return results_for(query_id)


@router.post("/demo/run")
def demo(req: DemoRequest = DemoRequest()):
    query_id = req.query_id
    try:
        return run_demo(query_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Demo failed: {exc}") from exc


@router.get("/privacy/demo")
def privacy_demo():
    return privacy_demo_pair()
