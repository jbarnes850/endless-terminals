You’re helping our FinOps team finish a security-oriented cost optimization scan in the existing workspace at `/home/user/finops-cloud-costs`. The project contains a small local scanner and sample cloud-cost inventory data. The important part of this task is that the project recently changed its source of truth: the old CSV finding file under `/home/user/finops-cloud-costs/reports/` is no longer authoritative, and the scanner should now write/read its canonical state from the configured state directory.

Please complete the end-to-end scan workflow and leave the workspace in the final state described below.

Work inside `/home/user/finops-cloud-costs`.

The project layout includes these relevant paths:

- `/home/user/finops-cloud-costs/bin/finops_security_scan.py`
- `/home/user/finops-cloud-costs/config/security-scan.toml`
- `/home/user/finops-cloud-costs/data/`
- `/home/user/finops-cloud-costs/reports/`
- `/home/user/finops-cloud-costs/state/`

Your job:

1. Inspect the scanner configuration at `/home/user/finops-cloud-costs/config/security-scan.toml`.
2. Confirm which inventory file and state directory the scanner is supposed to use now.
3. Run the scan against the current configured inventory, not against any retired or stale report.
4. Ensure the canonical scan result is written under the configured state directory.
5. Retire the stale legacy report so it cannot be mistaken for the current source of truth.
6. Produce a verification log that proves you validated the new state, not the old report.

Final required filesystem state:

- The canonical current finding artifact must exist at:

  `/home/user/finops-cloud-costs/state/security/current_findings.json`

- The canonical JSON artifact must be valid JSON and must contain:
  - top-level key `scanner`
  - top-level key `inventory`
  - top-level key `generated_at`
  - top-level key `findings`
  - `findings` must be an array
  - every item in `findings` must include:
    - `finding_id`
    - `resource_id`
    - `service`
    - `region`
    - `severity`
    - `monthly_cost_usd`
    - `cost_owner`
    - `issue`
    - `recommendation`

- The old legacy CSV report at:

  `/home/user/finops-cloud-costs/reports/security_findings.csv`

  must not remain as an active report. Retire it by renaming it to:

  `/home/user/finops-cloud-costs/reports/security_findings.csv.retired`

  Do not delete the retired file if it already existed or after renaming it; the retired artifact should remain available for audit.

- Create a human-readable final verification log at:

  `/home/user/finops-cloud-costs/reports/security-scan-final.log`

The verification log must contain exactly these seven lines, in this order, with no extra blank lines:

1. `scan_source=<absolute path to the inventory file actually used>`
2. `canonical_result=/home/user/finops-cloud-costs/state/security/current_findings.json`
3. `legacy_report=/home/user/finops-cloud-costs/reports/security_findings.csv.retired`
4. `legacy_active_present=<yes-or-no>`
5. `finding_count=<number of findings in the canonical JSON findings array>`
6. `critical_or_high_count=<number of canonical findings whose severity is CRITICAL or HIGH>`
7. `verification=new-state`

Formatting requirements for the log:

- Use absolute paths.
- `legacy_active_present` must be `yes` only if `/home/user/finops-cloud-costs/reports/security_findings.csv` still exists at the time you write the log; otherwise use `no`.
- `finding_count` must be computed from `/home/user/finops-cloud-costs/state/security/current_findings.json`.
- `critical_or_high_count` must also be computed from `/home/user/finops-cloud-costs/state/security/current_findings.json`.
- Do not compute either count from the retired CSV report.

Before finishing, verify that the active legacy CSV path is gone, the retired legacy CSV path exists, and the verification log reflects the canonical JSON state.
