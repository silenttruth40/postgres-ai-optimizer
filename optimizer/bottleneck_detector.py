from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.models import ExecutionNode, ParsedPlan


@dataclass
class Bottleneck:
    type: str
    severity: str
    node: str
    relation: str | None
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "node": self.node,
            "relation": self.relation,
            "reason": self.reason,
            "evidence": self.evidence,
        }


def detect_bottlenecks(plan: ParsedPlan) -> list[Bottleneck]:
    findings: list[Bottleneck] = []
    total = max(plan.metrics.execution_time_ms, 0.001)
    for node in plan.root.flatten():
        share = node.exclusive_time / total
        findings.extend(_seq_scan(node, share))
        findings.extend(_join(node, share))
        findings.extend(_sort(node, share))
        findings.extend(_cardinality(node))
        findings.extend(_buffers(node, share))
        findings.extend(_nested_loop(node, share))
        findings.extend(_aggregate(node, share))
    findings.sort(key=lambda b: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(b.severity, 3))
    return _dedupe(findings)


def _seq_scan(node: ExecutionNode, share: float) -> list[Bottleneck]:
    if node.node_type != "Seq Scan" or not node.relation:
        return []
    if node.actual_rows < 200 and share < 0.15:
        return []
    severity = "HIGH" if node.actual_rows >= 1000 or share >= 0.25 else "MEDIUM"
    return [
        Bottleneck(
            type="MISSING_INDEX",
            severity=severity,
            node=node.node_type,
            relation=node.relation,
            reason="Large filtered table scanned sequentially",
            evidence={
                "actual_rows": node.actual_rows,
                "plan_rows": node.plan_rows,
                "execution_time_ms": round(node.exclusive_time, 3),
                "filter": node.filter,
                "source": "Measured",
            },
        )
    ]


def _join(node: ExecutionNode, share: float) -> list[Bottleneck]:
    if "Join" not in node.node_type and "Nested Loop" not in node.node_type:
        return []
    if node.actual_rows < 1000 and share < 0.2:
        return []
    return [
        Bottleneck(
            type="EXPENSIVE_JOIN",
            severity="HIGH" if share >= 0.3 else "MEDIUM",
            node=node.node_type,
            relation=node.relation,
            reason="Join processed a large intermediate result",
            evidence={
                "actual_rows": node.actual_rows,
                "execution_time_ms": round(node.exclusive_time, 3),
                "join_type": node.join_type,
                "hash_cond": node.hash_cond,
                "source": "Measured",
            },
        )
    ]


def _sort(node: ExecutionNode, share: float) -> list[Bottleneck]:
    if node.node_type != "Sort":
        return []
    if share < 0.08 and node.actual_rows < 1000:
        return []
    return [
        Bottleneck(
            type="SORT_BOTTLENECK",
            severity="HIGH" if share >= 0.2 else "MEDIUM",
            node=node.node_type,
            relation=node.relation,
            reason="Expensive sort on a large row set",
            evidence={
                "actual_rows": node.actual_rows,
                "execution_time_ms": round(node.exclusive_time, 3),
                "temp_read_blocks": node.temp_read_blocks,
                "source": "Measured",
            },
        )
    ]


def _cardinality(node: ExecutionNode) -> list[Bottleneck]:
    if node.plan_rows <= 0:
        return []
    error = node.estimation_error
    if error < 10:
        return []
    return [
        Bottleneck(
            type="CARDINALITY_MISESTIMATION",
            severity="MEDIUM" if error < 100 else "HIGH",
            node=node.node_type,
            relation=node.relation,
            reason="Estimated rows differ sharply from actual rows",
            evidence={
                "estimated_rows": node.plan_rows,
                "actual_rows": node.actual_rows,
                "estimation_error": round(error, 2),
                "source": "Measured",
            },
        )
    ]


def _buffers(node: ExecutionNode, share: float) -> list[Bottleneck]:
    reads = node.shared_read_blocks
    hits = node.shared_hit_blocks
    if reads < 200:
        return []
    ratio = reads / max(reads + hits, 1)
    if ratio < 0.3:
        return []
    return [
        Bottleneck(
            type="BUFFER_PRESSURE",
            severity="MEDIUM",
            node=node.node_type,
            relation=node.relation,
            reason="High shared buffer reads relative to hits",
            evidence={
                "shared_read_blocks": reads,
                "shared_hit_blocks": hits,
                "read_ratio": round(ratio, 3),
                "source": "Measured",
            },
        )
    ]


def _nested_loop(node: ExecutionNode, share: float) -> list[Bottleneck]:
    if "Nested Loop" not in node.node_type:
        return []
    inner_rows = sum(child.actual_rows for child in node.children)
    if inner_rows < 500 and share < 0.2:
        return []
    return [
        Bottleneck(
            type="NESTED_LOOP",
            severity="HIGH" if inner_rows >= 5000 or share >= 0.25 else "MEDIUM",
            node=node.node_type,
            relation=node.relation,
            reason="Nested loop over large inputs",
            evidence={
                "actual_rows": node.actual_rows,
                "child_rows": inner_rows,
                "execution_time_ms": round(node.exclusive_time, 3),
                "source": "Measured",
            },
        )
    ]


def _aggregate(node: ExecutionNode, share: float) -> list[Bottleneck]:
    if node.node_type not in {"Aggregate", "HashAggregate"}:
        return []
    if share < 0.15 and node.actual_rows < 1000:
        return []
    return [
        Bottleneck(
            type="AGGREGATION_BOTTLENECK",
            severity="MEDIUM",
            node=node.node_type,
            relation=node.relation,
            reason="Aggregation processed a large input",
            evidence={
                "actual_rows": node.actual_rows,
                "execution_time_ms": round(node.exclusive_time, 3),
                "source": "Measured",
            },
        )
    ]


def _dedupe(items: list[Bottleneck]) -> list[Bottleneck]:
    seen: set[tuple] = set()
    out: list[Bottleneck] = []
    for item in items:
        key = (item.type, item.node, item.relation, item.reason)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
