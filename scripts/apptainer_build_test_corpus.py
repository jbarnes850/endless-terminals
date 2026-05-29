#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def iter_tasks(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("task_"))


def write_normalized_def(task_dir: Path) -> Path:
    src = task_dir / "container.def"
    dst = task_dir / "container.build.def"
    text = src.read_text(encoding="utf-8")
    text = text.replace(
        "Bootstrap: localimage\nFrom: ./ubuntu_22.04.sif",
        "Bootstrap: docker\nFrom: ubuntu:22.04",
    )
    chmod_line = "    chmod -R a+rwX /home/user\n"
    if "chmod -R a+rwX /home/user" not in text:
        if "\n%runscript" in text:
            text = text.replace("\n%runscript", "\n" + chmod_line + "\n%runscript")
        else:
            text = text.rstrip() + "\n" + chmod_line
    dst.write_text(text, encoding="utf-8")
    return dst


def run(cmd: list[str], timeout: int) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "duration_sec": round(time.time() - started, 3),
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "returncode": 124,
            "duration_sec": round(time.time() - started, 3),
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "timeout": True,
        }


def build_and_test(task_dir: Path, build_timeout: int, test_timeout: int) -> dict[str, Any]:
    row: dict[str, Any] = {
        "task": task_dir.name,
        "task_dir": str(task_dir),
        "build_ok": False,
        "initial_tests_ok": False,
        "error_stage": None,
    }
    def_path = write_normalized_def(task_dir)
    sif_path = task_dir / "container.sif"

    build = run(["apptainer", "build", "--force", str(sif_path), str(def_path)], build_timeout)
    row["build"] = build
    row["build_ok"] = build["returncode"] == 0 and sif_path.exists()
    if not row["build_ok"]:
        row["error_stage"] = "build"
        return row

    test = run(
        [
            "apptainer",
            "exec",
            "--containall",
            "--writable-tmpfs",
            "--cleanenv",
            "--bind",
            f"{task_dir}:/mnt",
            str(sif_path),
            "pytest",
            "-q",
            "/mnt/test_initial_state.py",
        ],
        test_timeout,
    )
    row["initial_tests"] = test
    row["initial_tests_ok"] = test["returncode"] == 0
    if not row["initial_tests_ok"]:
        row["error_stage"] = "initial_tests"
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SIFs and run initial tests for generated ET tasks.")
    parser.add_argument("--tasks-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--start-at", type=int, default=0)
    parser.add_argument("--num-tasks", type=int, default=None)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--build-timeout", type=int, default=1800)
    parser.add_argument("--test-timeout", type=int, default=300)
    args = parser.parse_args()

    root = Path(args.tasks_dir).resolve()
    tasks = iter_tasks(root)
    end = None if args.num_tasks is None else args.start_at + args.num_tasks
    selected = tasks[args.start_at:end]

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(build_and_test, task_dir, args.build_timeout, args.test_timeout): task_dir
            for task_dir in selected
        }
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            print(
                json.dumps(
                    {
                        "task": row["task"],
                        "build_ok": row["build_ok"],
                        "initial_tests_ok": row["initial_tests_ok"],
                        "error_stage": row["error_stage"],
                    }
                ),
                flush=True,
            )

    rows.sort(key=lambda r: r["task"])
    summary = {
        "tasks_dir": str(root),
        "selected": len(selected),
        "build_ok": sum(1 for row in rows if row["build_ok"]),
        "initial_tests_ok": sum(1 for row in rows if row["initial_tests_ok"]),
        "failed": sum(1 for row in rows if not row["initial_tests_ok"]),
    }
    out = {"summary": summary, "rows": rows}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
