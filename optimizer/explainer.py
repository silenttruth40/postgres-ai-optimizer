from __future__ import annotations

import logging
import os
from typing import Any

from backend.config import get_settings
from optimizer.bottleneck_detector import Bottleneck
from optimizer.candidate_generator import Candidate
from privacy.anonymizer import Anonymizer

logger = logging.getLogger("optimizer.explainer")

_RETIRED_MODELS = {
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
}

_FALLBACK_MODELS = (
    "gemini-2.5-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
)


def _resolve_api_key() -> str:
    settings = get_settings()
    return (settings.gemini_api_key or os.environ.get("GEMINI_API_KEY") or "").strip()


def _model_candidates() -> list[str]:
    settings = get_settings()
    configured = (settings.gemini_model or os.environ.get("GEMINI_MODEL") or "").strip()
    if configured.lower() in _RETIRED_MODELS:
        logger.warning("Configured Gemini model %s is retired; using current Flash models", configured)
        configured = ""
    ordered: list[str] = []
    for name in (configured, *_FALLBACK_MODELS):
        if name and name not in ordered and name.lower() not in _RETIRED_MODELS:
            ordered.append(name)
    return ordered or list(_FALLBACK_MODELS)


def _extract_gemini_text(data: dict[str, Any]) -> str | None:
    candidates_list = data.get("candidates") or []
    if not candidates_list:
        feedback = data.get("promptFeedback") or {}
        reason = feedback.get("blockReason") or data.get("error", {}).get("message")
        if reason:
            logger.warning("Gemini returned no candidates: %s", reason)
        return None
    content = candidates_list[0].get("content") or {}
    parts = content.get("parts") or []
    chunks: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            chunks.append(text.strip())
    if chunks:
        return "\n".join(chunks).strip()
    finish = candidates_list[0].get("finishReason")
    logger.warning("Gemini candidate had no text parts (finishReason=%s)", finish)
    return None


def _build_prompt(
    query_id: str,
    bottlenecks: list[Bottleneck],
    candidate: Candidate,
    anonymizer: Anonymizer,
    benchmark: dict | None,
    sql: str | None,
) -> str:
    anon_table = anonymizer.table_token(candidate.table) if candidate.table else "table_target"
    anon_cols = [anonymizer.column_token(c) for c in candidate.columns]
    anon_sql = anonymizer.anonymize_query(sql) if sql else ""
    anon_reason_text = anonymizer.anonymize_query(candidate.reason) if candidate.reason else ""
    anon_ddl = anonymizer.anonymize_query(candidate.sql) if candidate.sql else ""
    anon_rewrite = anonymizer.anonymize_query(candidate.rewritten_sql) if candidate.rewritten_sql else ""

    improvement = benchmark.get("improvement_percent") if benchmark else None
    status = (benchmark or {}).get("validation_status") or "not_benchmarked"
    imp_str = f"{improvement:.1f}% measured speedup" if improvement is not None else "plan-level estimate only"

    bottleneck_lines = []
    for item in bottlenecks[:4]:
        relation = anonymizer.table_token(item.relation) if item.relation else "unknown_relation"
        bottleneck_lines.append(
            f"- {item.severity} {item.type} on {item.node} / {relation}: {anonymizer.anonymize_query(item.reason)}"
        )

    prompt = (
        "You are a PostgreSQL performance specialist. Write a unique 4-6 sentence explanation "
        "for a DBA about THIS specific query and intervention. Do not reuse a generic template. "
        "Never invent table or column names other than the tokens provided.\n\n"
        f"Query id: {query_id}\n"
        f"Anonymized SQL:\n{anon_sql or '(not provided)'}\n\n"
        f"Action type: {candidate.type}\n"
        f"Target table token: {anon_table}\n"
        f"Target column tokens: {', '.join(anon_cols) or '(none)'}\n"
        f"Candidate reason: {anon_reason_text or '(none)'}\n"
        f"Proposed DDL: {anon_ddl or '(none)'}\n"
        f"Rewritten SQL: {anon_rewrite or '(none)'}\n"
        f"Sandbox status: {status}; {imp_str}\n"
        f"Detected bottlenecks:\n{chr(10).join(bottleneck_lines) or '- none classified'}\n\n"
        "Explain why this query is slow, why this action helps, and the write/storage trade-off. "
        "Use the tokenized identifiers exactly as given."
    )
    return prompt


def _explain_with_gemini(
    query_id: str,
    bottlenecks: list[Bottleneck],
    candidate: Candidate,
    anonymizer: Anonymizer,
    benchmark: dict | None,
    sql: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Return (text, error, model_used)."""
    api_key = _resolve_api_key()
    if not api_key:
        return None, "Gemini API key is not configured", None

    try:
        import httpx
    except Exception as exc:
        return None, f"httpx is unavailable: {exc}", None

    prompt = _build_prompt(query_id, bottlenecks, candidate, anonymizer, benchmark, sql)
    last_error = "Gemini request failed"
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    payloads = [
        {
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 640},
        },
        {"contents": contents},
    ]

    for model in _model_candidates():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for payload in payloads:
            try:
                res = httpx.post(
                    url,
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=20.0,
                )
            except Exception as exc:
                last_error = f"Gemini request error for {model}: {exc}"
                logger.warning(last_error)
                break

            if res.status_code == 200:
                try:
                    text = _extract_gemini_text(res.json())
                except Exception as exc:
                    last_error = f"Could not parse Gemini response: {exc}"
                    logger.warning(last_error)
                    break
                if text:
                    return anonymizer.deanonymize_text(text), None, model
                last_error = f"Gemini model {model} returned an empty explanation"
                break

            body = (res.text or "")[:240]
            last_error = f"Gemini API status {res.status_code} for {model}: {body}"
            logger.warning(last_error)
            if res.status_code == 400:
                continue
            if res.status_code != 404:
                return None, last_error, None
            break

    return None, last_error, None


def explain_recommendation(
    query_id: str,
    bottlenecks: list[Bottleneck],
    candidate: Candidate,
    anonymizer: Anonymizer | None = None,
    benchmark: dict | None = None,
    sql: str | None = None,
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
    gemini_explanation, gemini_error, gemini_model = _explain_with_gemini(
        query_id, bottlenecks, candidate, anon, benchmark, sql
    )
    if gemini_explanation:
        final_text = gemini_explanation
        engine = f"gemini ({gemini_model}) via zero-data privacy bridge"
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
        "gemini_error": gemini_error,
    }
    if anonymizer:
        payload["anonymized_for_ai"] = {
            "query_id": query_id,
            "candidate_type": candidate.type,
            "columns": [anonymizer.column_token(c) for c in candidate.columns],
            "table": anonymizer.table_token(candidate.table) if candidate.table else None,
            "sql": anonymizer.anonymize_query(sql) if sql else None,
        }
    return payload
