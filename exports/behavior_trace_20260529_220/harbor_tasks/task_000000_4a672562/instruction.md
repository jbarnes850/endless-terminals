You are helping me as a DevSecOps engineer enforce a small “policy as code” check for environment variables in a service workspace.

The workspace is `/home/user/workspace/policy-envcheck`. It contains a dotenv file at `/home/user/workspace/policy-envcheck/config/.env.release` and a policy file at `/home/user/workspace/policy-envcheck/policy/required-env.txt`. Your job is to inspect those inputs and create a machine-checkable compliance report.

Create the output directory `/home/user/workspace/policy-envcheck/audit` if it does not already exist, then write exactly one report file:

`/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt`

The report must be plain UTF-8 text and must use this exact section structure and labels:

1. First line:
`DOTENV POLICY REPORT`

2. Second line:
`workspace=/home/user/workspace/policy-envcheck`

3. Third line:
`env_file=/home/user/workspace/policy-envcheck/config/.env.release`

4. Fourth line:
`policy_file=/home/user/workspace/policy-envcheck/policy/required-env.txt`

5. Fifth line:
`status=FAIL` or `status=PASS`

6. Sixth line:
`missing_required_count=N`

7. Seventh line:
`forbidden_present_count=N`

8. Eighth line:
`duplicate_key_count=N`

9. Ninth line:
`parse_error_count=N`

10. Then a section header line:
`[missing_required]`

11. Under `[missing_required]`, list missing required variable names one per line in lexicographic order. If there are none, write exactly:
`NONE`

12. Then a section header line:
`[forbidden_present]`

13. Under `[forbidden_present]`, list forbidden variable names that are present in the dotenv file one per line in lexicographic order. If there are none, write exactly:
`NONE`

14. Then a section header line:
`[duplicate_keys]`

15. Under `[duplicate_keys]`, list duplicated keys one per line in lexicographic order, formatted exactly:
`KEY=count`
For example, if `API_TOKEN` appears three times, the line would be `API_TOKEN=3`. If there are no duplicate keys, write exactly:
`NONE`

16. Then a section header line:
`[parse_errors]`

17. Under `[parse_errors]`, list parse errors one per line in ascending line-number order, formatted exactly:
`line NUMBER: TEXT`
where `TEXT` is the full original line content from the dotenv file. If there are no parse errors, write exactly:
`NONE`

18. Then a section header line:
`[effective_values_sha256]`

19. Under `[effective_values_sha256]`, list the effective dotenv values for every valid parsed key after applying normal dotenv override behavior, one per line in lexicographic key order, formatted exactly:
`KEY=SHA256`
where `SHA256` is the lowercase SHA-256 hex digest of the final effective value only, not of the key and not including a newline. If no valid keys are parsed, write exactly:
`NONE`

Parsing rules for this task:

- Blank lines are ignored.
- Lines whose first non-space character is `#` are comments and ignored.
- A valid assignment may optionally begin with `export `.
- A valid key must match this regex: `[A-Za-z_][A-Za-z0-9_]*`
- The separator must be a single `=`.
- Values may be unquoted, single-quoted, or double-quoted.
- Preserve spaces inside quoted values.
- For unquoted values, trim leading and trailing whitespace around the value.
- For double-quoted values, interpret the common escaped sequences `\n`, `\t`, `\"`, and `\\`.
- For single-quoted values, take the contents literally between the quotes.
- Inline comments are not part of an unquoted value only when the `#` is preceded by at least one whitespace character.
- If a valid key appears multiple times, the final occurrence wins for the effective value, but all occurrences count toward duplicate detection.
- A line that is not a comment, not blank, and not a valid assignment according to these rules is a parse error.

Policy rules:

- `/home/user/workspace/policy-envcheck/policy/required-env.txt` contains one policy item per line.
- Blank lines and lines starting with `#` are ignored.
- Lines starting with `required:` name variables that must appear as valid parsed keys.
- Lines starting with `forbidden:` name variables that must not appear as valid parsed keys.
- The final report status is `PASS` only if all counts are zero for missing required variables, forbidden present variables, duplicate keys, and parse errors. Otherwise the status is `FAIL`.

Important: do not rely on shell `source`, `set -a`, or re-running the same failing environment-loading command if it does not work. The dotenv file may intentionally include syntax that normal shell sourcing cannot handle. If a first attempt to load it as shell variables fails or produces no progress, switch to directly parsing the file content and policy rules instead.

Before finishing, verify that `/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt` exists and follows the exact labels and ordering above. Do not include extra commentary, timestamps, markdown, or additional files in the audit directory.
