from __future__ import annotations

import sys
from pathlib import Path

# Automatically ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

try:
    from dashboard.api_client import APIError, OptimizerClient
    from dashboard.components import (
        CSS,
        ai_explanation_card,
        bottleneck_cards,
        candidate_card,
        performance_matrix_card,
    )
except ModuleNotFoundError:
    from api_client import APIError, OptimizerClient
    from components import (
        CSS,
        ai_explanation_card,
        bottleneck_cards,
        candidate_card,
        performance_matrix_card,
    )

try:
    from streamlit_ace import st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False

st.set_page_config(
    page_title="PostgreSQL AI Performance Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

client = OptimizerClient()

# Top Navigation / Title - Clean, unclipped hero header
st.markdown(
    """
<div class="top-header">
  <div>
    <div class="top-title">⚡ PostgreSQL AI Performance Optimizer</div>
    <div class="top-subtitle">PostgreSQL Query Optimization · Automated Index Recommendations · Live Benchmark Validation</div>
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

# Sidebar - Database Connection, Query Configuration & Actions
with st.sidebar:
    st.markdown("### PostgreSQL Database")
    try:
        db_cfg = client.get_database_config()
    except Exception:
        db_cfg = {}

    cur_db = db_cfg.get("database", "optimizer")
    cur_host = db_cfg.get("host", "127.0.0.1")
    cur_port = db_cfg.get("port", 5432)
    cur_tables = db_cfg.get("tables", [])
    
    st.markdown(f"**Target:** `🟢 {cur_db}` on `{cur_host}:{cur_port}`")
    if cur_tables:
        with st.expander(f"📁 Available Tables ({len(cur_tables)})", expanded=False):
            st.caption(", ".join(cur_tables))
            
    with st.expander("🔌 Connect to Manual / Custom Database", expanded=False):
        st.caption("Point the optimizer directly to your own PostgreSQL database instance:")
        new_db_host = st.text_input("Host", value=str(cur_host), key="db_host_input")
        new_db_port = st.number_input("Port", value=int(cur_port), min_value=1, max_value=65535, key="db_port_input")
        new_db_name = st.text_input("Database Name", value=str(cur_db), key="db_name_input")
        new_db_user = st.text_input("Username", value=db_cfg.get("user", "optimizer"), key="db_user_input")
        new_db_pass = st.text_input("Password", type="password", key="db_pass_input")
        
        if st.button("Connect & Scan Tables", use_container_width=True):
            try:
                switch_res = client.switch_database(
                    host=new_db_host,
                    port=int(new_db_port),
                    database=new_db_name,
                    user=new_db_user,
                    password=new_db_pass,
                )
                st.success(f"Connected to '{switch_res.get('database')}'. Discovered {switch_res.get('table_count')} tables!")
                st.session_state.analysis = None
                st.session_state.recs = None
                st.session_state.bench = None
                st.rerun()
            except Exception as exc:
                st.error(f"Connection failed: {exc}")

    st.markdown("---")
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
        
        # Show code preview of preset query
        with st.expander("View SQL Statement", expanded=False):
            st.code(active_sql, language="sql")
    else:
        active_id = "custom"
        default_custom = """SELECT c.customer_id, c.name
FROM customers c
WHERE (
    SELECT COUNT(*)
    FROM orders o
    WHERE o.customer_id = c.customer_id
) > 10;"""

        st.markdown("**Enter SQL query below:**")
        if HAS_ACE:
            active_sql = st_ace(
                value=default_custom,
                language="sql",
                theme="monokai",
                keybinding="vscode",
                font_size=13,
                tab_size=2,
                min_lines=8,
                max_lines=24,
                show_gutter=True,
                show_print_margin=False,
                wrap=True,
                auto_update=True,
                key="custom_sql_editor",
            )
            if not active_sql:
                active_sql = default_custom
        else:
            active_sql = st.text_area(
                "Enter SQL statement (SELECT / CTE)",
                value=default_custom,
                height=160,
            )

    st.markdown("---")
    st.markdown("### Optimization Engine")
    
    # Single primary button replacing the previous 3 individual buttons
    run_all = st.button("⚡ Run Optimization & Benchmark", use_container_width=True, type="primary")

    st.markdown("---")
    st.markdown("### System Status")
    db_status = "🟢 Connected" if health.get("postgres") else "🔴 Disconnected"
    sb_status = "🟢 Ready" if health.get("sandbox") else "🔴 Offline"
    gemini_status = "🟢 Active" if health.get("gemini") else "⚪ Optional"
    
    st.caption(f"**PostgreSQL DB:** {db_status}")
    st.caption(f"**Sandbox DB:** {sb_status}")
    st.caption(f"**Gemini AI Explainer:** {gemini_status}")

    # Optional expander to configure Gemini API Key live
    with st.expander("⚙️ Gemini AI Key (Optional)", expanded=not health.get("gemini")):
        st.caption("AI explanations are privacy-preserved: all tables, columns, and literals are masked before contacting Gemini.")
        new_key = st.text_input("Gemini API Key", type="password", placeholder="Paste AI Studio Key here", key="sidebar_gemini_key")
        if st.button("Apply API Key", use_container_width=True):
            if new_key.strip():
                try:
                    res = client.set_gemini_key(new_key.strip(), model=health.get("gemini_model") or "gemini-2.5-flash")
                    if res.get("gemini"):
                        st.success(f"Gemini API key configured ({res.get('gemini_model')}).")
                    else:
                        st.error("Key was not saved on the backend.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error saving key: {exc}")
            else:
                st.warning("Please enter a valid key.")

    st.caption("ℹ️ *Query runtimes are measured directly on PostgreSQL via EXPLAIN (ANALYZE, BUFFERS).*")


# Actions handling
if run_all:
    with st.spinner("Analyzing plan bottlenecks, generating AI improvised query, and executing live benchmarks on PostgreSQL..."):
        try:
            analysis = client.analyze(active_id, active_sql)
            st.session_state.analysis = analysis
            st.session_state.current_sql = active_sql
            st.session_state.current_id = active_id

            recs = client.recommend(active_id, active_sql)
            st.session_state.recs = recs

            candidates = recs.get("candidates", [])
            valid_cands = [c for c in candidates if c.get("type") != "NO_CHANGE"]
            
            # Prioritize REWRITE_QUERY (AI Improvised Query) if available
            rewrites = [c for c in valid_cands if c.get("type") == "REWRITE_QUERY"]
            cand_id = rewrites[0]["candidate_id"] if rewrites else (valid_cands[0]["candidate_id"] if valid_cands else (candidates[0]["candidate_id"] if candidates else None))

            bench = client.benchmark(active_id, cand_id, active_sql)
            st.session_state.bench = bench
            st.success("Optimization analysis & PostgreSQL benchmark completed successfully.")
        except APIError as exc:
            st.error(f"Pipeline error: {exc}")

# Tabs Layout - Clean DBA-friendly terminology
tab_optimization, tab_gnn, tab_privacy = st.tabs([
    "🚀 Performance & Benchmark",
    "🔍 Query Plan & Bottlenecks",
    "🔒 Data Privacy & Guardrails",
])

analysis = st.session_state.analysis
recs = st.session_state.recs
bench = st.session_state.bench
current_sql = st.session_state.current_sql or active_sql

# ----------------- TAB 1: OPTIMIZATION & BENCHMARK MATRIX -----------------
with tab_optimization:
    if bench:
        st.subheader("PostgreSQL Benchmark Comparison")
        performance_matrix_card(bench)

        # Show AI Explanation card if available
        if bench.get("explanation"):
            ai_explanation_card(bench["explanation"])

        # Show actual updated query side-by-side
        st.subheader("Side-by-Side Query Comparison")
        cand = bench.get("candidate", {})
        cand_type = cand.get("type")
        is_rewrite = cand_type == "REWRITE_QUERY"
        updated_sql = bench.get("updated_sql") or cand.get("rewritten_sql") or cand.get("sql")

        col_orig, col_opt = st.columns(2)
        with col_orig:
            st.markdown("**Original Query (User Input)**")
            st.caption("Executed live on connected PostgreSQL database.")
            st.code(current_sql, language="sql")

        with col_opt:
            if is_rewrite:
                st.markdown("**AI Improvised Query (Optimized SQL)**")
                technique = cand.get("technique") or "AI Plan Optimization"
                st.caption(f"✨ **{technique}**: Executed live on PostgreSQL with identical result set.")
            else:
                st.markdown("**Applied Optimization / Schema Change**")
                st.caption("✨ Recommended DDL index executed and validated in sandbox.")
            if updated_sql:
                st.code(updated_sql, language="sql")
            else:
                st.info("No query rewrite was required. Indexing recommendation applies.")

    else:
        st.info("Select or enter a query in the sidebar and click **'Run Optimization & Benchmark'** to measure real execution performance on PostgreSQL.")

    # Candidate recommendations
    st.markdown("---")
    st.subheader("Recommended Optimizations")
    candidates = (recs or {}).get("candidates") or (analysis or {}).get("candidates") or []
    visible_cands = [c for c in candidates if c.get("type") != "NO_CHANGE"]

    if visible_cands:
        for cand_item in visible_cands[:4]:
            candidate_card(cand_item)
            c_id = cand_item.get("candidate_id")
            c_type = cand_item.get("type")
            # Allow user to benchmark any specific candidate if desired
            if bench and bench.get("candidate", {}).get("candidate_id") != c_id:
                if st.button(f"⚡ Benchmark This Option ({c_type})", key=f"bench_btn_{c_id}"):
                    with st.spinner(f"Benchmarking candidate {c_id} on PostgreSQL..."):
                        try:
                            bench_cand = client.benchmark(st.session_state.current_id, c_id, current_sql)
                            st.session_state.bench = bench_cand
                            st.rerun()
                        except Exception as e:
                            st.error(f"Benchmark error: {e}")
    elif candidates:
        st.info("Current configuration is already optimal. No structural alterations needed.")
    else:
        st.caption("Run optimization to view ranked recommendations.")



# ----------------- TAB 2: QUERY PLAN & BOTTLENECKS -----------------
with tab_gnn:
    st.subheader("Query Execution Plan & Bottleneck Analysis")
    if analysis and analysis.get("gnn"):
        gnn = analysis["gnn"]
        b_node = gnn.get("bottleneck_node", {})
        attn_pct = gnn.get("attention_percent", 50.0)

        st.markdown(
            f"""
<div class="card" style="border-left: 4px solid #6366f1;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <h4 style="margin:0; color:#818cf8;">Primary Bottleneck: {gnn.get('bottleneck_class', 'DETECTED')}</h4>
    <span class="badge badge-success">Plan Impact: {attn_pct}%</span>
  </div>
  <p style="margin:0.6rem 0; font-size:0.95rem; line-height:1.5;">{gnn.get('explanation', 'Analysis complete.')}</p>
  <small style="color:#94a3b8;">Operator: <b>{b_node.get('node_type')}</b> | Table: <b>{b_node.get('relation') or 'N/A'}</b> | Time: <b>{b_node.get('exclusive_time', 0):.2f} ms</b></small>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("#### Query Plan Operations & Execution Timing")
        nodes_data = gnn.get("nodes", [])
        if nodes_data:
            st.dataframe(
                [
                    {
                        "Node ID": n["id"],
                        "Operator": n["node_type"],
                        "Relation": n["relation"] or "—",
                        "Time (ms)": n["exclusive_time"],
                        "Rows Scanned": n["actual_rows"],
                        "Time Share (%)": n["importance"],
                        "Status": "🔴 Slowest Node" if n.get("is_bottleneck") else "—",
                    }
                    for n in nodes_data
                ],
                use_container_width=True,
                hide_index=True,
            )

        with st.expander("Detected Query Bottlenecks"):
            bottleneck_cards(analysis.get("bottlenecks") or [])
    else:
        st.info("Run query optimization to inspect execution plan bottlenecks.")


# ----------------- TAB 3: PRIVACY & DATA GUARDRAILS -----------------
with tab_privacy:
    st.subheader("Data Privacy & Schema Guardrails")
    st.write(
        "To protect company privacy, **all raw sensitive data, table names, and column identifiers** are "
        "masked before any external AI analysis occurs. AI suggestions are then safely translated back "
        "into your real database schema."
    )

    if analysis and "privacy_trace" in analysis:
        trace = analysis["privacy_trace"]
        
        st.markdown(
            f"""
<div class="card" style="border-left: 4px solid #10b981; margin-bottom: 1.2rem;">
  <h4 style="margin:0; color:#34d399;">Privacy Guardrail Audit: {trace.get('guardrail_status', 'PASSED')}</h4>
  <p style="margin:0.4rem 0 0 0; font-size:0.85rem; color:#cbd5e1;">
    Sensitive Values Masked: <b>{trace.get('literals_removed', 0)}</b> | 
    Raw Production Values Exposed to AI: <b>0</b> | 
    Tables Masked: <b>{trace.get('tables_anonymized', 0)}</b> | 
    Columns Masked: <b>{trace.get('columns_anonymized', 0)}</b>
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown("**1. Raw User Query (DBA View)**")
            st.caption("Contains real database schema and query literals.")
            st.code(trace.get("raw_sql", ""), language="sql")

        with col_p2:
            st.markdown("**2. Anonymized Safe View (Sent to AI)**")
            st.caption("Zero literals. Tables & columns converted to tokens.")
            st.code(trace.get("anonymized_sql", ""), language="sql")

        with col_p3:
            st.markdown("**3. Reconstructed Query (DBA View)**")
            st.caption("AI output safely translated back to your real schema.")
            st.code(trace.get("reconstructed_sql", ""), language="sql")

    else:
        st.info("Run optimization on a query to inspect live end-to-end privacy masking and reconstruction traces.")
        # Fallback static demo
        try:
            demo_pair = client.privacy_demo()
            st.markdown("#### Sample Obfuscation Demonstration")
            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown("**Raw Input**")
                st.code(demo_pair.get("raw", ""), language="sql")
            with c_b:
                st.markdown("**Safe Model Input (Masked Tokens)**")
                st.code(demo_pair.get("anonymized", ""), language="sql")
        except Exception:
            pass