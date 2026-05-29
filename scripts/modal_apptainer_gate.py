from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import modal


APP_NAME = "endless-apptainer-gate"
REMOTE_CORPUS = Path("/root/behavior_trace_20260529_220")
BASE_SIF = Path("/root/ubuntu_22.04.sif")


app = modal.App(APP_NAME)

image = (
    modal.Image.from_registry("ubuntu:22.04", add_python="3.12")
    .run_commands(
        "apt-get update",
        "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "
        "ca-certificates curl gnupg gpg-agent software-properties-common sudo "
        "squashfs-tools fuse-overlayfs uidmap python3-pip",
        "add-apt-repository -y ppa:apptainer/ppa",
        "apt-get update",
        "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends apptainer-suid",
        "python3 -m pip install --no-cache-dir pytest",
    )
    .add_local_dir(
        "tasks/behavior_trace_20260529_220",
        remote_path=str(REMOTE_CORPUS),
        copy=True,
    )
)


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {
        "cmd": cmd,
        "cwd": str(cwd) if cwd else None,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def _normalized_def(task_dir: Path) -> Path:
    src = task_dir / "container.def"
    dst = task_dir / "container.modal.def"
    text = src.read_text(encoding="utf-8")
    text = text.replace("Bootstrap: localimage\nFrom: ./ubuntu_22.04.sif", "Bootstrap: docker\nFrom: ubuntu:22.04")
    if "chmod 755 /home/user" not in text and "\n%runscript" in text:
        text = text.replace("\n%runscript", "\n    chmod 755 /home/user\n\n%runscript")
    dst.write_text(text, encoding="utf-8")
    return dst


def _task_dirs() -> list[Path]:
    return sorted(p for p in REMOTE_CORPUS.iterdir() if p.is_dir() and p.name.startswith("task_"))


@app.function(image=image, timeout=60 * 60 * 6, cpu=4.0, memory=8192)
def run_apptainer_gate(start_at: int = 0, num_tasks: int = 1) -> dict[str, Any]:
    report: dict[str, Any] = {
        "app": APP_NAME,
        "remote_corpus": str(REMOTE_CORPUS),
        "base_sif": str(BASE_SIF),
        "probe": {},
        "summary": {
            "selected": 0,
            "base_pull_ok": False,
            "build_ok": 0,
            "initial_tests_ok": 0,
            "failed": 0,
        },
        "tasks": [],
    }

    report["probe"]["apptainer_version"] = _run(["apptainer", "--version"], timeout=60)
    report["probe"]["userns_clone"] = _run(
        ["bash", "-lc", "cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null || true"],
        timeout=60,
    )

    pull = _run(["apptainer", "pull", "--force", str(BASE_SIF), "docker://ubuntu:22.04"], timeout=1200)
    report["probe"]["base_pull"] = pull
    report["summary"]["base_pull_ok"] = pull["returncode"] == 0 and BASE_SIF.exists()
    if not report["summary"]["base_pull_ok"]:
        return report

    selected = _task_dirs()[start_at : start_at + num_tasks]
    report["summary"]["selected"] = len(selected)

    for task_dir in selected:
        row: dict[str, Any] = {
            "task": task_dir.name,
            "build": None,
            "initial_tests": None,
            "success": False,
        }
        def_path = _normalized_def(task_dir)
        sif_path = task_dir / "container.sif"

        build = _run(["apptainer", "build", "--force", str(sif_path), str(def_path)], timeout=1800)
        row["build"] = build
        if build["returncode"] != 0:
            report["summary"]["failed"] += 1
            report["tasks"].append(row)
            continue
        report["summary"]["build_ok"] += 1

        test = _run(
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
            timeout=600,
        )
        row["initial_tests"] = test
        if test["returncode"] == 0:
            row["success"] = True
            report["summary"]["initial_tests_ok"] += 1
        else:
            report["summary"]["failed"] += 1
        report["tasks"].append(row)

    return report


@app.local_entrypoint()
def main(start_at: int = 0, num_tasks: int = 1, out: str = "modal_apptainer_gate.json"):
    result = run_apptainer_gate.remote(start_at=start_at, num_tasks=num_tasks)
    Path(out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    print(f"wrote {out}")
