# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Scope note: a `CLAUDE.md` in the parent directory (`/Users/jarrodbarnes/CLAUDE.md`) describes an unrelated project (ml-intern / materials runtime) and is auto-loaded by directory cascade. Ignore it here — this repository is `endless-terminals` (Gandhi et al., "Scaling RL Environments for Terminal Agents", arXiv:2601.16443).

## What this is

A fully autonomous pipeline that **procedurally generates terminal-use RL environments without human annotation**, then samples solutions, filters by difficulty, and trains/evaluates terminal agents with RL. There is no human in the loop for task creation: an LLM invents the task, writes the container that sets it up, and writes the pytest suites that verify it.

## Commands

Python is managed by `uv` (Python 3.12+). The container runtime is **Apptainer/Singularity**, not Docker.

```bash
# One-time setup
./scripts/install_apptainer.sh          # installs apptainer-suid (needs sudo)
uv sync                                  # core deps
./scripts/get_ubuntu_sif.sh             # pulls ubuntu_22.04.sif (def files bootstrap from this localimage)

# All generation/solution LLM calls hit a LOCAL vLLM server. Start it first:
./scripts/launch_vllm_server.sh <tp_size> <dp_size>   # serves on localhost:8000

# Generate tasks (4-stage pipeline; --model must match what vLLM is serving)
python generate_tasks.py --num-tasks 100 --out-dir ./tasks --model Qwen/Qwen3-32B

# Before sampling/calibration, admit executable Apptainer environments only:
uv run python scripts/apptainer_build_test_corpus.py --tasks-dir ./tasks --out ./tasks/apptainer_executable_gate.json --eligible-out ./tasks/eligible.txt --base-sif ./ubuntu_22.04.sif

# Sample/calibrate only admitted tasks -> pass@k + trajectories under solutions/
uv run python scripts/run_eligible_calibration.py --eligible-file ./tasks/eligible.txt --admission-report ./tasks/apptainer_executable_gate.json --out ./tasks/calibration.json --model Qwen/Qwen3-32B

# Training (SkyRL lives in its OWN venv, not .venv)
python train/prepare_endless.py --task-dir ./tasks --output-dir ./data --build-sif
./scripts/install_sky.sh                 # clones novasky-ai/SkyRL into ./SkyRL, makes ./sky venv
./scripts/train.sh                       # ray start --head; main_endless.py --config-name base

# Evaluation on Harbor / terminal-bench (uses Docker, see conversion note below)
./scripts/setup.sh                       # uv tool install harbor
./scripts/parallel_harbor.sh --model path/to/model --parallel 8
```

There is **no test suite for the package itself**. Every `*.py` named `test_initial_state.py` / `test_final_state.py` is a *generated artifact* run with `pytest` *inside a container* to verify task state — not a unit test of this codebase. `uv run pytest` at the repo root tests nothing.

## Architecture

### The one core abstraction: `generator/env.py`

`InteractiveContainerEnvironment` manages a long-lived Apptainer **instance** with an interactive PTY-backed shell. It is reused by every other layer (solution sampling, RL training env, dataset prep, Harbor agent). Key design decisions that will bite you if unknown:

- **No prompt parsing.** Each `exec()` wraps the command in a subshell that prints a unique marker `__CMD_DONE__<uuid>__:<exit_code>`. A background reader thread drains the PTY non-blocking into a queue; `_read_until_marker` scans for the marker to know the command finished and recover its exit code. PTY echo is disabled; ANSI escapes are stripped.
- **Lifecycle:** `initialize()` starts an `apptainer instance` (`--containall --writable-tmpfs --cleanenv`), then a shell over the PTY, optionally running initial-state tests. Verifier files are staged through the host temp directory bound into the instance and copied into `/home/user`; avoid PTY heredocs for generated pytest files. `cleanup()` stops shell + instance and removes the temp dir.
- Home is always `/home/user`; the agent has **no root**.

### Task generation: the 4-stage funnel (`generate_tasks.py` → `_generate_batch`)

