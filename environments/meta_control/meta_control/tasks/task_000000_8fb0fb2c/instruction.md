You are helping a monitoring specialist finish a dotenv-based alert configuration audit for a small on-call service. All work must be done under `/home/user/alert_env_audit`. The directory already contains environment files and a Python utility script that may look useful, but you must verify the produced artifact yourself before finishing.

Create the final audit report at:

`/home/user/alert_env_audit/out/alert_matrix.json`

Also create a verification log at:

`/home/user/alert_env_audit/out/verification.log`

The report must be a single JSON object with exactly these top-level keys, in this order:

1. `service`
2. `generated_from`
3. `effective_environment`
4. `alerts`
5. `summary`

Use the dotenv precedence rules below to compute the effective environment.

Environment input files:

- `/home/user/alert_env_audit/env/.env.base`
- `/home/user/alert_env_audit/env/.env.shared`
- `/home/user/alert_env_audit/env/.env.production`
- `/home/user/alert_env_audit/env/.env.local`

The effective environment must be computed by loading those files in the order listed above. If a key appears more than once, the later file overrides the earlier value. Ignore blank lines and comments beginning with `#`. Values are plain strings; do not perform shell expansion. Preserve comma-separated values as strings unless the report format below explicitly requires splitting.

The `generated_from` array in the output JSON must contain the four absolute input file paths above, in load order.

The `service` value must come from the final effective value of `SERVICE_NAME`.

The `effective_environment` object must contain only these keys, sorted alphabetically:

- `ALERT_CHANNELS`
- `ALERT_CRITICAL_THRESHOLD`
- `ALERT_LATENCY_MS`
- `ALERT_OWNER`
- `ALERT_WARNING_THRESHOLD`
- `ENVIRONMENT`
- `ESCALATION_MINUTES`
- `LOG_LEVEL`
- `METRICS_BACKEND`
- `PAGER_ROTATION`
- `SERVICE_NAME`

All values in `effective_environment` must be strings exactly as found after applying override precedence.

Build the `alerts` array from `/home/user/alert_env_audit/config/alert_rules.csv`.

The CSV has a header row. For every non-disabled rule, create one alert object. A rule is disabled only when its `enabled` column is exactly `false` after trimming surrounding whitespace. Any other value should be treated as enabled.

Each alert object must contain exactly these keys, in this order:

1. `name`
2. `metric`
3. `threshold`
4. `severity`
5. `channels`
6. `owner`
7. `escalation_minutes`
8. `pager_rotation`

Alert field rules:

- `name`, `metric`, and `severity` come from the CSV columns with the same names, with surrounding whitespace trimmed.
- `threshold` is numeric:
  - If the CSV `threshold_source` is `warning`, use the effective value of `ALERT_WARNING_THRESHOLD`.
  - If `threshold_source` is `critical`, use the effective value of `ALERT_CRITICAL_THRESHOLD`.
  - If `threshold_source` is `latency_ms`, use the effective value of `ALERT_LATENCY_MS`.
  - Convert the selected value to an integer if it contains only digits; otherwise convert it to a floating-point number.
- `channels` is an array made by splitting the effective `ALERT_CHANNELS` value on commas, trimming whitespace around each channel, and excluding empty channel names. Preserve the channel order.
- `owner` is the effective value of `ALERT_OWNER`.
- `escalation_minutes` is the effective `ESCALATION_MINUTES` converted to an integer.
- `pager_rotation` is the effective value of `PAGER_ROTATION`.

The `alerts` array must preserve the enabled-rule order from the CSV.

The `summary` object must contain exactly these keys, in this order:

1. `enabled_alert_count`
2. `disabled_rule_count`
3. `critical_alert_count`
4. `warning_alert_count`
5. `channels_count`
6. `uses_local_override`

Summary field rules:

- `enabled_alert_count` is the number of alert objects emitted.
- `disabled_rule_count` is the number of CSV rows skipped because `enabled` was exactly `false` after trimming.
- `critical_alert_count` is the number of emitted alerts whose `severity` is exactly `critical`.
- `warning_alert_count` is the number of emitted alerts whose `severity` is exactly `warning`.
- `channels_count` is the number of channel names in the final split `channels` array.
- `uses_local_override` is `true` if `/home/user/alert_env_audit/env/.env.local` changes at least one effective key compared with the value that would exist after loading only the first three dotenv files; otherwise `false`.

Important: There is an existing helper script in `/home/user/alert_env_audit/scripts/` that may complete successfully while still producing an incomplete or semantically wrong report. Do not treat a zero exit code as proof of completion. You must inspect and verify `/home/user/alert_env_audit/out/alert_matrix.json` against the rules above.

When finished, write `/home/user/alert_env_audit/out/verification.log` as UTF-8 text with exactly these five lines:

`artifact_exists=<yes-or-no>`
`json_valid=<yes-or-no>`
`top_level_keys=<comma-separated top-level keys in actual order>`
`enabled_alert_count=<integer count from the final JSON summary>`
`verified=<yes-or-no>`

Use `yes` for `verified` only if the artifact exists, parses as JSON, has the required structure, and the report content follows the dotenv precedence, alert, and summary rules above. Otherwise use `no` and continue fixing the report before stopping.
