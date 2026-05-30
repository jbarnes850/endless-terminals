You are helping as a build engineer triage a release staging area. All files are under `/home/user/artifact_triage`, and you have write permission there. The staging area contains several candidate build directories under `/home/user/artifact_triage/candidates/`, plus policy/reference files under `/home/user/artifact_triage/policy/`.

Your goal is to identify the single candidate artifact set that is eligible for promotion, then produce two small text outputs with a disciplined evidence trail. This is intentionally a diagnosis task: several candidates look plausible, but each one should be eliminated or retained using concrete evidence from the files. Please avoid guessing from filenames alone.

Inputs available to inspect:

- `/home/user/artifact_triage/policy/release_policy.txt`
- `/home/user/artifact_triage/policy/expected_components.tsv`
- `/home/user/artifact_triage/candidates/*/manifest.txt`
- `/home/user/artifact_triage/candidates/*/checksums.sha256`
- `/home/user/artifact_triage/candidates/*/build.log`

A candidate is eligible only if all of the following are true:

1. Its `manifest.txt` contains `channel=stable`.
2. Its `manifest.txt` contains `signed=yes`.
3. Its `manifest.txt` contains `qa_status=pass`.
4. Its `manifest.txt` contains `schema_version=3`.
5. Its `manifest.txt` contains a `commit=` value that matches the allowed release commit specified in `/home/user/artifact_triage/policy/release_policy.txt`.
6. The component names and versions in its `manifest.txt` exactly match `/home/user/artifact_triage/policy/expected_components.tsv`.
   - In the manifest, component lines use the format `component=<name>\t<version>`.
   - In the expected file, component lines use the format `<name>\t<version>`.
   - Compare the set of name/version pairs, not comments or ordering.
7. Every component listed in `manifest.txt` has a corresponding checksum entry in `checksums.sha256`.
8. Its `build.log` must not contain any error, fatal, panic, or traceback message, case-insensitively.
9. Its `build.log` must contain a line indicating that packaging completed successfully.

Create exactly these two files:

1. `/home/user/artifact_triage/promotion_decision.txt`

This file must contain exactly four lines, in this format:

```text
selected_candidate=<candidate-directory-name>
artifact_id=<artifact id from selected manifest>
commit=<commit from selected manifest>
component_count=<number of selected components>
```

The candidate directory name is the final path component under `/home/user/artifact_triage/candidates/`, for example `build-abc123`. Do not include extra spaces, quotes, comments, or blank lines.

2. `/home/user/artifact_triage/triage_progress.log`

This file must be a compact evidence log showing that you converged by eliminating candidates rather than trying unrelated checks. It must contain one line per candidate directory, sorted lexicographically by candidate directory name, followed by one final verification line.

Each candidate line must use exactly this pipe-delimited format:

```text
candidate=<candidate-directory-name>|status=<SELECTED or REJECTED>|reason=<short reason>
```

Rules for the reason field:

- For the selected candidate, use `reason=all policy checks passed`.
- For rejected candidates, use the first failing reason from this ordered list:
  1. `wrong channel`
  2. `unsigned manifest`
  3. `qa failed`
  4. `schema mismatch`
  5. `commit not allowed`
  6. `component mismatch`
  7. `missing checksum`
  8. `build log contains failure`
  9. `packaging completion missing`

The final line of `/home/user/artifact_triage/triage_progress.log` must be exactly:

```text
verification=promotion_decision_matches_selected_candidate
```

After writing the files, verify them yourself by reading them back and checking the selected candidate against the policy files. Stop once the two output files are correct.
