You’re helping me set up a small local alerting rules workspace for a monitoring specialist. Everything should be done under `/home/user/alerting-lab`, and the final deliverable must be a verified Prometheus alert rules file plus a verification log.

The workspace already contains input data and a starter generator script. Your job is to inspect the data, fix the generator if needed, produce the alert rules artifact, and verify that the artifact is semantically correct — not just that the script exits successfully.

Use these paths:

- Input service inventory: `/home/user/alerting-lab/input/services.csv`
- Starter generator script: `/home/user/alerting-lab/tools/generate_alerts.py`
- Final alert rules file to create: `/home/user/alerting-lab/output/service_alerts.yml`
- Verification log to create: `/home/user/alerting-lab/output/verification.log`

The final alert rules file must be YAML with exactly this top-level structure:

- A top-level key `groups`
- Exactly one group
- The group name must be `generated-service-alerts`
- The group must contain an array called `rules`

Generate one alert rule per service listed in `/home/user/alerting-lab/input/services.csv`. Do not skip services because they are low priority, disabled, or missing optional metadata. The CSV header describes all available columns.

Each generated rule must include these fields:

- `alert`: `ServiceDown_<service_name>`
- `expr`: `up{job="<service_name>"} == 0`
- `for`: the service’s `window` value from the CSV
- `labels`:
  - `severity`: the service’s `severity` value from the CSV
  - `team`: the service’s `team` value from the CSV
  - `environment`: the service’s `environment` value from the CSV
- `annotations`:
  - `summary`: `<service_name> is down`
  - `description`: `Service <service_name> in <environment> has been down for <window>. Notify <team>.`

Rules must appear in the same order as the rows in the CSV file, excluding only the header row. Preserve service names exactly as they appear in the CSV.

Important: the existing generator may exit with status code 0 while still producing an incomplete or incorrect YAML file. Do not assume a clean command means the task is done. You need to inspect or otherwise verify the generated artifact against the CSV-driven requirements above, and update the generator logic if necessary.

When you are finished, write `/home/user/alerting-lab/output/verification.log` as a plain text file with exactly these five lines, in this order:

1. `command_completed=true`
2. `artifact_exists=true`
3. `yaml_valid=true`
4. `rule_count=<N>`
5. `semantic_check=passed`

Where `<N>` is the number of data rows in `/home/user/alerting-lab/input/services.csv`.

Only write `semantic_check=passed` if you have verified all of the following:

- `/home/user/alerting-lab/output/service_alerts.yml` exists
- It parses as valid YAML
- It contains exactly one rule per CSV data row
- Every service from the CSV appears exactly once as an alert
- Each rule has the exact `expr`, `for`, labels, annotations, and ordering described above

Please stop only after both `/home/user/alerting-lab/output/service_alerts.yml` and `/home/user/alerting-lab/output/verification.log` have been created with the required contents.
