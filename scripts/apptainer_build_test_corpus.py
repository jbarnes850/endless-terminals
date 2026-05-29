#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def iter_tasks(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("task_"))


def write_normalized_def(task_dir: Path, base_sif: Path | None, inject_pytest: bool) -> Path:
    src = task_dir / "container.def"
    dst = task_dir / "container.build.def"
    text = src.read_text(encoding="utf-8")

    if base_sif is not None:
        text = text.replace(
            "Bootstrap: localimage\nFrom: ./ubuntu_22.04.sif",
            f"Bootstrap: localimage\nFrom: {base_sif}",
        )
    elif "Bootstrap: localimage\nFrom: ./ubuntu_22.04.sif" in text and not (task_dir / "ubuntu_22.04.sif").exists():
        raise FileNotFoundError(f"{task_dir / 'ubuntu_22.04.sif'} is missing; pass --base-sif")

    text = text.replace("%post\n", "%post -c /bin/bash\n", 1)

    if inject_pytest and "pytest" not in text:
        pytest_block = """\
    if ! command -v pytest >/dev/null 2>&1; then
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-pytest
    fi
"""
        if "\n%runscript" in text:
            text = text.replace("\n%runscript", "\n" + pytest_block + "\n%runscript")
        else:
            text = text.rstrip() + "\n" + pytest_block
    dst.write_text(text, encoding="utf-8")
    return dst


def run(cmd: list[str], timeout: int, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
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


def build_and_test(
    task_dir: Path,
    build_timeout: int,
    test_timeout: int,
    base_sif: Path | None,
    inject_pytest: bool,
    tmp_root: Path | None,
    cache_root: Path | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "task": task_dir.name,
        "task_dir": str(task_dir),
        "build_ok": False,
        "initial_tests_ok": False,
        "error_stage": None,
    }
    try:
        def_path = write_normalized_def(task_dir, base_sif, inject_pytest)
    except Exception as exc:
        row["error_stage"] = "normalize_def"
        row["normalize_error"] = f"{type(exc).__name__}: {exc}"
        return row

    sif_path = task_dir / "container.sif"

    env = os.environ.copy()
    if tmp_root is not None:
        tmp_dir = tmp_root / task_dir.name
        tmp_dir.mkdir(parents=True, exist_ok=True)
        env["APPTAINER_TMPDIR"] = str(tmp_dir)
    if cache_root is not None:
        cache_dir = cache_root / task_dir.name
        cache_dir.mkdir(parents=True, exist_ok=True)
        env["APPTAINER_CACHEDIR"] = str(cache_dir)

    build = run(["apptainer", "build", "--force", str(sif_path), str(def_path)], build_timeout, env=env)
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
        env=env,
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
    parser.add_argument("--base-sif", default=None)
    parser.add_argument("--no-inject-pytest", action="store_true")
    parser.add_argument("--tmp-root", default=None)
    parser.add_argument("--cache-root", default=None)
    args = parser.parse_args()

    root = Path(args.tasks_dir).resolve()
    base_sif = Path(args.base_sif).resolve() if args.base_sif else None
    tmp_root = Path(args.tmp_root).resolve() if args.tmp_root else None
    cache_root = Path(args.cache_root).resolve() if args.cache_root else None
    tasks = iter_tasks(root)
    end = None if args.num_tasks is None else args.start_at + args.num_tasks
    selected = tasks[args.start_at:end]

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                build_and_test,
                task_dir,
                args.build_timeout,
                args.test_timeout,
                base_sif,
                not args.no_inject_pytest,
                tmp_root,
                cache_root,
            ): task_dir
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
