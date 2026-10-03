from ingestion.query_parser import parse_explain_json

SAMPLE_PLAN = {
    "Planning Time": 0.4,
    "Execution Time": 120.5,
    "Plan": {
        "Node Type": "Aggregate",
        "Actual Total Time": 120.5,
        "Actual Rows": 10,
        "Plan Rows": 10,
        "Total Cost": 200,
        "Shared Hit Blocks": 10,
        "Shared Read Blocks": 40,
        "Plans": [
            {
                "Node Type": "Hash Join",
                "Actual Total Time": 110.0,
                "Actual Rows": 10000,
                "Plan Rows": 800,
                "Total Cost": 180,
                "Join Type": "Inner",
                "Hash Cond": "(c.customer_id = o.customer_id)",
                "Shared Hit Blocks": 4,
                "Shared Read Blocks": 20,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "customers",
                        "Actual Total Time": 12.0,
                        "Actual Rows": 5000,
                        "Plan Rows": 5000,
                        "Total Cost": 40,
                        "Shared Hit Blocks": 2,
                        "Shared Read Blocks": 8,
                    },
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "orders",
                        "Filter": "(created_at >= CURRENT_DATE - '30 days')",
                        "Actual Total Time": 80.0,
                        "Actual Rows": 250000,
                        "Plan Rows": 1000,
                        "Total Cost": 90,
                        "Shared Hit Blocks": 1,
                        "Shared Read Blocks": 30,
                    },
                ],
            }
        ],
    },
}


def test_nested_plans_parsed():
    parsed = parse_explain_json(SAMPLE_PLAN)
    nodes = parsed.root.flatten()
    types = {n.node_type for n in nodes}
    assert "Hash Join" in types
    assert "Seq Scan" in types
    assert parsed.metrics.execution_time_ms == 120.5
    orders = next(n for n in nodes if n.relation == "orders")
    assert orders.actual_rows == 250000
    assert orders.actual_time == 80.0
    assert parsed.metrics.seq_scans == 2
    assert orders.estimation_error > 10
