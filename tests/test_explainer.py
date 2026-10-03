from optimizer.bottleneck_detector import Bottleneck
from optimizer.candidate_generator import Candidate
from optimizer.explainer import _build_prompt, _extract_gemini_text, explain_recommendation
from privacy.anonymizer import Anonymizer


def _candidate(**kwargs) -> Candidate:
    defaults = dict(
        candidate_id="C001",
        type="CREATE_INDEX",
        table="orders",
        columns=["customer_id", "created_at"],
        sql="CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at)",
        reason="Sequential scan on orders filtered by customer and date",
    )
    defaults.update(kwargs)
    return Candidate(**defaults)


def _bottlenecks() -> list[Bottleneck]:
    return [
        Bottleneck(
            type="MISSING_INDEX",
            severity="HIGH",
            node="Seq Scan",
            relation="orders",
            reason="Large filtered table scanned sequentially",
            evidence={"actual_rows": 12000},
        )
    ]


def test_prompts_differ_across_queries():
    sql_a = "SELECT * FROM orders WHERE customer_id = 42"
    sql_b = "SELECT customer_id, email FROM customers WHERE email = 'a@b.com'"
    prompt_a = _build_prompt(
        "Q001",
        _bottlenecks(),
        _candidate(),
        Anonymizer(),
        {"improvement_percent": 20},
        sql_a,
    )
    prompt_b = _build_prompt(
        "Q002",
        [
            Bottleneck(
                type="SEQ_SCAN",
                severity="MEDIUM",
                node="Seq Scan",
                relation="customers",
                reason="Unindexed equality filter on email",
                evidence={},
            )
        ],
        _candidate(
            table="customers",
            columns=["email"],
            sql="CREATE INDEX idx_customers_email ON customers (email)",
        ),
        Anonymizer(),
        {"improvement_percent": 55},
        sql_b,
    )
    assert prompt_a != prompt_b
    assert "42" not in prompt_a
    assert "a@b.com" not in prompt_b


def test_extract_gemini_text_skips_thought_only_parts():
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"thoughtSignature": "abc"},
                        {"text": "Use an index on table_002."},
                    ]
                },
                "finishReason": "STOP",
            }
        ]
    }
    assert _extract_gemini_text(data) == "Use an index on table_002."


def test_explainer_uses_gemini_when_http_succeeds(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Index table_002(column_001) to avoid the sequential scan."}
                            ]
                        }
                    }
                ]
            }

    from backend.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    get_settings.cache_clear()

    def fake_post(*args, **kwargs):
        assert "x-goog-api-key" in kwargs.get("headers", {})
        assert "generateContent" in args[0]
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    out = explain_recommendation(
        "Q001",
        _bottlenecks(),
        _candidate(),
        Anonymizer(),
        {"improvement_percent": 33.0, "validation_status": "VALIDATED"},
        sql="SELECT * FROM orders WHERE customer_id = 1",
    )
    assert "gemini" in out["engine"]
    assert "orders" in out["text"]
    assert out["gemini_error"] is None
    get_settings.cache_clear()
