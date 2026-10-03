from __future__ import annotations

import streamlit as st


def kpi_row(items: list[tuple[str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def bottleneck_cards(bottlenecks: list[dict]) -> None:
    if not bottlenecks:
        st.info("No bottlenecks classified.")
        return
    cols = st.columns(min(3, len(bottlenecks)))
    for col, item in zip(cols, bottlenecks[:3]):
        with col:
            st.markdown(
                f"""
<div class="card">
  <div class="sev {item.get('severity','').lower()}">{item.get('severity')}</div>
  <h4>{item.get('type')}</h4>
  <p>{item.get('node')} {item.get('relation') or ''}</p>
  <small>{item.get('reason')}</small>
</div>
""",
                unsafe_allow_html=True,
            )


def candidate_card(candidate: dict) -> None:
    conf = int(round((candidate.get("confidence") or 0) * 100))
    cols = ", ".join(candidate.get("columns") or [])
    st.markdown(
        f"""
<div class="card">
  <h4>{candidate.get('type')}</h4>
  <p>{candidate.get('table') or ''} {('('+cols+')') if cols else ''}</p>
  <p>{candidate.get('reason')}</p>
  <small>Confidence: {conf}% · Sources: {', '.join(candidate.get('sources') or [])}</small>
</div>
""",
        unsafe_allow_html=True,
    )


CSS = """
<style>
.stApp { background: #0b1220; color: #e2e8f0; }
.block-container { padding-top: 1.4rem; }
h1, h2, h3 { color: #f8fafc; }
.hero { padding: 0.2rem 0 1rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1rem; }
.hero p { color: #94a3b8; }
.card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 0.9rem 1rem; margin-bottom: 0.8rem; }
.sev { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.sev.high { background: #7f1d1d; color: #fecaca; }
.sev.medium { background: #78350f; color: #fde68a; }
.sev.low { background: #064e3b; color: #a7f3d0; }
code, pre { font-size: 0.85rem; }
</style>
"""
