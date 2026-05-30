I’m tuning an observability dashboard and need you to diagnose which one of several local service metric snapshots should be used as the dashboard’s “golden” baseline.

All input files are already present under `/home/user/observability/snapshots/`. Each file is a plain text Prometheus-style metrics snapshot for the same service taken at different times. The candidate files are named like `candidate-*.prom`. There may also be notes or helper files in the directory; only inspect the candidate `.prom` snapshots when deciding.

Please determine the single best candidate snapshot using this policy:

1. A usable snapshot must contain all three metric families:
   - `http_requests_total`
   - `process_cpu_seconds_total`
   - `up`
2. The `up` metric must indicate the service is healthy.
3. The snapshot must not contain an obvious scrape or exporter error marker.
4. Among the usable healthy snapshots, choose the one whose request-rate related counter state is most appropriate for a stable dashboard baseline. Avoid snapshots that look like startup resets, stale data, or clearly anomalous traffic compared with the other candidates.
5. If multiple snapshots look plausible, use the evidence in the snapshot contents to eliminate them one by one rather than guessing.

Create exactly one diagnostic report at:

`/home/user/observability/dashboard-baseline-report.txt`

The report must be UTF-8 text and must contain exactly these seven lines, in this exact order, with no extra blank lines:

1. `baseline_candidate=<filename>`
2. `candidate_count=<integer>`
3. `usable_count=<integer>`
4. `rejected=<comma-separated filename:reason entries sorted by filename>`
5. `selected_http_requests_total=<integer>`
6. `selected_up=<integer>`
7. `verification=passed`

Formatting requirements:

- `<filename>` must be only the basename, such as `candidate-a.prom`, not a full path.
- `candidate_count` must count only files matching `/home/user/observability/snapshots/candidate-*.prom`.
- `usable_count` must count candidates that pass the required metric-family, health, and error-marker checks before the final “best baseline” choice.
- The `rejected` line must include every candidate that was not selected, sorted alphabetically by filename.
- Each rejected entry must be formatted as `filename:reason`.
- Use short lowercase reason strings with hyphens instead of spaces, such as `missing-metric`, `unhealthy`, `scrape-error`, `startup-reset`, `stale`, or `traffic-anomaly`.
- `selected_http_requests_total` must be the total request counter value from the selected snapshot.
- `selected_up` must be the numeric value of the selected snapshot’s `up` metric.
- After writing the report, verify the file contents yourself before stopping.
