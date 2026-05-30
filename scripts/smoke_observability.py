#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def sample_rollouts() -> list[dict[str, Any]]:
    return [
        {
            "step": 0,
            "task": "meta_control",
            "example_id": 0,
            "reward": 1.0,
            "metrics": {
                "harbor_reward": 1.0,
                "stop_quality": 0.10,
                "repeat_action_penalty": 0.0,
                "reward_group_std": 0.5,
                "low_reward_variance_group": 0.0,
            },
            "trajectory": [
                {"role": "assistant", "tool_calls": [{"name": "shell", "arguments": {"cmd": "pytest -q"}}]},
                {"role": "tool", "content": "1 passed"},
                {"role": "assistant", "content": "done"},
            ],
            "stop_condition": "no_tools",
        },
        {
            "step": 0,
            "task": "meta_control",
            "example_id": 0,
            "reward": 0.0,
            "metrics": {
                "harbor_reward": 0.0,
                "stop_quality": -0.10,
                "repeat_action_penalty": -0.04,
                "reward_group_std": 0.5,
                "low_reward_variance_group": 0.0,
            },
            "trajectory": [
                {"role": "assistant", "tool_calls": [{"name": "shell", "arguments": {"cmd": "ls"}}]},
                {"role": "assistant", "tool_calls": [{"name": "shell", "arguments": {"cmd": "ls"}}]},
            ],
            "stop_condition": "max_turns_reached",
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke W&B and Weave observability for Laguna meta-control rollouts.")
    parser.add_argument("--project", default=os.getenv("WANDB_PROJECT", "laguna-meta-control"))
    parser.add_argument("--entity", default=os.getenv("WANDB_ENTITY"))
    parser.add_argument("--name", default="meta-control-observability-smoke")
    parser.add_argument("--out", type=Path, default=Path("/tmp/laguna-meta-control-observability.json"))
    parser.add_argument("--require-online", action="store_true")
    args = parser.parse_args()

    rollouts = sample_rollouts()
    rewards = [float(row["reward"]) for row in rollouts]
    metrics = {
        "reward/all/mean": sum(rewards) / len(rewards),
        "metrics/meta_control/reward_group_std": 0.5,
        "metrics/meta_control/low_reward_variance_group": 0.0,
        "stop_condition/meta_control/no_tools": 0.5,
        "stop_condition/meta_control/max_turns_reached": 0.5,
        "progress/samples": len(rollouts),
        "step": 0,
    }

    # W&B training-metric path. Launch uses require-online so training cannot
    # silently fall back to local-only metrics.
    import wandb

    mode = "online" if os.getenv("WANDB_API_KEY") or Path.home().joinpath(".netrc").exists() else "offline"
    if args.require_online and mode != "online":
        raise SystemExit("FAIL: W&B online auth is missing; set WANDB_API_KEY before launch.")
    wandb.init(project=args.project, entity=args.entity, name=args.name, mode=mode, dir=str(args.out.parent))
    table = wandb.Table(columns=["step", "task", "example_id", "reward", "stop_condition", "metrics", "trajectory"])
    for row in rollouts:
        table.add_data(
            row["step"],
            row["task"],
            row["example_id"],
            row["reward"],
            row["stop_condition"],
            json.dumps(row["metrics"], sort_keys=True),
            json.dumps(row["trajectory"], sort_keys=True),
        )
    wandb.log({**metrics, "rollouts": table})
    wandb.finish()

    weave_status = {"enabled": False, "reason": "not attempted"}
    try:
        import weave

        weave_project = f"{args.entity}/{args.project}" if args.entity else args.project
        client = weave.init(weave_project)

        @weave.op(name="meta_control_rollout_smoke")
        def trace_rollout(rollout: dict[str, Any]) -> dict[str, Any]:
            return {
                "task": rollout["task"],
                "example_id": rollout["example_id"],
                "reward": rollout["reward"],
                "metrics": rollout["metrics"],
                "stop_condition": rollout["stop_condition"],
                "trajectory": rollout["trajectory"],
            }

        traced = [trace_rollout(row) for row in rollouts]
        weave_status = {
            "enabled": True,
            "project": weave_project,
            "client": type(client).__name__,
            "num_traces": len(traced),
        }
    except Exception as exc:
        weave_status = {"enabled": False, "reason": f"{type(exc).__name__}: {exc}"}
        if args.require_online:
            raise SystemExit(f"FAIL: Weave trace smoke failed: {type(exc).__name__}: {exc}") from exc

    report = {
        "wandb": {"project": args.project, "entity": args.entity, "mode": mode, "run_name": args.name},
        "weave": weave_status,
        "metrics": metrics,
        "num_rollouts": len(rollouts),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
