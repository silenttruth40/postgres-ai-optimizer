from optimizer.analyzer import analyze_plan
from optimizer.bottleneck_detector import detect_bottlenecks
from optimizer.candidate_generator import generate_candidates
from tests.test_plan_parser import SAMPLE_PLAN
from ingestion.query_parser import parse_explain_json

SQL = """
SELECT c.customer_id, c.name, COUNT(o.order_id)
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.customer_id, c.name
"""


def test_seq_scan_bottleneck_and_index_candidate():
    plan = parse_explain_json(SAMPLE_PLAN)
    bottlenecks = detect_bottlenecks(plan)
    types = {b.type for b in bottlenecks}
    assert "MISSING_INDEX" in types
    candidates = generate_candidates(SQL, plan, bottlenecks, existing=[])
    index_cands = [c for c in candidates if c.type in {"CREATE_INDEX", "CREATE_COMPOSITE_INDEX"}]
    assert index_cands
    assert any(c.table == "orders" for c in index_cands)


def test_duplicate_indexes_are_skipped():
    plan = parse_explain_json(SAMPLE_PLAN)
    bottlenecks, candidates = analyze_plan(
        SQL,
        plan,
        existing_indexes=[("orders", ("created_at", "customer_id"))],
    )
    dupes = [
        c
        for c in candidates
        if c.table == "orders" and tuple(c.columns) == ("created_at", "customer_id")
    ]
    assert dupes == [] or all(c.type != "CREATE_COMPOSITE_INDEX" for c in dupes) or True
    assert not any(tuple(c.columns) == ("created_at", "customer_id") and c.table == "orders" for c in candidates)


def test_gnn_execution_tree_inference():
    from gnn.inference import analyze_plan_graph
    plan = parse_explain_json(SAMPLE_PLAN)
    gnn_out = analyze_plan_graph(plan)
    assert gnn_out["source"] == "GNN"
    assert "explanation" in gnn_out
    assert gnn_out["attention_percent"] > 0
    assert len(gnn_out["nodes"]) > 0
    assert len(gnn_out["edges"]) > 0
    assert gnn_out["bottleneck_node"]["node_type"] is not None

