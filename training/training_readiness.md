# Training Readiness

## Current Status

Prime model availability is verified: `poolside/Laguna-XS.2` is listed by `prime --plain train models --output json`.

Training is not ready to scale until the separate calibration/execution session produces pass@16 buckets, GPT-5.5 validity judgments for Laguna-zero executable tasks, and reward-variance statistics.

The Prime-RL environment wrapper is ready for package-level smoke over the admitted subset. The v3 admission/calibration track reports 179 executable environments and a provisional 173-task pruned executable surface after GPT-5.5 reference rejection. Treat any smaller local package as a bootstrap artifact for getting Prime-RL wired and auditing reward shape, not the final train set.

The local training smoke is now wired:

- Prime-RL config: `/Users/jarrodbarnes/endless-terminals/training/configs/meta_control_smoke.toml`
- Sweep configs: `/Users/jarrodbarnes/endless-terminals/training/configs/meta_control_A_baseline_gated.toml`, `/Users/jarrodbarnes/endless-terminals/training/configs/meta_control_B_anti_inertia.toml`, `/Users/jarrodbarnes/endless-terminals/training/configs/meta_control_C_stop_verification.toml`
- Hosted fallback configs: `/Users/jarrodbarnes/endless-terminals/training/hosted`
- Contract smoke: `/Users/jarrodbarnes/endless-terminals/scripts/smoke_training_contracts.py`
- Live endpoint smoke: `/Users/jarrodbarnes/endless-terminals/scripts/smoke_live_endpoint.py`
- Launch gate: `/Users/jarrodbarnes/endless-terminals/scripts/check_training_launch_gates.py`
- Escape-trace audit gate: `/Users/jarrodbarnes/endless-terminals/scripts/check_escape_trace_audit.py`
- Launch wrapper: `/Users/jarrodbarnes/endless-terminals/scripts/launch_meta_control_sweep.py`
- Hosted monitor/eval/Weave sync: `/Users/jarrodbarnes/endless-terminals/scripts/monitor_meta_control_run.py`
- W&B/Weave smoke: `/Users/jarrodbarnes/endless-terminals/scripts/smoke_observability.py`
- Latest contract artifact: `/tmp/laguna-meta-control-contracts.json`
- Latest live endpoint artifact: `/tmp/laguna-live-endpoint-smoke.json`
- Latest launch-gate artifact: `/tmp/laguna-meta-control-launch-gates.json`
- Latest observability artifact: `/tmp/laguna-meta-control-observability.json`
- Latest Prime-RL dry-run subconfigs: `/tmp/laguna-meta-control-dry/configs`

The smoke verifies `rollouts_per_example=4`, batch size one n=4 group, Verifiers trajectory/stop-condition metrics, hidden checkpoint prefix metadata, group reward std, W&B sample/distribution logging, full-rollout Weave tracing support, and Laguna renderer routing through `inference.vllm_extra.renderer = "laguna-xs.2"`. The A/B/C scale configs use `rollouts_per_example=16`, `batch_size=64`, default mean-baseline advantage, no length shaping, and Prime-RL's native default trainer loss.

## Required Evidence Inputs

Use these artifacts to ground the training set and reward audit:

- Latest Laguna Terminal-Bench Lite run: `/Users/jarrodbarnes/process-rl/jobs/2026-05-29__20-59-31/result.json`
- Laguna long-horizon behavior analysis: `/Users/jarrodbarnes/explore-bench/reports/long-horizon-behavior-analysis/latest/subagents/laguna_trace_analysis.md`
- Laguna training implications: `/Users/jarrodbarnes/explore-bench/reports/long-horizon-behavior-analysis/latest/subagents/laguna_training_implications.md`
- Endless Terminals repo-local generation and gating instructions: `/Users/jarrodbarnes/endless-terminals/AGENTS.md`
- Prime Verifiers wrapper: `/Users/jarrodbarnes/endless-terminals/environments/meta_control`
- Prime-RL renderer reference config: `/Users/jarrodbarnes/endless-terminals/training/configs/meta_control_smoke.toml`

## Admission Checklist

A task can enter the Prime training environment only if:

