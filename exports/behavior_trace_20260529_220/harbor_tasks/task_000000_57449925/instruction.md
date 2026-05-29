I need you to finish a configuration-change tracking job in `/home/user/config_manager`. The directory contains two snapshots of application configuration files under `/home/user/config_manager/baseline` and `/home/user/config_manager/current`, plus a writable output directory at `/home/user/config_manager/out`.

Your job is to produce a normalized change report that a configuration manager can ingest. Do not assume that lack of terminal output means the job is complete; some helper tools in this workspace are intentionally quiet. Inspect the files and verify the final artifact before stopping.

Create the final report at:

`/home/user/config_manager/out/change_report.tsv`

The report must be tab-separated UTF-8 text with Unix newlines. It must contain exactly one header row followed by one row per detected configuration change. The header must be exactly:

`component	key	change_type	baseline_value	current_value`

Definitions:

- Each configuration file is a plain text file containing key/value settings.
- Files may contain blank lines and comments beginning with `#`; ignore those lines.
- Valid setting lines use either `key=value` or `key: value`.
- Whitespace around keys, separators, and values must be trimmed.
- Inline comments beginning with ` #` after a value must be removed.
- Keys must be compared case-sensitively.
- Values must be compared exactly after trimming and inline-comment removal.
- The component name is the basename of the configuration file without its extension:
  - `api.conf` becomes `api`
  - `worker.conf` becomes `worker`
  - `db.conf` becomes `db`
- Compare files with the same basename from `baseline` and `current`.
- If a key exists only in baseline, its `change_type` is `removed`, and `current_value` must be empty.
- If a key exists only in current, its `change_type` is `added`, and `baseline_value` must be empty.
- If a key exists in both but the normalized values differ, its `change_type` is `modified`.
- If a key exists in both and values are identical, omit it from the report.
- Sort output rows after the header by `component`, then `key`, then `change_type`, all lexicographically ascending.
- Do not quote fields. Do not add extra columns. Do not include carriage returns.

Also create a verification log at:

`/home/user/config_manager/out/verification.log`

The verification log must contain exactly three lines in this format:

1. `report_path=/home/user/config_manager/out/change_report.tsv`
2. `row_count=<number of data rows in the report, excluding the header>`
3. `verification=<status>`

For the third line, use `verification=passed` only after you have run a meaningful check confirming that the generated report matches the source snapshots and formatting requirements. If your check fails, fix the report and rerun the check before writing `verification=passed`.

There is a helper verifier at `/home/user/config_manager/tools/verify_report.py`. You may use it, but do not treat quiet output from intermediate commands as success. Stop only after `/home/user/config_manager/out/change_report.tsv` exists, `/home/user/config_manager/out/verification.log` exists, and the verification step has confirmed the final invariant.
