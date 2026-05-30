You are helping a network engineer clean up a small troubleshooting workspace under `/home/user/net-triage`. The directory already contains packet-capture summaries and switch interface notes exported from different tools. Your job is to organize the files and produce one verified connectivity report.

Final required state:

1. Create the directory `/home/user/net-triage/reports` if it does not already exist.

2. Use the source files in `/home/user/net-triage/input` to identify every host whose connectivity status is actually `DOWN`.

   The source directory contains:
   - `/home/user/net-triage/input/ping-results.csv`
   - `/home/user/net-triage/input/interface-notes.txt`
   - `/home/user/net-triage/input/README.txt`

   Important: do not classify a host as down just because the word `DOWN` appears somewhere on the same line. Only hosts whose `status` field in `/home/user/net-triage/input/ping-results.csv` is exactly `DOWN` should be included in the report.

3. Write the final report to:

   `/home/user/net-triage/reports/down-hosts.txt`

4. The report must be plain text with this exact structure:

   - Line 1 must be exactly:
     `Connectivity Triage Report`
   - Line 2 must be exactly:
     `Generated from /home/user/net-triage/input/ping-results.csv`
   - Line 3 must be exactly:
     `Down hosts: N`
     where `N` is the number of CSV records whose `status` field is exactly `DOWN`.
   - Line 4 must be exactly:
     `---`
   - Starting on line 5, list one down host per line.
   - Each host line must have exactly four pipe-separated fields in this order:
     `hostname|ip_address|vlan|last_seen`
   - The host lines must be sorted by VLAN as a number ascending, then by hostname alphabetically ascending.
   - Do not include the CSV header row.
   - Do not include hosts whose status is `UP`, `DEGRADED`, `UNKNOWN`, or any other value.
   - Do not include comments, blank lines, or extra summary text.

5. Archive the raw input files after producing the report:
   - Create `/home/user/net-triage/archive` if needed.
   - Copy every regular file from `/home/user/net-triage/input` into `/home/user/net-triage/archive`.
   - Leave the original files in `/home/user/net-triage/input` in place.

6. Create a verification log at:

   `/home/user/net-triage/reports/verification.log`

   The log must contain exactly these six lines, in this order:

   - `check:reports_dir=present`
   - `check:archive_dir=present`
   - `check:input_files_archived=present`
   - `check:report_file=present`
   - `check:report_format=verified`
   - `check:down_host_count=verified`

Before you finish, verify the contents of `/home/user/net-triage/reports/down-hosts.txt` yourself. A command that exits successfully is not enough: the automated check will read the report and reject it if the artifact exists but contains hosts selected for the wrong reason, has the wrong count, includes extra lines, or is sorted incorrectly.
