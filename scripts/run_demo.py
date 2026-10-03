from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import ping
from backend.pipeline import run_demo
from scripts.init_db import init_both


def main() -> int:
    print("=" * 40)
    print("POSTGRES AI OPTIMIZER DEMO")
    print("=" * 40)
    if not ping(False) or not ping(True):
        print("PostgreSQL or sandbox is unavailable.")
        print("Start with: docker compose up --build")
        return 1
    print("Seeding databases if empty...")
    print(json.dumps(init_both(), indent=2))
    query_id = sys.argv[1] if len(sys.argv) > 1 else "Q001"
    result = run_demo(query_id)
    analysis = result["analysis"]
    bench = result["benchmark"]
    metrics = analysis["metrics"]
    bottlenecks = analysis.get("bottlenecks") or []
    rec = (result.get("recommendations") or [{}])[0]
    print()
    print(f"Query: {query_id}")
    print()
    print("Baseline:")
    print(f"Execution Time: {metrics.get('execution_time_ms'):.2f} ms  [Measured]")
    print()
    if bottlenecks:
        top = bottlenecks[0]
        print("Detected Bottleneck:")
        print(f"{top.get('type')} on {top.get('node')} {top.get('relation') or ''}")
        print(top.get("reason"))
        print()
    print("Recommendation:")
    print(f"{rec.get('type')} {rec.get('table') or ''} {rec.get('columns') or ''}")
    print(rec.get("reason"))
    print()
    print("Testing recommendation in sandbox...")
    print(f"Status: {bench.get('validation_status')}")
    opt = bench.get("optimized") or {}
    if opt:
        print()
        print("Optimized:")
        print(f"Execution Time: {opt.get('execution_time_ms'):.2f} ms  [Measured]")
        print()
        print("Improvement:")
        print(f"{bench.get('improvement_percent')}%")
    elif bench.get("error"):
        print(bench["error"])
    print()
    print("Recommendation Status:")
    print(bench.get("validation_status"))
    print()
    print("Privacy demo:")
    print(result["privacy_demo"]["raw"])
    print("->")
    print(result["privacy_demo"]["anonymized"])
    print("=" * 40)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
