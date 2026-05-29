You are helping with a small capacity-planning cleanup in a Linux container. The input files already exist and are readable under `/home/user/capacity_planner/`.

Create exactly one output file:

`/home/user/capacity_planner/outputs/overloaded_services.json`

The source data is split across two files:

1. `/home/user/capacity_planner/data/services.csv`
   - CSV header: `service,team,tier,cpu_limit_millicores,memory_limit_mib`
   - Each row describes a service and its configured resource limits.

2. `/home/user/capacity_planner/data/usage.json`
   - JSON object with a top-level key `samples`.
   - `samples` is an array of objects.
   - Each sample object contains:
     - `service`
     - `cpu_used_millicores`
     - `memory_used_mib`

Generate a JSON report containing only services whose CPU usage ratio is at least `0.80` OR whose memory usage ratio is at least `0.85`.

For each overloaded service, include these fields exactly:

- `service`
- `team`
- `tier`
- `cpu_ratio`
- `memory_ratio`
- `reason`

Formatting and content requirements:

- The output file must be valid JSON.
- The top-level value must be an array.
- Each array item must be a JSON object with exactly the six fields listed above.
- `cpu_ratio` must equal `cpu_used_millicores / cpu_limit_millicores`, rounded to exactly 3 decimal places as a JSON number.
- `memory_ratio` must equal `memory_used_mib / memory_limit_mib`, rounded to exactly 3 decimal places as a JSON number.
- `reason` must be:
  - `"cpu"` if only the CPU threshold is met,
  - `"memory"` if only the memory threshold is met,
  - `"cpu,memory"` if both thresholds are met.
- Sort the array by `service` in ascending alphabetical order.
- Do not include services that are missing from either input file.
- Do not include any extra metadata, comments, wrapper objects, or trailing text.
- Create the parent directory `/home/user/capacity_planner/outputs` if it does not already exist.

Before finishing, verify that `/home/user/capacity_planner/outputs/overloaded_services.json` exists and is parseable JSON. The automated check will compare the exact structure, ordering, field names, threshold logic, and numeric rounding.
