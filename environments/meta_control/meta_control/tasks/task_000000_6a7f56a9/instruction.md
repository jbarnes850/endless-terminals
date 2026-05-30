You’re helping me as a FinOps analyst clean up a small cloud-cost optimization workspace in `/home/user/finops_pkg_task`. I need you to use normal Linux package-management tooling plus local data processing to produce a verified savings report.

The workspace contains a Python project at `/home/user/finops_pkg_task` with:
- `/home/user/finops_pkg_task/requirements.txt`
- `/home/user/finops_pkg_task/data/cloud_inventory.jsonl`
- `/home/user/finops_pkg_task/data/package_price_catalog.csv`
- `/home/user/finops_pkg_task/scripts/estimate_savings.py`
- `/home/user/finops_pkg_task/README.md`

Your job is to make the reporting workflow work end-to-end and leave behind the exact deliverables described below.

Install the Python dependencies from `/home/user/finops_pkg_task/requirements.txt` into the user environment, without requiring root privileges. Use package-management commands that are appropriate for a non-root Linux container. If you need to isolate the install, keep all generated environment files inside `/home/user/finops_pkg_task`.

Then run or fix the savings-estimation workflow so that it reads:
- `/home/user/finops_pkg_task/data/cloud_inventory.jsonl`
- `/home/user/finops_pkg_task/data/package_price_catalog.csv`

and writes the final report to:

`/home/user/finops_pkg_task/output/savings_report.csv`

The report must be a CSV with exactly this header, in this order:

`service,environment,current_monthly_cost,recommended_monthly_cost,monthly_savings,action,package_source`

Each subsequent row must represent one optimizable cloud resource from the inventory. Do not include resources where the recommended package would not reduce cost. Do not include resources marked as already optimized.

For each included row:
- `service` and `environment` must come from the inventory.
- `current_monthly_cost` must be computed from the current package’s monthly price.
- `recommended_monthly_cost` must be computed from the recommended package’s monthly price.
- `monthly_savings` must equal `current_monthly_cost - recommended_monthly_cost`.
- Monetary values must be formatted with exactly two digits after the decimal point and no currency symbol.
- `action` must be exactly `DOWNGRADE_PACKAGE`.
- `package_source` must be the package source/name used to look up the recommended package in the catalog.

Sort report rows by:
1. descending numeric `monthly_savings`
2. ascending `service`
3. ascending `environment`

Also create a verification log at:

`/home/user/finops_pkg_task/output/verification.log`

The log must contain exactly five lines, each starting with the indicated checkpoint label:

1. `CHECKPOINT package_install: `
2. `CHECKPOINT command_completed: `
3. `CHECKPOINT artifact_exists: `
4. `CHECKPOINT artifact_valid: `
5. `CHECKPOINT semantic_correctness: `

For each checkpoint, write either `PASS` or `FAIL` after the label. For `FAIL`, append a short reason after a single space. For example, a valid line shape is `CHECKPOINT artifact_exists: PASS`.

Before you stop, verify the produced CSV itself rather than relying only on a zero exit code from a script. In particular, check that the artifact is present, has the exact header, contains the expected number of optimizable rows implied by the input data, is sorted as specified, and has internally consistent savings arithmetic. The final `verification.log` should show all five checkpoints as `PASS`.

Do not modify the input files under `/home/user/finops_pkg_task/data`. You may modify scripts under `/home/user/finops_pkg_task/scripts` if needed. Stop only after `/home/user/finops_pkg_task/output/savings_report.csv` and `/home/user/finops_pkg_task/output/verification.log` exist and the verification log shows all checkpoints passing.
