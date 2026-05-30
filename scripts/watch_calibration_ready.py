#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def ssh(host: str, command: str) -> str:
    result = run(["ssh", "-o", "BatchMode=yes", host, command])
    if result.returncode != 0:
        return ""
    return result.stdout


def remote_exists(host: str, path: str) -> bool:
    result = run(["ssh", "-o", "BatchMode=yes", host, f"test -s {path!r}"])
    return result.returncode == 0


def remote_count(host: str, path: str) -> int | None:
    out = ssh(host, f"test -s {path!r} && wc -l < {path!r} || true").strip()
    try:
        return int(out)
    except ValueError:
        return None


def discover_band_manifest(host: str, remote_root: str) -> str | None:
    command = (
        f"cd {remote_root!r} && "
        "find tasks/calibration_combined -maxdepth 2 -type f "
        "\\( -iname '*laguna_n8*band*' -o -iname '*band_manifest*' -o -iname '*trainable*manifest*' \\) "
        "| sort | tail -n 1"
    )
    out = ssh(host, command).strip()
    return f"{remote_root}/{out}" if out else None


def status(args: argparse.Namespace) -> dict:
    band = args.band_manifest or discover_band_manifest(args.host, args.remote_root)
    calibration_dir = f"{args.remote_root.rstrip('/')}/tasks/calibration_combined"
    pruned_manifest = args.pruned_manifest or f"{calibration_dir}/eligible_executable_pruned_current.txt"
    reject_list = args.reject_list or f"{calibration_dir}/reject_unsolved_by_laguna_and_gpt55_current.txt"
    too_hard_list = args.too_hard_list or f"{calibration_dir}/too_hard_valid_gpt55_current.txt"
    needs_reference = args.needs_reference or f"{calibration_dir}/needs_reference_laguna_zero_current.txt"
    pruned_count = remote_count(args.host, pruned_manifest)
    reject_count = remote_count(args.host, reject_list)
    too_hard_count = remote_count(args.host, too_hard_list)
    needs_reference_count = remote_count(args.host, needs_reference)
    running = ssh(args.host, "pgrep -af 'run_eligible_calibration.py|task_filters.py|prepare_endless.py' || true").strip()
    ready = bool(band and remote_exists(args.host, band))
    if args.reward_groups and not Path(args.reward_groups).exists():
        ready = False
    if args.escape_audit and not Path(args.escape_audit).exists():
        ready = False
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ready": ready,
        "band_manifest": band,
        "pruned_manifest": pruned_manifest,
        "pruned_count": pruned_count,
        "reject_count": reject_count,
        "too_hard_count": too_hard_count,
        "needs_reference_count": needs_reference_count,
        "reward_groups": str(args.reward_groups) if args.reward_groups else None,
        "escape_audit": str(args.escape_audit) if args.escape_audit else None,
        "running": running.splitlines(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch remote calibration artifacts and report train readiness.")
    parser.add_argument("--host", default="ubuntu@64.247.206.243")
    parser.add_argument("--remote-root", default="/home/ubuntu/endless-terminals")
    parser.add_argument("--pruned-manifest")
    parser.add_argument("--reject-list")
    parser.add_argument("--too-hard-list")
    parser.add_argument("--needs-reference")
    parser.add_argument("--band-manifest")
    parser.add_argument("--reward-groups", type=Path)
    parser.add_argument("--escape-audit", type=Path)
    parser.add_argument("--out", type=Path, default=Path("/tmp/meta-control-calibration-ready.json"))
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        report = status(args)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(report, sort_keys=True), flush=True)
        if args.once or report["ready"]:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
