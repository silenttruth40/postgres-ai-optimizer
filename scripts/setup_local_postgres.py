"""
Automated Local PostgreSQL Setup (No Docker required).
Downloads official portable PostgreSQL 16 binaries for Windows, initializes
a database cluster in data/pgsql/data, starts the server on port 5432,
creates 'optimizer' and 'optimizer_sandbox' databases, and initializes schema.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import httpx

DATA_DIR = PROJECT_ROOT / "data"
PGSQL_DIR = DATA_DIR / "pgsql"
BINARIES_ZIP = DATA_DIR / "postgresql-16.4-1-windows-x64-binaries.zip"
DOWNLOAD_URL = "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64-binaries.zip"
CLUSTER_DATA = PGSQL_DIR / "data"
LOG_FILE = PGSQL_DIR / "server.log"


def get_bin(name: str) -> Path:
    # EDB zip puts binaries inside pgsql/bin
    candidates = [
        PGSQL_DIR / "pgsql" / "bin" / f"{name}.exe",
        PGSQL_DIR / "bin" / f"{name}.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def download_binaries():
    if BINARIES_ZIP.exists() and BINARIES_ZIP.stat().st_size > 300_000_000:
        print(f"PostgreSQL zip already downloaded: {BINARIES_ZIP.name}")
        return

    print(f"Downloading portable PostgreSQL 16 for Windows (323 MB)...")
    print(f"URL: {DOWNLOAD_URL}")
    with httpx.stream("GET", DOWNLOAD_URL, follow_redirects=True, timeout=300.0) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        last_pct = 0
        with open(BINARIES_ZIP, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    pct = int((downloaded / total) * 100) if total else 0
                    if pct >= last_pct + 10:
                        print(f"  - Downloaded {pct}% ({downloaded // (1024*1024)} MB / {total // (1024*1024)} MB)...")
                        last_pct = pct

    print("Download completed successfully.")


def extract_binaries():
    initdb_path = get_bin("initdb")
    if initdb_path.exists():
        print("PostgreSQL binaries already extracted.")
        return

    print("Extracting PostgreSQL binaries to data/pgsql...")
    PGSQL_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BINARIES_ZIP, "r") as zf:
        zf.extractall(PGSQL_DIR)
    print("Extraction completed.")


def init_cluster():
    if (CLUSTER_DATA / "PG_VERSION").exists():
        print(f"Database cluster already initialized at {CLUSTER_DATA}.")
        return

    initdb = get_bin("initdb")
    print(f"Initializing database cluster with {initdb}...")
    CLUSTER_DATA.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(initdb),
        "-D", str(CLUSTER_DATA),
        "-U", "optimizer",
        "-A", "trust",
        "--encoding=UTF8",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"initdb failed: {res.stderr}")
        sys.exit(1)
    print("Cluster initialized successfully.")


def start_server():
    pg_ctl = get_bin("pg_ctl")
    pg_isready = get_bin("pg_isready")

    # Check if already running
    ready_cmd = [str(pg_isready), "-p", "5432"]
    if subprocess.run(ready_cmd, capture_output=True).returncode == 0:
        print("PostgreSQL server is already running on port 5432.")
        return

    print("Starting local PostgreSQL server on port 5432...")
    cmd = [
        str(pg_ctl),
        "-D", str(CLUSTER_DATA),
        "-l", str(LOG_FILE),
        "-o", "-p 5432",
        "start",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"pg_ctl start failed: {res.stderr}")
        sys.exit(1)

    # Wait for server to accept connections
    for _ in range(30):
        if subprocess.run(ready_cmd, capture_output=True).returncode == 0:
            print("PostgreSQL server is ready and accepting connections!")
            return
        time.sleep(0.5)

    print("Timed out waiting for PostgreSQL server to start.")
    sys.exit(1)


def create_databases():
    createdb = get_bin("createdb")
    for db in ["optimizer", "optimizer_sandbox"]:
        cmd = [str(createdb), "-p", "5432", "-U", "optimizer", db]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Created database: '{db}'")
        elif "already exists" in res.stderr.lower():
            print(f"Database '{db}' already exists.")
        else:
            print(f"createdb {db}: {res.stderr.strip()}")


def update_env():
    env_path = PROJECT_ROOT / ".env"
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    
    # Ensure port 5432 for both primary and sandbox
    replacements = {
        "POSTGRES_HOST=.*": "POSTGRES_HOST=localhost",
        "POSTGRES_PORT=.*": "POSTGRES_PORT=5432",
        "POSTGRES_DB=.*": "POSTGRES_DB=optimizer",
        "POSTGRES_USER=.*": "POSTGRES_USER=optimizer",
        "POSTGRES_PASSWORD=.*": "POSTGRES_PASSWORD=",
        "SANDBOX_POSTGRES_HOST=.*": "SANDBOX_POSTGRES_HOST=localhost",
        "SANDBOX_POSTGRES_PORT=.*": "SANDBOX_POSTGRES_PORT=5432",
        "SANDBOX_POSTGRES_DB=.*": "SANDBOX_POSTGRES_DB=optimizer_sandbox",
        "SANDBOX_POSTGRES_USER=.*": "SANDBOX_POSTGRES_USER=optimizer",
        "SANDBOX_POSTGRES_PASSWORD=.*": "SANDBOX_POSTGRES_PASSWORD=",
    }
    
    import re
    for pattern, repl in replacements.items():
        if re.search(pattern, content):
            content = re.sub(pattern, repl, content)
        else:
            content += f"\n{repl}"
            
    env_path.write_text(content, encoding="utf-8")
    print("Updated .env for local PostgreSQL configuration (port 5432).")


def main():
    print("==================================================")
    print("  Setting up Local PostgreSQL without Docker")
    print("==================================================")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download_binaries()
    extract_binaries()
    init_cluster()
    start_server()
    create_databases()
    update_env()
    print("\nLocal PostgreSQL setup is 100% complete and running!")


if __name__ == "__main__":
    main()
