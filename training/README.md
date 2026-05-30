# Prime-RL Training Spine

This folder is the fork-local Prime-RL handoff for behavior-conditioned Endless Terminals environments. We are not using Prime hosted training. The trainer path is self-managed `PrimeIntellect-ai/prime-rl` with `PrimeIntellect-ai/verifiers`, `PrimeIntellect-ai/renderers`, a mutable vLLM Laguna backend, and the native Verifiers terminal harness.

## Macro Framing

Research question: can behavior-conditioned synthetic terminal environments, generated from Laguna's own Terminal-Bench Lite failure modes and shaped through Endless Terminals, improve generalized terminal-agent performance by training progress tracking, verification-directed action, pivoting, bounded search, and stop calibration?

The target is not trace imitation. TBLite rollouts are evidence for task and reward design. The training signal must come from executable environments with hidden verifiers, calibrated difficulty, and reward variance.

## Prime And Runtime Status

Verified locally with Prime CLI:

```bash
prime --version
prime --plain whoami
prime --plain config view
prime --plain train models --output json
```

Observed:

- Prime CLI: `0.6.10`
- Account: `jbarnes850`
- Hosted training model present: `poolside/Laguna-XS.2`

Prime-RL should run online RL with the trainer and inference server connected by weight sync. The Modal TP4 public endpoint is useful for calibration and baseline pass@k, but it is not the training inference worker. On a 4xH100 node, start with a 2 GPU serving worker plus 2 GPU trainer allocation unless throughput measurements force a different split.

## Required Gates Before Training

Do not run Prime-RL training until the corpus has passed these gates, in order:

1. Executable-environment admission on an Apptainer-capable worker:
   - Build succeeds.
   - Container starts.
   - Initial verifier runs.
   - Shell smoke runs.
   - Final verifier invocation is reachable.
2. Laguna pass@16 calibration only on the executable subset.
3. Bucket tasks into `trivial`, `core`, `frontier`, `stretch`, and `broken`.
4. Run GPT-5.5 validity only on Laguna-zero executable tasks.
5. Reward-variance gate: hard stop if more than 50% of rollout groups have near-zero reward std (`std < 1e-5`).
6. Escape-trace gate: inspect rollouts for reward hacking, verifier leakage, repeated command loops, premature stop, and run-past-complete behavior.

## Data Discipline

Training candidates must come from the build-plus-initial-pass subset, not the raw generated corpus. Raw TBLite traces are not demonstrations and must not be included in policy-visible prompts.

Policy-visible task prompts may include ordinary public task context only. They must not include:

- Hidden verifier logic.
- Assertion names or checkpoint labels that reveal the solution.
- Difficulty bucket labels.
- Behavioral card metadata.
- Frontier/reference model outputs.

## Prime Environment Path

The Prime environment package should wrap the already-generated Endless Terminals tasks rather than replacing the ET generation funnel.

Current local package target:

```text
environments/meta_control/
```

It currently bundles the executable-admitted `meta_control` subset. This is acceptable for wrapper validation and reward plumbing, but the training manifest must be replaced by the final calibrated pass-band export before launch.

The environment should be installed locally for Prime-RL:

```text
meta-control
```

## Smoke Commands

After the environment package exists:

```bash
prime --plain env install meta-control -p environments --no-upgrade
uv run python - <<'PY'
import verifiers as vf
env = vf.load_environment("meta-control")
print(type(env.harness).__name__, len(env.taskset.load_tasks()))
PY
uv run rl @ training/configs/meta_control_smoke.toml --dry-run --output-dir /tmp/laguna-et-dry
```

`prime env build` is for OpenEnv image layouts with `proj/`; this package is a Verifiers environment wheel, so the correct local path is install, environment load smoke, Prime-RL dry run, then a one-batch rollout smoke against the trainable vLLM backend.

Repo-local smoke checks:

```bash
python3 scripts/smoke_training_contracts.py --json-out /tmp/laguna-meta-control-contracts.json
python3 scripts/smoke_live_endpoint.py --out /tmp/laguna-live-endpoint-smoke.json
python3 scripts/check_training_launch_gates.py \
  --calibration tasks/behavior_trace_20260529_220/calibration/buckets_current.json \
  --manifest environments/meta_control/meta_control/manifest.json \
  --min-trainable-tasks 1 \
  --out /tmp/laguna-meta-control-launch-gates.json
UV_PROJECT_ENVIRONMENT=/tmp/obs-smoke-venv uv run --no-project --with wandb --with weave \
  python scripts/smoke_observability.py --out /tmp/laguna-meta-control-observability.json
export PRIME_RL_ROOT=/Users/jarrodbarnes/endless-terminals/third_party/prime-rl
PYTHONPATH="${PRIME_RL_ROOT}/src" \
  UV_PROJECT_ENVIRONMENT=/tmp/prime-rl-config-smoke \
  uv run --no-project --python 3.12 \
    --with pydantic --with 'pydantic-config @ git+https://github.com/samsja/pydantic_config.git' \
    --with tomli --with tomli-w --with nvidia-ml-py --with torch --with wandb --with loguru --with rich --with tyro \
    python -m prime_rl.entrypoints.rl @ training/configs/meta_control_smoke.toml \
      --dry-run --output-dir /tmp/laguna-meta-control-dry
```

The dry-run writes resolved Prime-RL subconfigs to `/tmp/laguna-meta-control-dry/configs`. Check that smoke keeps `group_size = 4`, `batch_size = 4`, `use_token_client = false`, weak native `online_difficulty_filtering = true`, W&B sample/distribution logging, and `inference.toml` keeps `vllm_extra.renderer = "laguna-xs.2"`. The A/B/C configs currently use `group_size = 8`, `batch_size = 8`, default mean-baseline advantage with no length shaping, and `sample_ratio = 1.0` for all-rollout W&B sample logging.

Native Prime-RL filtering only drops average-reward all-fail/all-pass groups. It does not catch constant shaped-reward groups, so `scripts/check_training_launch_gates.py` remains mandatory before launch. Latest upstream Prime-RL honors W&B `sample_ratio`, but it does not provide native Weave rollout tracing in the repo-local checkout. Weave remains covered by `scripts/smoke_observability.py` and any post-run rollout sync path; do not claim full train-rollout Weave lineage until that path is exercised on the actual run artifacts.

After calibration completes and the final executable train set has replaced the bootstrap package, launch through:

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

Use `--mode hosted` only after `meta-control` has been pushed privately to Prime environments. The local wrapper already installs with `prime --plain env install meta-control -p environments --no-upgrade`; the hosted environment id used by the prepared configs is `jbarnes850/meta-control`.

## Laguna Renderer

Prime-RL has a Laguna-specific renderer in `PrimeIntellect-ai/renderers` at `renderers/laguna_xs2.py`. The upstream renderer map includes `poolside/Laguna-XS.2 -> laguna-xs.2`, and `LagunaXS2RendererConfig` defaults `enable_thinking = false`, matching the current endpoint smoke where responses include ordinary content and no `reasoning_content`.

For Prime-RL, use:

```toml
[inference.vllm_extra]
renderer = "laguna-xs.2"
enable_thinking = false
```

Reference config:

```text
training/configs/meta_control_smoke.toml
```

## Training Justification Gate

This training run is worth doing because it will improve the go/no-go decision for scaling behavior-conditioned Endless Terminals RL on Laguna for the post-training operator/research team as measured by hidden-verifier success, loop-rate reduction, action-diversity improvement, stop calibration, and reward-variance health, producing a smoke-trained checkpoint candidate through a multi-turn terminal environment where the policy can inspect files, edit code, run commands/tests, pivot after observations, and stop.
