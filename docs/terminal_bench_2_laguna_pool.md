# Terminal-Bench 2.0 Laguna XS.2 Runbook

## Direct Conclusion

The reproducible path for Laguna XS.2 is Harbor `terminal-bench@2.0` with the
Harbor `terminus-2` agent, calling Poolside's OpenAI-compatible API using the
credentials installed by `pool login`. `pool exec` is useful as an authentication
smoke, but it is not itself a Harbor environment adapter.

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

## Configuration Gate

Before a full run, verify the exact eval configuration:

```bash
pool exec -p "Return exactly: POOL_OK" -o json --sandbox disabled

uv run --extra harbor python scripts/run_tb2_laguna_pool.py \
  --n-tasks 1 \
  --max-turns 1 \
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
  --n-concurrent 4 \
  --no-delete
```

Daytona-style concurrency, if the Daytona credential is available in the
environment:

```bash
uv run --extra harbor python scripts/run_tb2_laguna_pool.py \
  --env daytona \
  --jobs-dir evals/tb2_laguna_pool/full_daytona \
  --job-name laguna-xs2-tb2-full-daytona \
  --n-concurrent 32
```

## Reporting

Use the Harbor job directory as the primary artifact. Report:

- Harbor version and dataset: `terminal-bench@2.0`.
- Task count and filters: full run means no `--n-tasks`, no include/exclude.
- Agent: `terminus-2`.
- Model: `openai/poolside/laguna-xs.2`.
- API base: Poolside credential `apiUrl` with `/v1` appended.
- Environment backend: `docker` or `daytona`.
- Temperature, concurrency, retry policy, and timeout multiplier.
- Per-task reward, errors, timeout status, token counts, and trajectory paths.

Do not compare against training until this OOD eval is run with the same Harbor
dataset version, agent scaffold, model id, and environment backend before and
after training.
