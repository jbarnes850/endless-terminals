# Executable Environment Gate Handoff

## Current substrate decision

Use the Prime Intellect A6000 Ubuntu worker for executable-environment gating.

- Prime pod: `07c8725919c24923961607522b97917c`
- Name: `endless-apptainer-a6000-gate`
- Provider: `massedcompute`
- SSH: `ubuntu@64.247.206.243`

Do not use Modal functions for Apptainer executable-environment gating. Modal
failed before task logic with user-namespace/setgroups errors:

```text
Could not write info to setgroups: Permission denied
Error while waiting event for user namespace mappings
```

That failure is a substrate mismatch, not generated-task evidence.

## First full gate diagnosis

The first full Prime/Ubuntu report was polluted and should not be treated as final corpus quality:

```text
211 selected
73 build_ok
27 initial_tests_ok
184 failed
```

From `tasks/behavior_trace_20260529_220/calibration/apptainer_build_test_full.json`:

- 138 build failures.
- 109 build failures were Docker Hub unauthenticated pull rate limits:

```text
TOOMANYREQUESTS: You have reached your unauthenticated pull rate limit
```

Those are infrastructure noise caused by repeatedly bootstrapping tasks from `docker://ubuntu:22.04`.

Real generator/container bugs remain:

- `%post` ran under `/bin/sh`, so `set -euo pipefail` failed with `Illegal option -o pipefail`.
- Hallucinated apt package: `sortutils`.
- Malformed generated `container.def`, for example `header key ./start_api.sh had no val`.
- Missing parent directories before heredoc writes.

Initial-state failures had mixed causes:

- 27 were pytest invocation failures: `FATAL: "pytest": executable file not found in $PATH`.
- Broad `chmod -R a+rwX /home/user` clobbered permission-sensitive tasks.
- One `tomllib` failure came from Python 3.10 stdlib mismatch.
- Several failures are Apptainer/FUSE user/permission mismatches, not necessarily Docker/Harbor failures.

## Current code-path fix

`scripts/apptainer_build_test_corpus.py` now supports a cleaner gate:

- Use `--base-sif` to point all tasks at one cached local Ubuntu SIF.
- Rewrite `%post` to `%post -c /bin/bash`.
- Start the SIF through `InteractiveContainerEnvironment`, matching the
  interactive Apptainer rollout substrate.
- Run initial tests inside that running environment.
- Smoke the `/home/user` shell with a benign command.
- Invoke the final verifier and accept only pytest pass/fail return codes.
- Use per-task `APPTAINER_TMPDIR` and `APPTAINER_CACHEDIR`.
- Avoid global chmod by default.
- Optional `--writable-compat auto` applies writability repair only to tasks with `os.access(..., W_OK)` checks and no obvious exact-mode assertions.

`generator/env.py` now aliases the runtime passwd entry so the interactive Apptainer shell presents the actual unprivileged uid as `user`, matching many generated verifier assumptions.

## Next clean gate command

On the Prime A6000 worker:

```bash
cd ~/endless-terminals
python3 scripts/apptainer_build_test_corpus.py \
  --tasks-dir tasks/behavior_trace_20260529_220 \
  --out tasks/behavior_trace_20260529_220/calibration/apptainer_executable_gate_clean.json \
  --eligible-out tasks/behavior_trace_20260529_220/eligible.txt \
  --base-sif base/ubuntu_22.04.sif \
  --workers 4 \
  --build-timeout 900 \
  --test-timeout 180 \
  --tmp-root /home/ubuntu/apptainer_gate_tmp_clean \
  --cache-root /home/ubuntu/apptainer_gate_cache_clean \
  --writable-compat auto
```

After that rerun, only rows with `executable_ok=true` are eligible for Laguna
calibration, GPT-5.5 validity, reward-variance analysis, Harbor export, Prime
Verifiers export, or training.
