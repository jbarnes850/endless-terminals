You are helping a database administrator reorganize query-optimization artifacts for a PostgreSQL performance investigation. Work only under `/home/user/dbadmin_link_lab`; do not use root privileges.

The directory `/home/user/dbadmin_link_lab` already contains several workload-specific folders under `/home/user/dbadmin_link_lab/workloads` and an output area at `/home/user/dbadmin_link_lab/active`. Your job is to replace copied “active” files with symbolic links so that the DBA can rotate workload inputs without duplicating files.

Complete all of the following:

1. Inspect the existing files under `/home/user/dbadmin_link_lab/workloads` and `/home/user/dbadmin_link_lab/active`.
2. In `/home/user/dbadmin_link_lab/active`, ensure the following entries are symbolic links, not regular files:
   - `/home/user/dbadmin_link_lab/active/current_schema.sql`
   - `/home/user/dbadmin_link_lab/active/current_stats.json`
   - `/home/user/dbadmin_link_lab/active/current_queries.sql`
   - `/home/user/dbadmin_link_lab/active/tuning_notes.md`
3. The four links must point to the correct source files for the “checkout” workload:
   - `current_schema.sql` must link to the checkout workload schema file.
   - `current_stats.json` must link to the checkout workload statistics file.
   - `current_queries.sql` must link to the checkout workload candidate queries file.
   - `tuning_notes.md` must link to the shared DBA tuning-notes file.
4. Make sure the links are relative symlinks rather than absolute symlinks. The relative paths should continue to work if the entire `/home/user/dbadmin_link_lab` directory is moved as a unit.
5. There may be stale files, stale links, or misleading similarly named files in the tree. Do not assume that existing active entries are already correct just because command output is quiet.
6. After fixing the symlinks, run the provided verification helper at:
   `/home/user/dbadmin_link_lab/bin/check_active_links.py`

The helper is intentionally quiet when most things are correct, so you must continue until you have produced the required report file below.

Create the final report file:

`/home/user/dbadmin_link_lab/active/link_verification_report.txt`

The report must contain exactly 7 lines in this format, with no extra blank lines:

```text
link_verification_report
current_schema.sql -> RELATIVE_TARGET
current_stats.json -> RELATIVE_TARGET
current_queries.sql -> RELATIVE_TARGET
tuning_notes.md -> RELATIVE_TARGET
check_active_links.py: PASS
verified: yes
```

Replace each `RELATIVE_TARGET` with the actual symlink target text as reported by the filesystem, not with a resolved absolute path. For example, if a link literally points to `../some/path/file.txt`, the report line must contain that exact relative target string.

The automated check will verify that:
- each of the four active entries is a symbolic link;
- each link points to the intended checkout/shared source file;
- each link target is relative;
- the verification helper succeeds;
- `/home/user/dbadmin_link_lab/active/link_verification_report.txt` exists and matches the required 7-line format exactly.

Before you finish, verify the final state yourself. Do not stop just because a link command or the helper prints little or no output.
