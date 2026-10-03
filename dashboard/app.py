from __future__ import annotations

import streamlit as st

from dashboard.api_client import APIError, OptimizerClient
from dashboard.charts import before_after, metric_bars, plan_graph_figure
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
labels = {q["query_id"]: f"{q['query_id']} — {q['title']}" for q in queries}

with st.sidebar:
    st.subheader("Demo query")
    query_id = st.selectbox("Select a slow query", ids, format_func=lambda q: labels.get(q, q))
    selected = next(q for q in queries if q["query_id"] == query_id)
    st.write(selected["description"])
    st.code(selected["sql"], language="sql")
    run_full = st.button("Run full demo", use_container_width=True, type="primary")
    do_analyze = st.button("Analyze Query", use_container_width=True)
    do_recommend = st.button("Generate Recommendations", use_container_width=True)
    do_bench = st.button("Test Best Recommendation", use_container_width=True)

if "analysis" not in st.session_state:
    st.session_state.analysis = None
    st.session_state.recs = None
    st.session_state.bench = None

if run_full:
    with st.spinner("Running analyze → recommend → sandbox benchmark..."):
        try:
            demo = client.demo(query_id)
            st.session_state.analysis = demo["analysis"]
            st.session_state.recs = {"candidates": demo["recommendations"]}
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
                st.session_state.analysis = st.session_state.recs.get("analysis")
        except APIError as exc:
            st.error(str(exc))

if do_bench:
    with st.spinner("Applying candidate in sandbox PostgreSQL..."):
        try:
            cand_id = None
            if st.session_state.recs and st.session_state.recs.get("candidates"):
                cand_id = st.session_state.recs["candidates"][0]["candidate_id"]
            st.session_state.bench = client.benchmark(query_id, cand_id)
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
                ("Execution", f"{metrics.get('execution_time_ms', 0):.2f} ms"),
                ("Planning", f"{metrics.get('planning_time_ms', 0):.2f} ms"),
                ("Rows", str(metrics.get("rows", 0))),
                ("Status", "SLOW" if (metrics.get("execution_time_ms") or 0) > 20 else "OK"),
            ]
        )
        st.caption("All timings are Measured from PostgreSQL EXPLAIN ANALYZE.")
        t1, t2 = st.tabs(["Anonymized SQL", "Raw demo SQL"])
        with t1:
            st.code(analysis.get("anonymized_sql") or "", language="sql")
        with t2:
            st.code(analysis.get("sql") or "", language="sql")
        st.plotly_chart(metric_bars(metrics), use_container_width=True)
        gnn = analysis.get("gnn") or {}
        st.plotly_chart(plan_graph_figure(gnn.get("nodes") or [], gnn.get("edges") or []), use_container_width=True)
        st.caption(f"Plan graph source: {gnn.get('source', 'Heuristic')}")
    else:
        st.info("Select a query and click Analyze Query.")

with right:
    st.subheader("Bottlenecks")
    if analysis:
        bottleneck_cards(analysis.get("bottlenecks") or [])
        with st.expander("Bottleneck evidence"):
            st.json(analysis.get("bottlenecks") or [])
    st.subheader("Recommendations")
    candidates = (recs or {}).get("candidates") or (analysis or {}).get("candidates") or []
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
        st.metric(
            "Improvement (measured)",
            "n/a" if improvement is None else f"{improvement:.2f}%",
            help="(baseline - optimized) / baseline * 100 from PostgreSQL",
        )
        kpi_row(
            [
                ("Before", f"{(base or {}).get('execution_time_ms', 0):.2f} ms"),
                ("After", f"{(opt or {}).get('execution_time_ms', 0):.2f} ms" if opt else "n/a"),
                ("Status", bench.get("validation_status") or ""),
            ]
        )
        st.plotly_chart(before_after(base, opt if opt else None), use_container_width=True)
        if bench.get("error"):
            st.warning(bench["error"])
        expl = bench.get("explanation") or {}
        st.subheader("Why was this recommendation made?")
        st.text(expl.get("text") or "")
    else:
        st.info("Test the best recommendation in the sandbox to see before/after metrics.")

st.subheader("Privacy")
privacy = (analysis or {}).get("privacy") or {}
p1, p2, p3, p4 = st.columns(4)
p1.metric("Raw values exposed to AI", privacy.get("raw_values_exposed_to_ai", 0))
p2.metric("Sensitive literals removed", privacy.get("sensitive_literals_removed", 0))
p3.metric("Anonymized tables", privacy.get("anonymized_tables", 0))
p4.metric("Anonymized columns", privacy.get("anonymized_columns", 0))
st.markdown("RAW QUERY → PRIVACY FILTER → ANONYMIZED REPRESENTATION → AI/ML ANALYSIS")
try:
    pair = client.privacy_demo()
    c1, c2 = st.columns(2)
    c1.code(pair.get("raw", ""), language="sql")
    c2.code(pair.get("anonymized", ""), language="sql")
except APIError:
    pass
