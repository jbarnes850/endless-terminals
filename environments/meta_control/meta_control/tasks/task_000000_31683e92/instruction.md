You are helping set up a local developer diagnostics workspace for a small Python service that is failing inconsistently during startup. Everything you need is under `/home/user/devops-log-lab`; do not use root privileges and do not modify anything outside `/home/user/devops-log-lab`.

The repository contains several plausible startup runners and several log files. Your job is to diagnose which development environment configuration is actually valid, create a clean runnable environment, and write a concise evidence report that can be checked automatically.

The important paths are:

- Repository root: `/home/user/devops-log-lab`
- Candidate environment files: `/home/user/devops-log-lab/env-candidates/`
- Service source: `/home/user/devops-log-lab/service/`
- Startup logs: `/home/user/devops-log-lab/logs/`
- Output directory you must create/use: `/home/user/devops-log-lab/diagnostics/`

You should inspect the available files and logs instead of guessing. There are multiple misleading partial-success signals: at least one candidate appears to import correctly but fails readiness checks, and at least one log looks severe but is from an unrelated old run. Use disciplined diagnosis: compare candidates, collect evidence, eliminate failed branches, then converge on one final configuration.

Set up the development environment in-place under `/home/user/devops-log-lab` so the chosen configuration can run using the repository’s Python code. You may create a virtual environment if useful, but it must stay somewhere under `/home/user/devops-log-lab`. You may run multiple inspections or checks in parallel if that helps, but the final report must show that your conclusion is evidence-based rather than a random choice.

When finished, create exactly these two files:

1. `/home/user/devops-log-lab/diagnostics/hypothesis_matrix.tsv`

This must be a UTF-8 TSV file with exactly one header line followed by one line per candidate environment file found in `/home/user/devops-log-lab/env-candidates/`, sorted lexicographically by candidate filename.

The header must be exactly:

```text
candidate	status	evidence	next_action
```

Each data row must contain exactly four tab-separated fields:

- `candidate`: the candidate filename only, such as `dev-a.env`
- `status`: one of exactly `ELIMINATED` or `SELECTED`
- `evidence`: a compact semicolon-separated summary of the decisive observed evidence for that candidate. It must mention at least one concrete log filename or command-observed symptom for every eliminated candidate.
- `next_action`: for eliminated candidates, this must start with `do_not_use:` followed by a short reason. For the selected candidate, this must start with `use_for_dev:` followed by a short reason.

Exactly one row must have `status` equal to `SELECTED`.

2. `/home/user/devops-log-lab/diagnostics/final_verification.log`

This must be a UTF-8 text file with exactly six non-empty lines in the following format:

```text
selected_candidate=<candidate filename>
app_module=<python module path used to start the service>
configured_port=<port number>
readiness_result=<PASS or FAIL>
health_json=<single-line JSON object returned by the service health/readiness endpoint or local readiness command>
stop_reason=<short explanation>
```

Rules for `final_verification.log`:

- `selected_candidate` must match the candidate marked `SELECTED` in the TSV.
- `app_module` must be the actual module path used to start or validate the service.
- `configured_port` must be the port that the selected configuration uses.
- `readiness_result` must be `PASS` only if you actually verified the selected configuration through the service’s intended readiness/health mechanism.
- `health_json` must be a single-line JSON object, not prose. Preserve the JSON keys and values returned by the working readiness mechanism.
- `stop_reason` must state that verification succeeded and that eliminated candidates were not pursued further.

You should also leave the repository in a runnable state for the selected development configuration. Automated checks will inspect both report files and may rerun the selected service validation from the repository root.

Before you stop, verify the report files are present, well-formed, and internally consistent. Stop after the valid configuration is selected and verified; do not continue trying unrelated commands once you have converged.
