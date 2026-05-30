#!/usr/bin/env python3
"""Launch the slow OpenRouter Laguna TB2 fallback without printing secrets."""
from __future__ import annotations

import os
import re
import subprocess
import argparse
from pathlib import Path


DEFAULT_KEY_FILE = Path("/Users/jarrodbarnes/sci-feasibility/.env")
KEY_NAME = "OPENROUTER_API_KEY"


def load_key(key_file: Path) -> str:
    for line in key_file.read_text(errors="ignore").splitlines():
        match = re.match(rf"^\s*{KEY_NAME}\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise SystemExit(f"{KEY_NAME} not found in {key_file}")


def read_include_tasks(path: Path | None) -> list[str]:
    if path is None:
        return []
    tasks = []
    for line in path.read_text().splitlines():
        task = line.strip()
        if task and not task.startswith("#"):
            tasks.append(task)
    if not tasks:
        raise SystemExit(f"No task names found in {path}")
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch an OpenRouter Laguna TB2 fallback without printing secrets.")
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE)
    parser.add_argument("--job-name", default="laguna-xs2-openrouter-key2-native-toolcall-timeoutx20-detached-full")
    parser.add_argument("--jobs-dir", default="evals/tb2_laguna_terminus_xml/full")
    parser.add_argument("--include-tasks-file", type=Path)
    parser.add_argument("--min-request-interval", default="15.0")
    parser.add_argument("--timeout-multiplier", default="20")
    parser.add_argument("--max-turns", default="64")
    parser.add_argument("--request-timeout", default="120")
    args = parser.parse_args()

    env = os.environ.copy()
    env[KEY_NAME] = load_key(args.key_file)
    command = [
        "uv",
        "run",
        "--extra",
        "harbor",
        "python",
        "scripts/run_tb2_laguna_terminus_xml.py",
        "--jobs-dir",
        args.jobs_dir,
        "--job-name",
        args.job_name,
        "--n-concurrent",
        "1",
        "--max-turns",
        args.max_turns,
        "--max-retries",
        "0",
        "--request-timeout",
        args.request_timeout,
        "--min-request-interval",
        args.min_request_interval,
        "--timeout-multiplier",
        args.timeout_multiplier,
        "--skip-probe",
    ]
    for task in read_include_tasks(args.include_tasks_file):
        command.extend(["--include-task-name", task])
    return subprocess.run(command, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
