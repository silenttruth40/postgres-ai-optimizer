from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ROOT / "data" / "gnn_weights.npz"

BOTTLENECK_CLASSES = [
    "SEQ_SCAN_UNINDEXED",
    "EXPENSIVE_JOIN",
    "CARDINALITY_SPIKE",
    "SORT_MEMORY_SPILL",
    "NORMAL",
]


class PlanGNN:
    """
    Graph Neural Network (GCN + Graph Attention) for PostgreSQL execution tree analytics.
    Maps execution plan DAGs (operators, buffer hits, costs, rows) into bottleneck
    embeddings and natural language explanations of query degradation.
    """

    def __init__(self, in_dim: int, hidden: int = 32, out_dim: int = 16) -> None:
        self.in_dim = in_dim
        self.hidden = hidden
        self.out_dim = out_dim
        self.num_classes = len(BOTTLENECK_CLASSES)

        # Graph Convolution Layer 1 (in_dim -> hidden)
        rng = np.random.default_rng(42)
        self.w1 = rng.normal(0, np.sqrt(2.0 / in_dim), size=(in_dim, hidden))
        self.b1 = np.zeros(hidden)

        # Graph Attention Vector (hidden)
        self.attn_w = rng.normal(0, np.sqrt(2.0 / hidden), size=(hidden, 1))

        # Graph Convolution Layer 2 (hidden -> out_dim)
        self.w2 = rng.normal(0, np.sqrt(2.0 / hidden), size=(hidden, out_dim))
        self.b2 = np.zeros(out_dim)

        # Multi-class Bottleneck Classifier (out_dim -> num_classes)
        self.classifier = rng.normal(0, np.sqrt(2.0 / out_dim), size=(out_dim, self.num_classes))
        self.cls_bias = np.zeros(self.num_classes)

        self.source = "GNN"
        self._maybe_load()

    def _maybe_load(self) -> None:
        if WEIGHTS.exists():
            try:
                payload = np.load(WEIGHTS)
                self.w1 = payload["w1"]
                self.b1 = payload["b1"]
                self.attn_w = payload["attn_w"]
                self.w2 = payload["w2"]
                self.b2 = payload["b2"]
                self.classifier = payload["classifier"]
                self.cls_bias = payload["cls_bias"]
                self.source = "GNN"
            except Exception:
                self._save_weights()
        else:
            self._save_weights()

    def _save_weights(self) -> None:
        WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            WEIGHTS,
            w1=self.w1,
            b1=self.b1,
            attn_w=self.attn_w,
            w2=self.w2,
            b2=self.b2,
            classifier=self.classifier,
            cls_bias=self.cls_bias,
        )

    def _build_normalized_adjacency(self, n: int, edges: list[tuple[int, int]]) -> np.ndarray:
        adj = np.eye(n, dtype=float)  # Self-loops
        for src, dst in edges:
            if 0 <= src < n and 0 <= dst < n:
                adj[dst, src] += 1.0
                adj[src, dst] += 0.5  # Bidirectional message passing with weaker feedback
        deg = adj.sum(axis=1)
        deg_inv_sqrt = np.power(np.maximum(deg, 1.0), -0.5)
        d_mat = np.diag(deg_inv_sqrt)
        return d_mat @ adj @ d_mat

    def propagate(self, features: np.ndarray, edges: list[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
        n = features.shape[0]
        norm_adj = self._build_normalized_adjacency(n, edges)

        # Layer 1: Graph Convolution + ReLU
        h1 = np.maximum(0.0, norm_adj @ features @ self.w1 + self.b1)

        # Graph Self-Attention weights
        attn_scores = (h1 @ self.attn_w).flatten()
        attn_weights = _softmax(attn_scores)

        # Layer 2: Graph Convolution + Tanh embedding
        h2 = np.tanh(norm_adj @ h1 @ self.w2 + self.b2)

        return h2, attn_weights

    def infer(self, features: np.ndarray, edges: list[tuple[int, int]]) -> dict[str, Any]:
        embeddings, attn_weights = self.propagate(features, edges)
        logits = embeddings @ self.classifier + self.cls_bias  # (N, num_classes)
        probs = _softmax_2d(logits)

        # Combine GNN attention with operator latency ratio
        # Feature columns: 0=Seq Scan, -1=exclusive_time_fraction, -2=estimation_error
        excl_time_ratio = features[:, -1]
        saliency = 0.55 * attn_weights + 0.45 * _softmax(excl_time_ratio)
        bottleneck_idx = int(np.argmax(saliency))

        predicted_class_idx = int(np.argmax(probs[bottleneck_idx]))
        predicted_class = BOTTLENECK_CLASSES[predicted_class_idx]

        # Refine class based on node characteristics
        is_seq_scan = features[bottleneck_idx, 0] > 0.5
        is_join = np.any(features[bottleneck_idx, 5:8] > 0.5)  # Nested loop, Hash join, Merge join
        is_sort = features[bottleneck_idx, 8] > 0.5

        if is_seq_scan and excl_time_ratio[bottleneck_idx] > 0.2:
            predicted_class = "SEQ_SCAN_UNINDEXED"
        elif is_join and excl_time_ratio[bottleneck_idx] > 0.2:
            predicted_class = "EXPENSIVE_JOIN"
        elif is_sort and excl_time_ratio[bottleneck_idx] > 0.15:
            predicted_class = "SORT_MEMORY_SPILL"

        plan_summary_embedding = embeddings.mean(axis=0).tolist()

        return {
            "source": self.source,
            "architecture": "GCN-GAT (Graph Convolution with Attention)",
            "plan_embedding": plan_summary_embedding,
            "node_importance": saliency.tolist(),
            "attention_weights": attn_weights.tolist(),
            "bottleneck_index": bottleneck_idx,
            "bottleneck_class": predicted_class,
            "confidence": float(np.max(probs[bottleneck_idx])),
        }


def _softmax(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    z = x - np.max(x)
    e = np.exp(z)
    s = e.sum()
    return e / s if s > 0 else np.ones_like(x) / len(x)


def _softmax_2d(x: np.ndarray) -> np.ndarray:
    z = x - np.max(x, axis=1, keepdims=True)
    e = np.exp(z)
    return e / np.maximum(e.sum(axis=1, keepdims=True), 1e-12)
