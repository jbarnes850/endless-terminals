You are helping a web developer diagnose a small production incident from an access log.

The input log file is at:

`/home/user/projects/shopsite/logs/access.log`

Create exactly one deliverable file at:

`/home/user/projects/shopsite/reports/error_summary.txt`

The report must summarize only failed checkout API requests. A failed checkout API request is any log line where:

1. the request path is exactly `/api/checkout`, ignoring any query string after `?`, and
2. the HTTP status code is in the 5xx range, meaning any integer from `500` through `599`.

Do not count failures for other API routes, static assets, health checks, or `/api/checkout-preview`. Do count `/api/checkout?...` as `/api/checkout`.

The report file must contain exactly four lines, in this exact order and format:

`TOTAL_FAILED_CHECKOUTS=<integer>`

`FIRST_FAILED_CHECKOUT=<timestamp>`

`LAST_FAILED_CHECKOUT=<timestamp>`

`STATUS_COUNTS=<status>:<count>,<status>:<count>,...`

Formatting requirements:

- No extra blank lines before, between, or after the four lines.
- Timestamps must be copied exactly from the first field of the matching log lines.
- If there are multiple status codes, `STATUS_COUNTS` must list them in ascending numeric status-code order.
- Counts must be decimal integers.
- The output file must be written to `/home/user/projects/shopsite/reports/error_summary.txt`.
- The directory `/home/user/projects/shopsite/reports` is writable and may already contain old or incorrect files.

There is a helper script in the project at `/home/user/projects/shopsite/scripts/summarize_checkout_errors.sh`, but do not assume that a clean exit means the report is correct. Before finishing, verify that the contents of `/home/user/projects/shopsite/reports/error_summary.txt` satisfy the rules above by checking the artifact itself against the log data.
