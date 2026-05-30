# Meta Control

Prime Verifiers wrapper for the behavior-conditioned Endless Terminals Harbor corpus.

This package currently bundles the build-plus-initial-pass subset exported from the 2026-05-29 behavior-trace corpus:

- Tasks: 27
- Source corpus: `/Users/jarrodbarnes/endless-terminals/tasks/behavior_trace_20260529_220`
- Export manifest: `meta_control/manifest.json`
- Default harness: `MetaControlHarness`
- Default program: native Verifiers base program with sandboxed terminal tools

This is intentionally pre-calibration. Laguna pass@4 buckets, GPT-5.5 validity on Laguna-zero tasks, reward variance, and escape-trace review should update the task selection before scaled Prime-RL training.

Local smoke:

```bash
uv build
prime --plain env install meta-control -p environments --no-upgrade
uv run python - <<'PY'
import verifiers as vf
env = vf.load_environment("meta-control")
print(type(env.harness).__name__, len(env.taskset.load_tasks()))
PY
```

For Prime-RL training with Laguna, use the `laguna-xs.2` renderer. It is implemented upstream in `PrimeIntellect-ai/renderers` as `renderers/laguna_xs2.py` and is mapped for `poolside/Laguna-XS.2`.
