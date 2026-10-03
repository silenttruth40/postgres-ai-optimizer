from __future__ import annotations

from backend.models import ParsedPlan
from optimizer.bottleneck_detector import detect_bottlenecks
from optimizer.candidate_generator import generate_candidates


def analyze_plan(sql: str, plan: ParsedPlan, existing_indexes=None):
    bottlenecks = detect_bottlenecks(plan)
    candidates = generate_candidates(sql, plan, bottlenecks, existing_indexes)
    return bottlenecks, candidates
