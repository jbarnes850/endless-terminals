#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def run_text(cmd: list[str], timeout: int = 10) -> str:
    try:
        result = subprocess.run(cmd, check=False, text=True, capture_output=True, timeout=timeout)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    text = (result.stdout or result.stderr).strip()
    return text[:4000]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def heartbeat(args: argparse.Namespace) -> dict:
    gate = load_json(args.launch_gate)
    obs = load_json(args.observability)
    contracts = load_json(args.contracts)
    delegation = load_json(args.delegation)
    prime_pods = run_text(["prime", "--plain", "pods", "list", "--output", "json"])
    source_mtime = args.session_log.stat().st_mtime if args.session_log.exists() else None
    if delegation:
        training_subset = (
            f"executable/pruned plumbing subset: {delegation.get('pruned_executable_current')}/"
            f"{delegation.get('executable_envs')} envs"
        )
    else:
        training_subset = "bootstrap/meta_control package" if not gate else gate.get("manifest", {}).get("path")
    policy_calibration = delegation.get("policy_calibration", "Laguna pass@16") if delegation else "Laguna pass@16"
    current_blocker = f"waiting on final {policy_calibration} band + reward groups"
    if gate and gate.get("ok"):
        current_blocker = "ready for launch gate escape-audit/reward-groups check"

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "Project": "Laguna meta-control Prime-RL",
        "Phase": "calibration-running / training-infra-armed",
        "Runs queued": ["A_baseline_gated", "B_anti_inertia"],
        "Runs running": [],
        "Runs completed": [],
        "Runs killed": [],
        "Training subset": training_subset,
        "Latest reward/final success": "no training run yet",
        "Loop/repeat trend": "pending rollout probe",
        "Stop-quality trend": "pending rollout probe",
        "Reward variance": gate.get("reward_groups", "pending reward-group artifact") if gate else "pending",
        "Checkpoint farming signs": "pending escape-trace audit",
        "TBLite/OOD status": "not started",
        "Current blocker": current_blocker,
        "Next action": "export calibrated pass-band meta_control, then run launch wrapper for A/B",
        "Go/No-Go": f"NO-GO for capability training until {policy_calibration} band and reward variance pass",
        "calibration_delegation": delegation,
        "observability": obs.get("weave", {}),
        "contracts": {
            "scale_configs": bool(contracts.get("scale_configs")),
            "weave_rollouts": bool((contracts.get("prime_rl") or {}).get("weave_rollouts")),
        },
        "prime_pods": prime_pods,
        "watched_session_mtime": source_mtime,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Laguna meta-control training heartbeat JSONL.")
    parser.add_argument("--out", type=Path, default=Path("/tmp/meta-control-training-heartbeat.jsonl"))
    parser.add_argument(
        "--session-log",
        type=Path,
        default=Path(
            "/Users/jarrodbarnes/.codex/sessions/2026/05/30/"
            "rollout-2026-05-30T00-26-12-019e760f-4477-7162-905e-db72fdff59f6.jsonl"
        ),
    )
    parser.add_argument("--launch-gate", type=Path, default=Path("/tmp/laguna-meta-control-launch-gates.json"))
    parser.add_argument("--observability", type=Path, default=Path("/tmp/laguna-meta-control-observability.json"))
    parser.add_argument("--contracts", type=Path, default=Path("/tmp/laguna-meta-control-contracts.json"))
    parser.add_argument("--delegation", type=Path, default=Path("/tmp/meta-control-calibration-delegation.json"))
    parser.add_argument("--interval", type=int, default=600)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    while True:
        with args.out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(heartbeat(args), sort_keys=True) + "\n")
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
