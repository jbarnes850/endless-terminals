You are helping with a small deployment rollout for a data pipeline. The workspace is writable and located at `/home/user/rollout`.

The rollout package contains:
- `/home/user/rollout/incoming/events.csv`
- `/home/user/rollout/config/release.env`
- `/home/user/rollout/bin/deploy_pipeline.sh`
- `/home/user/rollout/bin/check_rollout.py`

Please complete the rollout and do not stop after the deployment script runs silently. Some rollout steps intentionally produce little or no terminal output, so you must verify the final state before finishing.

Your required end state is:

1. Run the deployment script `/home/user/rollout/bin/deploy_pipeline.sh`.

2. If the deployment leaves any recoverable bad records, handle them as part of the rollout:
   - Inspect the files produced under `/home/user/rollout/staging`.
   - Valid transformed records must end up in `/home/user/rollout/staging/events.normalized.csv`.
   - Rejected records, if any, must remain in `/home/user/rollout/staging/events.rejected.csv`.
   - If there is a recoverable bad record caused only by a missing event type, fix the source data in `/home/user/rollout/incoming/events.csv` by setting that record’s event type to `unknown`, then rerun the deployment script.
   - Do not delete rejected-output files manually; the deployment script is responsible for regenerating staging outputs.

3. Run the targeted verification checker `/home/user/rollout/bin/check_rollout.py` after the final deployment attempt.

4. Create a rollout verification log at `/home/user/rollout/logs/rollout_verify.log`.

The verification log must contain exactly three lines in this exact format:

```text
deployment_status=<STATUS>
normalized_rows=<NUMBER>
rejected_rows=<NUMBER>
```

Formatting requirements:
- `<STATUS>` must be `ok` only if the final checker reports success.
- `<NUMBER>` values must be decimal integers.
- Count data rows only; do not count CSV header rows.
- The file must not contain extra blank lines or extra fields.
- The log directory `/home/user/rollout/logs` should exist if it is missing.

Before you finish, verify that `/home/user/rollout/logs/rollout_verify.log` exists and follows the exact three-line format above. The automated check will inspect the final contents of the rollout files and this log.
