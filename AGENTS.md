# Endless Terminals Agent Guide

This repository is being used to generate and calibrate behavior-conditioned
terminal RL environments for Laguna-XS.2. The immediate goal is a shareable,
trainable task corpus, not a new framework.

## Core Research Question

Can behavior-conditioned Endless Terminals tasks improve Laguna's realized
terminal-agent success by training meta-control: progress tracking,
recognition-to-action coupling, verification-directed action, and calibrated
stopping?

The target is generalized capability movement through better control over skills
Laguna already often expresses. Do not narrow the work to failure mitigation
only; the task distribution should hillclimb harder terminal-agent capability
axes while preserving measurable control signals.

## Non-Negotiables

- Keep the existing Endless Terminals LLM funnel. Insert deterministic behavior
  conditioning into it; do not replace it with hand-written tasks.
- Seed tasks from observed behavior: latest TBLite/Laguna traces, TRACE-style
  capability motifs, and OpenThoughts-Agent-v1-RL terminal/SWE task structure.
- Generate real terminal environments with `task.json`, `test_initial_state.py`,
  `test_final_state.py`, and `container.def`.
- Keep privileged truth and final-state assertions out of policy-visible task
  text.
- Treat `exit_code=0` as a weak signal. Final checks must inspect the required
  deliverable and semantic invariants.
- Use Laguna for difficulty calibration, not just for demo smoke tests.
- A task is not eligible for calibration, GPT-5.5 validity, reward-variance
  analysis, Harbor export, Prime Verifiers export, or training unless its
  Apptainer environment is executable.
- Use GPT-5.5/reference sampling only for generation and validity on tasks
  Laguna never solves; do not spend frontier calls on tasks with adequate
  policy signal.
- Do not launch training until executable-environment admission, Laguna pass@k
  calibration, reward-variance filtering, and split hygiene are done.
- Never commit `.env`, API keys, Modal tokens, raw SIFs, private session history,
  or local cache/state directories.

## Current Artifacts

- Behavior cards: `generator/behavior_cards.py`
- LLM task funnel: `generate_tasks.py`, `generator/task_template_gen.py`
- Model routing: `generator/__init__.py`
- Task selection gates: `generator/task_filters.py`
- Executable-environment gate: `scripts/apptainer_build_test_corpus.py`
- Laguna calibration runner: `scripts/run_eligible_calibration.py`
- Harbor/Prime export: `scripts/export_harbor_prime.py`
- Design rationale: `docs/task_family_v1.md`
- Trainable Harbor/Prime environment package: `environments/meta_control`

The raw `tasks/` corpus may be ignored by git. Regenerate or copy it explicitly
when a colleague needs the full local task tree.

## Environment Setup

Use Python 3.12+ and `uv`.

```bash
uv sync
```

Create a local `.env` with the required routing variables. Do not commit it.

```bash
POLICY_MODEL=laguna
REFERENCE_MODEL=gpt-5.5
LAGUNA_API_BASE=https://jbarnes850--specbench-laguna-xs2-vllm-serve.modal.run/v1
LAGUNA_API_KEY=<secret>
OPENAI_API_KEY=<secret>
OPENAI_REASONING_EFFORT=low
```

Backend routing is model-name based:

- `laguna*` routes to `LAGUNA_API_BASE`.
- `gpt-*` and `o*` route to OpenAI.
- Other model names route to local vLLM at `http://localhost:8000/v1`.

Before expensive runs, smoke the Laguna endpoint:

```bash
curl -sS "$LAGUNA_API_BASE/models" \
  -H "Authorization: Bearer $LAGUNA_API_KEY"
```

Expected model id is `laguna`; current known `max_model_len` is `258048`.

## Generation Funnel

The intended end-to-end funnel is:

1. Behavioral analysis: use Laguna/TBLite traces to identify concrete control
   failures and capability next-steps.
2. Deterministic behavior cards: encode the failure motif, required pivot, and
   reward-observable capability in `generator/behavior_cards.py`.
3. LLM generation: use the existing ET four-stage funnel to create task
   template, initial-state test, final-state test, and container definition.
4. Static validation: compile generated pytest files and lint changed generator
   code.
5. Executable-environment gate: build SIFs, start them with the interactive
   Apptainer runtime, run initial tests, smoke the shell, and invoke the final
   verifier.
6. Laguna pass@k calibration: run multiple Laguna rollouts per eligible task.
7. Reference validity gate: run GPT-5.5 only on Laguna-zero tasks.
8. Band and reward-variance selection: keep tasks with `0 < Laguna pass@k < 1`
   and reject groups with dead reward variance.
9. Escape-trace review: prefer tasks where a passing Laguna rollout shows
   dead-end signal -> semantically different action -> prefix progress.
10. Export to Harbor/Prime only after the task survives the gates.

Do not collapse these gates into a single "generated tasks look plausible"
claim. Plausible task text is not an executable RL environment.

