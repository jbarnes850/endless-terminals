#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.env import InteractiveContainerEnvironment


def iter_tasks(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("task_"))


def write_report(
    out_path: Path,
    eligible_out: Path | None,
    tasks_dir: Path,
    selected_count: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows_sorted = sorted(rows, key=lambda row: row["task"])
    summary = {
        "tasks_dir": str(tasks_dir),
        "selected": selected_count,
        "build_ok": sum(1 for row in rows_sorted if row["build_ok"]),
        "runtime_start_ok": sum(1 for row in rows_sorted if row["runtime_start_ok"]),
        "initial_tests_ok": sum(1 for row in rows_sorted if row["initial_tests_ok"]),
        "shell_smoke_ok": sum(1 for row in rows_sorted if row["shell_smoke_ok"]),
        "final_verifier_invoked_ok": sum(1 for row in rows_sorted if row["final_verifier_invoked_ok"]),
        "executable_ok": sum(1 for row in rows_sorted if row["executable_ok"]),
        "failed": sum(1 for row in rows_sorted if not row["executable_ok"]),
        "incomplete": selected_count - len(rows_sorted),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"summary": summary, "rows": rows_sorted}, indent=2), encoding="utf-8")
    if eligible_out:
        eligible = [row["task_dir"] for row in rows_sorted if row["executable_ok"]]
        eligible_out.parent.mkdir(parents=True, exist_ok=True)
        eligible_out.write_text("\n".join(eligible) + ("\n" if eligible else ""), encoding="utf-8")
    return summary


MODE_SENSITIVE_PATTERNS = (
    "mode_octal",
    "mode_of(",
    "expected_mode",
    "stat.S_IMODE",
    "0o",
    "0644",
    "0755",
    "0775",
    "0700",
    "0664",
    "0666",
    "0o644",
    "0o755",
    "0o775",
    "0o700",
    "0o664",
    "0o666",
)


def wants_writable_compat(task_dir: Path) -> bool:
    test_path = task_dir / "test_initial_state.py"
    if not test_path.exists():
        return False
    text = test_path.read_text(encoding="utf-8", errors="ignore")
    if "os.access" not in text or "W_OK" not in text:
        return False
    return not any(pattern in text for pattern in MODE_SENSITIVE_PATTERNS)


def append_to_post(text: str, block: str) -> str:
    match = re.search(r"(?ms)^%post[^\n]*\n.*?(?=^%[A-Za-z]|\Z)", text)
    if not match:
        return text.rstrip() + "\n" + block
    return text[: match.end()] + "\n" + block + text[match.end() :]


def write_normalized_def(
    task_dir: Path,
    base_sif: Path | None,
    inject_pytest: bool,
    writable_compat: str,
    agent_uid: int | None,
    agent_gid: int | None,
) -> Path:
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

    if inject_pytest and "ENDLESS_TERMINALS_PYTEST_COMPAT" not in text:
        pytest_block = """\
    # ENDLESS_TERMINALS_PYTEST_COMPAT: generated verifiers are pytest files.
    if ! command -v pytest >/dev/null 2>&1; then
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-pytest
    fi
"""
        text = append_to_post(text, pytest_block)

    apply_writable_compat = writable_compat == "always" or (
        writable_compat == "auto" and wants_writable_compat(task_dir)
    )
    if apply_writable_compat and "ENDLESS_TERMINALS_WRITABLE_COMPAT" not in text:
        compat_block = """\
    # ENDLESS_TERMINALS_WRITABLE_COMPAT: Apptainer/FUSE can report W_OK=false
    # for owner-writable paths in unprivileged shells. Keep exact-mode tasks
    # untouched; for non-mode-sensitive tasks, make the agent workspace writable.
    if id user >/dev/null 2>&1; then
        chown -R user:user /home/user 2>/dev/null || true
    fi
    chmod -R a+rwX /home/user
"""
        text = append_to_post(text, compat_block)
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


def tail_output(text: str, limit: int = 4000) -> str:
    return text[-limit:]


def write_text_into_running_env(env: InteractiveContainerEnvironment, path: str, text: str) -> tuple[bool, str]:
    if env.temp_dir is None:
        return False, "Container environment temp_dir is not initialized"
    staged = env.temp_dir / f"gate_{uuid.uuid4().hex}.py"
    staged.write_text(text, encoding="utf-8")
    return env.exec(f"cp {shlex.quote(str(staged))} {shlex.quote(path)}")


def invoke_final_verifier(env: InteractiveContainerEnvironment, final_test_path: Path) -> dict[str, Any]:
    text = final_test_path.read_text(encoding="utf-8")
    write_ok, write_output = write_text_into_running_env(env, "/home/user/test_final.py", text)
    if not write_ok:
        return {
            "ok": False,
            "write_ok": False,
            "output_tail": tail_output(write_output),
        }

    command = (
        "python3 -m pytest -q /home/user/test_final.py; "
        "pytest_code=$?; "
        "printf '__ENDLESS_FINAL_VERIFIER_EXIT__=%s\\n' \"$pytest_code\"; "
        "rm -f /home/user/test_final.py; "
        "test \"$pytest_code\" = \"0\" || test \"$pytest_code\" = \"1\""
    )
    ok, output = env.exec(command)
    return {
        "ok": ok and "__ENDLESS_FINAL_VERIFIER_EXIT__=" in output,
        "write_ok": True,
        "output_tail": tail_output(output),
    }


