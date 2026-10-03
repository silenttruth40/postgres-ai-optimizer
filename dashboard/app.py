from __future__ import annotations

import streamlit as st

from dashboard.api_client import APIError, OptimizerClient
from dashboard.components import CSS, bottleneck_cards, candidate_card, kpi_row

st.set_page_config(
    page_title="PostgreSQL AI Optimizer",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

client = OptimizerClient()

st.markdown(
    """
<div class="hero">
  <h1>AI-Powered PostgreSQL Performance Optimizer</h1>
  <p>Privacy-preserving intelligent query optimization</p>
</div>
""",
    unsafe_allow_html=True,
)

try:
    health = client.health()
except APIError as exc:
    st.error(f"Backend unavailable. Start FastAPI / docker compose first. {exc}")
    st.stop()

status = "ok" if health.get("status") == "ok" else "degraded"

st.caption(
    f"API {status} · demo DB {'up' if health.get('postgres') else 'down'} · "
    f"sandbox {'up' if health.get('sandbox') else 'down'}"
)

try:
    queries = client.queries()
except APIError as exc:
    st.error(str(exc))
    st.stop()

ids = [q["query_id"] for q in queries]
labels = {
    q["query_id"]: f"{q['query_id']} — {q['title']}"
    for q in queries
}

with st.sidebar:
    st.subheader("Demo query")

    query_id = st.selectbox(
        "Select a slow query",
        ids,
        format_func=lambda q: labels.get(q, q),
    )

    selected = next(q for q in queries if q["query_id"] == query_id)

    st.write(selected["description"])
    st.code(selected["sql"], language="sql")

    run_full = st.button(
        "Run full demo",
        use_container_width=True,
        type="primary",
    )

    do_analyze = st.button(
        "Analyze Query",
        use_container_width=True,
    )

    do_recommend = st.button(
        "Generate Recommendations",
        use_container_width=True,
    )

    do_bench = st.button(
        "Test Best Recommendation",
        use_container_width=True,
    )

if "analysis" not in st.session_state:
    st.session_state.analysis = None
    st.session_state.recs = None
    st.session_state.bench = None

if run_full:
    with st.spinner("Running analyze → recommend → sandbox benchmark..."):
        try:
            demo = client.demo(query_id)

            st.session_state.analysis = demo["analysis"]
            st.session_state.recs = {
                "candidates": demo["recommendations"]
            }
            st.session_state.bench = demo["benchmark"]
        except APIError as exc:
            st.error(str(exc))

if do_analyze:
    with st.spinner("Running EXPLAIN ANALYZE..."):
        try:
            st.session_state.analysis = client.analyze(query_id)
            st.session_state.recs = None
            st.session_state.bench = None
        except APIError as exc:
            st.error(str(exc))

if do_recommend:
    with st.spinner("Scoring candidates..."):
        try:
            st.session_state.recs = client.recommend(query_id)

            if st.session_state.analysis is None:
                st.session_state.analysis = (
                    st.session_state.recs.get("analysis")
                )
        except APIError as exc:
            st.error(str(exc))

if do_bench:
    with st.spinner("Applying candidate in sandbox PostgreSQL..."):
        try:
            cand_id = None

            candidates = (
                st.session_state.recs.get("candidates")
                if st.session_state.recs
                else []
            ) or []

            tested_candidates = [
                c for c in candidates
                if c.get("type") != "NO_CHANGE"
            ]

            if tested_candidates:
                cand_id = tested_candidates[0]["candidate_id"]

            st.session_state.bench = client.benchmark(
                query_id,
                cand_id,
            )
        except APIError as exc:
            st.error(str(exc))

analysis = st.session_state.analysis
recs = st.session_state.recs
bench = st.session_state.bench

left, right = st.columns([1.15, 1])

with left:
    st.subheader("Query analysis")

    if analysis:
        metrics = analysis.get("metrics") or {}

        kpi_row(
            [
                ("Query ID", analysis.get("query_id", query_id)),
                (
                    "Execution",
                    f"{metrics.get('execution_time_ms', 0):.2f} ms",
                ),
                (
                    "Planning",
                    f"{metrics.get('planning_time_ms', 0):.2f} ms",
                ),
                ("Rows", str(metrics.get("rows", 0))),
                (
                    "Status",
                    "SLOW"
                    if (metrics.get("execution_time_ms") or 0) > 20
                    else "OK",
                ),
            ]
        )

        st.caption(
            "All timings are measured from PostgreSQL EXPLAIN ANALYZE."
        )

        t1, t2 = st.tabs(["Anonymized SQL", "Raw demo SQL"])

        with t1:
            st.code(
                analysis.get("anonymized_sql") or "",
                language="sql",
            )

        with t2:
            st.code(
                analysis.get("sql") or "",
                language="sql",
            )

        st.subheader("Measured PostgreSQL metrics")

        metric_rows = [
            {
                "Metric": "Execution time",
                "Value": f"{metrics.get('execution_time_ms', 0):.2f} ms",
            },
            {
                "Metric": "Planning time",
                "Value": f"{metrics.get('planning_time_ms', 0):.2f} ms",
            },
            {
                "Metric": "Rows returned",
                "Value": str(metrics.get("rows", 0)),
            },
            {
                "Metric": "Shared buffer hits",
                "Value": str(metrics.get("shared_hit_blocks", 0)),
            },
            {
                "Metric": "Shared buffer reads",
                "Value": str(metrics.get("shared_read_blocks", 0)),
            },
            {
                "Metric": "Total buffer usage",
                "Value": str(
                    (metrics.get("shared_hit_blocks") or 0)
                    + (metrics.get("shared_read_blocks") or 0)
                ),
            },
        ]

        st.dataframe(
            metric_rows,
            use_container_width=True,
            hide_index=True,
        )

        gnn = analysis.get("gnn") or {}
        nodes = gnn.get("nodes") or []

        st.subheader("Execution plan summary")

        if nodes:
            plan_rows = []

            for node in nodes:
                plan_rows.append(
                    {
                        "Node": node.get("node_type") or "Unknown",
                        "Relation": node.get("relation") or "-",
                        "Actual Rows": node.get("actual_rows") or 0,
                        "Actual Time": (
                            f"{node.get('actual_time_ms', 0):.3f} ms"
                        ),
                        "Importance": (
                            f"{(node.get('importance') or 0) * 100:.1f}%"
                        ),
                    }
                )

            st.dataframe(
                plan_rows,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"Plan analysis source: {gnn.get('source', 'Heuristic')}. "
                "The execution plan is analyzed as structured data; "
                "no graph visualization is shown."
            )
        else:
            st.info("No execution plan node data available.")

    else:
        st.info("Select a query and click Analyze Query.")

with right:
    st.subheader("Bottlenecks")

    if analysis:
        bottleneck_cards(
            analysis.get("bottlenecks") or []
        )

        with st.expander("Bottleneck evidence"):
            st.json(
                analysis.get("bottlenecks") or []
            )

    st.subheader("Recommendations")

    candidates = (
        (recs or {}).get("candidates")
        or (analysis or {}).get("candidates")
        or []
    )

    if candidates:
        for cand in candidates[:4]:
            candidate_card(cand)
    else:
        st.info("Generate recommendations after analysis.")

    st.subheader("Benchmark")

    if bench:
        base = bench.get("baseline") or {}
        opt = bench.get("optimized") or {}

        improvement = bench.get("improvement_percent")

        if improvement is None:
            improvement_text = "n/a"
        else:
            improvement_text = f"{improvement:.2f}%"

        st.metric(
            "Measured improvement",
            improvement_text,
            help="Calculated from PostgreSQL sandbox measurements.",
        )

        kpi_row(
            [
                (
                    "Before",
                    f"{(base or {}).get('execution_time_ms', 0):.2f} ms",
                ),
                (
                    "After",
                    f"{(opt or {}).get('execution_time_ms', 0):.2f} ms"
                    if opt
                    else "n/a",
                ),
                (
                    "Status",
                    bench.get("validation_status") or "UNKNOWN",
                ),
            ]
        )

        st.subheader("Benchmark details")

        benchmark_rows = [
            {
                "Metric": "Baseline execution time",
                "Value": f"{(base or {}).get('execution_time_ms', 0):.2f} ms",
            },
            {
                "Metric": "Optimized execution time",
                "Value": (
                    f"{(opt or {}).get('execution_time_ms', 0):.2f} ms"
                    if opt
                    else "n/a"
                ),
            },
            {
                "Metric": "Improvement",
                "Value": improvement_text,
            },
            {
                "Metric": "Validation status",
                "Value": bench.get("validation_status") or "UNKNOWN",
            },
        ]

        st.dataframe(
            benchmark_rows,
            use_container_width=True,
            hide_index=True,
        )

        if bench.get("candidate_rejected"):
            st.warning(
                "The tested optimization was slower than the baseline "
                "and was rejected. The current configuration is retained."
            )

        if bench.get("error"):
            st.warning(bench["error"])

        expl = bench.get("explanation") or {}

        st.subheader("Why was this recommendation made?")

        st.text(
            expl.get("text")
            or "No explanation was returned."
        )

    else:
        st.info(
            "Test the best recommendation in the sandbox "
            "to see before/after metrics."
        )

st.subheader("Privacy")

privacy = (analysis or {}).get("privacy") or {}

p1, p2, p3, p4 = st.columns(4)

p1.metric(
    "Raw values exposed to AI",
    privacy.get("raw_values_exposed_to_ai", 0),
)

p2.metric(
    "Sensitive literals removed",
    privacy.get("sensitive_literals_removed", 0),
)

p3.metric(
    "Anonymized tables",
    privacy.get("anonymized_tables", 0),
)

p4.metric(
    "Anonymized columns",
    privacy.get("anonymized_columns", 0),
)

st.markdown(
    "RAW QUERY → PRIVACY FILTER → ANONYMIZED REPRESENTATION → AI/ML ANALYSIS"
)

try:
    pair = client.privacy_demo()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Raw query")
        st.code(
            pair.get("raw", ""),
            language="sql",
        )

    with c2:
        st.subheader("Anonymized query")
        st.code(
            pair.get("anonymized", ""),
            language="sql",
        )

except APIError:
    pass