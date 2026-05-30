You are helping a monitoring specialist finish a small alert-rule database migration and produce a validation artifact.

The working directory is `/home/user/monitoring-migration`. It contains an existing SQLite database at `/home/user/monitoring-migration/alerts.db` and a migration file at `/home/user/monitoring-migration/migrations/002_add_alert_metadata.sql`.

Please do the following:

1. Apply the migration SQL file to the SQLite database `/home/user/monitoring-migration/alerts.db`.
2. Validate the migrated database using the validation helper at `/home/user/monitoring-migration/validate_alerts.py`.
3. Create the validation report file `/home/user/monitoring-migration/migration_validation.log`.

The automated checker will inspect `/home/user/monitoring-migration/migration_validation.log`, so the file must follow this exact format:

- UTF-8 text.
- Exactly 6 non-empty lines.
- No extra blank lines before, between, or after the lines.
- Each line must be in `KEY=VALUE` format.
- The keys must appear in this exact order:

```text
MIGRATION_APPLIED
SCHEMA_OK
ROW_COUNT_OK
CRITICAL_ALERTS_OK
VALIDATION_STATUS
CHECKLIST
```

The values must be derived from the actual post-migration database validation result:

- `MIGRATION_APPLIED` must be `yes` only if the migration has actually been applied to the database.
- `SCHEMA_OK` must be `yes` only if the expected migrated columns/tables are present.
- `ROW_COUNT_OK` must be `yes` only if the alert rows survived migration with the expected count.
- `CRITICAL_ALERTS_OK` must be `yes` only if critical alert rows are still valid after migration.
- `VALIDATION_STATUS` must be `pass` only if all validation checks pass.
- `CHECKLIST` must be a comma-separated checklist in this exact order: `migration,schema,row_count,critical_alerts`. Each item must be suffixed with `:ok` or `:fail` based on the validation result.

For example, the shape of the final file must be:

```text
MIGRATION_APPLIED=yes-or-no
SCHEMA_OK=yes-or-no
ROW_COUNT_OK=yes-or-no
CRITICAL_ALERTS_OK=yes-or-no
VALIDATION_STATUS=pass-or-fail
CHECKLIST=migration:ok-or-fail,schema:ok-or-fail,row_count:ok-or-fail,critical_alerts:ok-or-fail
```

Do not replace the database with a new one; update the existing `/home/user/monitoring-migration/alerts.db`. Before finishing, make sure the validation log reflects the actual result of the migration and validation, not just the existence of the database or script.
