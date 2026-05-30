You are helping me debug a small local “distributed” dataset indexing workflow for a research project. Everything is under `/home/user/research_cluster`. The workflow simulates three independent worker shards that each scan part of a dataset and write a shard manifest. The problem is that the workers often run quietly, and a successful-looking command may still leave the final combined manifest incomplete. Please do not stop after just launching the workers; inspect the artifacts and verify the final invariant before finishing.

The input dataset is organized as follows:

- `/home/user/research_cluster/datasets/raw/alpha/`
- `/home/user/research_cluster/datasets/raw/beta/`
- `/home/user/research_cluster/datasets/raw/gamma/`

There is also a worker script at:

- `/home/user/research_cluster/bin/scan_shard.py`

and a merge/check script at:

- `/home/user/research_cluster/bin/merge_manifests.py`

Your task is to run the shard-scanning workflow, debug any incomplete shard output, and produce the final verified manifest.

Required final artifacts:

1. A combined manifest at `/home/user/research_cluster/datasets/manifests/final_manifest.tsv`.

2. A verification log at `/home/user/research_cluster/run_logs/verification.log`.

The final manifest must be a UTF-8 TSV file with exactly this header line:

`dataset	shard	record_id	filename	size_bytes	sha256`

After the header, it must contain one row per raw data file found under the three raw dataset directories. Rows must be sorted lexicographically by `dataset`, then numeric `shard`, then `record_id`, then `filename`. The `sha256` column must contain the SHA-256 digest of the file contents, not the filename. The `size_bytes` column must be the exact file size in bytes.

The worker script accepts a shard number and is supposed to write its output under `/home/user/research_cluster/datasets/manifests/shards/`. The merge script is supposed to combine the shard manifests into the final manifest. You may inspect either script if needed. The workflow is intentionally quiet when commands succeed, so lack of terminal output is not enough to assume the work is done.

Please run the shard scans in parallel where appropriate, then ensure all shard outputs are complete before merging. If a shard output is missing or incomplete, diagnose and rerun only what is needed. Do not modify the raw dataset files.

The verification log must be created by you at `/home/user/research_cluster/run_logs/verification.log` after your final check. Its format is strict and will be checked automatically. It must contain exactly five lines:

`status=<OK or FAIL>`
`raw_file_count=<integer>`
`manifest_row_count=<integer>`
`shard_files=<comma-separated list of shard manifest basenames in ascending shard order>`
`verified_at=<ISO-8601 UTC timestamp ending in Z>`

For example, the timestamp format should look like `2025-02-14T09:31:07Z`. The `status` must be `OK` only if you have confirmed that the final manifest row count equals the total number of raw files under `/home/user/research_cluster/datasets/raw`, that every row has six tab-separated fields, and that every listed digest/size matches the corresponding raw file. Otherwise use `FAIL`.

When you are done, stop only after `/home/user/research_cluster/datasets/manifests/final_manifest.tsv` exists and `/home/user/research_cluster/run_logs/verification.log` reports `status=OK`.
