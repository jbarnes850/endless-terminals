You are helping with a small DevSecOps policy-as-code data pipeline cleanup in `/home/user/policy-pipeline`.

The repository currently has an old policy exceptions source file and a pipeline script that still reads from the old location. Your job is to migrate the source of truth, update the pipeline to use the new canonical policy endpoint file, retire the stale old path, and verify the final state from the new location.

Final required state:

1. Create the new canonical directory and JSON policy file:
   - Directory: `/home/user/policy-pipeline/config/policy`
   - File: `/home/user/policy-pipeline/config/policy/exceptions.json`
   - The file must be valid JSON.
   - It must preserve all existing exception records from the current legacy exception data, without changing their field names or values.
   - It must contain a top-level object with exactly these keys:
     - `schema_version`
     - `exceptions`
   - `schema_version` must be the string value `2024-ops-policy-v2`.
   - `exceptions` must be an array of exception objects migrated from the legacy file.

2. Update the pipeline script:
   - File: `/home/user/policy-pipeline/bin/render_policy_report.py`
   - It must read exceptions only from `/home/user/policy-pipeline/config/policy/exceptions.json`.
   - It must not read from `/home/user/policy-pipeline/data/legacy_exceptions.json`.
   - It must produce the same policy report semantics as before, using the migrated exceptions.

3. Retire the old source of truth:
   - The file `/home/user/policy-pipeline/data/legacy_exceptions.json` must not remain as an active readable data source.
   - It is acceptable to remove it or replace it with a small human-readable retirement notice, but the pipeline must not depend on it.
   - If you leave a notice file at that path, it must clearly say the canonical source is `/home/user/policy-pipeline/config/policy/exceptions.json`.

4. Run the report pipeline and write the verification log:
   - Run the pipeline from the repository root `/home/user/policy-pipeline`.
   - The pipeline must write its final report to `/home/user/policy-pipeline/output/policy_report.json`.
   - Create `/home/user/policy-pipeline/output/migration_verification.log`.
   - The log file must contain exactly five non-empty lines in this order and format:

```text
old_source_retired=<true_or_false>
new_source_exists=<true_or_false>
pipeline_source=<absolute_path_used_by_pipeline>
report_path=/home/user/policy-pipeline/output/policy_report.json
verified_from_new_source=<true_or_false>
```

For the final answer to the user, briefly state what you changed and confirm that `/home/user/policy-pipeline/output/migration_verification.log` was written. Do not include command transcripts.
