You are helping with a disk-usage cleanup/migration for an MLOps experiment workspace under `/home/user/mlops_workspace`. The workspace contains experiment artifact directories, an older disk-usage cache, and a newer tracking location that should become the only source of truth.

Your job is to perform an end-to-end artifact inventory, migrate the authoritative disk-usage state to the new location, retire the old state path, and write verification logs proving you checked the final state from the new source rather than from stale files.

The relevant paths are:

- Workspace root: `/home/user/mlops_workspace`
- Experiment artifact tree: `/home/user/mlops_workspace/experiments`
- Old disk-usage state directory: `/home/user/mlops_workspace/.du_cache`
- New authoritative disk-usage state directory: `/home/user/mlops_workspace/.artifact_index`
- Final human-readable report: `/home/user/mlops_workspace/reports/artifact_disk_report.tsv`
- Final verification log: `/home/user/mlops_workspace/reports/verification.log`

You do not have root access and should only modify files inside `/home/user/mlops_workspace`.

The old state under `/home/user/mlops_workspace/.du_cache` may appear valid and may contain plausible-looking totals, but it is no longer authoritative. Do not finish by validating against that old directory. The required final state is that `/home/user/mlops_workspace/.artifact_index` contains the authoritative generated inventory, while `/home/user/mlops_workspace/.du_cache` is retired so that future tools cannot accidentally treat it as the source of truth.

Please complete these steps:

1. Analyze disk usage for every experiment directory directly under `/home/user/mlops_workspace/experiments`.
   - Each direct child directory of `/home/user/mlops_workspace/experiments` is one experiment.
   - For each experiment, calculate:
     - total artifact size in bytes,
     - number of regular files,
     - number of checkpoint files,
     - number of metric files,
     - number of log files.
   - Checkpoint files are files ending in `.ckpt`, `.pt`, `.pth`, or `.onnx`.
   - Metric files are files named `metrics.json`, ending in `.metrics.json`, or ending in `.csv`.
   - Log files are files ending in `.log` or `.txt`.
   - The categories may overlap only if the filename rules overlap; count them strictly by the filename rules above.
   - Use byte-accurate file sizes, not rounded human-readable sizes.

2. Generate the new authoritative inventory at:
   - `/home/user/mlops_workspace/.artifact_index/inventory.tsv`

   The file must be tab-separated UTF-8 text with exactly one header line followed by one row per experiment. The header must be exactly:

   `experiment_id	total_bytes	file_count	checkpoint_count	metric_count	log_count	largest_file_bytes	largest_file_relpath`

   Requirements for rows:
   - `experiment_id` must be the experiment directory basename.
   - `total_bytes`, `file_count`, `checkpoint_count`, `metric_count`, `log_count`, and `largest_file_bytes` must be base-10 integers with no commas.
   - `largest_file_relpath` must be the path to the largest regular file in that experiment, relative to the experiment directory.
   - If there is a tie for largest file, choose the lexicographically smallest relative path.
   - Sort rows by `total_bytes` descending, then by `experiment_id` ascending.
   - Do not include hidden state directories such as `.du_cache`, `.artifact_index`, or `reports` as experiments.

3. Generate a summary file at:
   - `/home/user/mlops_workspace/.artifact_index/summary.json`

   It must be valid JSON with exactly these top-level keys:

   - `schema_version`
   - `source`
   - `experiment_count`
   - `total_bytes`
   - `total_files`
   - `largest_experiment`
   - `largest_experiment_bytes`
   - `generated_by`

   Required values:
   - `schema_version` must be the string `"artifact-index-v2"`.
   - `source` must be the string `"/home/user/mlops_workspace/experiments"`.
   - `experiment_count` must equal the number of experiment rows in the inventory.
   - `total_bytes` must equal the sum of `total_bytes` from the inventory.
   - `total_files` must equal the sum of `file_count` from the inventory.
   - `largest_experiment` must match the first experiment in the sorted inventory.
   - `largest_experiment_bytes` must match that experiment’s `total_bytes`.
   - `generated_by` must be the string `"terminal-agent"`.

4. Retire the old state path:
   - The directory `/home/user/mlops_workspace/.du_cache` must not remain as an active directory.
   - Preserve its prior contents in a readable archive or retired location inside `/home/user/mlops_workspace`, but do not leave `/home/user/mlops_workspace/.du_cache/inventory.tsv` available as a normal active file.
   - The final authoritative inventory must be `/home/user/mlops_workspace/.artifact_index/inventory.tsv`.

5. Create the final report at:
   - `/home/user/mlops_workspace/reports/artifact_disk_report.tsv`

   It must be tab-separated UTF-8 text. The first line must be exactly:

   `rank	experiment_id	total_bytes	file_count	checkpoint_count	metric_count	log_count	largest_file_relpath`

   Then include one row per experiment using the same sorted order as the inventory. Requirements:
   - `rank` starts at `1` and increments by one.
   - Do not include `largest_file_bytes` in this report.
   - All numeric fields must be decimal integers with no commas.
   - The report must be derived from the new authoritative inventory in `/home/user/mlops_workspace/.artifact_index/inventory.tsv`, not from the retired old cache.

6. Create the verification log at:
   - `/home/user/mlops_workspace/reports/verification.log`

   The file must contain exactly these six lines, in this order, with values filled in after the equals signs:

   `checked_old_path_retired=<true-or-false>`
   `checked_new_inventory_exists=<true-or-false>`
   `checked_summary_matches_inventory=<true-or-false>`
   `checked_report_matches_inventory=<true-or-false>`
   `new_inventory_path=/home/user/mlops_workspace/.artifact_index/inventory.tsv`
   `old_cache_path=/home/user/mlops_workspace/.du_cache`

   All four boolean values must be lowercase `true` only if you have actually checked the final filesystem state after the migration/report generation. Be careful not to trust old console output or files from `/home/user/mlops_workspace/.du_cache`.

You may use parallel shell tools or scripts if helpful because the experiment tree can contain many files. Before finishing, verify the final state by reading from `/home/user/mlops_workspace/.artifact_index/inventory.tsv` and by confirming that `/home/user/mlops_workspace/.du_cache` is no longer an active directory.
