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

### 🚀 Easiest Option: One-Click Launch (No Docker Required)

You can launch the entire project (local PostgreSQL, FastAPI backend, and Streamlit dashboard) with a single command:

**Option A (Windows Double-Click or Command Line):**
```cmd
run.bat
```

**Option B (Python Launcher):**
```powershell
.\.venv\Scripts\python run.py
```

This single command will:
1. Verify / start your local PostgreSQL instance on port `5432`.
2. Start the FastAPI backend server on `http://127.0.0.1:8000`.
3. Start the Streamlit UI on `http://localhost:8501`.
4. Automatically open your browser to the interactive dashboard.

---

### Manual Step-by-Step Commands (Without Docker)

If you prefer starting services manually across individual terminal windows:

```powershell
# 1. Start PostgreSQL (runs locally on 127.0.0.1:5432):
.\.venv\Scripts\python scripts/control_local_postgres.py start

# 2. Start the Backend API (Terminal 1):
.\.venv\Scripts\uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 3. Start the Streamlit Dashboard (Terminal 2):
.\.venv\Scripts\streamlit run dashboard/app.py
```

Open your browser at **http://localhost:8501**.

To stop local PostgreSQL when finished:
```powershell
.\.venv\Scripts\python scripts/control_local_postgres.py stop
```

---

### 🔌 Connecting Your Own Manual / Large Database

You can point the optimizer directly to any manual PostgreSQL database:
1. **Via the Web UI**:
   - In the dashboard sidebar, expand **"🔌 Connect to Manual / Custom Database"**.
   - Enter your `Host`, `Port`, `Database Name`, `Username`, and `Password`.
   - Click **"Connect & Scan Tables"**. All tables are auto-discovered from `information_schema.tables` and immediately available.
2. **Via `.env`**:
   - Update `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in `.env`.

---

### ⚡ Running Query Optimization & Benchmark
1. Select **Custom SQL Query** in the sidebar.
2. Enter or paste your query in the code editor.
3. Click **"⚡ Run Optimization & Benchmark"**.
4. Both your **Original User Query** and the **AI Improvised Query** will execute live on PostgreSQL with `EXPLAIN (ANALYZE, BUFFERS)`.
5. View the side-by-side SQL diff and the comprehensive execution performance matrix (runtimes, buffer cache hits, physical disk reads, and speedup factor).

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
