# ProcessRL Reproduction Runbook

This runbook records the public, reproducible path for the ProcessRL terminal
environment release. It intentionally excludes private endpoint URLs, API keys,
prebuilt container images, rollout scratch logs, and local worker paths.

The release artifact is:

- Hugging Face dataset: `Jarrodbarnes/processrl-terminal-environments`
- Public split: `53` train environments and `14` heldout environments
- Packaging boundary: executable environment source definitions, not prebuilt
  Docker images or Apptainer SIFs

## 1. Generate Candidate Environments

Use the behavior-conditioned Endless Terminals funnel. The exact public release
was generated in chunks so admission yield and behavior coverage could be
measured before generating more raw candidates.

```bash
uv run python generate_tasks.py \
  --num-tasks 220 \
  --out-dir tasks/behavior_trace_20260529_220 \
  --model gpt-5.5 \
  --behavior-conditioned \
  --behavior-seed 20260529 \
  --skip-def-build-test \
  --batch-size 32 \
  --max-concurrency 32 \
  --max-tokens 2048
```

Additional balancing chunks can be generated with explicit behavior cards:

```bash
uv run python generate_tasks.py \
  --num-tasks 120 \
  --out-dir tasks/behavior_trace_20260530_chunk2_balanced \
  --model gpt-5.5 \
  --behavior-conditioned \
  --behavior-seed 20260530 \
  --behavior-card-ids exit_code_false_success,wander_loop_without_convergence,old_state_new_state_confusion,premature_stop_on_sparse_feedback,repeat_loop_after_dead_end,partial_progress_stall \
  --skip-def-build-test \
  --batch-size 20 \
  --max-concurrency 16 \
  --max-tokens 8192
```

`--skip-def-build-test` only defers the build gate. It is not an admission
condition.

## 2. Static Validation

```bash
uv run ruff check generate_tasks.py generator scripts
uv run python -m py_compile generate_tasks.py generator/*.py scripts/*.py
find tasks/behavior_trace_<slug> -name 'test_*.py' -print0 \
  | xargs -0 uv run python -m py_compile
```

## 3. Executable Environment Admission

Run this on an Apptainer-capable worker. A task is eligible for calibration only
when `executable_ok=true`.

```bash
uv run python scripts/apptainer_build_test_corpus.py \
  --tasks-dir tasks/behavior_trace_<slug> \
  --out tasks/behavior_trace_<slug>/calibration/apptainer_executable_gate.json \
  --eligible-out tasks/behavior_trace_<slug>/eligible.txt \
  --workers 4 \
  --base-sif base/ubuntu_22.04.sif \
  --tmp-root /tmp/endless-apptainer-tmp \
  --cache-root /tmp/endless-apptainer-cache
```

Executable admission requires all of:

1. `container.def` builds into a SIF.
2. The SIF starts under the interactive rollout runtime.
3. The initial-state verifier passes inside the running environment.
4. A benign shell command runs in `/home/user`.
5. The final-state verifier can be invoked and returns a valid pass/fail signal.

## 4. Laguna Policy Calibration

The original target was `n=16`, but the public release used a time-bounded
`n=8` policy band after strict executable admission. This is valid for the
released pilot corpus but should not be silently described as an `n=16`
calibration.

```bash
uv run python scripts/run_eligible_calibration.py \
  --eligible-file tasks/calibration_combined/eligible_executable_pruned_plus_chunk2_current.txt \
  --admission-report tasks/calibration_combined/apptainer_executable_gate_plus_chunk2_180.json \
  --out tasks/calibration_combined/laguna_calibration_n8.json \
  --model laguna \
  --summary-model laguna_n8 \
  --n 8 \
  --max-actions 16 \
  --max-tokens 2048 \
  --temperature 1.0 \
  --task-workers 3 \
  --pool-workers 4 \
  --model-concurrency 2
```

Policy-band interpretation for this release:

- keep: `1/8..7/8`
- preferred: `2/8..6/8`
- trivial: `8/8`
- needs reference: `0/8`

## 5. Reference Validity For Policy-Zero Tasks

Run GPT-5.5 only on policy-zero tasks. This is a solvability/reference triage
gate, not the policy training band.

