#!/usr/bin/env python3
"""Summarize split Harbor TB2 Laguna shard jobs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def task_names_from_lock(job_dir: Path) -> set[str]:
    lock_path = job_dir / "lock.json"
    if not lock_path.exists():
        return set()
    lock = load_json(lock_path)
    return {row["task"]["name"] for row in lock.get("trials", [])}


def completed_trials(job_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for result_path in job_dir.glob("*/result.json"):
        result = load_json(result_path)
        task_name = result.get("task_name")
        if task_name:
            rows[task_name] = {
                "trial_name": result.get("trial_name"),
                "reward": result.get("reward"),
                "n_input_tokens": (result.get("agent_result") or {}).get("n_input_tokens"),
                "n_output_tokens": (result.get("agent_result") or {}).get("n_output_tokens"),
            }
    return rows


def running_trials(job_dir: Path) -> list[str]:
    running = []
    for trial_dir in job_dir.iterdir() if job_dir.exists() else []:
        if not trial_dir.is_dir():
            continue
        if not (trial_dir / "result.json").exists():
            running.append(trial_dir.name)
    return sorted(running)


def summarize(job_dirs: list[Path]) -> dict[str, Any]:
    expected: set[str] = set()
    completed: dict[str, dict[str, Any]] = {}
    jobs = []
    for job_dir in job_dirs:
        expected_for_job = task_names_from_lock(job_dir)
        completed_for_job = completed_trials(job_dir)
        expected.update(expected_for_job)
        completed.update(completed_for_job)
        result_path = job_dir / "result.json"
        result = load_json(result_path) if result_path.exists() else {}
        jobs.append(
            {
                "job_dir": str(job_dir),
                "expected": len(expected_for_job),
                "completed": len(completed_for_job),
                "running": running_trials(job_dir),
                "stats": result.get("stats"),
                "finished_at": result.get("finished_at"),
            }
        )

    pending = sorted(expected - set(completed))
    rewards = [row.get("reward") for row in completed.values()]
    return {
        "expected_total": len(expected),
        "completed_unique": len(completed),
        "pending_unique": len(pending),
        "pending_tasks": pending,
        "reward_mean": sum(rewards) / len(rewards) if rewards else None,
        "jobs": jobs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path, nargs="+")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    summary = summarize(args.job_dir)
    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
