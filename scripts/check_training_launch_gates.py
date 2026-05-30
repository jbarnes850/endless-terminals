#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
import json
from pathlib import Path
import statistics
from typing import Any


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"FAIL: missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"FAIL: invalid JSON at {path}: {exc}") from exc


def iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from iter_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_mappings(child)


def task_name(row: Mapping[str, Any]) -> str | None:
    for key in ["task_name", "task", "task_id", "name", "env_id", "example_id"]:
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    path = row.get("task_dir") or row.get("harbor_task_dir") or row.get("source_task_dir")
    if isinstance(path, str) and path:
        return Path(path).name
    return None


def pass_fraction(row: Mapping[str, Any]) -> float | None:
    for key in [
        "pass_rate",
        "pass@16",
        "pass_at_16",
        "laguna_pass_rate",
        "policy_pass_at_k",
        "success_rate",
    ]:
        value = row.get(key)
        if isinstance(value, int | float):
            return float(value)
    passed = None
    total = None
    for key in ["passed", "successes", "num_success", "pass_count"]:
        value = row.get(key)
        if isinstance(value, int | float):
            passed = float(value)
            break
    for key in ["total", "attempts", "num_rollouts", "k", "n"]:
        value = row.get(key)
        if isinstance(value, int | float) and float(value) > 0:
            total = float(value)
            break
    if passed is not None and total:
        return passed / total
    return None


def collect_calibration_rows(value: Any) -> dict[str, float]:
    rows: dict[str, float] = {}
    for row in iter_mappings(value):
        name = task_name(row)
        rate = pass_fraction(row)
        if name is not None and rate is not None:
            rows[name] = rate
    return rows


def normalize_task_id(value: str) -> str:
    return Path(value.split("/")[-1]).name


def collect_manifest_tasks(manifest: Mapping[str, Any]) -> set[str]:
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        fail("manifest must contain a rows list")
    tasks: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = task_name(row)
        if name is not None:
            tasks.add(normalize_task_id(name))
    if not tasks:
        fail("manifest contains no package task names")
    return tasks


def collect_reward_groups(value: Any) -> list[list[float]]:
    groups: list[list[float]] = []
    for row in iter_mappings(value):
        rewards = row.get("rewards")
        if isinstance(rewards, list) and rewards and all(isinstance(item, int | float) for item in rewards):
            groups.append([float(item) for item in rewards])
            continue
        rollouts = row.get("rollouts")
        if isinstance(rollouts, list):
            rollout_rewards = []
            for rollout in rollouts:
                if isinstance(rollout, Mapping) and isinstance(rollout.get("reward"), int | float):
                    rollout_rewards.append(float(rollout["reward"]))
            if rollout_rewards:
                groups.append(rollout_rewards)
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(description="Check meta-control training launch gates.")
    parser.add_argument("--calibration", type=Path, action="append", required=True)
    parser.add_argument("--reward-groups", type=Path, action="append", default=[])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--require-manifest-exact", action="store_true")
    parser.add_argument("--expected-rollouts", type=int, default=4)
    parser.add_argument("--min-trainable-tasks", type=int, default=1)
    parser.add_argument("--std-threshold", type=float, default=1e-5)
    parser.add_argument("--max-low-variance-fraction", type=float, default=0.5)
    parser.add_argument("--out", type=Path, default=Path("/tmp/laguna-meta-control-launch-gates.json"))
    args = parser.parse_args()

    calibration_rates: dict[str, float] = {}
    for path in args.calibration:
        calibration_rates.update(collect_calibration_rows(load_json(path)))
    if not calibration_rates:
        fail("no calibration task pass rates found")

    trainable = {name: rate for name, rate in calibration_rates.items() if 0.0 < rate < 1.0}
    trivial = {name: rate for name, rate in calibration_rates.items() if rate >= 1.0}
    zero = {name: rate for name, rate in calibration_rates.items() if rate <= 0.0}
    if len(trainable) < args.min_trainable_tasks:
        fail(f"only {len(trainable)} trainable tasks found; need at least {args.min_trainable_tasks}")

    manifest_report = None
    if args.manifest is not None:
        manifest_tasks = collect_manifest_tasks(load_json(args.manifest))
        trainable_tasks = {normalize_task_id(name) for name in trainable}
        missing_calibration = sorted(task for task in manifest_tasks if task not in calibration_rates)
        non_trainable = sorted(task for task in manifest_tasks if task not in trainable_tasks)
        missing_from_manifest = sorted(task for task in trainable_tasks if task not in manifest_tasks)
        if missing_calibration:
            fail(f"{len(missing_calibration)} packaged tasks are missing calibration rows: {missing_calibration[:10]}")
        if non_trainable:
            fail(f"{len(non_trainable)} packaged tasks are outside the trainable band: {non_trainable[:10]}")
        if args.require_manifest_exact and missing_from_manifest:
            fail(f"{len(missing_from_manifest)} trainable calibrated tasks are absent from package manifest: {missing_from_manifest[:10]}")
        manifest_report = {
            "package_tasks": len(manifest_tasks),
            "missing_calibration": len(missing_calibration),
            "non_trainable": len(non_trainable),
            "missing_from_manifest": len(missing_from_manifest),
            "exact_required": args.require_manifest_exact,
        }

    groups: list[list[float]] = []
    for path in args.reward_groups:
        groups.extend(collect_reward_groups(load_json(path)))

    variance = None
    if groups:
        low_variance = [
            group
            for group in groups
            if len(group) >= args.expected_rollouts and statistics.pstdev(group) < args.std_threshold
        ]
        low_fraction = len(low_variance) / len(groups)
        if low_fraction > args.max_low_variance_fraction:
            fail(
                f"reward variance gate failed: {len(low_variance)}/{len(groups)} groups "
                f"below std {args.std_threshold}"
            )
        variance = {
            "groups": len(groups),
            "low_variance_groups": len(low_variance),
            "low_variance_fraction": low_fraction,
            "std_threshold": args.std_threshold,
        }

    report = {
        "calibration": {
            "total": len(calibration_rates),
            "trainable_band": len(trainable),
            "zero": len(zero),
            "trivial": len(trivial),
            "min_trainable_tasks": args.min_trainable_tasks,
        },
        "reward_variance": variance,
        "manifest": manifest_report,
        "status": "pass",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
