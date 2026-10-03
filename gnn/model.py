from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ROOT / "data" / "gnn_weights.npz"


class PlanGNN:
    """Two-layer graph convolution. Uses NumPy weights; optional PyG/Torch."""

    def __init__(self, in_dim: int, hidden: int = 32, out_dim: int = 16) -> None:
        rng = np.random.default_rng(7)
        self.w1 = rng.normal(0, 0.1, size=(in_dim, hidden))
        self.w2 = rng.normal(0, 0.1, size=(hidden, out_dim))
        self.classifier = rng.normal(0, 0.1, size=(out_dim,))
        self.source = "Heuristic"
        self._maybe_load()

    def _maybe_load(self) -> None:
        if WEIGHTS.exists():
            payload = np.load(WEIGHTS)
            self.w1 = payload["w1"]
            self.w2 = payload["w2"]
            self.classifier = payload["classifier"]
            self.source = "GNN"

    def propagate(self, features: np.ndarray, edges: list[tuple[int, int]]) -> np.ndarray:
        n = features.shape[0]
        adj = np.eye(n)
        for src, dst in edges:
            adj[dst, src] += 1.0
            adj[src, src] += 0.0
        deg = adj.sum(axis=1, keepdims=True).clip(min=1.0)
        norm = adj / deg
        h = np.tanh(norm @ features @ self.w1)
        return np.tanh(norm @ h @ self.w2)

    def infer(self, features: np.ndarray, edges: list[tuple[int, int]]) -> dict:
        embeddings = self.propagate(features, edges)
        scores = embeddings @ self.classifier
        # Blend with exclusive-time so untrained weights still highlight slow nodes.
        time_col = features[:, -1]
        importance = 0.65 * _softmax(time_col) + 0.35 * _softmax(scores)
        bottleneck_idx = int(np.argmax(importance))
        return {
            "source": self.source,
            "plan_embedding": embeddings.mean(axis=0).tolist(),
            "node_importance": importance.tolist(),
            "bottleneck_index": bottleneck_idx,
            "bottleneck_class": "SEQ_SCAN" if features[bottleneck_idx, 0] > 0.5 else "OTHER",
        }


def _softmax(x: np.ndarray) -> np.ndarray:
    z = x - np.max(x)
    e = np.exp(z)
    return e / e.sum()
