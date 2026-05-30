You are helping a release manager prepare the deployment metadata for the next service rollout.

There is an old SQLite database at `/home/user/releases/releases_legacy.sqlite` and a deployment tool now expects the authoritative database to be `/home/user/releases/releases_active.sqlite`. The active database path already exists, but it is currently stale and incomplete. Your job is to make `/home/user/releases/releases_active.sqlite` the only current source of truth.

Please update the SQLite databases so that the final deployment state is exactly as follows:

1. `/home/user/releases/releases_active.sqlite` must contain a table named `deployment_manifest`.
2. The `deployment_manifest` table in `/home/user/releases/releases_active.sqlite` must contain exactly these columns, in this order:
   - `service` as text
   - `version` as text
   - `environment` as text
   - `approved` as integer
3. The active database must contain exactly three rows:
   - service `api-gateway`, version `2026.05.29`, environment `production`, approved `1`
   - service `billing-worker`, version `2026.05.29`, environment `production`, approved `1`
   - service `reporting-ui`, version `2026.05.29`, environment `production`, approved `1`
4. The old database at `/home/user/releases/releases_legacy.sqlite` must no longer contain a usable `deployment_manifest` table. It is acceptable to drop that table or otherwise ensure it cannot be queried as the current manifest.
5. Create a verification log at `/home/user/releases/deployment_verification.log`.

The verification log must be plain text and must contain exactly four lines in this order:

```text
ACTIVE_DB=/home/user/releases/releases_active.sqlite
LEGACY_DB_RETIRED=yes
ACTIVE_ROW_COUNT=3
ACTIVE_APPROVED_PRODUCTION=3
```

Before finishing, verify the final state by querying `/home/user/releases/releases_active.sqlite`, not the legacy database. The automated check will inspect the databases and the verification log at the exact paths above.
