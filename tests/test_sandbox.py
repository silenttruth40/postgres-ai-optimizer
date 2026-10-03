from sandbox.manager import validate_candidate
from sandbox.benchmark import benchmark_candidate

import pytest


def test_invalid_index_is_rejected():
    with pytest.raises(ValueError):
        validate_candidate(
            {
                "type": "CREATE_INDEX",
                "table": "pg_shadow",
                "columns": ["passwd"],
                "sql": "CREATE INDEX IF NOT EXISTS idx_bad ON pg_shadow (passwd)",
            }
        )


def test_partition_is_not_auto_applied():
    with pytest.raises(ValueError):
        validate_candidate({"type": "PARTITION", "table": "orders"})


def test_benchmark_no_change_without_postgres(monkeypatch):
    class DummyMetrics:
        execution_time_ms = 10.0
        planning_time_ms = 1.0
        rows = 3
        shared_hit_blocks = 1
        shared_read_blocks = 0

    class DummyPlan:
        metrics = DummyMetrics()

    monkeypatch.setattr("sandbox.benchmark.run_query_metrics", lambda sql, sandbox=False: DummyPlan())
    result = benchmark_candidate("SELECT 1", {"type": "NO_CHANGE"})
    assert result["validation_status"] == "NO_CHANGE"
    assert result["improvement_percent"] == 0.0
    assert result["baseline"]["source"] == "Measured"
