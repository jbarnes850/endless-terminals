#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_tasks import _safe_write_text
from generator import summary_filename
from generator.sample_solutions import run_n_solutions


def read_eligible(path: Path) -> list[Path]:
    return [Path(line.strip()).resolve() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_task(task_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    summary_path = task_dir / "solutions" / summary_filename(args.model)
    if summary_path.exists() and not args.force:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return {
            "task": task_dir.name,
            "task_dir": str(task_dir),
            "status": "skipped_existing",
            "num_runs": data.get("num_runs"),
            "num_success": data.get("num_success"),
        }

    (task_dir / "solutions").mkdir(exist_ok=True)
    summary = run_n_solutions(
        num_solutions=args.n,
        container_sif_path=str(task_dir / "container.sif"),
        initial_test_path=str(task_dir / "test_initial_state.py"),
        final_test_path=str(task_dir / "test_final_state.py"),
        def_path=str(task_dir / "container.def"),
        task_path=str(task_dir / "task.json"),
        max_actions=args.max_actions,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        save_dir=str(task_dir / "solutions"),
        verbose=args.verbose,
        num_pool_workers=args.pool_workers,
        run_initial_tests=False,
    )
    _safe_write_text(summary_path, json.dumps(summary, indent=2))
    return {
        "task": task_dir.name,
        "task_dir": str(task_dir),
        "status": "completed",
        "num_runs": summary.get("num_runs"),
        "num_success": summary.get("num_success"),
        "pass_at_k": summary.get("pass_at_k", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run model calibration on eligible build+initial-pass task dirs.")
    parser.add_argument("--eligible-file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--n", type=int, default=4)
    parser.add_argument("--max-actions", type=int, default=16)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--task-workers", type=int, default=4)
    parser.add_argument("--pool-workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    eligible = read_eligible(Path(args.eligible_file))
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.task_workers) as pool:
        futures = {pool.submit(run_task, task_dir, args): task_dir for task_dir in eligible}
        for fut in as_completed(futures):
            try:
                row = fut.result()
            except Exception as exc:
                task_dir = futures[fut]
                row = {
                    "task": task_dir.name,
                    "task_dir": str(task_dir),
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            rows.append(row)
            print(json.dumps(row), flush=True)

    rows.sort(key=lambda row: row["task"])
    summary = {
        "model": args.model,
        "eligible_count": len(eligible),
        "completed": sum(row["status"] == "completed" for row in rows),
        "skipped_existing": sum(row["status"] == "skipped_existing" for row in rows),
        "failed": sum(row["status"] == "failed" for row in rows),
    }
    out = {"summary": summary, "rows": rows}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
