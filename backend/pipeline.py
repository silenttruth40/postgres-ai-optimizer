from __future__ import annotations

from typing import Any

from backend.database import ping
from gnn.inference import analyze_plan_graph
from ingestion.catalog import DEMO_QUERIES, get_demo_query
from optimizer.analyzer import analyze_plan
from optimizer.explainer import explain_recommendation
from privacy.anonymizer import Anonymizer, privacy_demo_pair
from rl.agent import get_agent
from rl.environment import state_from_plan
from sandbox.benchmark import benchmark_candidate
from sandbox.manager import list_indexes
from backend.database import get_connection

_STORE: dict[str, dict[str, Any]] = {}


def _sql_changed(query_id: str, sql: str | None) -> bool:
    if not sql:
        return False
    stored = _STORE.get(query_id, {}).get("sql")
    return bool(stored) and stored.strip() != sql.strip()


def list_queries() -> list[dict[str, Any]]:
    return [
        {
            "query_id": q.query_id,
            "title": q.title,
            "description": q.description,
            "problem_class": q.problem_class,
            "sql": q.sql,
        }
        for q in DEMO_QUERIES.values()
    ]


def _existing_indexes(sandbox: bool = False) -> list[tuple[str, tuple[str, ...]]]:
    try:
        with get_connection(sandbox=sandbox) as conn:
            return list_indexes(conn)
    except Exception:
        return []


def analyze_query(query_id: str, sql: str | None = None) -> dict[str, Any]:
    query = get_demo_query(query_id, sql)
    from ingestion.collector import collect

    collected = collect(query, sandbox=False)
    plan = collected["plan"]
    anonymizer = Anonymizer()
    anonymized_sql = anonymizer.anonymize_query(query.sql)
    anonymized_plan = anonymizer.anonymize_plan(plan.to_dict())
    bottlenecks, candidates = analyze_plan(query.sql, plan, _existing_indexes())
    try:
        gnn = analyze_plan_graph(plan)
    except Exception as exc:
        gnn = {"source": "Heuristic", "error": str(exc), "nodes": [], "edges": []}
    if gnn.get("source") == "GNN":
        for cand in candidates:
            if "GNN" not in cand.sources:
                cand.sources.append("GNN")
    agent = get_agent()
    state = state_from_plan(plan, query.sql, index_count=len(_existing_indexes()))
    ranked = agent.rank(candidates, state)
    payload = {
        "query_id": query.query_id,
        "title": query.title,
        "description": query.description,
        "sql": query.sql,
        "anonymized_sql": anonymized_sql,
        "metrics": plan.metrics.__dict__,
        "metrics_source": "Measured",
        "plan": plan.to_dict(),
        "anonymized_plan": anonymized_plan,
        "bottlenecks": [b.to_dict() for b in bottlenecks],
        "candidates": [c.to_dict() for c in ranked],
        "gnn": gnn,
        "privacy": anonymizer.stats(),
        "privacy_trace": anonymizer.privacy_verification_trace(query.sql),
        "postgres_ok": ping(False),
        "sandbox_ok": ping(True),
    }
    _STORE.setdefault(query.query_id, {})["analysis"] = payload
    _STORE[query.query_id]["ranked"] = ranked
    _STORE[query.query_id]["bottlenecks"] = bottlenecks
    _STORE[query.query_id]["anonymizer"] = anonymizer
    _STORE[query.query_id]["sql"] = query.sql
    return payload


def recommend_query(query_id: str, sql: str | None = None) -> dict[str, Any]:
    if query_id not in _STORE or "analysis" not in _STORE[query_id] or _sql_changed(query_id, sql):
        analyze_query(query_id, sql)
    analysis = _STORE[query_id]["analysis"]
    ranked = _STORE[query_id]["ranked"]
    return {"query_id": query_id, "candidates": [c.to_dict() for c in ranked], "analysis": analysis}


def benchmark_query(query_id: str, candidate_id: str | None = None, sql: str | None = None) -> dict[str, Any]:
    if query_id not in _STORE or "ranked" not in _STORE[query_id] or _sql_changed(query_id, sql):
        recommend_query(query_id, sql)
    ranked = _STORE[query_id]["ranked"]
    candidate = ranked[0]
    if candidate_id:
        candidate = next((c for c in ranked if c.candidate_id == candidate_id), ranked[0])
    sql_text = _STORE[query_id]["sql"]
    result = benchmark_candidate(sql_text, candidate.to_dict())
    if result.get("improvement_percent") is not None:
        if "Benchmark evidence" not in candidate.sources:
            candidate.sources.append("Benchmark evidence")
    explanation = explain_recommendation(
        query_id,
        _STORE[query_id]["bottlenecks"],
        candidate,
        _STORE[query_id].get("anonymizer"),
        result,
        sql_text,
    )
    payload = {
        "query_id": query_id,
        "candidate": candidate.to_dict(),
        "baseline": result.get("baseline"),
        "optimized": result.get("optimized"),
        "improvement_percent": result.get("improvement_percent"),
        "speedup_factor": result.get("speedup_factor", 1.0),
        "hit_diff": result.get("hit_diff", 0),
        "read_diff": result.get("read_diff", 0),
        "validation_status": result.get("validation_status"),
        "applied_to": result.get("applied_to"),
        "write_latency_overhead_ms": result.get("write_latency_overhead_ms", 0.0),
        "storage_overhead_mb": result.get("storage_overhead_mb", 0.0),
        "updated_sql": result.get("updated_sql") or candidate.rewritten_sql or candidate.sql,
        "error": result.get("error"),
        "explanation": explanation,
    }
    history = _STORE[query_id].setdefault("benchmarks", [])
    history.append(payload)
    _STORE[query_id]["latest_benchmark"] = payload
    return payload



def results_for(query_id: str) -> dict[str, Any]:
    data = _STORE.get(query_id)
    if not data:
        return {"query_id": query_id, "history": []}
    return {
        "query_id": query_id,
        "analysis": data.get("analysis"),
        "history": data.get("benchmarks", []),
        "latest": data.get("latest_benchmark"),
    }


def run_demo(query_id: str = "Q001") -> dict[str, Any]:
    analysis = analyze_query(query_id)
    recs = recommend_query(query_id)
    bench = benchmark_query(query_id, recs["candidates"][0]["candidate_id"] if recs["candidates"] else None)
    return {
        "query_id": query_id,
        "analysis": analysis,
        "recommendations": recs["candidates"],
        "benchmark": bench,
        "privacy_demo": privacy_demo_pair(),
    }
