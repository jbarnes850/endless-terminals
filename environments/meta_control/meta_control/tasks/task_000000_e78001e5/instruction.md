You’re helping an observability engineer tune a Grafana-style dashboard backed by SQLite data.

The working directory is `/home/user/observability_dashboard`. It already contains a SQLite database at `/home/user/observability_dashboard/metrics.db` and a draft Python exporter at `/home/user/observability_dashboard/export_dashboard_summary.py`.

Please produce the final dashboard summary artifact at:

`/home/user/observability_dashboard/dashboard_summary.json`

The database contains service latency samples and dashboard widget definitions. The existing exporter may run without crashing, but do not assume that a zero exit code means the deliverable is correct. Inspect the generated artifact and verify it against the database before you finish.

Final artifact requirements:

1. `dashboard_summary.json` must be valid JSON.
2. The top-level JSON object must contain exactly these keys:
   - `generated_for`
   - `time_window`
   - `services`
   - `dashboard_widgets`
   - `verification`
3. `generated_for` must be the string:
   - `observability-engineering`
4. `time_window` must be an object with exactly:
   - `start`: ISO-8601 timestamp string from the earliest sample included
   - `end`: ISO-8601 timestamp string from the latest sample included
   - `sample_count`: integer count of included rows
5. Only production data from the last 30 minutes of the run window should be included. In this database, that means rows where:
   - `environment` is `prod`
   - `ts` is greater than or equal to the run’s cutoff timestamp recorded in the database metadata
6. `services` must be an array sorted alphabetically by service name. Each service object must contain exactly:
   - `service`: service name
   - `samples`: number of included samples for that service
   - `avg_latency_ms`: average latency for that service, rounded to 2 decimal places
   - `p95_latency_ms`: nearest-rank 95th percentile latency for that service, rounded to 2 decimal places
   - `error_rate`: fraction of included samples where `status` is not `ok`, rounded to 4 decimal places
7. `dashboard_widgets` must be an array of dashboard widget objects sorted by `widget_id` ascending. Include only widgets whose `enabled` value is true. Each widget object must contain exactly:
   - `widget_id`
   - `title`
   - `service`
   - `metric`
8. `verification` must be an object with exactly:
   - `checked`: boolean `true`
   - `notes`: string `artifact compared against sqlite source rows`
9. Create a verification log at:

`/home/user/observability_dashboard/verification.log`

The log must be plain text with exactly four lines in this order:

- `command_completed=true`
- `artifact_exists=true`
- `artifact_valid_json=true`
- `semantic_checks_passed=true`

Important: a script completing successfully is not enough. Before writing the final verification line, confirm that the JSON content satisfies the filtering, sorting, rounding, widget inclusion, and percentile requirements above. If the existing exporter produces a file but the semantic checks do not match the database, update the processing logic and regenerate the artifact.
