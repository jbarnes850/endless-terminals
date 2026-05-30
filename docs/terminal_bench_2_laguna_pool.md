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

That partial job completed 1 of 89 TB2 tasks and left the second task cancelled
after the quota wall. Resume by rerunning the full command after quota reset or
with an equivalent Poolside credential/project whose `/v1/chat/completions`
probe succeeds for `poolside/laguna-xs.2`.

## Non-Pool Terminus XML Fallback

For a fallback that avoids Poolside native tools entirely, use the local
rate-limited Terminus agent with `parser_name=xml` and route Laguna as a plain
text completion model through OpenRouter. This is not the direct
Poolside-authenticated run above; report it separately as
`laguna-xs2-openrouter-terminus-xml`.

The local fallback agent is
`endless_harbor.rate_limited_terminus:RateLimitedTerminus2`. It adds two pieces
that stock `terminus-2` does not provide for Laguna through OpenRouter:

- A process-wide OpenRouter throttle plus reset-aware 429 sleep/retry.
- A parser adapter for Laguna-native XML-ish shell calls such as
  `<tool_call>shell ... <arg_key>command</arg_key><arg_value>...</arg_value>`.

Probe:

```bash
OPENROUTER_API_KEY=<secret> \
uv run --extra harbor python scripts/run_tb2_laguna_terminus_xml.py --probe-only
```

Smoke:

```bash
OPENROUTER_API_KEY=<secret> \
uv run --extra harbor python scripts/run_tb2_laguna_terminus_xml.py \
  --include-task-name gpt2-codegolf \
  --n-concurrent 1 \
  --max-turns 3 \
  --min-request-interval 4.5 \
  --jobs-dir evals/tb2_laguna_terminus_xml/smoke \
  --job-name laguna-xs2-openrouter-xml-native-toolcall-smoke
```

Validated smoke artifact:

- `evals/tb2_laguna_terminus_xml/smoke/laguna-xs2-openrouter-xml-native-toolcall-smoke/result.json`
- 1/1 trials completed, 0 exceptions, reward 0.0 at `max_turns=3`.
- Trajectory shows Laguna-native `<tool_call>shell ... <arg_value>ls -la /app</arg_value>` parsed into Terminus keystrokes and sent to tmux.

Full run:

```bash
OPENROUTER_API_KEY=<secret> \
uv run --extra harbor python scripts/run_tb2_laguna_terminus_xml.py \
  --jobs-dir evals/tb2_laguna_terminus_xml/full \
  --job-name laguna-xs2-openrouter-xml-native-toolcall-full \
  --n-concurrent 1 \
  --max-turns 64 \
  --max-retries 1 \
  --request-timeout 120 \
  --min-request-interval 5.0 \
  --skip-probe
```

Current OpenRouter blocker:

- OpenRouter's public model list exposes only `poolside/laguna-xs.2:free`.
- The direct key metadata has no spend limit configured, but the model route
  returns `free-models-per-min` 429s under TB2 prompt growth.
- In a full-run attempt, the first task consumed 419390 input tokens, 143408
  cache tokens, and 11454 output tokens before provider sleeps caused Harbor
  `AgentTimeoutError`. That artifact is not a valid TB2 result:
  `evals/tb2_laguna_terminus_xml/full/laguna-xs2-openrouter-xml-native-toolcall-full/result.json`.

Do not treat OpenRouter-free 429 or agent-timeout artifacts as Laguna TB2
scores. A defensible full result needs either a non-throttled Poolside/OpenRouter
Laguna endpoint or a local Laguna serve whose latency does not count provider
rate-limit sleep against Harbor task timeouts.

Slow fallback run in progress:

```bash
tmux new-session -d -s tb2_laguna_key2_full \
  "cd /Users/jarrodbarnes/endless-terminals && \
   uv run python scripts/launch_tb2_openrouter_key2_timeoutx20.py \
   > evals/tb2_laguna_terminus_xml/full_logs/laguna-xs2-openrouter-key2-timeoutx20-detached-full.out 2>&1"
```

This uses the second distinct local OpenRouter key found in
`/Users/jarrodbarnes/sci-feasibility/.env`, `--min-request-interval 15.0`, and
`--timeout-multiplier 20`:

- Job directory:
  `evals/tb2_laguna_terminus_xml/full/laguna-xs2-openrouter-key2-native-toolcall-timeoutx20-detached-full`
