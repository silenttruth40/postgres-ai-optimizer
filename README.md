# PostgreSQL AI Performance Optimizer
> **Problem Statement 4**: Zero-Data Privacy · Graph Neural Networks (GNN) · Reinforcement Learning (RL) · Sandbox Validation

An AI-driven query tuning and execution plan analysis platform that enforces **strict zero-exposure data guardrails**. The system converts raw SQL queries and PostgreSQL execution plans into bitmasked, tokenized structural hashes before AI processing, predicts bottlenecks via a Graph Neural Network (GCN + GAT), ranks recommendations via Reinforcement Learning, and verifies improvements in an isolated PostgreSQL sandbox.

---

## Architecture Overview

```
[Raw User Query (DBA)]
        │  (e.g., SELECT * FROM orders WHERE customer_id = 42...)
        ▼
[Data Obfuscation & Bitmasking Layer] 
        │  • Literals/PII stripped to <REDACTED>
        │  • Tables/Columns converted to structural tokens (table_001, column_002)
        ▼
[Execution Tree Analytics Module (GNN)]
        │  • GCN-GAT with operator attention saliency (%)
        │  • Identifies dominant bottleneck operator (Seq Scan, Hash Join, Sort Spill)
        ▼
[AI & RL Optimization Agent]
        │  • Ranks candidate indexes (composite, partial), query rewrites, and partition strategies
        ▼
[PostgreSQL Simulation Sandbox]
        │  • Executes EXPLAIN ANALYZE in sandbox container (port 5433)
        │  • Calculates % speedup, write-latency overhead (+ms), and storage footprint (+MB)
        ▼
[Reverse-Mapping / Re-Hashing Engine]
        │  • Safely translates tokenized recommendations back to real database schema
        ▼
[Minimalist Interactive Dashboard]
        • Side-by-side SQL comparison (Original vs Rewritten SQL / Index DDL)
        • Simulated Performance Improvement Matrix (+XX% Faster)
        • Zero-Exposure Privacy Audit Proof
```

---

## Quick Start Guide

### Option 1: Run with Docker Compose (Recommended)

Requires Docker Desktop installed and running.

```bash
# 1. Build and start all 4 services (postgres, sandbox-postgres, backend, dashboard)
docker compose up --build

# 2. Access the applications:
#    - Interactive Dashboard: http://localhost:8501
#    - FastAPI Swagger Docs:  http://localhost:8000/docs
```

---

### Option 2: Run Locally with Python (.venv)

A local virtual environment `.venv` has already been pre-configured with all dependencies.

#### 1. Configure Environment
Open `.env` and set your configuration (and optional Gemini API key):
```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
SANDBOX_POSTGRES_PORT=5433
GEMINI_API_KEY=your_gemini_key_here
```

#### 2. Start PostgreSQL Databases (via Docker or local PostgreSQL)
```bash
docker compose up -d postgres sandbox-postgres
```

#### 3. Seed Realistic High-Volume Dataset (100,000+ Rows)
```powershell
.\.venv\Scripts\python scripts/load_real_dataset.py --mode realistic --rows 100000
```

#### 4. Start the Backend API
```powershell
.\.venv\Scripts\uvicorn backend.main:app --port 8000 --reload
```

#### 5. Start the Streamlit Dashboard (In a new terminal)
```powershell
.\.venv\Scripts\streamlit run dashboard/app.py
```

Open your browser at **http://localhost:8501**.

---

## Running Automated Tests

Run the full pytest suite (18 unit tests covering privacy obfuscation, reverse-mapping, API endpoints, GNN inference, and sandbox validation):

```powershell
.\.venv\Scripts\pytest
```

---

## Retraining the GNN and RL Models

To regenerate model weights in `data/gnn_weights.npz` and `data/rl_policy.npz`:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python scripts/train_models.py
```
