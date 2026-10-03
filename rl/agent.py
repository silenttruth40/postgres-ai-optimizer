from __future__ import annotations

from pathlib import Path

import numpy as np

from optimizer.candidate_generator import Candidate
from rl.environment import ACTIONS, OptimizerState
from rl.rewards import reward

WEIGHTS = Path(__file__).resolve().parents[1] / "data" / "rl_policy.npz"


class RankingAgent:
    def __init__(self) -> None:
        self.action_bias = {name: 0.0 for name in ACTIONS}
        self.action_bias["CREATE_COMPOSITE_INDEX"] = 0.25
        self.action_bias["CREATE_INDEX"] = 0.2
        self.action_bias["REWRITE_QUERY"] = 0.35
        self.action_bias["UPDATE_STATISTICS"] = 0.02
        self.action_bias["NO_CHANGE"] = -0.05
        self.action_bias["PARTITION"] = -0.1
        self.source = "Heuristic"
        self._maybe_load()

    def _maybe_load(self) -> None:
        if WEIGHTS.exists():
            payload = np.load(WEIGHTS, allow_pickle=True)
            stored = payload["bias"].item()
            self.action_bias.update(stored)
            self.source = "RL"

    def score(self, candidate: Candidate, state: OptimizerState) -> float:
        vec = state.vector()
        seq = vec[3]
        joins = vec[2]
        base = self.action_bias.get(candidate.type, 0.0) + candidate.confidence
        if candidate.type in {"CREATE_INDEX", "CREATE_COMPOSITE_INDEX"}:
            base += 0.15 * seq + 0.05 * joins
            base += reward(candidate.confidence * 40, index_columns=len(candidate.columns))
        if candidate.type == "REWRITE_QUERY":
            base += 0.25
            if "select *" in (candidate.rewritten_sql or "").lower():
                base -= 0.2
        return float(base)

    def rank(self, candidates: list[Candidate], state: OptimizerState) -> list[Candidate]:
        scored = []
        for cand in candidates:
            cand.confidence = max(0.05, min(0.99, cand.confidence * 0.5 + 0.5 * (self.score(cand, state) / 2 + 0.5)))
            if self.source not in cand.sources:
                cand.sources.append(self.source)
            scored.append((self.score(cand, state), cand))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [cand for _, cand in scored]


def get_agent() -> RankingAgent:
    return RankingAgent()
