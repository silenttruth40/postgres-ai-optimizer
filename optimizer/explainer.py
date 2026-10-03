from __future__ import annotations

from optimizer.candidate_generator import Candidate
from optimizer.bottleneck_detector import Bottleneck
from privacy.anonymizer import Anonymizer


def explain_recommendation(
    query_id: str,
    bottlenecks: list[Bottleneck],
    candidate: Candidate,
    anonymizer: Anonymizer | None = None,
    benchmark: dict | None = None,
) -> dict:
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

    text = f"""Recommendation:
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
{', '.join(candidate.sources) or 'Heuristic'}
"""
    payload = {
        "query_id": query_id,
        "recommendation": rec_text,
        "why_slow": why_slow,
        "why_recommendation": candidate.reason,
        "expected_impact": expected,
        "evidence": [b.to_dict() for b in bottlenecks],
        "text": text.strip(),
        "engine": "deterministic_local",
    }
    if anonymizer:
        payload["anonymized_for_ai"] = {
            "query_id": query_id,
            "candidate_type": candidate.type,
            "columns": [anonymizer.column_token(c) for c in candidate.columns],
            "table": anonymizer.table_token(candidate.table) if candidate.table else None,
        }
    return payload
