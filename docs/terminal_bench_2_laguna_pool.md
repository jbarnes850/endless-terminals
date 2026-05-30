# Terminal-Bench 2.0 Laguna XS.2 Runbook

## Direct Conclusion

The reproducible path for Laguna XS.2 is Harbor `terminal-bench@2.0` with the
local `pool-laguna-terminus-2` agent adapter. The adapter preserves Harbor's
Terminus 2 tmux/verifier harness, but calls Poolside's OpenAI-compatible API
using the credentials installed by `pool login` and exposes terminal actions as
native Poolside tool calls (`bash_command`, `keystrokes`, and `done`). `pool
exec` is useful as an authentication smoke, but it is not itself a Harbor
environment adapter.

## Source Facts

- Terminal-Bench 2.0 is 89 Harbor-format terminal tasks with task instructions,
  Docker environments, final-state tests, and oracle solutions.
- The paper's neutral model-comparison scaffold is Terminus 2: one headless
  terminal tool, Bash command execution, and context summarization near the
  model context limit.
- The current public task checkout inspected for this setup was
  `harbor-framework/terminal-bench-2` at commit
  `2fd12b88aafdd04a52c298e3940bcb189f9766d6`.
- The local Poolside endpoint lists `poolside/laguna-xs.2` with a 262144-token
  context window and 32768 max completion tokens.
- Direct Harbor `terminus-2` is not equivalent for Laguna XS.2 here: the model
  can emit Poolside-native tool calls instead of Terminus XML/JSON. Use
  `endless_harbor.pool_laguna_agent:PoolLagunaTerminus2`.
- The adapter consumes Poolside native tool calls directly instead of parsing
  fake XML. This keeps Harbor's tmux/verifier loop while avoiding Terminus XML
  parser feedback in Laguna's chat history.
- `pool exec` and `pool acp` are valid authentication/control-plane smokes, but
  they are not currently a clean TB2 scoring backend: `pool exec` injects its
  own workspace agent harness and does not expose a visible per-run model pin
  for `poolside/laguna-xs.2`.

## Configuration Gate

Before a full run, verify the exact eval configuration:

```bash
pool exec -p "Return exactly: POOL_OK" -o json --sandbox disabled
uv run --extra harbor python scripts/run_tb2_laguna_pool.py --probe-only

uv run --extra harbor python scripts/run_tb2_laguna_pool.py \
  --include-task-name gpt2-codegolf \
  --n-concurrent 1 \
  --max-turns 3 \
  --no-delete \
  --jobs-dir evals/tb2_laguna_pool/smoke \
  --job-name laguna-xs2-smoke
```

For a local oracle substrate smoke:

```bash
uv run --extra harbor harbor run \
  -d terminal-bench@2.0 \
  -a oracle \
  -l 1 \
  -n 1 \
  --jobs-dir evals/tb2_pool_smoke/oracle \
  -y
```

## Full Laguna XS.2 Run

Local Docker, conservative concurrency:

```bash
uv run --extra harbor python scripts/run_tb2_laguna_pool.py \
  --jobs-dir evals/tb2_laguna_pool/full \
  --job-name laguna-xs2-tb2-full \
  --n-concurrent 1 \
  --max-turns 64 \
  --max-retries 1 \
  --request-timeout 120 \
  --no-delete
```

Higher environment concurrency is substrate-dependent and Poolside-rate-limit
dependent. Do not raise `--n-concurrent` unless a short smoke shows no 429s and
no empty-turn storm. Daytona-style concurrency, if the Daytona credential is
available in the environment:

```bash
uv run --extra harbor python scripts/run_tb2_laguna_pool.py \
  --env daytona \
  --jobs-dir evals/tb2_laguna_pool/full_daytona \
  --job-name laguna-xs2-tb2-full-daytona \
  --n-concurrent 32 \
  --max-turns 64 \
  --max-retries 1
```

## Reporting

Use the Harbor job directory as the primary artifact. Report:

- Harbor version and dataset: `terminal-bench@2.0`.
- Task count and filters: full run means no `--n-tasks`, no include/exclude.
- Agent: `pool-laguna-terminus-2`
  (`endless_harbor.pool_laguna_agent:PoolLagunaTerminus2`).
- Model: `openai/poolside/laguna-xs.2`.
- API base: Poolside credential `apiUrl` with `/v1` appended.
- Environment backend: `docker` or `daytona`.
- Temperature, max turns, max completion tokens, Poolside retry policy, request
  timeout, concurrency, Harbor retry policy, and timeout multiplier.
- Per-task reward, errors, timeout status, token counts, and trajectory paths.

Do not compare against training until this OOD eval is run with the same Harbor
dataset version, agent scaffold, model id, and environment backend before and
after training.

## Current Blocker

The latest full local attempt reached the live Harbor+Poolside path but stopped
after Poolside returned a hard quota response from `/v1/chat/completions`:

```text
429 {'error': 'usage limit exceeded'}
```

The primary artifact is:

```text
evals/tb2_laguna_pool/full/local-pool-native-laguna-xs2-tb2-full-n1-maxturn64-bash-tool-timeout120
```

That partial job completed 1 of 89 TB2 tasks and left the second task cancelled
after the quota wall. Resume by rerunning the full command after quota reset or
with an equivalent Poolside credential/project whose `/v1/chat/completions`
probe succeeds for `poolside/laguna-xs.2`.
