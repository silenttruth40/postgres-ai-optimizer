from __future__ import annotations

import streamlit as st

from dashboard.api_client import APIError, OptimizerClient
from dashboard.components import CSS, bottleneck_cards, candidate_card

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

    selected = next(
        q for q in queries
        if q["query_id"] == query_id
    )

    st.write(selected["description"])

    st.code(
        selected["sql"],
        language="sql",
    )

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
    with st.spinner(
        "Running analyze → recommend → sandbox benchmark..."
    ):
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
    with st.spinner(
        "Applying candidate in sandbox PostgreSQL..."
    ):
        try:
            cand_id = None

            candidates = (
                st.session_state.recs.get("candidates")
                if st.session_state.recs
                else []
            ) or []

            tested_candidates = [
                candidate
                for candidate in candidates
                if candidate.get("type") != "NO_CHANGE"
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
    st.subheader("Query Analysis")

    if analysis:
        st.caption(
            "Query analyzed using PostgreSQL EXPLAIN ANALYZE."
        )

        st.subheader("Anonymized SQL")

        st.code(
            analysis.get("anonymized_sql") or "",
            language="sql",
        )

        st.subheader("Original SQL")

        st.code(
            analysis.get("sql") or "",
            language="sql",
        )

        gnn = analysis.get("gnn") or {}

        if gnn:
            st.caption(
                f"Execution plan analyzed using "
                f"{gnn.get('source', 'heuristic')} plan analysis."
            )

    else:
        st.info(
            "Select a query and click Analyze Query."
        )

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

    else:
        st.info(
            "Run query analysis to detect bottlenecks."
        )

    st.subheader("Recommendations")

    candidates = (
        (recs or {}).get("candidates")
        or (analysis or {}).get("candidates")
        or []
    )

    visible_candidates = [
        candidate
        for candidate in candidates
        if candidate.get("type") != "NO_CHANGE"
    ]

    if visible_candidates:
        for candidate in visible_candidates[:4]:
            candidate_card(candidate)
    elif candidates:
        st.info(
            "No optimization candidate is currently "
            "recommended. Keeping the current configuration "
            "is the safe fallback."
        )
    else:
        st.info(
            "Generate recommendations after analysis."
        )

    st.subheader("Sandbox Benchmark")

    if bench:
        baseline = bench.get("baseline") or {}
        optimized = bench.get("optimized") or {}

        improvement = bench.get("improvement_percent")
        validation_status = (
            bench.get("validation_status")
            or "UNKNOWN"
        )

        st.markdown("**Before**")
        st.write(
            f"{baseline.get('execution_time_ms', 0):.2f} ms"
        )

        st.markdown("**After**")

        if optimized:
            st.write(
                f"{optimized.get('execution_time_ms', 0):.2f} ms"
            )
        else:
            st.write("Not available")

        st.markdown("**Measured Improvement**")

        if improvement is None:
            st.write("Not available")
        else:
            st.write(f"{improvement:.2f}%")

        st.markdown("**Validation Status**")
        st.write(validation_status)

        if bench.get("candidate_rejected"):
            st.warning(
                "The tested optimization was slower than "
                "the baseline and was rejected. The current "
                "configuration is retained."
            )

        if bench.get("error"):
            st.warning(bench["error"])

        explanation = bench.get("explanation") or {}

        st.subheader(
            "Why was this recommendation made?"
        )

        st.write(
            explanation.get("text")
            or "No explanation was returned."
        )

    else:
        st.info(
            "Test the best recommendation in the sandbox "
            "to see the measured result."
        )

st.subheader("Privacy Protection")

privacy = (analysis or {}).get("privacy") or {}

st.write(
    "The query passes through a privacy filter before "
    "AI/ML analysis. Sensitive literal values are removed "
    "or anonymized."
)

st.markdown(
    "RAW QUERY → PRIVACY FILTER → "
    "ANONYMIZED REPRESENTATION → AI/ML ANALYSIS"
)

try:
    pair = client.privacy_demo()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Raw Query")

        st.code(
            pair.get("raw", ""),
            language="sql",
        )

    with c2:
        st.subheader("Anonymized Query")

        st.code(
            pair.get("anonymized", ""),
            language="sql",
        )

except APIError:
    pass