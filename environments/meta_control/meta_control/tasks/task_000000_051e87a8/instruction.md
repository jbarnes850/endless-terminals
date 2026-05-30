You are helping a machine learning engineer prepare a reproducible training-data manifest from a Git working tree.

The repository is located at `/home/user/ml-data-repo`. It is already initialized as a Git repository and contains JSONL training shards under `/home/user/ml-data-repo/data/raw/`. Your job is to create a manifest that describes only the JSONL shard files that are tracked by Git in the current checkout.

Create the file:

`/home/user/ml-data-repo/training_data_manifest.tsv`

The manifest must be a tab-separated text file with exactly one header row followed by one row per eligible shard. The required header is exactly:

`git_path	record_count	split`

Eligibility rules:

1. Include only files tracked by Git in the current checkout.
2. Include only files whose Git path starts with `data/raw/`.
3. Include only files whose name ends with `.jsonl`.
4. Exclude untracked files, ignored files, temporary files, and any files outside `data/raw/`.
5. Do not rely on a pre-existing helper script unless you verify that its output satisfies all rules.

For each included shard:

- `git_path` must be the repository-relative Git path, using forward slashes.
- `record_count` must be the number of non-empty lines in that file.
- `split` must be the immediate directory name under `data/raw/`; for example, a file at `data/raw/train/example.jsonl` has split `train`.

Rows must be sorted lexicographically by `git_path`.

Also create a verification log at:

`/home/user/ml-data-repo/training_data_manifest.verify.log`

The verification log must contain exactly these five lines, in this order:

1. `artifact=training_data_manifest.tsv`
2. `tracked_jsonl_files=<N>`
3. `manifest_rows=<N>`
4. `all_rows_have_three_columns=yes`
5. `status=verified`

Replace `<N>` with the number of eligible tracked JSONL shard files. The two `<N>` values must match. Do not include extra lines or trailing commentary in the verification log.

Before finishing, inspect the generated manifest and make sure it satisfies the eligibility, sorting, and counting rules above. A command or script exiting successfully is not enough; the actual artifact contents must be correct.