Each stage is a batched LLM call; items that fail a stage are dropped before the next.

1. **Task template** (`generator/task_template_gen.py`) — emits XML with `<task>` (public description) and `<truth>` (**privileged** ground-truth). Diversity comes from randomly composing `TASK_CATEGORIES × COMPLEXITY_LEVELS × SCENARIO_CONTEXTS` into the user prompt.
2. **Initial-state test** (`generator/initial_state_test_gen.py`) — pytest asserting the container's *starting* state (files/dirs/processes that must exist before the agent acts). Generated from the truth.
3. **Final-state test** (`generator/completion_test_gen.py`) — pytest asserting the *end* state after the task is solved. Generated from truth + the initial test.
4. **Apptainer def** (`generator/apptainer_def_gen.py`) — LLM writes a `.def`; generated files are candidates only. Calibration/export/training eligibility requires the separate executable-environment gate in `scripts/apptainer_build_test_corpus.py`.

Output per task: `task.json` (`description`, `truth`, `name`), `test_initial_state.py`, `test_final_state.py`, `container.def`, `container.sif`, `solutions/`. Task dirs are named `task_<idx>_<8hexuuid>`.

The **`truth` ↔ `description` separation is the integrity invariant**: secret verification data lives only in `<truth>`, never in the public description; tests are written from the truth so they can check exact end-states the agent cannot see. Preserve this whenever editing the generation prompts.

### Shared LLM client: `generator/__init__.py`

`chat_completion_batch` is the single concurrent client used by all generation/solution code. It is **hardcoded to `http://localhost:8000/v1` with `api_key="nokey"`** (a local vLLM server) — the `AzureOpenAI`/`OpenAI` imports are vestigial. So `--model` is only a routing string that must match the served model. The **one exception** is `generator/convert_to_harbor/convert_sif_docker.py`, which calls the *real* OpenAI/Anthropic APIs via `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`.

### Agent action protocol (shared across 3 entry points)

System prompt forces the model to think in `<think>...</think>` then emit exactly one of `<command>SHELL</command>` **XOR** `<action>done</action>`. `_extract_action` (in `generator/sample_solutions.py`) parses this and is imported by the RL env and the Harbor agent. Note the inline TODO: it now takes the **last** `<command>` match; models trained on the old code used the **first** — a real behavioral difference when reproducing older results.

### Solution sampling & difficulty filtering (`generator/sample_solutions.py`)

`run_n_solutions` spins up N identical containers in parallel, runs the agent loop with all envs stepping in parallel each turn, runs final tests, and reports an **unbiased pass@k** estimator. Do not run it on generated files alone: the task must first pass `scripts/apptainer_build_test_corpus.py` with `executable_ok=true` (build, runtime start, initial verifier, `/home/user` shell smoke, final verifier invocation). Difficulty is enforced downstream by keeping only tasks where a strong reference model (o3) achieves **pass@16 > 0**, read from `solutions/o3_summary.json`. `prepare_endless.py`, `convert_sif_docker.py`, and older `generate_solutions.py --filter-solved` flows hard-depend on that file existing.

### Training (`train/`) — SkyRL (Ray + vLLM + FSDP)

- `prepare_endless.py` — filters o3-solved tasks, optionally builds SIFs in parallel, writes `train.parquet` / `validation.parquet` in the SkyRL schema (`env_class="endless"`, rule-based `reward_spec` whose `ground_truth` is the task dir, `extra_info.task_dir` + `max_time`).
- `sky_endless.py` — `SkyRLContainerEnv(BaseTextEnv)` wraps `InteractiveContainerEnvironment` for rollouts. **Lazy-initializes** the container on first `step()` (not in `__init__`) to stop Ray from spawning containers during non-rollout phases. Terminates on `done` / `max_turns` / `max_time`; reward is 1 iff final tests pass.
- `main_endless.py` — registers the `endless` env with `skyrl_gym` and runs `BasePPOExp`.
- `confs/` — `base.yaml` (Llama-3.2-3B, PPO with a critic via GAE), `base_qwen.yaml` (Qwen2.5-7B), `base_qwen3_otak8.yaml` (OpenThinker-Agent-v1). These inherit SkyRL's `ppo_base_config`.
- **SkyRL is installed in a separate `./sky` uv venv** from a cloned `novasky-ai/SkyRL` repo (`install_sky.sh`); training does not run from the main `.venv`. `convert_fsdp_to_hf.py` converts checkpoints back to HF format.

