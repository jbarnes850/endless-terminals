You are acting as a database reliability engineer validating that the local backup-status API is healthy before a scheduled maintenance window.

A small HTTP service will already be running inside the container and listening on localhost. Your job is to query it with curl, extract the required backup information, and write a verification report.

Use the API endpoint:

`http://127.0.0.1:48731/api/v1/backups/latest`

The endpoint returns JSON describing the latest database backup. You may inspect the response however you like, but the final deliverable must be the file:

`/home/user/backup_api_verification.log`

Create or overwrite that file so that it contains exactly 5 lines, in this exact order and format:

1. `endpoint=http://127.0.0.1:48731/api/v1/backups/latest`
2. `http_status=<HTTP_STATUS_CODE>`
3. `backup_id=<BACKUP_ID_FROM_JSON>`
4. `database=<DATABASE_NAME_FROM_JSON>`
5. `verified=<yes_or_no>`

Rules for the values:

- `http_status` must be the actual HTTP status code returned by curl for the endpoint.
- `backup_id` must come from the JSON field named `backup_id`.
- `database` must come from the JSON field named `database`.
- `verified` must be `yes` only if all of the following are true:
  - the HTTP status code is `200`
  - the JSON field `state` is exactly `completed`
  - the JSON field `checksum_verified` is exactly boolean `true`
  - the JSON field `storage_redundancy` is exactly `multi_az`
- Otherwise, `verified` must be `no`.

The automated checker will read only `/home/user/backup_api_verification.log`, so make sure the file exists and has no extra blank lines, comments, timestamps, JSON blobs, or additional text. Before you finish, verify that the file still has exactly the five required lines and that the later `verified` line did not break any of the earlier values.
