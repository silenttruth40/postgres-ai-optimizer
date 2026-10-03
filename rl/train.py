from __future__ import annotations

from pathlib import Path

import numpy as np

from rl.environment import ACTIONS
from rl.rewards import reward

OUT = Path(__file__).resolve().parents[1] / "data" / "rl_policy.npz"


def train(episodes: int = 200) -> dict[str, float]:
    rng = np.random.default_rng(42)
    bias = {name: 0.0 for name in ACTIONS}
    for _ in range(episodes):
        seq_scans = rng.integers(0, 4)
        improvement = float(rng.uniform(-20, 70))
        for action in ACTIONS:
            if action in {"CREATE_INDEX", "CREATE_COMPOSITE_INDEX"} and seq_scans:
                r = reward(max(improvement, 5), index_columns=2 if "COMPOSITE" in action else 1)
            elif action == "NO_CHANGE":
                r = reward(0)
            else:
                r = reward(improvement * 0.1)
            bias[action] = 0.9 * bias[action] + 0.1 * r
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez(OUT, bias=bias)
    return bias


if __name__ == "__main__":
    print(train())
