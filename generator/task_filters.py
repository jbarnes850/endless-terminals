"""Two-gate task selection for RL training.

Two gates, two models, orthogonal jobs:

  * Validity / solvable-at-all  -> REFERENCE model (frontier, e.g. GPT-5.5).
    Few false negatives, certifies the task is well-formed and a solution exists.
  * Trainable band              -> POLICY model (Laguna).
    Keeps tasks where the policy sometimes-but-not-always succeeds, so a GRPO/CISPO
    rollout group on the task has non-zero reward variance (mixed 0/1 rewards).

The frontier model is expensive, so it is used only as a TIE-BREAKER on the tasks
the policy never solves: policy pass@k == 0 is ambiguous between "task is broken"
and "task is valid but too hard", and the reference disambiguates.

Per-task solver results are read from ``<task>/solutions/<model>_summary.json``
(written by generate_solutions.py / sample_solutions.run_n_solutions). Each summary
holds ``num_runs``, ``num_success`` and a ``pass_at_k`` curve.

Buckets returned by :func:`classify_task`:

  * ``trainable``        - 0 < policy_success < policy_runs   (the RL training set)
  * ``trivial``          - policy_success == policy_runs       (policy already solves it every time)
  * ``too_hard_valid``   - policy_success == 0 AND reference pass@k > 0  (curriculum / later stage)
  * ``broken``           - policy_success == 0 AND reference pass@k == 0 (drop: likely unsolvable)
  * ``needs_reference``  - policy_success == 0 AND no reference summary yet (run the frontier gate)
  * ``no_policy_data``   - no policy summary present (run the policy gate first)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from generator import POLICY_MODEL, REFERENCE_MODEL, summary_filename

TRAINABLE = "trainable"
TRIVIAL = "trivial"
TOO_HARD_VALID = "too_hard_valid"
BROKEN = "broken"
NEEDS_REFERENCE = "needs_reference"
NO_POLICY_DATA = "no_policy_data"

BUCKETS = [TRAINABLE, TRIVIAL, TOO_HARD_VALID, BROKEN, NEEDS_REFERENCE, NO_POLICY_DATA]


def load_summary(task_dir: Path, model: str) -> Optional[Dict[str, Any]]:
    """Read a solver's per-task summary json, or None if absent/unreadable."""
    p = Path(task_dir) / "solutions" / summary_filename(model)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def success_counts(summary: Dict[str, Any]) -> Tuple[int, int]:
    """Return (num_success, num_runs). Falls back to deriving num_runs from results."""
    runs = summary.get("num_runs")
    if runs is None:
        runs = len(summary.get("results", []) or [])
    succ = summary.get("num_success")
    if succ is None:
        succ = sum(1 for r in (summary.get("results", []) or []) if r.get("success"))
    return int(succ), int(runs)


def pass_at_k(summary: Optional[Dict[str, Any]], k: int) -> Optional[float]:
    """pass@k from a summary, or None if unavailable. Keys may be str or int."""
    if not summary:
        return None
    pak = summary.get("pass_at_k", {}) or {}
    val = pak.get(str(k))
    if val is None:
        val = pak.get(k)
    return None if val is None else float(val)


def zero_std_group_fraction(success_frac: float, group_size: int) -> float:
    """Expected fraction of all-same (zero-advantage) rollout groups.

    For a per-task success probability p and a GRPO group of size G, a group has
    zero reward variance (hence zero advantage / zero gradient) when all G rollouts
    are successes or all are failures: p**G + (1-p)**G. This ties the band filter to
    the RLVR reward-variance HARD-STOP gate: a "trainable" task with p too close to
    0 or 1 still produces mostly dead groups.
    """
    p = max(0.0, min(1.0, success_frac))
    return p ** group_size + (1.0 - p) ** group_size


def classify_task(
    task_dir: Path,
    policy_model: str = POLICY_MODEL,
    reference_model: str = REFERENCE_MODEL,
    k: int = 16,
    group_size: int = 16,
) -> Dict[str, Any]:
    """Classify a single task directory into a training-selection bucket."""
    task_dir = Path(task_dir)
    policy = load_summary(task_dir, policy_model)
    info: Dict[str, Any] = {
        "task": task_dir.name,
        "policy_model": policy_model,
        "reference_model": reference_model,
        "policy_success": None,
        "policy_runs": None,
        "policy_success_frac": None,
        "policy_pass_at_k": pass_at_k(policy, k),
        "reference_pass_at_k": pass_at_k(load_summary(task_dir, reference_model), k),
        "zero_std_group_frac": None,
        "bucket": None,
    }

    if policy is None:
        info["bucket"] = NO_POLICY_DATA
        return info

    succ, runs = success_counts(policy)
    info["policy_success"] = succ
    info["policy_runs"] = runs
    if runs > 0:
        frac = succ / runs
        info["policy_success_frac"] = frac
        info["zero_std_group_frac"] = zero_std_group_fraction(frac, group_size)

    if runs > 0 and 0 < succ < runs:
        info["bucket"] = TRAINABLE
    elif runs > 0 and succ == runs:
        info["bucket"] = TRIVIAL
    else:  # succ == 0 (policy never solved it) -> consult the reference tie-breaker
        ref_pak = info["reference_pass_at_k"]
        if ref_pak is None:
            info["bucket"] = NEEDS_REFERENCE
        elif ref_pak > 0:
            info["bucket"] = TOO_HARD_VALID
        else:
            info["bucket"] = BROKEN
    return info


