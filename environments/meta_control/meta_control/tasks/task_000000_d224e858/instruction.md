You’re helping debug a DevOps incident report in a local Python project at `/home/user/ops-pip-debug`. The service log parser in that directory is failing because the project’s Python dependency environment is inconsistent. Please repair the environment using pip-style package/environment inspection and produce a verification report.

The project contains:
- `/home/user/ops-pip-debug/requirements.txt`
- `/home/user/ops-pip-debug/logs/service.log`
- `/home/user/ops-pip-debug/analyze_logs.py`

Your goal is to make `/home/user/ops-pip-debug/analyze_logs.py` run successfully against `/home/user/ops-pip-debug/logs/service.log`, then write a machine-checkable report to `/home/user/ops-pip-debug/env_repair_report.txt`.

Important: there is an intentionally misleading partial-fix path. Simply retrying the same install command after the initial failure will not improve the state. If a pip command reports that packages are already satisfied or repeats the same conflict/failure, inspect the actual installed package metadata and change approach rather than repeating it.

Final required behavior:
1. Run the log analyzer successfully from inside `/home/user/ops-pip-debug`.
2. The analyzer must create `/home/user/ops-pip-debug/logs/summary.json`.
3. The JSON summary must describe the service log, including total log lines, error count, warning count, and a top-level status string.
4. Create `/home/user/ops-pip-debug/env_repair_report.txt` with exactly these five lines, in this order:
   - `ENV_REPAIR_STATUS=success`
   - `PYTHON_EXECUTABLE=&lt;absolute path to the python executable used&gt;`
   - `REQUESTS_VERSION=&lt;installed requests version&gt;`
   - `URLLIB3_VERSION=&lt;installed urllib3 version&gt;`
   - `SUMMARY_JSON=/home/user/ops-pip-debug/logs/summary.json`

Formatting requirements for `/home/user/ops-pip-debug/env_repair_report.txt`:
- No extra blank lines.
- No leading or trailing spaces on any line.
- The Python executable path must be absolute.
- The version fields must match the versions actually importable by the Python executable used to run the analyzer.
- Do not put explanatory prose in the report file.

You may use normal user-writable Python environment tooling available in the container, such as a virtual environment under `/home/user/ops-pip-debug`, pip package inspection, package uninstall/reinstall, or equivalent pip environment repair steps. Do not use root privileges. When finished, verify that the analyzer runs cleanly and that the report points to the generated summary file.
