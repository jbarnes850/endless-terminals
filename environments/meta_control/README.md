# Meta Control

Prime Verifiers wrapper for the behavior-conditioned Endless Terminals Harbor corpus.

This package bundles the current executable-admitted Laguna pass-band export for meta-control RL. The task list was selected from the behavior-trace corpus after executable admission, Laguna n=8 banding, and GPT-5.5 reference pruning on Laguna-zero tasks.

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

For Prime-RL training with Laguna, use the `laguna-xs.2` renderer.
