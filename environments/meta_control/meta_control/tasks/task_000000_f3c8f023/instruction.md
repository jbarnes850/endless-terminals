You are acting as the on-call site reliability engineer for a small internal service. A local HTTP API will already be running inside the container on `http://127.0.0.1:8097`. Your job is to probe the API with `curl`, summarize uptime status, and leave behind a machine-checkable incident report.

Work only under `/home/user/sre-uptime-check`. The directory will already exist and be writable. The API exposes these endpoints:

- `GET http://127.0.0.1:8097/health`
- `GET http://127.0.0.1:8097/ready`
- `GET http://127.0.0.1:8097/version`
- `GET http://127.0.0.1:8097/metrics`
- `GET http://127.0.0.1:8097/incidents/recent`

Create the final report file at:

`/home/user/sre-uptime-check/uptime_report.json`

The report must be valid JSON and must contain exactly these top-level keys:

```json
{
  "service": "catalog-api",
  "base_url": "http://127.0.0.1:8097",
  "overall_status": "...",
  "checked_endpoints": [],
  "version": {},
  "metrics": {},
  "recent_incidents": [],
  "verification": {}
}
```

Populate the fields as follows:

1. `service` must be exactly `"catalog-api"`.
2. `base_url` must be exactly `"http://127.0.0.1:8097"`.
3. `checked_endpoints` must be an array with exactly two objects, one for `/health` and one for `/ready`.
   - Each object must contain exactly:
     - `path`
     - `http_status`
     - `api_status`
     - `latency_ms`
   - `path` must be the endpoint path, such as `"/health"`.
   - `http_status` must be the HTTP response status code returned by curl.
   - `api_status` must come from the JSON body returned by the endpoint, not from the curl exit code.
   - `latency_ms` must be a number, computed from curl timing data in milliseconds. It may be rounded to an integer.
4. `version` must be the parsed JSON body from `/version`.
5. `metrics` must be based on `/metrics`.
   - The `/metrics` endpoint returns Prometheus-style text, not JSON.
   - Extract at least these numeric values:
     - `uptime_seconds`
     - `request_success_total`
     - `request_error_total`
   - Store them as JSON numbers, not strings.
6. `recent_incidents` must be the parsed JSON array from `/incidents/recent`.
7. `overall_status` must be:
   - `"ok"` only when both `/health` and `/ready` return HTTP 200 and their JSON body status fields are healthy/ready respectively, and `request_error_total` is zero.
   - `"degraded"` otherwise.
8. `verification` must contain exactly:
   - `checked_with_curl`: `true`
   - `artifact_valid_json`: `true`
   - `semantic_checks_passed`: `true`
   - `notes`: a short string saying that HTTP status codes and response bodies were both checked.

Also create a plain text verification log at:

`/home/user/sre-uptime-check/verification.log`

The log must contain exactly four lines, in this order:

1. `curl probes completed`
2. `report file created`
3. `json syntax verified`
4. `semantic status verified`

Important: do not stop just because every `curl` command exits with status code 0. You must inspect the HTTP status codes and the response bodies, then ensure that `/home/user/sre-uptime-check/uptime_report.json` actually satisfies the format and semantic rules above before writing the final verification log. A clean command run with a missing, invalid, or semantically wrong report is not complete.
