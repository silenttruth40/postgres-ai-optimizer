from __future__ import annotations

from typing import Any
import streamlit as st


def performance_matrix_card(bench: dict[str, Any]) -> None:
    """Renders a sleek minimalist performance improvement matrix."""
    baseline = bench.get("baseline") or {}
    optimized = bench.get("optimized") or {}
    improvement = bench.get("improvement_percent")
    status = bench.get("validation_status") or "UNKNOWN"
    write_overhead = bench.get("write_latency_overhead_ms", 0.0)
    storage_mb = bench.get("storage_overhead_mb", 0.0)

    base_time = baseline.get("execution_time_ms", 0.0)
    opt_time = optimized.get("execution_time_ms", 0.0) if optimized else base_time

    # Determine badge color & text
    if improvement is not None and improvement > 5:
        badge_class = "badge-success"
        badge_text = f"+{improvement:.1f}% FASTER"
    elif improvement is not None and improvement >= 0:
        badge_class = "badge-neutral"
        badge_text = "NEUTRAL (0.0%)"
    else:
        badge_class = "badge-rejected"
        badge_text = "REJECTED (DEGRADED)"

    st.markdown(
        f"""
<div class="matrix-card">
  <div class="matrix-header">
    <div>
      <span class="matrix-title">SIMULATED BENCHMARK MATRIX</span>
      <span class="matrix-status">{status}</span>
    </div>
    <div class="badge {badge_class}">{badge_text}</div>
  </div>
  <div class="matrix-grid">
    <div class="matrix-stat">
      <span class="stat-label">Baseline Latency</span>
      <span class="stat-value">{base_time:.2f} ms</span>
    </div>
    <div class="matrix-stat">
      <span class="stat-label">Optimized Latency</span>
      <span class="stat-value highlight">{opt_time:.2f} ms</span>
    </div>
    <div class="matrix-stat">
      <span class="stat-label">Write Overhead</span>
      <span class="stat-value">+{write_overhead:.1f} ms</span>
    </div>
    <div class="matrix-stat">
      <span class="stat-label">Storage Impact</span>
      <span class="stat-value">+{storage_mb:.1f} MB</span>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def candidate_card(candidate: dict[str, Any]) -> None:
    conf = int(round((candidate.get("confidence") or 0) * 100))
    cols = ", ".join(candidate.get("columns") or [])
    kind = candidate.get("type", "")
    sources = ", ".join(candidate.get("sources") or [])
    
    table_info = f"<code>{candidate.get('table', '')}</code>" if candidate.get("table") else ""
    col_info = f"({', '.join(f'<code>{c}</code>' for c in (candidate.get('columns') or []))})" if cols else ""

    st.markdown(
        f"""
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
    <span class="cand-type">{kind}</span>
    <span class="cand-conf">{conf}% Confidence</span>
  </div>
  <div style="margin-bottom:0.4rem;">{table_info} {col_info}</div>
  <p class="cand-reason">{candidate.get('reason', '')}</p>
  <small style="color:#64748b;">Sources: {sources or 'Heuristic + RL'}</small>
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
/* Minimalist Dark Theme */
.stApp { background: #080d1a; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.block-container { padding-top: 1.2rem; max-width: 1200px; }
h1, h2, h3, h4 { color: #f8fafc; font-weight: 600; }

/* Top Header */
.top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 0;
  border-bottom: 1px solid #1e293b;
  margin-bottom: 1.2rem;
}
.top-title { font-size: 1.35rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em; }
.top-subtitle { font-size: 0.85rem; color: #64748b; margin-top: 0.2rem; }

/* Minimalist Card */
.card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 0.9rem 1rem;
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
  border-radius: 8px;
  padding: 1.1rem 1.2rem;
  margin-bottom: 1rem;
}
.matrix-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid #1e293b;
}
.matrix-title { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em; color: #94a3b8; }
.matrix-status {
  font-size: 0.75rem;
  color: #38bdf8;
  margin-left: 0.6rem;
  padding: 0.15rem 0.45rem;
  background: rgba(56, 189, 248, 0.1);
  border-radius: 4px;
}
.matrix-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}
.matrix-stat { display: flex; flex-direction: column; }
.stat-label { font-size: 0.75rem; color: #64748b; margin-bottom: 0.3rem; }
.stat-value { font-size: 1.25rem; font-weight: 700; color: #f8fafc; }
.stat-value.highlight { color: #10b981; }

/* Badges */
.badge {
  padding: 0.3rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.badge-success { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-neutral { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }
.badge-rejected { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

/* Candidate items */
.cand-type { font-size: 0.85rem; font-weight: 600; color: #38bdf8; }
.cand-conf { font-size: 0.75rem; color: #94a3b8; }
.cand-reason { font-size: 0.85rem; color: #cbd5e1; margin: 0.2rem 0; }

code {
  background: #1e293b !important;
  color: #38bdf8 !important;
  padding: 0.1rem 0.35rem !important;
  border-radius: 4px !important;
  font-size: 0.82rem !important;
}
</style>
"""
