You’re helping a FinOps analyst prepare a small cloud-cost export bundle for an internal optimization review. The working directory is `/home/user/finops/cloud-costs`.

The raw cost export files are in `/home/user/finops/cloud-costs/raw`. Your job is to create a SHA-256 checksum manifest for the analyst so the bundle can be verified before it is uploaded to the reporting system.

Create this file:

`/home/user/finops/cloud-costs/audit/cloud_cost_checksums.sha256`

The manifest must contain exactly one line for each regular `.csv` file directly inside `/home/user/finops/cloud-costs/raw`. Do not include non-CSV files, subdirectories, helper scripts, temporary files, or files from any other directory.

Each line must use this exact format:

`&lt;64-character lowercase sha256 checksum&gt;  raw/&lt;filename&gt;`

Important formatting details:
- Use SHA-256, not MD5 or SHA-1.
- Use exactly two spaces between the checksum and `raw/&lt;filename&gt;`.
- The path field must start with `raw/` and must not be an absolute path.
- Sort the lines alphabetically by the `raw/&lt;filename&gt;` path.
- End the file with a single trailing newline.
- The file must not contain blank lines, comments, headers, or summaries.

There may be a helper script in the project that appears to create a checksum file. You may use it if it is correct, but do not assume command success means the deliverable is correct. Before finishing, inspect or otherwise verify that the manifest itself satisfies the format and data requirements above.

Also create a verification log at:

`/home/user/finops/cloud-costs/audit/verification.log`

The verification log must contain exactly these four lines, using this exact key/value format:

`artifact_exists=yes`
`algorithm=sha256`
`csv_file_count=&lt;number of csv files included in the manifest&gt;`
`manifest_verified=yes`

The `csv_file_count` value must match the number of CSV files directly under `/home/user/finops/cloud-costs/raw` that are represented in the final manifest.

Stop only after the checksum manifest exists, has the correct format, includes the correct files, uses SHA-256 checksums for the current file contents, and the verification log has been written exactly as specified.