def iter_task_dirs(tasks_root: Path) -> List[Path]:
    return sorted(
        d for d in Path(tasks_root).iterdir() if d.is_dir() and "task" in d.name
    )


def select_task_dirs(
    tasks_root: Path,
    gate: str = "band",
    policy_model: str = POLICY_MODEL,
    reference_model: str = REFERENCE_MODEL,
    k: int = 16,
    max_zero_std_group_frac: Optional[float] = None,
    group_size: int = 16,
) -> List[Path]:
    """Return task dirs that pass the selected gate.

    gate="band"     : the trainable band (0 < policy success < runs). This is the
                      primary RL gate and the default.
    gate="reference": the legacy validity gate (reference pass@k > 0). Use for eval
                      set construction where you want solvable tasks, not the band.

    When ``max_zero_std_group_frac`` is set (band gate only), additionally drop
    band tasks whose expected zero-advantage group fraction exceeds it for the
    given ``group_size`` (guards the RLVR reward-variance HARD-STOP gate).
    """
    out: List[Path] = []
    for d in iter_task_dirs(tasks_root):
        if gate == "reference":
            if (pass_at_k(load_summary(d, reference_model), k) or 0.0) > 0:
                out.append(d)
            continue
        # band gate
        info = classify_task(d, policy_model, reference_model, k, group_size)
        if info["bucket"] != TRAINABLE:
            continue
        if max_zero_std_group_frac is not None:
            zsg = info.get("zero_std_group_frac")
            if zsg is not None and zsg > max_zero_std_group_frac:
                continue
        out.append(d)
    return out


def _main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="Two-gate task selection (validity + trainable band).")
    ap.add_argument("--tasks-dir", required=True, help="Directory containing task_* dirs")
    ap.add_argument("--policy-model", default=POLICY_MODEL)
    ap.add_argument("--reference-model", default=REFERENCE_MODEL)
    ap.add_argument("--pass-k", type=int, default=16)
    ap.add_argument("--group-size", type=int, default=16,
                    help="RL rollout group size, for the zero-std-group estimate")
    ap.add_argument("--max-zero-std-group-frac", type=float, default=None,
                    help="Optionally drop band tasks whose expected zero-advantage "
                         "group fraction exceeds this (e.g. 0.5 per the HARD-STOP gate)")
    ap.add_argument("--out", default=None, help="Write the manifest json here (default: <tasks-dir>/band_manifest.json)")
    args = ap.parse_args(argv)

    rows = [
        classify_task(d, args.policy_model, args.reference_model, args.pass_k, args.group_size)
        for d in iter_task_dirs(args.tasks_dir)
    ]
    hist: Dict[str, int] = {b: 0 for b in BUCKETS}
    for r in rows:
        hist[r["bucket"]] = hist.get(r["bucket"], 0) + 1

    needs_ref = [r["task"] for r in rows if r["bucket"] == NEEDS_REFERENCE]
    trainable = select_task_dirs(
        args.tasks_dir, "band", args.policy_model, args.reference_model,
        args.pass_k, args.max_zero_std_group_frac, args.group_size,
    )

    out_path = Path(args.out) if args.out else Path(args.tasks_dir) / "band_manifest.json"
    out_path.write_text(json.dumps({
        "policy_model": args.policy_model,
        "reference_model": args.reference_model,
        "pass_k": args.pass_k,
        "group_size": args.group_size,
        "max_zero_std_group_frac": args.max_zero_std_group_frac,
        "histogram": hist,
        "trainable_task_dirs": [str(p) for p in trainable],
        "needs_reference_tasks": needs_ref,
        "rows": rows,
    }, indent=2), encoding="utf-8")

    total = len(rows)
    print(f"Classified {total} tasks ({args.policy_model} vs {args.reference_model}, k={args.pass_k}):")
    for b in BUCKETS:
        print(f"  {b:18s} {hist.get(b, 0):4d}")
    print(f"Trainable set after band gate: {len(trainable)}")
    if needs_ref:
        print(f"Run the reference gate ({args.reference_model}) on {len(needs_ref)} policy-zero tasks to disambiguate.")
    print(f"Manifest written to {out_path}")


if __name__ == "__main__":
    _main()
