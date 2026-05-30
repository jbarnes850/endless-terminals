#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


SELF_MANAGED_CONFIGS = {
    "A": Path("training/configs/meta_control_A_baseline_gated.toml"),
    "B": Path("training/configs/meta_control_B_anti_inertia.toml"),
    "C": Path("training/configs/meta_control_C_stop_verification.toml"),
}

HOSTED_CONFIGS = {
    "A": Path("training/hosted/A_baseline_gated.toml"),
    "B": Path("training/hosted/B_anti_inertia.toml"),
    "C": Path("training/hosted/C_stop_verification.toml"),
}


def run(cmd: list[str], *, execute: bool, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(cmd), flush=True)
    if execute:
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)


def capture_json(cmd: list[str]) -> object:
    output = subprocess.check_output(cmd, text=True)
    return json.loads(output)


def trainable_count(report_path: Path) -> int:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return int(report["calibration"]["trainable_band"])


def assert_gpu_available() -> None:
    if shutil.which("nvidia-smi") is None:
        raise SystemExit("FAIL: nvidia-smi is not available; run self-managed Prime-RL on the GPU node.")


def assert_wandb_online() -> None:
    if not os.environ.get("WANDB_API_KEY") and not Path.home().joinpath(".netrc").exists():
        raise SystemExit("FAIL: W&B online auth is missing; set WANDB_API_KEY or run wandb login before launch.")


def weave_project() -> str:
    explicit = os.environ.get("WEAVE_PROJECT")
    if explicit:
        return explicit
    project = os.environ.get("WANDB_PROJECT", "laguna-meta-control")
    entity = os.environ.get("WANDB_ENTITY")
    return f"{entity}/{project}" if entity else project


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate and launch the Laguna meta-control RL sweep.")
    parser.add_argument("--mode", choices=["hosted", "self-managed"], default="self-managed")
    parser.add_argument("--calibration", type=Path, action="append", required=True)
    parser.add_argument("--reward-groups", type=Path, action="append", default=[])
    parser.add_argument("--manifest", type=Path, default=Path("environments/meta_control/meta_control/manifest.json"))
    parser.add_argument("--require-manifest-exact", action="store_true")
    parser.add_argument("--escape-audit", type=Path)
    parser.add_argument("--runs", nargs="+", choices=["A", "B", "C"], default=["A", "B"])
    parser.add_argument("--include-c-if-trainable-at-least", type=int, default=64)
    parser.add_argument("--execute", action="store_true", help="Actually launch spend-bearing training.")
    parser.add_argument("--skip-live-endpoint", action="store_true")
    args = parser.parse_args()

    if "C" in args.runs:
        print("C requested explicitly; launch gate will still run before execution.", flush=True)
    if args.execute and not args.reward_groups:
        raise SystemExit("FAIL: --execute requires at least one --reward-groups artifact")
    if args.execute and args.escape_audit is None:
        raise SystemExit("FAIL: --execute requires --escape-audit")
    if args.execute and args.manifest is None:
        raise SystemExit("FAIL: --execute requires --manifest")

    gate_path = Path("/tmp/laguna-meta-control-launch-gates.json")
    gate_cmd = [
        sys.executable,
        "scripts/check_training_launch_gates.py",
        "--min-trainable-tasks",
        "1",
        "--out",
        str(gate_path),
    ]
    for path in args.calibration:
        gate_cmd.extend(["--calibration", str(path)])
    for path in args.reward_groups:
        gate_cmd.extend(["--reward-groups", str(path)])
    if args.manifest is not None:
        gate_cmd.extend(["--manifest", str(args.manifest)])
    if args.require_manifest_exact:
        gate_cmd.append("--require-manifest-exact")
    run(gate_cmd, execute=True)
    if args.escape_audit is not None:
        run([sys.executable, "scripts/check_escape_trace_audit.py", "--audit", str(args.escape_audit)], execute=True)

    selected_runs = list(args.runs)
    if "C" in selected_runs and trainable_count(gate_path) < args.include_c_if_trainable_at_least:
        selected_runs.remove("C")
        print("Skipping C: trainable band is below configured threshold.", flush=True)

    run([sys.executable, "scripts/smoke_training_contracts.py"], execute=True)
    if not args.skip_live_endpoint:
        run([sys.executable, "scripts/smoke_live_endpoint.py"], execute=True)
    if args.execute:
        assert_wandb_online()
        run(
            [
                "uv",
                "run",
                "--no-project",
                "--with",
                "wandb",
                "--with",
                "weave",
                "python",
                "scripts/smoke_observability.py",
                "--require-online",
                "--project",
                os.environ.get("WANDB_PROJECT", "laguna-meta-control"),
                "--out",
                "/tmp/laguna-meta-control-observability-launch.json",
            ],
            execute=True,
        )
    run(["prime", "--plain", "env", "install", "meta-control", "-p", "environments", "--no-upgrade"], execute=True)

    if args.mode == "hosted":
        model_data = capture_json(["prime", "--plain", "train", "models", "--output", "json"])
        models = model_data.get("models", []) if isinstance(model_data, dict) else []
        if not any(row.get("name") == "poolside/Laguna-XS.2" and not row.get("at_capacity") for row in models):
            raise SystemExit("FAIL: hosted Laguna model is missing or at capacity.")
        if args.execute:
            run(["prime", "--plain", "env", "push", "meta-control", "-p", "environments", "--visibility", "PRIVATE", "--auto-bump"], execute=True)
        for run_id in selected_runs:
            run(["prime", "--plain", "train", str(HOSTED_CONFIGS[run_id]), "--env-file", ".env", "-y"], execute=args.execute)
        return

    if args.execute:
        assert_gpu_available()
    common_prefix = [
        "uv",
        "run",
        "--no-project",
        "--python",
        "3.12",
        "--with",
        "pydantic",
        "--with",
        "pydantic-config @ git+https://github.com/samsja/pydantic_config.git",
        "--with",
        "tomli",
        "--with",
        "tomli-w",
        "--with",
        "nvidia-ml-py",
        "--with",
        "torch",
        "--with",
        "wandb",
        "--with",
        "weave",
        "--with",
        "loguru",
        "--with",
        "rich",
        "--with",
        "tyro",
        "python",
        "-m",
        "prime_rl.entrypoints.rl",
    ]
    env = {
        **os.environ,
        "PYTHONPATH": "/Users/jarrodbarnes/ai-scientist-training/prime-rl/src",
        "WEAVE_PROJECT": weave_project(),
        "WEAVE_REQUIRED": "1",
        "WANDB_PROJECT": os.environ.get("WANDB_PROJECT", "laguna-meta-control"),
    }
    for run_id in selected_runs:
        run([*common_prefix, "@", str(SELF_MANAGED_CONFIGS[run_id])], execute=args.execute, env=env)


if __name__ == "__main__":
    main()
