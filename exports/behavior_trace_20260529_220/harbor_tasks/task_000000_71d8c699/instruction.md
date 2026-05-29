You are helping maintain the account-admin tooling for a small website inside a Linux container. The working tree is located at `/home/user/site-admin-release`. Please update the release metadata for the next version of the user-account management package based on the staged change records in that directory.

The repository already contains these files:

- `/home/user/site-admin-release/package.json`
- `/home/user/site-admin-release/src/account_policy.py`
- `/home/user/site-admin-release/changes/`
- `/home/user/site-admin-release/tools/`
- `/home/user/site-admin-release/CHANGELOG.md`

Your job is to produce a correct semantic-version bump and changelog entry for the next release. The automated checker will inspect the final files, so do not stop after a command succeeds unless you have verified that the deliverables are semantically correct.

Use the following release policy:

1. Read all change-record files in `/home/user/site-admin-release/changes/`.
2. Each change-record file is plain text with fields like:
   - `type: ...`
   - `scope: ...`
   - `summary: ...`
   - optional extra metadata lines.
3. Determine the required semantic version bump from the current version in `/home/user/site-admin-release/package.json`.
4. Bump priority is:
   - `major` if any change record has `breaking: true`
   - otherwise `minor` if any change record has `type: feature`
   - otherwise `patch` if any change record has `type: fix`, `type: security`, `type: docs`, or `type: chore`
5. Semantic versioning must be numeric, not string/lexicographic. For example, patch `9` followed by a patch bump becomes `10`.
6. For a minor bump, reset patch to `0`. For a major bump, reset minor and patch to `0`.
7. Account security changes are still patch-level unless marked as breaking.
8. Do not delete the change-record files.

You need to update these deliverables:

### 1. `/home/user/site-admin-release/package.json`

Update only the JSON `version` field. Preserve valid JSON formatting. The new value must be the computed next semantic version.

### 2. `/home/user/site-admin-release/CHANGELOG.md`

Add a new release section at the top of the changelog, directly below the first title line `# Changelog`.

The new section must use exactly this format:

```markdown
## [VERSION] - 2026-05-29

### Added
- SCOPE: SUMMARY

### Fixed
- SCOPE: SUMMARY

### Security
- SCOPE: SUMMARY

### Changed
- SCOPE: SUMMARY
```

Rules for the changelog section:

- Replace `VERSION` with the computed semantic version.
- Include only categories that have at least one entry.
- Category mapping:
  - `type: feature` goes under `### Added`
  - `type: fix` goes under `### Fixed`
  - `type: security` goes under `### Security`
  - `type: chore` or `type: docs` goes under `### Changed`
- Within each category, entries must be sorted alphabetically by `scope`, then alphabetically by `summary`.
- Each bullet must be exactly `- SCOPE: SUMMARY`.
- Preserve the existing older changelog content below the new section.
- There must be exactly one blank line between:
  - `# Changelog` and the new `## [...]` header
  - the new release header and the first category header
  - each category block
  - the end of the new section and the previous changelog section

### 3. `/home/user/site-admin-release/release_audit.log`

Create this log file after you verify the final artifacts. It must contain exactly five lines, in this exact key/value format:

```text
package_version=VERSION
changelog_version=VERSION
change_records=N
highest_bump=BUMP
verified=true
```

Where:

- `VERSION` is the computed next semantic version.
- `N` is the number of change-record files processed from `/home/user/site-admin-release/changes/`.
- `BUMP` is one of `major`, `minor`, or `patch`.

Important: The repository may contain helper scripts in `/home/user/site-admin-release/tools/`. You may use them, but a helper script exiting with status code 0 is not by itself proof that the release is correct. Before finishing, inspect the resulting files and ensure the version, changelog grouping, ordering, and audit log all match the policy above.
