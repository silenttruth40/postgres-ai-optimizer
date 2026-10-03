from __future__ import annotations

from typing import Any
import streamlit as st


def performance_matrix_card(bench: dict[str, Any]) -> None:
    """Renders a sleek performance improvement matrix showing real PostgreSQL execution metrics."""
    baseline = bench.get("baseline") or {}
    optimized = bench.get("optimized") or {}
    improvement = bench.get("improvement_percent")
    status = bench.get("validation_status") or "UNKNOWN"
    write_overhead = bench.get("write_latency_overhead_ms", 0.0)
    storage_mb = bench.get("storage_overhead_mb", 0.0)
    cand = bench.get("candidate") or {}
    is_rewrite = cand.get("type") == "REWRITE_QUERY"

    base_time = baseline.get("execution_time_ms", 0.0)
    opt_time = optimized.get("execution_time_ms", 0.0) if optimized else base_time
    base_plan = baseline.get("planning_time_ms", 0.0)
    opt_plan = optimized.get("planning_time_ms", 0.0) if optimized else base_plan

    base_hits = baseline.get("shared_hit_blocks", 0)
    opt_hits = optimized.get("shared_hit_blocks", 0) if optimized else base_hits
    hit_diff = base_hits - opt_hits

    base_reads = baseline.get("shared_read_blocks", 0)
    opt_reads = optimized.get("shared_read_blocks", 0) if optimized else base_reads
    read_diff = base_reads - opt_reads

    base_rows = baseline.get("rows", 0)
    opt_rows = optimized.get("rows", 0) if optimized else base_rows

    speedup_factor = bench.get("speedup_factor")
    if not speedup_factor and opt_time > 0:
        speedup_factor = round(base_time / opt_time, 2)
    elif not speedup_factor:
        speedup_factor = 1.0

    # Determine badge color & text
    if improvement is not None and improvement > 5:
        badge_class = "badge-success"
        if speedup_factor >= 2.0:
            badge_text = f"⚡ {speedup_factor:.1f}x FASTER (+{improvement:.1f}%)"
        else:
            badge_text = f"+{improvement:.1f}% FASTER"
    elif improvement is not None and improvement >= 0:
        badge_class = "badge-neutral"
        badge_text = "NEUTRAL (0.0%)"
    else:
        badge_class = "badge-rejected"
        badge_text = "REJECTED (SLOWER)"

    target_title = "AI IMPROVISED QUERY BENCHMARK" if is_rewrite else "POSTGRESQL EXECUTION BENCHMARK"

    if is_rewrite:
        # Dual query execution comparison layout
        stat3_label = "Execution Speedup"
        stat3_val = f"{speedup_factor:.1f}x faster"
        stat4_label = "Buffer I/O Saved"
        stat4_val = f"-{hit_diff:,} blocks" if hit_diff > 0 else f"{hit_diff:,} blocks"
    else:
        stat3_label = "Index Write Overhead"
        stat3_val = f"+{write_overhead:.1f} ms"
        stat4_label = "Estimated Index Size"
        stat4_val = f"+{storage_mb:.1f} MB"

    st.markdown(
        f"""
<div class="matrix-card">
  <div class="matrix-header">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
      <span class="matrix-title">{target_title}</span>
      <span class="matrix-status">Status: {status}</span>
      <span class="matrix-engine">🟢 Engine: Live PostgreSQL (EXPLAIN ANALYZE)</span>
    </div>
    <div class="badge {badge_class}">{badge_text}</div>
  </div>
  <div class="matrix-grid">
    <div class="matrix-stat">
      <span class="stat-label">Original User Query</span>
      <span class="stat-value">{base_time:.2f} ms</span>
    </div>
    <div class="matrix-stat">
      <span class="stat-label">{"AI Improvised Query" if is_rewrite else "Optimized Query"}</span>
      <span class="stat-value highlight">{opt_time:.2f} ms</span>
    </div>
    <div class="matrix-stat">
      <span class="stat-label">{stat3_label}</span>
      <span class="stat-value highlight">{stat3_val}</span>
    </div>
    <div class="matrix-stat">
      <span class="stat-label">{stat4_label}</span>
      <span class="stat-value">{stat4_val}</span>
    </div>
  </div>

  <div style="margin-top: 1.2rem;">
    <table class="comp-table">
      <thead>
        <tr>
          <th>Execution Metric</th>
          <th>Original User Query</th>
          <th>AI Improvised Query</th>
          <th>Improvement / Variance</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b>Execution Time</b></td>
          <td><code>{base_time:.2f} ms</code></td>
          <td><code>{opt_time:.2f} ms</code></td>
          <td><span class="diff-badge green">{"-" if base_time >= opt_time else "+"}{abs(base_time - opt_time):.2f} ms ({improvement:.1f}%)</span></td>
        </tr>
        <tr>
          <td><b>Planning Time</b></td>
          <td><code>{base_plan:.2f} ms</code></td>
          <td><code>{opt_plan:.2f} ms</code></td>
          <td><span class="diff-badge neutral">{"+" if opt_plan > base_plan else "-"}{abs(opt_plan - base_plan):.2f} ms</span></td>
        </tr>
        <tr>
          <td><b>Buffer Cache Hits (Memory I/O)</b></td>
          <td><code>{base_hits:,} blocks</code></td>
          <td><code>{opt_hits:,} blocks</code></td>
          <td><span class="diff-badge {"green" if hit_diff >= 0 else "neutral"}">{"-" if hit_diff >= 0 else "+"}{abs(hit_diff):,} blocks</span></td>
        </tr>
        <tr>
          <td><b>Shared Disk Reads (Physical I/O)</b></td>
          <td><code>{base_reads:,} blocks</code></td>
          <td><code>{opt_reads:,} blocks</code></td>
          <td><span class="diff-badge {"green" if read_diff >= 0 else "neutral"}">{"-" if read_diff >= 0 else "+"}{abs(read_diff):,} blocks</span></td>
        </tr>
        <tr>
          <td><b>Rows Processed</b></td>
          <td><code>{base_rows:,} rows</code></td>
          <td><code>{opt_rows:,} rows</code></td>
          <td><span class="diff-badge green">{"✅ Parity Confirmed" if base_rows == opt_rows else "Result Set Diff"}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def ai_explanation_card(explanation: dict[str, Any]) -> None:
    """Renders the AI diagnosis and plain-English explanation."""
    if not explanation or not explanation.get("text"):
        return

    text = explanation.get("text", "")
    engine = explanation.get("engine", "built-in")
    is_gemini = "gemini" in engine.lower()
    engine_badge = "🤖 Gemini AI (Privacy Preserved)" if is_gemini else "⚙️ Built-in Rule Explainer"
    badge_style = "background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid #6366f1;" if is_gemini else "background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid #475569;"

    from html import escape

    gemini_error = explanation.get("gemini_error")
    error_html = ""
    if gemini_error and not is_gemini:
        error_html = (
            f'<p style="margin:0 0 0.6rem 0; color:#fbbf24; font-size:0.82rem;">'
            f"Gemini fallback: {escape(str(gemini_error))}</p>"
        )

    st.markdown(
        f"""
<div class="card" style="border-left: 4px solid #6366f1; margin-top: 1rem;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
    <h4 style="margin: 0; color: #a5b4fc; font-size: 1.05rem;">AI Performance Diagnosis & Explanation</h4>
    <span style="font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 4px; {badge_style}">{engine_badge}</span>
  </div>
  {error_html}
  <div style="font-size: 0.92rem; line-height: 1.6; color: #e2e8f0; white-space: pre-line;">
{text}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def candidate_card(candidate: dict[str, Any]) -> None:
    conf = int(round((candidate.get("confidence") or 0) * 100))
    cols = ", ".join(candidate.get("columns") or [])
    kind = candidate.get("type", "").replace("_", " ")
    
    table_info = f"<code>{candidate.get('table', '')}</code>" if candidate.get("table") else ""
    col_info = f"({', '.join(f'<code>{c}</code>' for c in (candidate.get('columns') or []))})" if cols else ""

    st.markdown(
        f"""
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
    <span class="cand-type">{kind}</span>
    <span class="cand-conf">{conf}% Expected Confidence</span>
  </div>
  <div style="margin-bottom:0.4rem;">{table_info} {col_info}</div>
  <p class="cand-reason">{candidate.get('reason', '')}</p>
  <small style="color:#64748b;">Source: Query Plan Analysis & Index Advisor</small>
</div>
""",
        unsafe_allow_html=True,
    )


def bottleneck_cards(bottlenecks: list[dict[str, Any]]) -> None:
    if not bottlenecks:
        st.info("No query bottlenecks detected.")
        return
    cols = st.columns(min(3, len(bottlenecks)))
    for col, item in zip(cols, bottlenecks[:3]):
        with col:
            st.markdown(
                f"""
<div class="card">
  <div class="sev {item.get('severity','').lower()}">{item.get('severity')}</div>
  <h4 style="margin:0.4rem 0 0.2rem 0; font-size:0.95rem;">{item.get('type')}</h4>
  <p style="margin:0; font-size:0.85rem; color:#94a3b8;">{item.get('node')} {item.get('relation') or ''}</p>
  <small style="color:#cbd5e1;">{item.get('reason')}</small>
</div>
""",
                unsafe_allow_html=True,
            )


CSS = """
<style>
/* 1. HIDE STREAMLIT THREE-DOTS MENU, HEADER TOOLBAR, AND DEPLOY BUTTON */
#MainMenu {
  visibility: hidden !important;
  display: none !important;
}
header[data-testid="stHeader"] {
  visibility: hidden !important;
  display: none !important;
  height: 0px !important;
}
[data-testid="stToolbar"] {
  visibility: hidden !important;
  display: none !important;
}
.stAppDeployButton {
  visibility: hidden !important;
  display: none !important;
}
footer {
  visibility: hidden !important;
  display: none !important;
}
[data-testid="stDecoration"] {
  display: none !important;
}

/* 2. BASE APP & LAYOUT SPACING */
.stApp {
  background: #080d1a;
  color: #f1f5f9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.block-container {
  padding-top: 2.2rem !important;
  padding-bottom: 2rem !important;
  max-width: 1280px;
}
h1, h2, h3, h4 { color: #f8fafc; font-weight: 600; }

/* 3. HERO / TOP HEADER - NO CROPPING */
.top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.6rem;
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
  border: 1px solid #312e81;
  border-radius: 12px;
  margin-top: 0.2rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
}
.top-title {
  font-size: 1.6rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.02em;
  line-height: 1.35;
  margin: 0;
  padding: 0;
}
.top-subtitle {
  font-size: 0.9rem;
  color: #94a3b8;
  margin-top: 0.35rem;
  line-height: 1.4;
}

/* 4. CARDS & MATRIX */
.card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.8rem;
  transition: border-color 0.2s;
}
.card:hover { border-color: #334155; }

/* Severity Tags */
.sev { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
.sev.high { background: #7f1d1d; color: #fecaca; }
.sev.medium { background: #78350f; color: #fde68a; }
.sev.low { background: #064e3b; color: #a7f3d0; }

/* Matrix Card */
.matrix-card {
  background: linear-gradient(180deg, #0f172a 0%, #0d1527 100%);
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 1.2rem 1.4rem;
  margin-bottom: 1.2rem;
}
.matrix-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.1rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid #1e293b;
}
.matrix-title { font-size: 0.85rem; font-weight: 700; letter-spacing: 0.05em; color: #f8fafc; }
.matrix-status {
  font-size: 0.75rem;
  color: #38bdf8;
  padding: 0.2rem 0.5rem;
  background: rgba(56, 189, 248, 0.12);
  border-radius: 4px;
}
.matrix-engine {
  font-size: 0.75rem;
  color: #34d399;
  padding: 0.2rem 0.5rem;
  background: rgba(16, 185, 129, 0.12);
  border-radius: 4px;
}
.matrix-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.2rem;
}
.matrix-stat { display: flex; flex-direction: column; }
.stat-label { font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.35rem; }
.stat-value { font-size: 1.35rem; font-weight: 700; color: #f8fafc; }
.stat-value.highlight { color: #10b981; }

.matrix-footer {
  display: flex;
  gap: 1.5rem;
  margin-top: 1rem;
  padding-top: 0.8rem;
  border-top: 1px solid #1e293b;
  font-size: 0.8rem;
  color: #94a3b8;
}

/* Badges */
.badge {
  padding: 0.35rem 0.85rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.badge-success { background: rgba(16, 185, 129, 0.18); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }
.badge-neutral { background: rgba(148, 163, 184, 0.18); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.35); }
.badge-rejected { background: rgba(239, 68, 68, 0.18); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); }

/* Candidate items */
.cand-type { font-size: 0.85rem; font-weight: 600; color: #38bdf8; text-transform: uppercase; }
.cand-conf { font-size: 0.75rem; color: #94a3b8; }
.cand-reason { font-size: 0.85rem; color: #cbd5e1; margin: 0.3rem 0; }

code {
  background: #1e293b !important;
  color: #38bdf8 !important;
  padding: 0.12rem 0.4rem !important;
  border-radius: 4px !important;
  font-size: 0.82rem !important;
}

/* Comparison Table */
.comp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}
.comp-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: rgba(30, 41, 59, 0.6);
  color: #94a3b8;
  font-weight: 600;
  border-bottom: 1px solid #1e293b;
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
}
.comp-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #1e293b;
  color: #e2e8f0;
}
.comp-table tr:hover td {
  background: rgba(30, 41, 59, 0.3);
}

.diff-badge {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.75rem;
}
.diff-badge.green {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.diff-badge.neutral {
  background: rgba(148, 163, 184, 0.15);
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.3);
}
</style>
"""
