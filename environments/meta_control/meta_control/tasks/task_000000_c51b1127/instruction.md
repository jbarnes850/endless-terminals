You are helping with a small log-analysis investigation in a Linux container.

A SQLite database has already been prepared at:

`/home/user/log-investigation/access_logs.sqlite`

It contains web access events for a single application. Your job is to identify which request path was responsible for a burst of HTTP 500 errors during the incident window.

Please inspect the database using SQLite and create a verification report at:

`/home/user/log-investigation/incident_summary.txt`

The report must contain exactly 4 lines, in this exact format:

`incident_window=<START_ISO8601>,<END_ISO8601>`  
`top_error_path=<PATH>`  
`error_count=<COUNT>`  
`checked_candidates=<N>`

Requirements:

1. Treat the incident window as all log rows whose timestamp is between `2024-04-18T14:00:00` and `2024-04-18T14:09:59`, inclusive.
2. Consider only rows where `status = 500`.
3. Find the request path with the highest number of HTTP 500 responses during that window.
4. `checked_candidates` must be the number of distinct request paths that had at least one HTTP 500 response during the incident window.
5. Use the exact ISO8601 timestamps shown above for the first line.
6. Do not include extra whitespace, headings, blank lines, explanations, or additional output in `/home/user/log-investigation/incident_summary.txt`.
7. Before finishing, verify the file exists and that it has exactly 4 lines.

The goal is to do a focused investigation: check the relevant evidence in the database, eliminate non-leading paths, write the report, verify it, and stop.