### Evaluation: Harbor / terminal-bench (`endless_harbor/endless_agent.py`)

`EndlessAgent(BaseAgent)` adapts the same action protocol (reusing `SYSTEM_MESSAGE` / `USER_TEMPLATE` / `_extract_action`) to the Harbor benchmark. It injects extra restrictions (no sudo, no interactive tools, non-interactive flags), and recovers from context overflow by truncating chat and rebuilding the first user turn with a summarized command history. `scripts/parallel_harbor.sh` shells out to `harbor jobs start` per task on the `daytona` env and scrapes reward from stdout. (Internal identity is still `"echos"` with default model `obiwan96/ota-350` — leftover naming, same system.)

Because Harbor/terminal-bench run on **Docker**, `generator/convert_to_harbor/` bridges the gap: `convert_sif_docker.py` LLM-converts each `container.def` → `Dockerfile`, builds, and re-runs initial tests; `add_reward_file.py` rewrites each task's `tests/test.sh` to write `1`/`0` to `/logs/verifier/reward.txt`.

`tasks.json` (repo root) is 10 sample tasks already in terminal-bench v2 format (`task_id`, `instruction`, `metadata{difficulty,category}`, `config{...}`) — a reference for the Harbor-side schema, not the generator's native format.

## Gotchas

- **A local vLLM server on `localhost:8000` is a hard prerequisite** for `generate_tasks.py`, `generate_solutions.py`, and anything importing `chat_completion_batch`. Without it, every generation call fails (and is silently retried then dropped).
- **Apptainer, not Docker**, for generation/solutions/training. Build needs `--fakeroot --userns`; def files `Bootstrap: localimage` from `./ubuntu_22.04.sif`, so that file must exist in CWD.
- **Docker/Harbor exportability is not calibration eligibility.** The calibration universe is only the Apptainer `executable_ok=true` subset: SIF built, interactive runtime started, initial tests passed, `/home/user` shell smoked, final verifier callable.
- **Author-machine absolute paths are hardcoded** in a couple of places and will break elsewhere: `generator/env.py` `build_container()` rewrites the def to `/data/v-kangandhi/endless/ubuntu_22.04.sif`; `convert_sif_docker.py --retry-failed` rewrites `/data/v-kangandhi/endless` → `/home/v-kangandhi`. Check/patch these before running on a new host.
- **SIF building is commented out** in `generate_tasks.py`'s async path — generated tasks ship `container.def` but no `container.sif`. SIFs are built later by `generate_solutions.py` (`build_and_test`), `prepare_endless.py --build-sif`, or `env.build_container()`.
- Generation parallelism is `ThreadPoolExecutor`-based; failures resolve to `None` and are filtered, so low yield usually means the vLLM server, Apptainer, or prompts are misconfigured rather than a crash.

## Conventions

- Each generator stage is a `*_gen.py` exposing a `generate_*_batch` / `iterate_*_batch` function plus a `SYSTEM_MSG` and `USER_TEMPLATE`. Follow that shape when adding a stage, and wire it into `generate_tasks.py:_generate_batch` in funnel order.
- `tasks/`, `data/`, `*.sif`, `solutions/`, and run logs are gitignored — don't commit generated artifacts.
- Modifying the action protocol means editing `_extract_action` and **all three** consumers (`sample_solutions.py`, `sky_endless.py`, `endless_agent.py`) together, or trajectories and rewards will silently diverge.
