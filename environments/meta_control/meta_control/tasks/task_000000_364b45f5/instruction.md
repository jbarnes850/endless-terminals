You are helping a log analyst investigate worker-process patterns in a small Linux container. All work should be done under `/home/user/process_audit`.

The input log is `/home/user/process_audit/worker_events.log`. It contains timestamped process lifecycle events for several background workers. Each line is pipe-delimited with exactly these fields:

`ISO8601_TIMESTAMP|PID|WORKER_NAME|EVENT|DETAIL`

Your job is to create a concise summary report at:

`/home/user/process_audit/active_worker_summary.txt`

The report must identify which worker PIDs were still active at the end of the log and list them in ascending numeric PID order.

A worker PID counts as active only if its most recent lifecycle event in the log is `START`. If a PID has both `START` and later `STOP` events, it is not active. Do not infer activity from the process name alone; the PID lifecycle is authoritative.

Important: there is an existing helper script at `/home/user/process_audit/make_summary.sh`. You may inspect or use it, but do not assume success just because it exits cleanly. Before finishing, verify that the contents of `/home/user/process_audit/active_worker_summary.txt` match the lifecycle pattern in `/home/user/process_audit/worker_events.log`.

The output file must contain exactly the following structure:

1. First line:
`ACTIVE_WORKER_SUMMARY`

2. Second line:
`source=/home/user/process_audit/worker_events.log`

3. Third line:
`active_count=N`

where `N` is the number of active worker PIDs.

4. Then one line per active PID, sorted by numeric PID ascending, in this exact format:

`PID=<pid> WORKER=<worker_name> STARTED_AT=<timestamp> DETAIL=<detail>`

For each active PID, use the timestamp and detail from that PID’s most recent `START` event.

5. Final line:
`verification=manual_artifact_checked`

There must be no blank lines, no extra columns, no extra whitespace at line ends, and no commentary outside this format.

After creating the report, also create a verification note at:

`/home/user/process_audit/verification.log`

This file must contain exactly three lines:

`checked_input=/home/user/process_audit/worker_events.log`
`checked_output=/home/user/process_audit/active_worker_summary.txt`
`status=verified`

Stop only when both files exist and the summary has been checked against the input log, not merely when a command exits with status 0.
