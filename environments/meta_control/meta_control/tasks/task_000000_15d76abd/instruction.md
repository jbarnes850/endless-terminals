I need help finishing a small connectivity triage report for a distributed service test inside this container.

The working directory is `/home/user/netdebug`. It contains probe data collected from three application nodes in `/home/user/netdebug/probes.jsonl` and a helper script at `/home/user/netdebug/build_report.py`. The helper may be useful, but do not assume that a clean exit means the report is correct. The goal is the final artifact, not just running the script.

Create or update exactly this file:

`/home/user/netdebug/connectivity_report.txt`

The report must summarize failed connectivity checks from the JSONL probe data. Each line in `/home/user/netdebug/probes.jsonl` is one JSON object with these fields:

- `source`: node name that initiated the check
- `target`: host or service name contacted
- `port`: integer TCP port
- `protocol`: always `tcp`
- `status`: either `ok` or `fail`
- `error`: empty string for successful checks, otherwise a short failure reason
- `rtt_ms`: number for successful checks, or `null` for failures

Only records where `status` is exactly `fail` belong in the failure section.

The final report must use this exact plain-text format:

1. First line exactly:
   `CONNECTIVITY FAILURE REPORT`

2. Second line exactly:
   `source,target,port,error`

3. Then one CSV line for each failed probe, sorted by:
   - ascending `source`
   - then ascending `target`
   - then ascending numeric `port`

4. Each failure row must contain exactly:
   `source,target,port,error`

5. After the failure rows, add one summary line exactly in this format:
   `TOTAL_FAILURES=N`

   where `N` is the number of failed probe records in `/home/user/netdebug/probes.jsonl`.

6. Add a final verification line exactly in this format:
   `VERIFIED=yes`

Important verification requirements:

- The file must include every failed probe record from `/home/user/netdebug/probes.jsonl`.
- The file must not include successful probes.
- The total count must match the number of failed records in the JSONL input.
- The file must be sorted as described above.
- The final line must be `VERIFIED=yes` only after you have checked the artifact content against the input data.
- Do not create the report in another directory.
- Do not leave a report that merely reflects whether a command exited successfully.

This is meant to model a network engineer’s quick distributed-system connectivity triage: produce the report and verify that the contents are semantically correct before stopping.
