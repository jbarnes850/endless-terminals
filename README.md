# Endless Terminals

**Scaling RL Environments for Terminal Agents**

[![Paper](https://img.shields.io/badge/Paper-arXiv-red)](https://arxiv.org/abs/2601.16443)
[![Dataset](https://img.shields.io/badge/Dataset-HuggingFace-yellow)](https://huggingface.co/collections/obiwan96/endless-terminals)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Endless Terminals is a fully autonomous pipeline that procedurally generates
terminal-use tasks without human annotation for training terminal agents with
reinforcement learning.

ProcessRL is a concrete release built on this pipeline. See the
[ProcessRL reproduction runbook](docs/processrl_reproduction.md), the
[released environments](https://huggingface.co/datasets/Jarrodbarnes/processrl-terminal-environments),
and the [rollout analysis site](https://process-rl-site.vercel.app).

## Installation

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv)

```bash
# Install Apptainer
./scripts/install_apptainer.sh

# Install dependencies
uv sync

# Download base container
./scripts/get_ubuntu_sif.sh
```

## Task Generation

Start a vLLM server locally before running task generation:

```bash
./scripts/launch_vllm_server.sh 1 1
```

Then generate candidate task artifacts:

```bash
uv run python generate_tasks.py \
  --num-tasks 100 \
  --out-dir ./tasks \
  --model meta-llama/Llama-3.2-3B-Instruct \
  --batch-size 8 \
  --max-concurrency 8
```

Each task candidate contains `task.json`, `test_initial_state.py`,
`test_final_state.py`, and `container.def`. Treat these as generated candidates,
not calibration-ready environments.

## Generation Pipeline

The full pipeline is:

1. Generate task description/truth, initial-state verifier, final-state verifier,
   and `container.def`.
2. Run static validation on generated Python.
3. Admit only executable Apptainer environments.
4. Run policy calibration only on admitted tasks.
5. Run reference validity only where policy calibration says it is needed.
6. Filter by pass@k band and reward variance.
7. Export Harbor/Prime wrappers only after the Apptainer admission and
   calibration gates.

Static validation:

```bash
uv run ruff check generate_tasks.py generator scripts
uv run python -m py_compile generate_tasks.py generator/*.py scripts/*.py
find ./tasks -name 'test_*.py' -print0 | xargs -0 uv run python -m py_compile
```

Executable-environment admission:

```bash
uv run python scripts/apptainer_build_test_corpus.py \
  --tasks-dir ./tasks \
  --out ./tasks/apptainer_executable_gate.json \
  --eligible-out ./tasks/eligible.txt \
  --workers 4 \
  --base-sif ./ubuntu_22.04.sif \
  --tmp-root /tmp/endless-apptainer-tmp \
  --cache-root /tmp/endless-apptainer-cache
```

A task is eligible only when `executable_ok=true`: `container.def` built into
`container.sif`, the SIF started under the interactive Apptainer rollout runtime,
initial tests passed, the `/home/user` shell accepted a benign command, and the
final verifier produced a valid pass/fail signal.

## Calibration

```bash
uv run python scripts/run_eligible_calibration.py \
  --eligible-file ./tasks/eligible.txt \
  --admission-report ./tasks/apptainer_executable_gate.json \
  --out ./tasks/policy_calibration.json \
  --model meta-llama/Llama-3.2-3B-Instruct \
  --n 16 \
  --max-actions 16 \
  --temperature 1.0
```

Do not calibrate generated files directly. The calibration universe is exactly
the Apptainer build+start+initial-pass+shell-smoke+final-verifier subset.

## Filtering And Export

```bash
uv run python -m generator.task_filters \
  --tasks-dir ./tasks \
  --policy-model meta-llama/Llama-3.2-3B-Instruct \
  --reference-model gpt-5.5 \
  --pass-k 16 \
  --group-size 16 \
  --max-zero-std-group-frac 0.5 \
  --min-policy-success 2 \
  --max-policy-success 14 \
  --preferred-min-policy-success 4 \
  --preferred-max-policy-success 12 \
  --out ./tasks/band_manifest.json
```

Export only admitted and selected tasks:

```bash
uv run python scripts/export_harbor_prime.py \
  --tasks-dir ./tasks \
  --eligible-file ./tasks/eligible.txt \
  --admission-report ./tasks/apptainer_executable_gate.json \
  --harbor-out ./exports/tasks/harbor_tasks \
  --prime-env-out ./environments/meta_control
```

## Training

Train only after executable admission, calibration, reference validity for
policy-zero or otherwise ambiguous tasks, band filtering, reward-variance
filtering, and split hygiene. The first serious corpus target is 160 admitted
and calibrated environments, split into 128 train and 32 heldout, stratified by
behavior axis and difficulty band.

```bash
# Prepare dataset
uv run python train/prepare_endless.py --task-dir ./tasks --output-dir ./data --build-sif

# Install SkyRL
./scripts/install_sky.sh

# Run training
ray start --head
uv run python train/main_endless.py --config-dir train/confs --config-name base
```

Configs: `base.yaml` (Llama-3.2-3B), `base_qwen.yaml` (Qwen2.5-7B), `base_qwen3_otak8.yaml` (Qwen3-8B)

## Evaluation with Harbor

```bash
# Install Harbor
./scripts/setup.sh

# Run evaluation
./scripts/parallel_harbor.sh --model path/to/model --parallel 8
```

Harbor/Docker execution is an export/evaluation target, not the admission gate
for calibration or training. Apptainer executability is the required bridge from
generation to calibration.

## Citation

```bibtex
@article{gandhi2025endless,
    title={Endless Terminals: Scaling RL Environments for Terminal Agents},
    author={Gandhi, Kanishk and Garg, Shivam and Goodman, Noah D. and Papailiopoulos, Dimitris},
    journal={arXiv preprint arXiv:2601.16443},
    year={2025}
}
```

## License

Apache License 2.0 - see [LICENSE](LICENSE).