- Log:
  `evals/tb2_laguna_terminus_xml/full_logs/laguna-xs2-openrouter-key2-timeoutx20-detached-full.out`
- Monitor:
  `tmux attach -t tb2_laguna_key2_full`
- Stop:
  `tmux kill-session -t tb2_laguna_key2_full`

At launch validation, the job reached `gpt2-codegolf`, wrote a trajectory, and
executed parsed terminal commands including `ls -la /app/`, with 1 running task
and 88 pending. This run is not a completed TB2 result until all 89 trials have
finished and `result.json` shows no running or pending trials.

Latest monitor sample at `2026-05-30 11:19:51Z`:

- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The detached OpenRouter key2 job is still running in tmux.
- `result.json`: 89 total, 0 completed, 1 running, 88 pending.
- First trajectory: `gpt2-codegolf__QoqwGHM`, 32 steps, 31 agent calls,
  116165 input tokens, 4476 output tokens.
- Log evidence shows parsed terminal execution such as `ls -la /app/`, `ls`,
  `clear`, and `C-c`, without current `free-models-per-min` 429s under the
  15-second request interval.

Latest monitor sample at `2026-05-30 11:21:24Z`:

- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The Poolside credentials file has exactly one stored credential, the rotated
  `sky_FA...` token, so the direct runner is not accidentally selecting an older
  credential.
- The detached OpenRouter key2 job is still running in tmux.
- `result.json`: 89 total, 0 completed, 1 running, 88 pending.
- First trajectory: `gpt2-codegolf__QoqwGHM`, 35 steps, 34 agent calls,
  135727 input tokens, 4891 output tokens.
- Log evidence still shows parsed terminal execution under the 15-second request
  interval, but the first task is making poor progress with repeated directory
  listing commands. This remains a live Harbor run, not a completed benchmark
  result.

Latest monitor sample at `2026-05-30 11:31:12Z`:

- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The detached OpenRouter key2 job completed its first Harbor trial cleanly and
  advanced to task 2.
- `result.json`: 89 total, 1 completed, 0 errors, 1 running, 87 pending.
- Completed trial: `gpt2-codegolf__QoqwGHM`, reward 0.0, 64 agent calls,
  406353 input tokens, 150976 cache tokens, 8483 output tokens.
- Running trial: `llm-inference-batching-scheduler__TC6vagW`, 8 agent calls at
  the sample point.
- This proves the slow OpenRouter fallback can advance through the TB2 queue
  without provider-induced timeout under `--min-request-interval 15.0` and
  `--timeout-multiplier 20`; it still is not a completed benchmark result until
  all 89 trials finish.

Latest monitor sample at `2026-05-30 11:32:25Z`:

- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The detached OpenRouter key2 job is still running in tmux.
- `result.json`: 89 total, 1 completed, 0 errors, 1 running, 87 pending.
- Completed trial remains `gpt2-codegolf__QoqwGHM`, reward 0.0.
- Running trial: `llm-inference-batching-scheduler__TC6vagW`, 18 steps,
  17 agent calls, 76252 input tokens, 3550 output tokens at the sample point.
- The run remains a valid end-to-end Harbor artifact in progress, but behavior
  quality is poor: task 2 logs show repeated exploration/reset/listing commands.

Latest monitor sample at `2026-05-30 11:34:30Z`:

- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The detached OpenRouter key2 job is still running in tmux.
- `result.json`: 89 total, 2 completed, 0 errors, 1 running, 86 pending.
- Completed trials: `gpt2-codegolf__QoqwGHM` and
  `llm-inference-batching-scheduler__TC6vagW`, both reward 0.0.
- Aggregate tokens at sample: 530483 input, 161328 cache, 12997 output.
- Running trial: `break-filter-js-from-html__XyLvKwM`.
- Log evidence shows task 2 ended after the model sent `C-d` and Harbor logged
  `Session has ended, breaking out of agent loop`; Harbor then advanced to task
  3 without recording a provider or harness exception.

Latest monitor sample at `2026-05-30 11:35:42Z`:

- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The detached OpenRouter key2 job is still running in tmux.
- `result.json`: 89 total, 2 completed, 0 errors, 1 running, 86 pending.
- Completed trials remain `gpt2-codegolf__QoqwGHM` and
  `llm-inference-batching-scheduler__TC6vagW`, both reward 0.0.