```bash
uv run python scripts/run_eligible_calibration.py \
  --eligible-file tasks/calibration_combined/eligible_reference_laguna_n8_zero.txt \
  --admission-report tasks/calibration_combined/apptainer_executable_gate_plus_chunk2_180.json \
  --out tasks/calibration_combined/gpt55_reference_laguna_n8_zero_n4.json \
  --model gpt-5.5 \
  --summary-model gpt-5.5 \
  --n 4 \
  --max-actions 40 \
  --max-tokens 2048 \
  --temperature 1.0 \
  --task-workers 1 \
  --pool-workers 4 \
  --model-concurrency 2
```

Tasks with `Laguna 0/8` and `GPT-5.5 0/4` are rejected from the public core
release. Tasks with `Laguna 0/8` and `GPT-5.5 >0/4` are stretch/curriculum
candidates, not core RL train tasks.

## 6. Band Manifest

```bash
uv run python -m generator.task_filters \
  --tasks-dir tasks/calibration_combined \
  --eligible-file tasks/calibration_combined/eligible_executable_pruned_plus_chunk2_current.txt \
  --policy-model laguna_n8 \
  --reference-model gpt-5.5 \
  --pass-k 8 \
  --group-size 8 \
  --min-policy-success 1 \
  --max-policy-success 7 \
  --preferred-min-policy-success 2 \
  --preferred-max-policy-success 6 \
  --max-zero-std-group-frac 0.5 \
  --out tasks/calibration_combined/band_manifest_laguna_n8_plus_chunk2_final.json
```

## 7. Materialize Release Splits

The final release split is derived from the band manifest, not hand-picked task
text:

- `trainable`: rows bucketed as `trainable`
- `stretch`: rows bucketed as `too_hard_valid`
- `reject`: rows bucketed as `broken` or `trivial`
- train/heldout: deterministic behavior-stratified split of the `trainable`
  set, sorted within each behavior by empirical policy success and task id

For the public release this produced `53` train and `14` heldout environments.
The release should be regenerated from the manifest if calibration is rerun.

## 8. Export Train And Heldout Environments

```bash
uv run python scripts/export_harbor_prime.py \
  --tasks-dir tasks/behavior_trace_20260529_220 \
  --tasks-dir tasks/behavior_trace_20260530_chunk1 \
  --tasks-dir tasks/behavior_trace_20260530_targeted_exit_bounded \
  --tasks-dir tasks/behavior_trace_20260530_chunk2_balanced \
  --eligible-file tasks/calibration_combined/eligible_train_laguna_n8_plus_chunk2_final.txt \
  --admission-report tasks/calibration_combined/apptainer_executable_gate_laguna_n8_plus_chunk2_final.json \
  --harbor-out exports/processrl_core_v1/train_harbor \
  --prime-env-out environments/processrl_core_train

uv run python scripts/export_harbor_prime.py \
  --tasks-dir tasks/behavior_trace_20260529_220 \
  --tasks-dir tasks/behavior_trace_20260530_chunk1 \
  --tasks-dir tasks/behavior_trace_20260530_targeted_exit_bounded \
  --tasks-dir tasks/behavior_trace_20260530_chunk2_balanced \
  --eligible-file tasks/calibration_combined/eligible_heldout_laguna_n8_plus_chunk2_final.txt \
  --admission-report tasks/calibration_combined/apptainer_executable_gate_laguna_n8_plus_chunk2_final.json \
  --harbor-out exports/processrl_core_v1/heldout_harbor \
  --prime-env-out environments/processrl_core_heldout
```

## 9. Package For Hugging Face

The public dataset should contain only source definitions:

- train and heldout Prime/Harbor task packages
- metadata JSONL for train, heldout, and all tasks
- a dataset card
- the repository license

Do not upload prebuilt Docker images, Apptainer SIFs, solver traces, rollout
scratch logs, local worker paths, API keys, or private calibration artifacts.

The published dataset is:

```bash
hf repos create Jarrodbarnes/processrl-terminal-environments --type dataset --exist-ok
hf upload Jarrodbarnes/processrl-terminal-environments /tmp/processrl_hf_dataset \
  --type dataset \
  --commit-message "Publish ProcessRL terminal environments"
```
