from __future__ import annotations

from pathlib import Path

import numpy as np

from gnn.graph_builder import NODE_TYPES
from gnn.model import PlanGNN, WEIGHTS
from rl.train import train as train_rl


def train_gnn(steps: int = 80) -> None:
    rng = np.random.default_rng(0)
    in_dim = len(NODE_TYPES) + 10
    model = PlanGNN(in_dim)
    w1, w2, clf = model.w1.copy(), model.w2.copy(), model.classifier.copy()
    lr = 0.05
    for _ in range(steps):
        n = int(rng.integers(3, 8))
        features = rng.normal(size=(n, in_dim))
        features[:, 0] = 0
        features[0, 0] = 1  # seq scan
        features[0, -1] = 2.0
        edges = [(i, min(i + 1, n - 1)) for i in range(n - 1)]
        emb = model.propagate(features, edges)
        scores = emb @ clf
        # push seq-scan node (0) to be highest
        target = np.zeros(n)
        target[0] = 1.0
        pred = np.exp(scores - scores.max())
        pred = pred / pred.sum()
        grad = pred - target
        clf = clf - lr * (emb.T @ grad)
        model.classifier = clf
        model.w1, model.w2 = w1, w2
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    np.savez(WEIGHTS, w1=w1, w2=w2, classifier=clf)
    print(f"Wrote {WEIGHTS}")


if __name__ == "__main__":
    train_gnn()
    print("RL bias", train_rl())