def build_and_test(
    task_dir: Path,
    build_timeout: int,
    test_timeout: int,
    base_sif: Path | None,
    inject_pytest: bool,
    writable_compat: str,
    agent_uid: int | None,
    agent_gid: int | None,
    tmp_root: Path | None,
    cache_root: Path | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "task": task_dir.name,
        "task_dir": str(task_dir),
        "build_ok": False,
        "runtime_start_ok": False,
        "initial_tests_ok": False,
        "shell_smoke_ok": False,
        "final_verifier_invoked_ok": False,
        "executable_ok": False,
        "calibration_eligible": False,
        "error_stage": None,
    }
    try:
        def_path = write_normalized_def(
            task_dir,
            base_sif,
            inject_pytest,
            writable_compat,
            agent_uid,
            agent_gid,
        )
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

    container_env = InteractiveContainerEnvironment(
        container_sif_path=str(sif_path),
        initial_test_path=str(task_dir / "test_initial_state.py"),
        final_test_path=str(task_dir / "test_final_state.py"),
        def_path=str(def_path),
        verbose=False,
        read_timeout=float(test_timeout),
    )
    try:
        try:
            runtime_start_ok = container_env.initialize(run_initial_tests=False)
            row["runtime_start"] = {"ok": runtime_start_ok}
            row["runtime_start_ok"] = runtime_start_ok
            if not runtime_start_ok:
                row["error_stage"] = "runtime_start"
                return row

            started = time.time()
            initial_tests_ok = container_env.run_initial_tests()
            row["initial_tests"] = {
                "ok": initial_tests_ok,
                "duration_sec": round(time.time() - started, 3),
            }
            row["initial_tests_ok"] = initial_tests_ok
            if not initial_tests_ok:
                row["error_stage"] = "initial_tests"
                return row

            shell_ok, shell_output = container_env.exec(
                "test \"$PWD\" = /home/user && printf 'endless-shell-smoke\\n'",
                timeout=float(test_timeout),
            )
            row["shell_smoke"] = {
                "ok": shell_ok and "endless-shell-smoke" in shell_output,
                "output_tail": tail_output(shell_output),
            }
            row["shell_smoke_ok"] = row["shell_smoke"]["ok"]
            if not row["shell_smoke_ok"]:
                row["error_stage"] = "shell_smoke"
                return row

            final_verifier = invoke_final_verifier(container_env, task_dir / "test_final_state.py")
            row["final_verifier"] = final_verifier
            row["final_verifier_invoked_ok"] = final_verifier["ok"]
            if not row["final_verifier_invoked_ok"]:
                row["error_stage"] = "final_verifier_invocation"
                return row
        except Exception as exc:
            row["error_stage"] = row.get("error_stage") or "gate_exception"
            row["gate_exception"] = f"{type(exc).__name__}: {exc}"
            return row
    finally:
        try:
            container_env.cleanup()
        except Exception as exc:
            row["cleanup_exception"] = f"{type(exc).__name__}: {exc}"

    row["executable_ok"] = all(
        bool(row[key])
        for key in (
            "build_ok",
            "runtime_start_ok",
            "initial_tests_ok",
            "shell_smoke_ok",
            "final_verifier_invoked_ok",
        )
    )
    row["calibration_eligible"] = row["executable_ok"]
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Admit executable Apptainer environments for generated ET tasks.")
    parser.add_argument("--tasks-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--start-at", type=int, default=0)
    parser.add_argument("--num-tasks", type=int, default=None)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--build-timeout", type=int, default=1800)
    parser.add_argument("--test-timeout", type=int, default=300)
    parser.add_argument("--base-sif", default=None)
    parser.add_argument("--no-inject-pytest", action="store_true")
    parser.add_argument("--writable-compat", choices=("none", "auto", "always"), default="none")
    parser.add_argument("--agent-uid", type=int, default=None)
    parser.add_argument("--agent-gid", type=int, default=None)
    parser.add_argument("--tmp-root", default=None)
    parser.add_argument("--cache-root", default=None)
    parser.add_argument("--eligible-out", default=None)
    args = parser.parse_args()

    root = Path(args.tasks_dir).resolve()
    base_sif = Path(args.base_sif).resolve() if args.base_sif else None
    tmp_root = Path(args.tmp_root).resolve() if args.tmp_root else None
    cache_root = Path(args.cache_root).resolve() if args.cache_root else None
    tasks = iter_tasks(root)
    end = None if args.num_tasks is None else args.start_at + args.num_tasks
    selected = tasks[args.start_at:end]

    rows: list[dict[str, Any]] = []
    out_path = Path(args.out)
    eligible_out = Path(args.eligible_out) if args.eligible_out else None
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                build_and_test,
                task_dir,
                args.build_timeout,
                args.test_timeout,
                base_sif,
                not args.no_inject_pytest,
                args.writable_compat,
                args.agent_uid,
                args.agent_gid,
                tmp_root,
                cache_root,
            ): task_dir
            for task_dir in selected
        }
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            write_report(out_path, eligible_out, root, len(selected), rows)
            print(
                json.dumps(
                    {
                        "task": row["task"],
                        "build_ok": row["build_ok"],
                        "runtime_start_ok": row["runtime_start_ok"],
                        "initial_tests_ok": row["initial_tests_ok"],
                        "shell_smoke_ok": row["shell_smoke_ok"],
                        "final_verifier_invoked_ok": row["final_verifier_invoked_ok"],
                        "executable_ok": row["executable_ok"],
                        "error_stage": row["error_stage"],
                    }
                ),
                flush=True,
            )

    summary = write_report(out_path, eligible_out, root, len(selected), rows)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