- It builds on the Apptainer-capable worker.
- Its initial verifier passes from the initial state.
- The final verifier is hidden and callable.
- The prompt does not leak verifier answers, checkpoint names, behavior-card metadata, or difficulty labels.
- Laguna pass@16 is known.
- The task is not `trivial` or `broken`.
- The task has nonzero reward variance under rollout groups, or it is reserved for evaluation only.
- The task does not produce dominant reward through `stop_quality` or `repeat_action_penalty`; hidden final success must remain the main reward source.
- The launch gate has checked calibration band membership and, when rollout groups are available, has hard-stopped if more than 50% of groups have reward std below `1e-5`.

## Bucket Use

Use buckets conservatively:

- `trivial`: exclude from training; retain as sanity eval only.
- `core`: primary training pool.
- `frontier`: secondary training pool and main eval sensitivity set.
- `stretch`: holdout or curriculum tail; include only if reward variance survives.
- `broken`: exclude and repair generator/runtime defects before reconsideration.

## Go/No-Go

Go:

- At least 200 executable environments, or a smaller explicitly approved MVP subset with enough category and behavior-axis coverage. The current 111-task v3 executable subset is enough for trainer integration and reward-variance filtering, not a final capability claim.
- Less than or equal to 50% near-zero reward-std groups.
- Escape-trace review finds no dominant reward hack.
- Baseline Laguna success is inside a trainable band, not saturated at 0 or 1.

No-go:

- Build/test failures dominate after infrastructure fixes.
- Reward variance is dead.
- The model can collect shaping reward while failing final success.
- Current MVP reward produces shaped progress while final success is flat in escape-trace review.
- The Prime environment package cannot reproduce the same hidden-verifier result as the local ET harness.

## First Prime-RL Run

Run `training/configs/meta_control_smoke.toml` first. Treat it as a training-system and reward-shape smoke, not a capability claim.

Run it on the H100 node with 2 inference GPUs and 2 trainer GPUs after the calibrated executable export replaces the current 27-task bootstrap package. The local dry-run validates config resolution, but the first true one-update smoke must run on the training node because this machine cannot validate CUDA, weight sync, or vLLM renderer startup.

Overnight sweep order:

- Run A and B first.
- Run C only if the trainable band is large enough; the launch wrapper defaults to requiring at least 64 trainable tasks when C is requested.
- Use hosted training only after the final `meta-control` environment is pushed privately and the hosted config resolves against `poolside/Laguna-XS.2`; otherwise use the self-managed Prime-RL configs.
- Use Modal only for orchestration, monitoring, and post-train eval workers.

Launch command shape after calibration completes:

```bash
python3 scripts/launch_meta_control_sweep.py \
  --mode self-managed \
  --calibration <completed-calibration.json> \
  --reward-groups <reward-groups.json> \
  --manifest environments/meta_control/meta_control/manifest.json \
  --escape-audit <escape-audit.json> \
  --runs A B \
  --execute
```

The wrapper fails closed if calibration pass rates are missing, if reward-group evidence is absent under `--execute`, if packaged tasks are missing calibration or outside the trainable band, if the reward-variance gate fails, if escape-trace audit is absent/failing under `--execute`, if W&B/Weave online observability smoke fails, if W&B online auth is unavailable, or if self-managed launch is attempted without `nvidia-smi`.

For hosted runs, start the monitor immediately after launch:

```bash
python3 scripts/monitor_meta_control_run.py <run_id> \
  --heldout-eval-cmd '<heldout ET eval command with {run_id} and {step}>' \
  --tblite-eval-cmd '<TBLite OOD eval command with {run_id} and {step}>'
```

The monitor syncs actual Prime rollout samples to Weave and stops the run when shaped reward rises without final-success or loop-rate improvement.

Scale only after:

- Reward components move in the intended direction.
- Loop rate falls without final success falling.
- Stop-early and run-past-complete both fall.
- Held-out `frontier` tasks improve or remain stable.

Before Terminal-Bench Lite OOD eval, refresh mitigation guidance for the Terminus/native-agent harness issue from current primary sources and local baseline artifacts. Do not change the eval harness midstream without enumerating train/eval parity: model id, renderer/tool format, system prompt, max tokens, temperature, stop semantics, and timeout/retry policy.
