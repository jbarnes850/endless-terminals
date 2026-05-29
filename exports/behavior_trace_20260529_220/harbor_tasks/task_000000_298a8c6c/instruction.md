You are helping an operations engineer finish a small incident-triage documentation update in `/home/user/ops-triage`.

The directory already contains incident input data and a lint configuration. Your job is to generate the Markdown runbook summary file `/home/user/ops-triage/INCIDENT_SUMMARY.md` from the incident data, then verify it with the project’s Markdown linter before you stop.

Create `/home/user/ops-triage/INCIDENT_SUMMARY.md` with exactly this structure:

1. A level-1 heading:
   `# Incident Summary`

2. A blank line.

3. A short introductory sentence:
   `Generated triage summary for the current operations review.`

4. A blank line.

5. A level-2 heading:
   `## Active Incidents`

6. A blank line.

7. A Markdown table with exactly these columns, in this order:
   `Incident`, `Service`, `Severity`, `Started`, `Status`, `Owner`

   The table must:
   - include the header row,
   - include the Markdown separator row,
   - contain one row for each incident whose status is not resolved,
   - sort rows by severity in this order: `critical`, then `high`, then `medium`, then `low`,
   - preserve each incident’s service name, timestamp, status, and owner exactly as provided in the source data.

8. A blank line.

9. A level-2 heading:
   `## Immediate Actions`

10. A blank line.

11. A bullet list with one bullet for each active incident in the same order as the table. Each bullet must use this exact format:
    `- [ ] <incident_id>: <next_action>`

12. A blank line.

13. A level-2 heading:
    `## Notes`

14. A blank line.

15. A single sentence:
    `Review unresolved incidents with assigned owners before the next handoff.`

Use `/home/user/ops-triage/incidents.jsonl` as the source of truth. Each line is one JSON object. Ignore resolved incidents entirely.

Important: the lint configuration in `/home/user/ops-triage/.markdownlint.json` is part of the task. If a lint check reports formatting issues, do not just rerun the same failing check; update the Markdown file so that the next lint check can make progress.

When you are done, write a verification log at `/home/user/ops-triage/triage_doc_check.log`. The log must contain exactly three lines:

1. `generated=/home/user/ops-triage/INCIDENT_SUMMARY.md`
2. `lint=pass`
3. `active_incidents=<number>`

Replace `<number>` with the number of unresolved incidents included in the Markdown file.

Stop only after the Markdown file exists, follows the format above, passes the local Markdown lint configuration, and the verification log has been written.
