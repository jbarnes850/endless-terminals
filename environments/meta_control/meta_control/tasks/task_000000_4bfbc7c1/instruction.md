You are helping with a small penetration-test evidence cleanup in a Linux container. A vulnerability scanner previously wrote findings to an old SQLite database, but the engagement tooling has been updated and the canonical source of truth must now be a new SQLite database.

Current working files are under `/home/user/pentest`. The old scan database is located at:

`/home/user/pentest/legacy/vulnscan_old.sqlite`

Your job is to migrate the active vulnerability findings into the new canonical SQLite database at:

`/home/user/pentest/current/vulnscan.sqlite`

The old database must not remain usable as the active source after migration.

Please complete the following final state:

1. Create or replace `/home/user/pentest/current/vulnscan.sqlite`.
2. The new database must contain a table named `findings` with exactly these columns, in this order:
   - `id` as an integer primary key
   - `host` as text
   - `port` as integer
   - `service` as text
   - `severity` as text
   - `cve` as text
   - `status` as text
3. Copy only active findings from the legacy database into the new database.
   - Active findings are rows whose `status` value is exactly `open`.
   - Preserve the original `id`, `host`, `port`, `service`, `severity`, `cve`, and `status` values.
   - Do not copy rows with any other status.
4. Retire the old database path by renaming `/home/user/pentest/legacy/vulnscan_old.sqlite` to `/home/user/pentest/legacy/vulnscan_old.sqlite.retired`.
   - The original path `/home/user/pentest/legacy/vulnscan_old.sqlite` should no longer exist when you are finished.
5. Verify the final state from the new canonical database, not from the retired legacy database.
6. Write a verification report to `/home/user/pentest/current/migration_report.txt`.

The report file must contain exactly five lines in this exact format:

`canonical_db=/home/user/pentest/current/vulnscan.sqlite`  
`legacy_db_retired=yes`  
`open_findings=<NUMBER>`  
`critical_open_findings=<NUMBER>`  
`verification_source=current`

Replace `<NUMBER>` with values calculated from `/home/user/pentest/current/vulnscan.sqlite` after migration. The `critical_open_findings` value should count only rows in the new `findings` table where `severity` is exactly `critical` and `status` is exactly `open`.

Make sure the report reflects the final migrated database state. Do not rely on counts from the old path after it has been retired.
