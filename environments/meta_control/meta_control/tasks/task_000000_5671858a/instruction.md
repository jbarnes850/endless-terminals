I’m testing an API integration locally and need a clean dotenv-derived environment snapshot for a mock request runner.

Work inside `/home/user/api-integration`. The directory already contains dotenv-style configuration files and a small helper script that may look useful. Please produce the final deliverable file:

`/home/user/api-integration/build/request.env`

The file must be generated from the dotenv files in `/home/user/api-integration` using these rules:

1. Read `/home/user/api-integration/.env` first.
2. Read `/home/user/api-integration/.env.local` second.
3. Treat `/home/user/api-integration/.env.local` as the higher-priority file: if the same key appears in both files, the value from `.env.local` must be used.
4. Ignore blank lines and full-line comments.
5. Preserve values exactly after dotenv parsing, including punctuation and embedded URL characters.
6. Remove surrounding single or double quotes from values when they are used only as dotenv quoting.
7. Do not include any variables whose final value is empty.
8. Do not include variables that are comments, disabled examples, or malformed lines.
9. The output must contain only the environment variables required for the integration request:
   - `API_BASE_URL`
   - `API_TOKEN`
   - `CLIENT_ID`
   - `FEATURE_FLAGS`
   - `REQUEST_TIMEOUT_MS`
10. Sort the output lines alphabetically by variable name.
11. Each line in `/home/user/api-integration/build/request.env` must be exactly:
   `KEY=value`
12. The file must end with a trailing newline.
13. Do not print shell `export` statements into the file.
14. Do not include quotes around values in the output file.

Also create a verification log at:

`/home/user/api-integration/build/verification.log`

The log must be plain text with exactly these four lines, in this order:

`artifact_exists=yes`
`line_count=5`
`keys_sorted=yes`
`dotenv_precedence_verified=yes`

Only write `dotenv_precedence_verified=yes` after you have inspected the generated artifact and confirmed that the higher-priority dotenv file actually won for overlapping keys. If a helper command exits successfully but the artifact is missing, incomplete, unsorted, contains quotes, contains `export`, includes empty variables, or uses the lower-priority values, fix the generation logic and regenerate the artifact before writing the verification log.

Stop when both `/home/user/api-integration/build/request.env` and `/home/user/api-integration/build/verification.log` exist and match the requirements above.
