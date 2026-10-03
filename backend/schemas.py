from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query_id: str
    sql: str | None = None


class RecommendRequest(BaseModel):
    query_id: str
    sql: str | None = None


class BenchmarkRequest(BaseModel):
    query_id: str
    candidate_id: str | None = None
    sql: str | None = None


class DemoRequest(BaseModel):
    query_id: str = "Q001"


class QuerySummary(BaseModel):
    query_id: str
    title: str
    description: str
    problem_class: str
    sql: str


class BottleneckOut(BaseModel):
    type: str
    severity: str
    node: str
    relation: str | None = None
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class CandidateOut(BaseModel):
    candidate_id: str
    type: str
    table: str | None = None
    columns: list[str] = Field(default_factory=list)
    sql: str | None = None
    rewritten_sql: str | None = None
    reason: str
    confidence: float
    sources: list[str] = Field(default_factory=list)
    estimated: bool = True


class MetricsOut(BaseModel):
    execution_time_ms: float
    planning_time_ms: float
    rows: int
    shared_hit_blocks: int
    shared_read_blocks: int
    source: str = "Measured"


class BenchmarkOut(BaseModel):
    query_id: str
    candidate: CandidateOut
    baseline: MetricsOut
    optimized: MetricsOut | None = None
    improvement_percent: float | None = None
    validation_status: str
    applied_to: str = "sandbox"
    error: str | None = None
