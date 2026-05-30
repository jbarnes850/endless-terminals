You are helping as a backup engineer verify which of several currently running integrity-check jobs is the real production verification job and which are decoys/stale workers.

In the container, there will be several user-owned processes running with similar names and arguments. Your job is to inspect the process table, identify the single correct production backup integrity verifier process, and write one audit line to:

`/home/user/backup_audit/integrity_process_report.tsv`

The directory `/home/user/backup_audit` is writable. Do not require root privileges. You may use normal process-inspection tools available in a Linux terminal.

The report file must contain exactly two lines:

1. A header line exactly:
`timestamp_utc	pid	status	evidence`

2. One data line describing the production verifier process you selected.

The data line must be tab-separated with exactly four fields:

- `timestamp_utc`: current UTC timestamp in ISO-8601 basic form ending in `Z`, formatted like `YYYY-MM-DDTHH:MM:SSZ`.
- `pid`: the numeric PID of the selected running process.
- `status`: exactly `verified`.
- `evidence`: a compact semicolon-separated explanation showing why this process was selected and why the obvious alternatives were rejected.

The `evidence` field must include all of the following labels exactly once, in any order, with non-empty values after each equals sign:

- `selected_cmd=`
- `accepted_dataset=`
- `accepted_epoch=`
- `rejected=`

The `rejected=` value should briefly mention at least two rejected candidate reasons, such as wrong dataset, dry-run mode, stale epoch, or helper/child process.

Before finishing, verify that the PID you wrote still belongs to the selected running verifier process and that the report file has exactly two lines in the requested tab-separated format. Once the file is correct, stop; do not keep exploring unrelated commands.
