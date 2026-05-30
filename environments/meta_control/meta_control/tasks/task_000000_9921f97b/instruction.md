I need you to do a small MLOps artifact housekeeping task in the Linux container.

There is an experiment workspace at `/home/user/mlops_runs`. It contains several candidate run directories under `/home/user/mlops_runs/candidates`. Each candidate directory may contain some combination of model artifacts, metrics, and status files. Your job is to inspect the candidates, determine which single run is the valid completed run, and promote only that run’s deployable artifacts into the model registry directory.

Use the following criteria to identify the valid run:

1. The run directory must contain a file named `status.txt` whose content indicates the run completed successfully.
2. The run directory must contain a file named `metrics.json`.
3. The run directory must contain a file named `model.pkl`.
4. The run directory must contain a file named `schema.json`.
5. If multiple directories look plausible at first, use the available files to eliminate incomplete or failed candidates. Do not guess based only on the directory name.

Create the registry directory if it does not already exist:

`/home/user/mlops_runs/registry/churn_model`

After identifying the valid completed run, copy exactly these three files from the valid candidate directory into `/home/user/mlops_runs/registry/churn_model`:

- `model.pkl`
- `metrics.json`
- `schema.json`

Do not copy `status.txt` into the registry directory.

Also create a verification log at:

`/home/user/mlops_runs/registry/churn_model/promotion_audit.log`

The automated checker will verify the exact structure of this log. It must contain exactly four lines, in this order:

1. `selected_run=<RUN_DIRECTORY_NAME>`
2. `eliminated=<COMMA_SEPARATED_RUN_DIRECTORY_NAMES>`
3. `copied_files=model.pkl,metrics.json,schema.json`
4. `verification=complete`

Formatting requirements:

- `<RUN_DIRECTORY_NAME>` must be only the basename of the selected candidate directory, not the full path.
- `<COMMA_SEPARATED_RUN_DIRECTORY_NAMES>` must list every non-selected candidate directory basename, sorted alphabetically, separated by commas, with no spaces.
- The copied files line must appear exactly as shown above.
- The verification line must appear exactly as shown above.
- The log must not contain extra blank lines or extra text.

Before finishing, verify that `/home/user/mlops_runs/registry/churn_model` contains exactly the three promoted artifact files plus `promotion_audit.log`, and no other files.
