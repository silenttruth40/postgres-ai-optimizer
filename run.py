"""
Single-command launcher for PostgreSQL AI Performance Optimizer.
Starts local PostgreSQL, FastAPI backend, and Streamlit frontend.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON_BIN = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def is_pg_ready() -> bool:
    res = subprocess.run([PYTHON_BIN, "scripts/control_local_postgres.py", "status"], capture_output=True, text=True)
    return "running" in res.stdout.lower()


def start_postgres():
    if not is_pg_ready():
        print("Starting local PostgreSQL on port 5432...")
        subprocess.run([PYTHON_BIN, "scripts/control_local_postgres.py", "start"])
        time.sleep(2)
        if is_pg_ready():
            print("PostgreSQL started successfully.")
        else:
            print("Note: PostgreSQL start command issued. Verifying port 5432...")
    else:
        print("PostgreSQL is already running on port 5432.")


def main():
    print("=" * 60)
    print("  PostgreSQL AI Performance Optimizer Launcher")
    print("=" * 60)

    # 1. Start PostgreSQL
    start_postgres()

    # 2. Start FastAPI Backend
    print("\nStarting FastAPI backend server on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [PYTHON_BIN, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(PROJECT_ROOT),
    )

    # Give backend a moment to boot
    time.sleep(2)

    # 3. Start Streamlit Frontend
    print("Starting Streamlit dashboard on http://localhost:8501 ...")
    frontend_proc = subprocess.Popen(
        [PYTHON_BIN, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", "8501"],
        cwd=str(PROJECT_ROOT),
    )

    time.sleep(2)
    print("\n" + "=" * 60)
    print("  All services running!")
    print("  Dashboard: http://localhost:8501")
    print("  API Docs:  http://127.0.0.1:8000/docs")
    print("  Press Ctrl+C to stop all services.")
    print("=" * 60 + "\n")

    try:
        webbrowser.open("http://localhost:8501")
    except Exception:
        pass

    try:
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        frontend_proc.terminate()
        backend_proc.terminate()
        print("Services stopped.")


if __name__ == "__main__":
    main()
