from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_queries():
    response = client.get("/queries")
    assert response.status_code == 200
    body = response.json()
    assert any(item["query_id"] == "Q001" for item in body)


def test_analyze_unknown_query():
    response = client.post("/analyze", json={"query_id": "NOPE"})
    assert response.status_code in {404, 503}


def test_recommend_and_results_shape(monkeypatch):
    sample = {
        "query_id": "Q001",
        "candidates": [{"candidate_id": "C001", "type": "CREATE_INDEX", "sources": ["Heuristic"]}],
        "analysis": {"query_id": "Q001", "bottlenecks": []},
    }
    monkeypatch.setattr("backend.routes.recommendations.recommend_query", lambda query_id, sql=None: sample)
    response = client.post("/recommend", json={"query_id": "Q001"})
    assert response.status_code == 200
    assert response.json()["candidates"][0]["candidate_id"] == "C001"

    monkeypatch.setattr(
        "backend.routes.benchmarks.results_for",
        lambda query_id: {"query_id": query_id, "history": []},
    )
    response = client.get("/results/Q001")
    assert response.status_code == 200
    assert response.json()["query_id"] == "Q001"


def test_benchmark_endpoint_mocked(monkeypatch):
    payload = {
        "query_id": "Q001",
        "candidate": {"candidate_id": "C001", "type": "CREATE_INDEX"},
        "baseline": {"execution_time_ms": 10, "source": "Measured"},
        "optimized": {"execution_time_ms": 4, "source": "Measured"},
        "improvement_percent": 60.0,
        "validation_status": "VALIDATED",
    }
    monkeypatch.setattr(
        "backend.routes.benchmarks.benchmark_query",
        lambda query_id, candidate_id=None, sql=None: payload,
    )
    response = client.post("/benchmark", json={"query_id": "Q001", "candidate_id": "C001"})
    assert response.status_code == 200
    assert response.json()["validation_status"] == "VALIDATED"


def test_custom_query_analysis_endpoint(monkeypatch):
    custom_sql = "SELECT customer_id, name FROM customers WHERE customer_id = 99"
    sample = {
        "query_id": "custom",
        "sql": custom_sql,
        "anonymized_sql": "SELECT column_001, column_002 FROM table_001 WHERE column_001 = <REDACTED>",
        "bottlenecks": [],
        "candidates": [],
        "gnn": {"source": "GNN"},
    }
    monkeypatch.setattr("backend.routes.analysis.analyze_query", lambda query_id, sql=None: sample)
    response = client.post("/analyze", json={"query_id": "custom", "sql": custom_sql})
    assert response.status_code == 200
    data = response.json()
    assert data["query_id"] == "custom"
    assert data["sql"] == custom_sql
    assert "column_001" in data["anonymized_sql"]


def test_set_gemini_config():
    response = client.post("/config/gemini", json={"api_key": "test_dummy_key", "model": "gemini-1.5-flash"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["gemini"] is True

