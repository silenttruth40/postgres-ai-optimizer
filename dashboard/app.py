from __future__ import annotations

import streamlit as st

from dashboard.api_client import APIError, OptimizerClient
from dashboard.components import (
    CSS,
    bottleneck_cards,
    candidate_card,
    performance_matrix_card,
)

st.set_page_config(
    page_title="PostgreSQL AI Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

client = OptimizerClient()

# Top Navigation / Title
st.markdown(
    """
<div class="top-header">
  <div>
    <div class="top-title">PostgreSQL AI Performance Optimizer</div>
    <div class="top-subtitle">Zero-Data Exposure · Graph Neural Networks · Reinforcement Learning · Sandbox Validation</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Check backend health
try:
    health = client.health()
except APIError as exc:
    st.error(f"Backend API unavailable at http://localhost:8000. Start backend service first. ({exc})")
    st.stop()

# State initialization
if "analysis" not in st.session_state:
    st.session_state.analysis = None
    st.session_state.recs = None
    st.session_state.bench = None
    st.session_state.current_sql = None
    st.session_state.current_id = "Q001"

try:
    queries = client.queries()
except APIError as exc:
    st.error(str(exc))
    st.stop()

ids = [q["query_id"] for q in queries]
labels = {q["query_id"]: f"{q['query_id']} — {q['title']}" for q in queries}

# Sidebar - Query Configuration & Actions
with st.sidebar:
    st.markdown("### Query Input")
    input_mode = st.radio(
        "Source",
        ["Preset Benchmark Queries", "Custom SQL Query"],
        label_visibility="collapsed",
    )

    if input_mode == "Preset Benchmark Queries":
        query_id = st.selectbox(
            "Select slow query",
            ids,
            format_func=lambda q: labels.get(q, q),
        )
        selected = next(q for q in queries if q["query_id"] == query_id)
        st.caption(selected["description"])
        active_sql = selected["sql"]
        active_id = query_id
    else:
        active_id = "custom"
        default_custom = """SELECT c.customer_id, c.name, COUNT(o.order_id) AS total_orders
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '60 days'
  AND o.amount > 100
GROUP BY c.customer_id, c.name
ORDER BY total_orders DESC;"""
        active_sql = st.text_area(
            "Enter SQL statement (SELECT / CTE)",
            value=default_custom,
            height=160,
        )

    st.markdown("---")
    st.markdown("### Optimization Engine")
    
    run_all = st.button("⚡ Run Full Optimization Pipeline", use_container_width=True, type="primary")
    c1, c2 = st.columns(2)
    with c1:
        do_analyze = st.button("1. Analyze (GNN)", use_container_width=True)
    with c2:
        do_recommend = st.button("2. Recommend (RL)", use_container_width=True)
    do_bench = st.button("3. Benchmark in Sandbox", use_container_width=True)

    st.markdown("---")
    db_status = "🟢 Connected" if health.get("postgres") else "🔴 Disconnected"
    sb_status = "🟢 Ready" if health.get("sandbox") else "🔴 Offline"
    st.caption(f"Demo DB: {db_status} | Sandbox DB: {sb_status}")

# Actions handling
if run_all:
    with st.spinner("Executing: Bitmask Hashing → GNN Analysis → RL Ranking → Sandbox Simulation..."):
        try:
            analysis = client.analyze(active_id, active_sql)
            st.session_state.analysis = analysis
            st.session_state.current_sql = active_sql
            st.session_state.current_id = active_id

            recs = client.recommend(active_id, active_sql)
            st.session_state.recs = recs

            candidates = recs.get("candidates", [])
            valid_cands = [c for c in candidates if c.get("type") != "NO_CHANGE"]
            cand_id = valid_cands[0]["candidate_id"] if valid_cands else (candidates[0]["candidate_id"] if candidates else None)

            bench = client.benchmark(active_id, cand_id, active_sql)
            st.session_state.bench = bench
            st.success("Optimization pipeline completed successfully.")
        except APIError as exc:
            st.error(f"Pipeline error: {exc}")

elif do_analyze:
    with st.spinner("Analyzing plan with Graph Neural Network..."):
        try:
            st.session_state.analysis = client.analyze(active_id, active_sql)
            st.session_state.current_sql = active_sql
            st.session_state.current_id = active_id
            st.session_state.recs = None
            st.session_state.bench = None
        except APIError as exc:
            st.error(str(exc))

elif do_recommend:
    with st.spinner("Scoring and ranking candidate interventions..."):
        try:
            st.session_state.recs = client.recommend(active_id, active_sql)
            if not st.session_state.analysis:
                st.session_state.analysis = st.session_state.recs.get("analysis")
        except APIError as exc:
            st.error(str(exc))

elif do_bench:
    with st.spinner("Simulating candidate in isolated PostgreSQL Sandbox..."):
        try:
            if not st.session_state.recs:
                st.session_state.recs = client.recommend(active_id, active_sql)
            candidates = st.session_state.recs.get("candidates", [])
            valid_cands = [c for c in candidates if c.get("type") != "NO_CHANGE"]
            cand_id = valid_cands[0]["candidate_id"] if valid_cands else (candidates[0]["candidate_id"] if candidates else None)
            st.session_state.bench = client.benchmark(active_id, cand_id, active_sql)
        except APIError as exc:
            st.error(str(exc))

# Tabs Layout
tab_optimization, tab_gnn, tab_privacy = st.tabs([
    "🚀 Optimization & Performance Matrix",
    "🧠 GNN Execution Tree Analytics",
    "🛡️ Zero-Exposure Privacy Audit",
])

analysis = st.session_state.analysis
recs = st.session_state.recs
bench = st.session_state.bench
current_sql = st.session_state.current_sql or active_sql

# ----------------- TAB 1: OPTIMIZATION & BENCHMARK MATRIX -----------------
with tab_optimization:
    if bench:
        st.subheader("Sandbox Verification Matrix")
        performance_matrix_card(bench)

        # Show actual updated query side-by-side or stacked
        st.subheader("Query Optimization Result")
        updated_sql = bench.get("updated_sql") or (bench.get("candidate", {}).get("rewritten_sql") or bench.get("candidate", {}).get("sql"))

        col_orig, col_opt = st.columns(2)
        with col_orig:
            st.markdown("**Original Query (User Input)**")
            st.code(current_sql, language="sql")

        with col_opt:
            st.markdown("**Optimized Output / Applied Schema Change**")
            if updated_sql:
                st.code(updated_sql, language="sql")
                if bench.get("candidate", {}).get("type") == "REWRITE_QUERY":
                    st.caption("✨ Safely rewritten SQL query to eliminate nested loop / redundant scans.")
                elif "INDEX" in (bench.get("candidate", {}).get("type") or ""):
                    st.caption("✨ Recommended DDL index to execute for achieving the validated speedup.")
            else:
                st.info("No query rewrite was required. Indexing or statistics recommendation applies.")

    elif analysis:
        st.info("Query analyzed. Click **'3. Benchmark in Sandbox'** to simulate and measure percentage speedup.")
    else:
        st.info("Select or enter a query in the sidebar and click **'Run Full Optimization Pipeline'**.")

    # Candidate recommendations
    st.markdown("---")
    st.subheader("AI Recommendations (Ranked by RL Agent)")
    candidates = (recs or {}).get("candidates") or (analysis or {}).get("candidates") or []
    visible_cands = [c for c in candidates if c.get("type") != "NO_CHANGE"]

    if visible_cands:
        for cand in visible_cands[:4]:
            candidate_card(cand)
    elif candidates:
        st.info("Current configuration is already optimal. No structural alterations needed.")
    else:
        st.caption("Generate recommendations to view RL-ranked optimization candidates.")


# ----------------- TAB 2: GNN EXECUTION TREE ANALYTICS -----------------
with tab_gnn:
    st.subheader("Execution Tree Analytics Module (GNN)")
    if analysis and analysis.get("gnn"):
        gnn = analysis["gnn"]
        b_node = gnn.get("bottleneck_node", {})
        attn_pct = gnn.get("attention_percent", 50.0)

        st.markdown(
            f"""
<div class="card" style="border-left: 4px solid #6366f1;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <h4 style="margin:0; color:#818cf8;">GNN Bottleneck Classification: {gnn.get('bottleneck_class', 'DETECTED')}</h4>
    <span class="badge badge-success">GNN Attention: {attn_pct}%</span>
  </div>
  <p style="margin:0.6rem 0; font-size:0.95rem; line-height:1.5;">{gnn.get('explanation', 'Analysis complete.')}</p>
  <small style="color:#94a3b8;">Operator: <b>{b_node.get('node_type')}</b> | Table: <b>{b_node.get('relation') or 'N/A'}</b> | Time: <b>{b_node.get('exclusive_time', 0):.2f} ms</b></small>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("#### Execution Plan DAG Nodes")
        nodes_data = gnn.get("nodes", [])
        if nodes_data:
            st.dataframe(
                [
                    {
                        "Node ID": n["id"],
                        "Operator": n["node_type"],
                        "Relation": n["relation"] or "—",
                        "Exclusive Time (ms)": n["exclusive_time"],
                        "Rows Scanned": n["actual_rows"],
                        "GNN Importance (%)": n["importance"],
                        "Is Culprit": "🔴 Primary" if n.get("is_bottleneck") else "—",
                    }
                    for n in nodes_data
                ],
                use_container_width=True,
                hide_index=True,
            )

        with st.expander("Classical PostgreSQL Bottlenecks Detected"):
            bottleneck_cards(analysis.get("bottlenecks") or [])
    else:
        st.info("Run query analysis to see Graph Neural Network node-level execution tree analytics.")


# ----------------- TAB 3: PRIVACY & REVERSE-HASHING VERIFICATION -----------------
with tab_privacy:
    st.subheader("Data Obfuscation & Reverse-Mapping Verification")
    st.write(
        "Problem Statement 4 mandates **100% zero exposure of raw sensitive data** to AI models. "
        "The system obfuscates raw queries into structural metadata hashes before AI processing, "
        "and de-anonymizes recommendations back to the DBA's schema terms."
    )

    if analysis and "privacy_trace" in analysis:
        trace = analysis["privacy_trace"]
        
        st.markdown(
            f"""
<div class="card" style="border-left: 4px solid #10b981; margin-bottom: 1.2rem;">
  <h4 style="margin:0; color:#34d399;">Privacy Guardrail Audit: {trace.get('guardrail_status', 'PASSED')}</h4>
  <p style="margin:0.4rem 0 0 0; font-size:0.85rem; color:#cbd5e1;">
    Sensitive Literals Stripped: <b>{trace.get('literals_removed', 0)}</b> | 
    Raw Production Values Exposed to AI: <b>0</b> | 
    Tables Hashed: <b>{trace.get('tables_anonymized', 0)}</b> | 
    Columns Hashed: <b>{trace.get('columns_anonymized', 0)}</b>
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown("**1. Raw User Query (DBA View)**")
            st.caption("Contains company schema & sensitive literals.")
            st.code(trace.get("raw_sql", ""), language="sql")

        with col_p2:
            st.markdown("**2. Hashed Representation (AI View)**")
            st.caption("Zero literals. Tables & columns converted to tokens.")
            st.code(trace.get("anonymized_sql", ""), language="sql")

        with col_p3:
            st.markdown("**3. Reverse-Mapped Query (Re-Hashed)**")
            st.caption("AI output safely translated back to DBA schema.")
            st.code(trace.get("reconstructed_sql", ""), language="sql")

    else:
        st.info("Analyze a query to inspect live end-to-end obfuscation and reverse-mapping traces.")
        # Fallback static demo
        try:
            demo_pair = client.privacy_demo()
            st.markdown("#### Sample Obfuscation Demonstration")
            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown("**Raw Input**")
                st.code(demo_pair.get("raw", ""), language="sql")
            with c_b:
                st.markdown("**AI Model Input (Anonymized Tokens)**")
                st.code(demo_pair.get("anonymized", ""), language="sql")
        except Exception:
            pass