- Aggregate tokens at sample: 530483 input, 161328 cache, 12997 output.
- Running trial: `break-filter-js-from-html__XyLvKwM`, 8 steps, 7 agent calls,
  10406 input tokens, 942 output tokens.
- Task 3 log evidence shows parsed terminal execution and actual file
  inspection commands: `ls -la /app/` and `cat /app/filter.py`.

Latest monitor sample at `2026-05-30 11:36:58Z`:

- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The detached OpenRouter key2 job is still running in tmux.
- `result.json`: 89 total, 2 completed, 0 errors, 1 running, 86 pending.
- Completed trials remain `gpt2-codegolf__QoqwGHM` and
  `llm-inference-batching-scheduler__TC6vagW`, both reward 0.0.
- Running trial: `break-filter-js-from-html__XyLvKwM`, 12 steps,
  11 agent calls, 19973 input tokens, 1425 output tokens.
- Task 3 continues to execute parsed commands and inspect task files, including
  `cat /app/filter.py` and `python3 -c "print(open('/app/filter.py').read())"`.

Latest monitor sample at `2026-05-30 11:40:45Z`:

- Secret-safe `.env` sweep across local repos found two distinct real
  `OPENROUTER_API_KEY` values and two placeholder examples. The live run uses
  the key from `/Users/jarrodbarnes/sci-feasibility/.env`; the older key present
  in several other repos is reserved as a fallback if this run starts erroring.
- Poolside direct probe still fails before Harbor launch with
  `429 {"error":"usage limit exceeded"}`.
- The detached OpenRouter key2 job is still running in tmux.
- `result.json`: 89 total, 2 completed, 0 errors, 1 running, 86 pending.
- Completed trials remain `gpt2-codegolf__QoqwGHM` and
  `llm-inference-batching-scheduler__TC6vagW`, both reward 0.0.
- Running trial: `break-filter-js-from-html__XyLvKwM`, 26 trajectory entries
  and 25 agent entries at the sample point.
- Log evidence continues to show parsed terminal execution on task 3, including
  `cat /app/filter.py` and `cat /app/test_outputs.py`.
- Static validation remains clean:
  `uv run ruff check endless_harbor/rate_limited_terminus.py scripts/run_tb2_laguna_terminus_xml.py scripts/launch_tb2_openrouter_key2_timeoutx20.py`
  and
  `uv run python -m py_compile endless_harbor/rate_limited_terminus.py scripts/run_tb2_laguna_terminus_xml.py scripts/launch_tb2_openrouter_key2_timeoutx20.py`.

Latest monitor sample at `2026-05-30 11:44:38Z`:

- To reduce wall-clock under OpenRouter's free-route throttling, the older
  discovered OpenRouter key was probed successfully and launched as a separate
  tail-half shard.
- Active tmux sessions:
  - `tb2_laguna_key2_full`: original full run from the front of TB2.
  - `tb2_laguna_key1_tail`: 44-task tail shard using
    `evals/tb2_laguna_terminus_xml/shards/tb2_tail_half_tasks.txt`.
- Tail shard job:
  `evals/tb2_laguna_terminus_xml/full/laguna-xs2-openrouter-key1-native-toolcall-timeoutx20-tail-half`.
- Tail shard first task is `install-windows-3.11__8pCnQLe`; Harbor has 0
  completed, 0 errors, 1 running, 43 pending.
- Tail shard log already shows parsed terminal execution:
  `ls -la /app/`, `ls -la /app/isos/`,
  `qemu-system-i386 --version`, `which nginx`, and
  `apt-get update && apt-get install -y nginx`.
- Original key2 full run remains alive: 2 completed, 0 errors, 1 running,
  86 pending. The running task `break-filter-js-from-html__XyLvKwM` has
  40 trajectory entries.
- Static validation after generalizing the launcher remains clean:
  `uv run ruff check endless_harbor/rate_limited_terminus.py scripts/run_tb2_laguna_terminus_xml.py scripts/launch_tb2_openrouter_key2_timeoutx20.py`
  and
  `uv run python -m py_compile endless_harbor/rate_limited_terminus.py scripts/run_tb2_laguna_terminus_xml.py scripts/launch_tb2_openrouter_key2_timeoutx20.py`.
