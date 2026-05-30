import sys
import pathlib
import argparse
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import datasets
import json
from pathlib import Path

sys.path.insert(0, str(pathlib.Path().resolve()))
from generator.env import InteractiveContainerEnvironment

from generator.sample_solutions import SYSTEM_MESSAGE, USER_TEMPLATE
from generator import POLICY_MODEL, REFERENCE_MODEL
from generator.task_filters import select_task_dirs


def build_container_for_task(task_dir_name, task_dir, verbose=True):
    """Build container for a single task. Returns (task_dir_name, success)."""
    sif_path = Path(task_dir) / task_dir_name / "container.sif"
    def_path = Path(task_dir) / task_dir_name / "container.def"
    initial_test_path = Path(task_dir) / task_dir_name / "test_initial_state.py"
    final_test_path = Path(task_dir) / task_dir_name / "test_final_state.py"
    
    if sif_path.exists():
        return task_dir_name, True
    
    try:
        env = InteractiveContainerEnvironment(
            container_sif_path=sif_path,
            initial_test_path=initial_test_path,
            final_test_path=final_test_path,
            def_path=def_path,
            verbose=verbose,
        )
        ok = env.build_container()
        if not ok:
            print(f"Failed to build SIF for {task_dir_name}")
            return task_dir_name, False
        return task_dir_name, True
    except Exception as e:
        print(f"Error building SIF for {task_dir_name}: {e}")
        return task_dir_name, False


def build_container_for_task_path(task_path, verbose=True):
    task_path = Path(task_path)
    if (task_path / "container.sif").exists():
        return str(task_path), True
    try:
        env = InteractiveContainerEnvironment(
            container_sif_path=task_path / "container.sif",
            initial_test_path=task_path / "test_initial_state.py",
            final_test_path=task_path / "test_final_state.py",
            def_path=task_path / "container.def",
            verbose=verbose,
        )
        ok = env.build_container()
        if not ok:
            print(f"Failed to build SIF for {task_path}")
            return str(task_path), False
        return str(task_path), True
    except Exception as e:
        print(f"Error building SIF for {task_path}: {e}")
        return str(task_path), False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="./data")
    parser.add_argument("--task-dir", default="./tasks")
    parser.add_argument("--eligible-file", default=None,
                        help="Optional newline-delimited executable task dirs; allows combined corpora across roots")
    parser.add_argument("--difficulty", default="none")
    parser.add_argument("--max-time", default=300)
    parser.add_argument("--eval-count", type=int, default=100)
    parser.add_argument("--build-sif", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-workers", type=int, default=20, help="Number of parallel workers for building containers")
    parser.add_argument("--gate", choices=["band", "reference"], default="band",
                        help="Task selection gate: 'band' = policy (Laguna) pass@k in (0,1) for "
                             "non-zero RL reward variance (default); 'reference' = frontier "
                             "validity gate (reference pass@k > 0).")
    parser.add_argument("--policy-model", default=POLICY_MODEL)
    parser.add_argument("--reference-model", default=REFERENCE_MODEL)
    parser.add_argument("--pass-k", type=int, default=16)
    parser.add_argument("--group-size", type=int, default=16,
                        help="RL rollout group size, for the zero-std-group estimate")
    parser.add_argument("--max-zero-std-group-frac", type=float, default=None,
                        help="Drop band tasks whose expected zero-advantage group fraction "
                             "exceeds this (e.g. 0.5 per the RLVR reward-variance HARD-STOP gate)")
    parser.add_argument("--min-policy-success", type=int, default=1)
    parser.add_argument("--max-policy-success", type=int, default=None)

    args = parser.parse_args()
    random.seed(args.seed)
    # Two-gate selection: default to the trainable band (policy pass@k in (0,1)),
    # falling back to the legacy reference-solvable gate when --gate reference.
    selected = select_task_dirs(
        args.task_dir,
        gate=args.gate,
        policy_model=args.policy_model,
        reference_model=args.reference_model,
        k=args.pass_k,
        max_zero_std_group_frac=args.max_zero_std_group_frac,
        group_size=args.group_size,
        min_policy_success=args.min_policy_success,
        max_policy_success=args.max_policy_success,
        eligible_file=Path(args.eligible_file) if args.eligible_file else None,
    )
    task_paths = sorted(Path(p).resolve() for p in selected)
    print(f"Selected {len(task_paths)} task dirs via '{args.gate}' gate "
          f"(policy={args.policy_model}, reference={args.reference_model}, k={args.pass_k})")
    random.shuffle(task_paths)
    task_descriptions = [json.load(open(path / "task.json"))["description"] for path in task_paths]

    # Build containers in parallel if requested
    failed_tasks = set()
    if args.build_sif:
        print(f"Building containers in parallel with {args.max_workers} workers...")
        completed = 0
        total = len(task_paths)
        progress_lock = Lock()
        
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            # Submit all build tasks with verbose=False
            future_to_task = {
                executor.submit(build_container_for_task_path, task_path, verbose=False): str(task_path)
                for task_path in task_paths
            }
            
            # Process results as they complete
            for future in as_completed(future_to_task):
                task_name, success = future.result()
                if not success:
                    failed_tasks.add(task_name)
                
                with progress_lock:
                    completed += 1
                    print(f"\rProgress: {completed}/{total} ({len(failed_tasks)} failed)", end='', flush=True)
        
        print()  # New line after progress
        print(f"Container building complete. Failed: {len(failed_tasks)}/{len(task_paths)}")

    # Prepare datasets
    train_dataset, val_dataset = [], []
    for t, task_path in enumerate(task_paths):
        # Skip failed tasks
        if str(task_path) in failed_tasks:
            continue
            
        row = {}
        row["description"] = task_descriptions[t]
        row["task_dir"] = str(task_path)
        initial_test_path = task_path / "test_initial_state.py"
        
        with open(initial_test_path, "r") as f:
            test_py = f.read()
        
        if t < len(task_paths) - args.eval_count:
            train_dataset.append(row)
        else:
            val_dataset.append(row)
    
    # convert to hf dataset
    train_dataset = datasets.Dataset.from_list(train_dataset)
    val_dataset = datasets.Dataset.from_list(val_dataset)


    # add a row to each data item that represents a unique id
    def make_map_fn(split):
        def process_fn(example, idx):
            system_prompt = SYSTEM_MESSAGE
            question = USER_TEMPLATE.format(task_description=example["description"])

            data = {
                "data_source": "endless",
                "prompt": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": question,
                    }
                ],
                "env_class": "endless",
                "reward_spec": {
                    "method": "rule",
                    "ground_truth": example["task_dir"],
                },
                "extra_info": {
                    "task_dir": example["task_dir"],
                    "max_time": args.max_time,
                },
            }
            return data

        return process_fn

    train_dataset = train_dataset.map(function=make_map_fn("train"), with_indices=True)
    val_dataset = val_dataset.map(function=make_map_fn("val"), with_indices=True)

    print(f"Train dataset size: {len(train_dataset)}")
    print(f"Val dataset size: {len(val_dataset)}")
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    train_dataset.to_parquet(os.path.join(output_dir, "train.parquet"))
    val_dataset.to_parquet(os.path.join(output_dir, "validation.parquet"))
