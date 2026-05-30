You are acting as a build engineer cleaning up a local artifact handoff area. The project currently has build artifacts under an old staging path, but the canonical artifact location has changed. Please perform the migration using terminal file operations appropriate for batch artifact handling, ideally using `find` and `xargs`.

Initial public paths:

- Old artifact source directory: `/home/user/build_staging/legacy_artifacts`
- New canonical artifact directory: `/home/user/build_staging/release_artifacts`
- Verification log to create: `/home/user/build_staging/artifact_migration.log`

What needs to be done:

1. Move every regular file whose filename ends in `.tar.gz` from `/home/user/build_staging/legacy_artifacts` into `/home/user/build_staging/release_artifacts`.
   - Preserve each artifact filename exactly.
   - Do not move non-`.tar.gz` files.
   - Do not copy the artifacts; the old artifact path must no longer contain those `.tar.gz` files after the migration.
   - The new canonical directory must contain the migrated artifacts.

2. After the migration, create `/home/user/build_staging/artifact_migration.log`.
   - This log must reflect the final state of the new canonical artifact directory, not the old legacy directory.
   - The automated checker will verify the log format exactly.

The log file must contain exactly these three lines:

```text
SOURCE_RETIRED=<number>
DESTINATION_COUNT=<number>
DESTINATION_FILES=<comma-separated filenames>
```

Formatting requirements:

- `SOURCE_RETIRED` must be `yes` if `/home/user/build_staging/legacy_artifacts` contains zero `.tar.gz` files after migration; otherwise it must be `no`.
- `DESTINATION_COUNT` must be the number of `.tar.gz` files present directly inside `/home/user/build_staging/release_artifacts` after migration.
- `DESTINATION_FILES` must list the `.tar.gz` filenames present directly inside `/home/user/build_staging/release_artifacts` after migration.
- The filenames in `DESTINATION_FILES` must be sorted in bytewise/alphabetical order.
- The filenames must be separated by commas with no spaces.
- If there are no destination `.tar.gz` files, `DESTINATION_FILES` must be empty after the equals sign.
- The log must not include extra blank lines or extra text.

Before you finish, verify the final state from `/home/user/build_staging/release_artifacts`, not from `/home/user/build_staging/legacy_artifacts`.
