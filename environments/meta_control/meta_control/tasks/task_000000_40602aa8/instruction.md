You’re helping with a small log-analysis cleanup in `/home/user/log-audit`. The directory contains several daily web log files and a `current.log` symbolic link that may not point to the correct latest log. Your job is to inspect the existing files, update the symbolic link, and write a short verification report.

Final required state:

1. The symbolic link `/home/user/log-audit/current.log` must point to the latest daily log file in `/home/user/log-audit/daily/`.
   - Daily logs are named using the format `web-YYYY-MM-DD.log`.
   - “Latest” means the greatest date in the filename, not the newest filesystem modification time.
   - The link must be a symbolic link, not a copied file or hard link.
   - The link target may be relative or absolute, but it must resolve to the correct latest daily log file.

2. Create the file `/home/user/log-audit/current-pattern-report.txt`.
   - The report must be plain UTF-8 text.
   - It must contain exactly 4 lines.
   - The automated checker will verify the exact line labels, separators, and values.
   - Use this exact format:

```text
current_link=/home/user/log-audit/current.log
resolved_target=<absolute path that current.log resolves to>
error_count=<number of lines in the resolved log containing the exact substring ERROR>
warning_count=<number of lines in the resolved log containing the exact substring WARN>
```

Important details:
- Count only lines from the log file that `current.log` resolves to after you fix the link.
- Match the substrings exactly as shown: `ERROR` and `WARN`.
- Do not count lowercase variants such as `error` or `warn`.
- Do not include extra spaces around `=`.
- Do not include a trailing summary, comments, blank lines, or command output in the report.
- Verify the report contents before finishing; a command can exit successfully even if the link or report is semantically wrong.

You should stop only when `/home/user/log-audit/current.log` resolves to the correct latest dated daily log and `/home/user/log-audit/current-pattern-report.txt` exactly follows the format above with counts from that resolved file.