Rubric/schema/task generation is not enough; executable environment admission
is the bridge to calibration.

## Behavior Axes To Preserve

Use the existing behavior cards unless there is new trace evidence that demands
a replacement. Current axes:

- `verification_directed_action`: avoid `exit_code=0` false success.
- `recognition_to_action_coupling`: after a dead-end, change action class in a
  way that advances state.
- `bounded_search_discipline`: convert high action diversity into convergence.
- `stop_continue_calibration`: continue under sparse feedback; stop only after
  verified completion.
- `stateful_migration_verification`: verify the new source of truth, not stale
  state.
- `long_horizon_progress_ledger`: carry satisfied and unsatisfied constraints
  across turns.

Task richness means each environment has real files, state transitions,
misleading-but-natural intermediate signals, and artifact-level final checks.
It does not mean adding decorative complexity or unrelated dependencies.

## Generate A New Corpus

Use GPT-5.5 for rich task generation when available:

```bash
uv run python generate_tasks.py \
  --num-tasks 220 \
  --out-dir tasks/behavior_trace_<date_or_slug> \
  --model gpt-5.5 \
  --behavior-conditioned \
  --behavior-seed 20260529 \
  --skip-def-build-test \
  --batch-size 32 \
  --max-concurrency 32 \
  --max-tokens 2048
```

Use `--skip-def-build-test` only when local Apptainer is unavailable. It is not
a pass condition; it defers the build gate.

After generation, record:

- requested count
- saved task count
- behavior-card distribution
- pytest compile result
- model and endpoint used
- whether executable-environment admission was actually run

## Static Validation

Run these before claiming a corpus exists:

```bash
uv run ruff check generate_tasks.py generator scripts
uv run python -m py_compile generate_tasks.py generator/*.py scripts/*.py
find tasks/behavior_trace_<slug> -name 'test_*.py' -print0 \
  | xargs -0 uv run python -m py_compile
```

If generated tests fail to compile, fix the generator or regenerate. Do not
manually patch individual generated tasks unless the edit is explicitly part of
a controlled repair pass.

## Executable Environment Admission Gate

On an Apptainer-capable worker:

```bash
uv run python scripts/apptainer_build_test_corpus.py \
  --tasks-dir tasks/behavior_trace_<slug> \
  --out tasks/behavior_trace_<slug>/apptainer_executable_gate.json \
  --eligible-out tasks/behavior_trace_<slug>/eligible.txt \
  --workers 4 \
  --base-sif /path/to/ubuntu_22.04.sif \
  --tmp-root /tmp/endless-apptainer-tmp \
  --cache-root /tmp/endless-apptainer-cache
```

The calibration universe is exactly the Apptainer
build+runtime-start+initial-pass+shell-smoke+final-verifier-invocation subset.
Do not run Laguna pass@k on tasks that only have generated files, parse, export,
or build under Docker/Harbor.

Executable means all of these pass on the intended Apptainer substrate:

1. `container.def` normalizes/builds into `container.sif`.
2. The SIF starts successfully under the same runtime mode used by Endless
   Terminals interactive rollouts.
3. The initial-state verifier passes inside that running environment.
4. The agent shell can execute at least one benign command in `/home/user`.
5. The final-state verifier can be invoked and returns a valid pass/fail signal,
   even if the task is unsolved.

If writing the eligible list manually, filter only on `executable_ok=true`:

```bash
python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("tasks/behavior_trace_<slug>/apptainer_executable_gate.json").read_text())
rows = report["rows"]
eligible = [r["task_dir"] for r in rows if r.get("executable_ok")]
Path("tasks/behavior_trace_<slug>/eligible.txt").write_text("\n".join(eligible) + "\n")
print(len(eligible))
PY
```

## Laguna Pass@k Calibration

Run Laguna only after a clean executable-environment gate:

```bash
uv run python scripts/run_eligible_calibration.py \
  --eligible-file tasks/behavior_trace_<slug>/eligible.txt \
  --admission-report tasks/behavior_trace_<slug>/apptainer_executable_gate.json \
  --out tasks/behavior_trace_<slug>/laguna_calibration.json \
  --model laguna \
  --n 16 \
  --max-actions 16 \
  --max-tokens 2048 \
  --temperature 1.0 \
  --task-workers 4 \
  --pool-workers 4
```

This writes per-task `solutions/laguna_summary.json` files. These summaries are
the policy band gate input.

## Frontier Validity Gate

Classify after Laguna calibration:

```bash
uv run python -m generator.task_filters \
  --tasks-dir tasks/behavior_trace_<slug> \
  --policy-model laguna \
  --reference-model gpt-5.5 \
  --pass-k 16 \
  --group-size 16 \
  --max-zero-std-group-frac 0.5 \
  --min-policy-success 2 \
  --max-policy-success 14 \
  --preferred-min-policy-success 4 \
  --preferred-max-policy-success 12 \
  --out tasks/behavior_trace_<slug>/band_manifest.json
```

