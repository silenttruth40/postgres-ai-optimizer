from __future__ import annotations

from pathlib import Path
import numpy as np

from gnn.graph_builder import NODE_TYPES
from gnn.model import PlanGNN, WEIGHTS, BOTTLENECK_CLASSES
from rl.train import train as train_rl


def train_gnn(steps: int = 150) -> None:
    rng = np.random.default_rng(42)
    in_dim = len(NODE_TYPES) + 10  # 17 node types + 10 metrics
    model = PlanGNN(in_dim)
    
    lr = 0.02
    for step in range(steps):
        # Generate synthetic plan graphs with realistic bottlenecks
        n = int(rng.integers(3, 8))
        features = np.zeros((n, in_dim))
        
        # Scenario: Node 0 is Seq Scan with high rows and high exclusive time
        features[0, 0] = 1.0  # Seq Scan
        features[0, -1] = 0.75  # 75% of total time
        features[0, -7] = np.log1p(25000)  # 25,000 actual rows
        
        # Other nodes (Sort, Aggregate, Materialize)
        for i in range(1, n):
            op_idx = int(rng.integers(1, len(NODE_TYPES)))
            features[i, op_idx] = 1.0
            features[i, -1] = 0.25 / (n - 1)
            features[i, -7] = np.log1p(rng.integers(10, 500))
            
        edges = [(i - 1, i) for i in range(1, n)]
        
        # Forward pass
        embeddings, attn_w = model.propagate(features, edges)
        logits = embeddings @ model.classifier + model.cls_bias
        
        # Target: Node 0 is SEQ_SCAN_UNINDEXED (class 0)
        target = np.zeros_like(logits)
        target[0, 0] = 1.0  # SEQ_SCAN_UNINDEXED
        for i in range(1, n):
            target[i, 4] = 1.0  # NORMAL
            
        # Softmax cross entropy gradient
        exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)
        grad = (probs - target) / n
        
        # Update classifier and attention
        model.classifier -= lr * (embeddings.T @ grad)
        model.cls_bias -= lr * grad.sum(axis=0)

    # Save trained weights
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        WEIGHTS,
        w1=model.w1,
        b1=model.b1,
        attn_w=model.attn_w,
        w2=model.w2,
        b2=model.b2,
        classifier=model.classifier,
        cls_bias=model.cls_bias,
    )
    print(f"Successfully trained and saved GNN weights to {WEIGHTS}")


if __name__ == "__main__":
    train_gnn()
    print("RL bias:", train_rl())
