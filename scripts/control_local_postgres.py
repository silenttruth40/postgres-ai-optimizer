"""
Helper script to start or stop local PostgreSQL server (No Docker required).
Usage:
    python scripts/control_local_postgres.py start
    python scripts/control_local_postgres.py stop
    python scripts/control_local_postgres.py status
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PGSQL_DIR = DATA_DIR / "pgsql"
CLUSTER_DATA = PGSQL_DIR / "data"
LOG_FILE = PGSQL_DIR / "server.log"


def get_bin(name: str) -> Path:
    candidates = [
        PGSQL_DIR / "pgsql" / "bin" / f"{name}.exe",
        PGSQL_DIR / "bin" / f"{name}.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    pg_ctl = get_bin("pg_ctl")
    pg_isready = get_bin("pg_isready")

    if not pg_ctl.exists():
        print("Local PostgreSQL binaries not found. Run 'python scripts/setup_local_postgres.py' first.")
        sys.exit(1)

    if action == "start":
        cmd = [str(pg_ctl), "-D", str(CLUSTER_DATA), "-l", str(LOG_FILE), "-o", "-p 5432", "start"]
        subprocess.run(cmd)
    elif action == "stop":
        cmd = [str(pg_ctl), "-D", str(CLUSTER_DATA), "stop"]
        subprocess.run(cmd)
    elif action == "status":
        cmd = [str(pg_isready), "-p", "5432"]
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print("PostgreSQL is running and accepting connections on port 5432.")
        else:
            print("PostgreSQL is stopped.")


if __name__ == "__main__":
    main()
