You’re helping with a small log-analysis optimization check in `/home/user/solver_case`. The directory already contains an input file at `/home/user/solver_case/events.csv` and a Python utility at `/home/user/solver_case/select_patterns.py`.

Please investigate the event patterns by using the provided optimization utility to choose the best compact set of patterns, then write a concise analyst report.

Your final deliverable must be the file:

`/home/user/solver_case/pattern_report.txt`

The report must contain exactly 5 non-empty lines in this exact format:

1. `solver_status=<status>`
2. `selected_count=<integer>`
3. `selected_patterns=<comma-separated pattern ids in ascending order>`
4. `covered_events=<integer>`
5. `total_score=<integer>`

Requirements:

- Run the provided solver utility in `/home/user/solver_case/select_patterns.py`; do not manually guess the selected pattern set.
- The utility may produce little or no terminal output, so do not treat silence as success.
- Inspect the files it creates in `/home/user/solver_case/output/`.
- Verify the final report by running the provided checker at `/home/user/solver_case/check_report.py`.
- The checker’s success message must be written verbatim to `/home/user/solver_case/verification.log`.
- Stop only after `/home/user/solver_case/pattern_report.txt` exists and the checker has confirmed it.

The report should use the solver result, not the raw event list. If the solver output includes multiple data files, use the one that records the final optimization solution.
