#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from typing import Any


def run_json(cmd: list[str]) -> dict[str, Any]:
    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"FAIL: {' '.join(cmd)}\n{exc.output}") from exc
    return json.loads(output)


def run_shell_template(template: str, run_id: str, step: int) -> None:
    command = template.format(run_id=shlex.quote(run_id), step=step)
    print("+ " + command, flush=True)
    subprocess.run(command, shell=True, check=True)


def metric_value(row: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = row.get(name)
        if isinstance(value, int | float):
            return float(value)
        metrics = row.get("metrics")
        if isinstance(metrics, dict) and isinstance(metrics.get(name), int | float):
            return float(metrics[name])
    return None


def should_stop(metrics: list[dict[str, Any]], window: int) -> str | None:
    if len(metrics) < window * 2:
        return None
    before = metrics[-(window * 2) : -window]
    after = metrics[-window:]

    def avg(rows: list[dict[str, Any]], *names: str) -> float | None:
        values = [metric_value(row, *names) for row in rows]
        present = [value for value in values if value is not None]
        return sum(present) / len(present) if present else None

    shaped_before = avg(before, "reward/all/mean", "reward_mean", "mean_reward")
    shaped_after = avg(after, "reward/all/mean", "reward_mean", "mean_reward")
    final_before = avg(before, "metrics/meta_control/harbor_reward", "harbor_reward", "final_success")
    final_after = avg(after, "metrics/meta_control/harbor_reward", "harbor_reward", "final_success")
    loop_before = avg(before, "metrics/meta_control/adjacent_repeat_count", "adjacent_repeat_count", "loop_rate")
    loop_after = avg(after, "metrics/meta_control/adjacent_repeat_count", "adjacent_repeat_count", "loop_rate")

    if shaped_before is None or shaped_after is None or final_before is None or final_after is None:
        return None
    shaped_delta = shaped_after - shaped_before
    final_delta = final_after - final_before
    loop_delta = 0.0 if loop_before is None or loop_after is None else loop_after - loop_before
    if shaped_delta > 0 and final_delta <= 0 and loop_delta >= 0:
        return (
            "shaped reward improved without final-success or loop-rate improvement "
            f"(shaped_delta={shaped_delta:.4f}, final_delta={final_delta:.4f}, loop_delta={loop_delta:.4f})"
        )
    return None


def sync_rollouts_to_weave(run_id: str, step: int, num: int, project: str) -> None:
    import weave

    data = run_json(["prime", "--plain", "train", "rollouts", run_id, "--step", str(step), "--num", str(num)])
    samples = data.get("samples") or []
    client = weave.init(project)

    @weave.op(name="prime_meta_control_rollout")
    def record_rollout(sample: dict[str, Any]) -> dict[str, Any]:
        return sample

    for sample in samples:
        if isinstance(sample, dict):
            record_rollout(sample)
    print(f"synced {len(samples)} rollout samples to Weave via {type(client).__name__}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor a Prime hosted meta-control run.")
    parser.add_argument("run_id")
    parser.add_argument("--poll-sec", type=int, default=300)
    parser.add_argument("--rollouts-per-step", type=int, default=100)
    parser.add_argument("--weave-project", default=os.getenv("WEAVE_PROJECT", "laguna-meta-control"))
    parser.add_argument("--heldout-eval-cmd", help="Shell template run at sample/checkpoint steps. Supports {run_id} and {step}.")
    parser.add_argument("--tblite-eval-cmd", help="Shell template run at sample/checkpoint steps. Supports {run_id} and {step}.")
    parser.add_argument("--stop-window", type=int, default=3)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("/tmp/laguna-meta-control-monitor.jsonl"))
    args = parser.parse_args()

    seen_steps: set[int] = set()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    while True:
        progress = run_json(["prime", "--plain", "train", "progress", args.run_id])
        metrics_data = run_json(["prime", "--plain", "train", "metrics", args.run_id, "--limit", "200"])
        metrics = [row for row in metrics_data.get("metrics", []) if isinstance(row, dict)]
        stop_reason = should_stop(metrics, args.stop_window)
        if stop_reason:
            subprocess.run(["prime", "--plain", "train", "stop", args.run_id], check=False)

        sample_steps = progress.get("steps_with_samples") or []
        for step in sample_steps:
            if not isinstance(step, int) or step in seen_steps:
                continue
            seen_steps.add(step)
            sync_rollouts_to_weave(args.run_id, step, args.rollouts_per_step, args.weave_project)
            if args.heldout_eval_cmd:
                run_shell_template(args.heldout_eval_cmd, args.run_id, step)
            if args.tblite_eval_cmd:
                run_shell_template(args.tblite_eval_cmd, args.run_id, step)

        event = {
            "run_id": args.run_id,
            "latest_step": progress.get("latest_step"),
            "sample_steps_seen": sorted(seen_steps),
            "stop_reason": stop_reason,
        }
        with args.out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        print(json.dumps(event, sort_keys=True), flush=True)
        if stop_reason or args.once:
            break
        time.sleep(args.poll_sec)


if __name__ == "__main__":
    main()
