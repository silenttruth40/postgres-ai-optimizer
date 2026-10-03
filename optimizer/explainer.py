from __future__ import annotations

from typing import Any

from backend.config import get_settings
from optimizer.bottleneck_detector import Bottleneck
from optimizer.candidate_generator import Candidate
from privacy.anonymizer import Anonymizer


def _explain_with_gemini(
    query_id: str,
    bottlenecks: list[Bottleneck],
    candidate: Candidate,
    anonymizer: Anonymizer,
    benchmark: dict | None,
) -> str | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    try:
        import httpx

        # Obfuscated / tokenized prompt: ZERO raw table names, column names, or literals are sent to Gemini!
        anon_table = anonymizer.table_token(candidate.table) if candidate.table else "table_target"
        anon_cols = [anonymizer.column_token(c) for c in candidate.columns]
        improvement = benchmark.get("improvement_percent") if benchmark else None
        imp_str = f"{improvement:.1f}% measured speedup" if improvement is not None else "simulated improvement"

        prompt = (
            f"You are a PostgreSQL database optimization AI. "
            f"Explain the following database performance intervention in 3-4 concise sentences for a DBA:\n"
            f"- Action Type: {candidate.type}\n"
            f"- Target Table: {anon_table}\n"
            f"- Target Columns: {', '.join(anon_cols)}\n"
            f"- Measured Speedup: {imp_str}\n"
            f"- Detected Bottlenecks: {', '.join(b.type for b in bottlenecks[:2])}\n"
            f"Explain why this intervention resolves the bottleneck and what write/storage overhead trade-offs to expect. "
            f"Use the tokenized table and column identifiers exactly as provided."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        res = httpx.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10.0)
        if res.status_code == 200:
            data = res.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Reverse-map / re-hash Gemini's tokenized response back to the user's real schema
            return anonymizer.deanonymize_text(raw_text)
    except Exception:
        pass
    return None


def explain_recommendation(
    query_id: str,
    bottlenecks: list[Bottleneck],
    candidate: Candidate,
    anonymizer: Anonymizer | None = None,
    benchmark: dict | None = None,
) -> dict[str, Any]:
    anon = anonymizer or Anonymizer()
    top = bottlenecks[0] if bottlenecks else None
    why_slow = (
        f"{top.reason} on {top.node}" + (f" ({top.relation})" if top and top.relation else "")
        if top
        else "No dominant bottleneck was classified."
    )
    evidence_lines = []
    for item in bottlenecks[:4]:
        evidence_lines.append(
            f"- {item.severity} {item.type}: {item.reason} evidence={item.evidence}"
        )
    if candidate.type in {"CREATE_INDEX", "CREATE_COMPOSITE_INDEX"}:
        cols = ", ".join(candidate.columns)
        rec_text = f"Create index on {candidate.table}({cols})."
        expected = "Potential reduction in rows scanned and faster join/filter execution."
    elif candidate.type == "REWRITE_QUERY":
        rec_text = "Rewrite the SQL to a safer equivalent shape."
        expected = "Lower tuple width or a more efficient join shape."
    elif candidate.type == "UPDATE_STATISTICS":
        rec_text = f"Run ANALYZE on {candidate.table}."
        expected = "Better row estimates and plan choices. Label: Estimated until benchmarked."
    elif candidate.type == "JOIN_STRATEGY":
        rec_text = "Prefer hash join over nested loop for this plan shape."
        expected = "Lower join time on large inputs. Label: Estimated until benchmarked."
    elif candidate.type == "PARTITION":
        rec_text = f"Consider range partitioning {candidate.table} by created_at."
        expected = "Estimated only; not auto-applied in the sandbox."
    else:
        rec_text = "Leave the schema unchanged."
        expected = "No measured improvement is claimed."

    validation = "The recommendation is tested in the sandbox before being marked VALIDATED."
    if benchmark:
        status = benchmark.get("validation_status")
        improvement = benchmark.get("improvement_percent")
        if improvement is None:
            validation = f"Sandbox status: {status}."
        else:
            validation = (
                f"Sandbox status: {status}. Measured improvement: {improvement:.2f}% "
                "(PostgreSQL EXPLAIN ANALYZE)."
            )

    default_text = f"""Recommendation:
{rec_text}

Why the query is slow:
{why_slow}

Why this recommendation:
{candidate.reason}

Evidence:
{chr(10).join(evidence_lines) or '- No bottleneck evidence'}

Expected impact:
{expected}

Validation:
{validation}

Sources:
{', '.join(candidate.sources) or 'GNN + RL'}
"""

    engine = "deterministic_gnn_local"
    gemini_explanation = _explain_with_gemini(query_id, bottlenecks, candidate, anon, benchmark)
    if gemini_explanation:
        final_text = gemini_explanation
        engine = f"gemini ({get_settings().gemini_model}) via zero-data privacy bridge"
    else:
        final_text = default_text.strip()

    payload = {
        "query_id": query_id,
        "recommendation": rec_text,
        "why_slow": why_slow,
        "why_recommendation": candidate.reason,
        "expected_impact": expected,
        "evidence": [b.to_dict() for b in bottlenecks],
        "text": final_text,
        "engine": engine,
    }
    if anonymizer:
        payload["anonymized_for_ai"] = {
            "query_id": query_id,
            "candidate_type": candidate.type,
            "columns": [anonymizer.column_token(c) for c in candidate.columns],
            "table": anonymizer.table_token(candidate.table) if candidate.table else None,
        }
    return payload
