You are helping as a database administrator with a small legacy SQLite query-optimization probe in `/home/user/dbadmin`. The application team left an old benchmarking script at `/home/user/dbadmin/legacy_query_probe.py` and a database at `/home/user/dbadmin/tickets.sqlite3`. Your job is to run the legacy probe, compare the plausible indexing hypotheses it supports, and record the single index recommendation that is best supported by the probe output.

Work only under `/home/user/dbadmin`; you do not need root access. The script is intentionally old, so first run it in the normal way available in the container and use its own help/output to determine the supported options. Do not replace the database or invent results manually. The realistic DBA workflow here is: gather evidence from the probe, eliminate losing index candidates, choose the best one, and stop after producing the requested artifacts.

The probe is expected to evaluate alternative indexes for the slow report query used by the support dashboard. It may print noisy or legacy-looking console output, but each successful benchmark run includes machine-readable evidence for the candidate being tested. There are three plausible candidates to compare:

- `idx_tickets_status_created`
- `idx_tickets_customer_status`
- `idx_tickets_assignee_created`

Create two files:

1. `/home/user/dbadmin/progress.log`

   This must be a plain UTF-8 text log showing that you converged instead of wandering. It must contain exactly four non-empty lines, in this order:

   - Line 1 must start with `hypothesis: ` and list the three candidate index names separated by commas and spaces.
   - Line 2 must start with `evidence: ` and briefly summarize the measured result for `idx_tickets_status_created`.
   - Line 3 must start with `evidence: ` and briefly summarize the measured result for `idx_tickets_customer_status`.
   - Line 4 must start with `evidence: ` and briefly summarize the measured result for `idx_tickets_assignee_created`.

   Each evidence line must include the candidate index name and the measured median latency in milliseconds in the form `median_ms=<number>`. Use the numbers reported by the probe.

2. `/home/user/dbadmin/optimization_decision.json`

   This must be valid JSON with exactly these top-level keys:

   ```json
   {
     "chosen_index": "...",
     "rejected_indexes": ["...", "..."],
     "decision_basis": {
       "metric": "median_ms",
       "lower_is_better": true,
       "measurements": {
         "idx_tickets_status_created": 0,
         "idx_tickets_customer_status": 0,
         "idx_tickets_assignee_created": 0
       }
     },
     "verified": true
   }
   ```

   Requirements for the JSON:
   - `chosen_index` must be the candidate with the lowest measured `median_ms`.
   - `rejected_indexes` must contain the other two candidates, sorted alphabetically.
   - `decision_basis.metric` must be exactly `median_ms`.
   - `decision_basis.lower_is_better` must be the boolean `true`.
   - `decision_basis.measurements` must contain all three candidate names as keys and their measured numeric median latencies as values.
   - `verified` must be the boolean `true`.
   - Do not include any extra top-level keys.

Before finishing, verify that both files exist, that the JSON parses, and that the selected index is justified by the three measured latencies.