For tasks bucketed as `needs_reference`, run the reference solver and classify
again. Keep:

- `trainable`: primary RL set. For the first serious corpus, target empirical
  Laguna success `2/16..14/16`, with `4/16..12/16` preferred but not treated as
  a rigid law.
- `too_hard_valid`: curriculum or future capability climb.

Drop:

- `trivial`: no RL reward variance.
- `low_signal` / `near_trivial`: outside the hard keep band for the current
  corpus target.
- `broken`: invalid or unsolved by both policy and reference.
- tasks exceeding the zero-std group threshold.

The hard-stop rule is: if more than 50% of rollout groups have near-zero reward
standard deviation (`std < 1e-5`) on a key axis, the gradient is dead. Do not
train through this.

## Reward Design Requirements

Final-state assertions should be decomposed into ordered, prefix-gated
checkpoints:

1. environment validity
2. semantic repair or state creation
3. downstream query/probe over the repaired state
4. final artifact
5. verified done-state

Reward shaping should use the longest satisfied prefix, not raw independent
assertion count. This prevents farming easy partial assertions or satisfying a
later artifact accidentally before the real prerequisite is correct.

Completion and stop quality must dominate partial progress. A partial harvester
that never finishes must score well below a completed task with correct stop.

Action-change credit is valid only when all three are true:

- the previous turn showed failure or non-progress,
- the next action is semantically different,
- the changed action advances the prefix.

Never reward superficial command diversity by itself. Laguna already shows
high-diversity wander loops.

## Export To Harbor And Prime

After executable-environment admission and calibration gates, export the
selected subset:

```bash
uv run python scripts/export_harbor_prime.py \
  --tasks-dir tasks/<corpus-slug> \
  --eligible-file tasks/<corpus-slug>/eligible.txt \
  --admission-report tasks/<corpus-slug>/apptainer_executable_gate.json \
  --prime-env-out environments/meta_control
```

Prime wrapper smoke:

```bash
cd environments/meta_control
uv run vf-build meta-control
prime eval run meta-control -m openai/gpt-5-nano
```

Do not call a Prime/Harbor export training-ready until the underlying ET tasks
have passed executable-environment admission, Laguna calibration, and band
filtering.

## Review Checklist For A Colleague Agent

Before handing back results, answer these directly:

- How many tasks were requested, saved, build-passed, runtime-started,
  initial-state-passed, shell-smoked, final-verifier-invoked, executable, and
  Laguna-calibrated?
- What is the distribution across behavior card and capability?
- What are the band buckets: trainable, trivial, too-hard-valid, broken,
  needs-reference, no-policy-data?
- What fraction of trainable candidates fail the zero-std reward-variance gate?
- Which tasks demonstrate the intended escape trace: dead-end -> different
  action -> prefix advance?
- Which tasks look rich but are invalid, leaky, trivial, or reward-hackable?
- What exact model endpoints, temperatures, max tokens, and pass@k were used?

If any answer is missing, say it is missing. Do not infer it from task text.

## Success Criteria

- Calibration runs only after a clean executable-environment gate, not merely
  after task generation.
- The eligible manifest contains only tasks that built, started, passed initial
  tests, accepted a shell command, and exposed a callable final verifier.
- First serious corpus target is 160 admitted/calibrated environments: 128 train
  and 32 heldout, stratified by behavior axis and difficulty band.

## Common Failure Modes

- Overengineering the pipeline instead of producing gated tasks.
- Treating generated natural-language descriptions as validated environments.
- Creating tasks where raw exit status satisfies the apparent goal.
- Letting final tests leak solution structure through public files or stdout.
- Rewarding independent checkpoint count instead of ordered prefix progress.
- Letting Laguna-zero tasks into RL without reference validity separation.
- Training on pass@k==0 or pass@k==1 tasks and expecting useful RL variance.
- Hiding Apptainer unavailability behind `--skip-def-build-test`.
- Treating Docker/Harbor exportability as calibration eligibility.
- Mixing action protocols between generation, calibration, training, and eval.

## Done Definition

A task corpus is ready for RL only when:

- generated task artifacts exist for every candidate,
- generated pytest files compile,
- SIFs build on an Apptainer-capable worker,
- SIFs start with the same interactive runtime used by rollouts,
- initial-state tests pass inside containers,
- the agent shell executes a benign command in `/home/user`,
- final-state verifiers are callable and return valid pass/fail signals,
- Laguna pass@k summaries exist,
- GPT-5.5/reference validity has resolved Laguna-zero tasks,
- band manifest identifies a non-trivial trainable set,
- reward-variance hard-stop passes,
- train/eval split is disjoint,
- and the export target is verified by a real smoke run.

Until then, call it a generated candidate corpus, not a training-ready corpus.
