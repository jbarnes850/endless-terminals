You are helping with a small cloud-architecture migration for a service named `billing-api`. The service used to read its runtime configuration from `/home/user/cloud-migration/legacy/.env`, but the new deployment standard requires the active dotenv file to live at `/home/user/cloud-migration/current/.env`.

Please migrate the configuration so that `/home/user/cloud-migration/current/.env` becomes the only active source of truth.

Final required state:

1. The directory `/home/user/cloud-migration/current` must exist.
2. The file `/home/user/cloud-migration/current/.env` must exist and contain exactly these three variable names, one per line, in this order:
   - `BILLING_API_ENDPOINT`
   - `BILLING_REGION`
   - `FEATURE_FLAG_LEDGER_V2`
3. The values must preserve the existing production semantics from the legacy dotenv file, except:
   - `BILLING_API_ENDPOINT` must point to the new `v2` endpoint instead of the old `v1` endpoint.
   - `FEATURE_FLAG_LEDGER_V2` must be enabled.
4. The old dotenv file at `/home/user/cloud-migration/legacy/.env` must be retired so it cannot be mistaken for the active configuration anymore. It should not remain as a usable dotenv file.
5. Create a verification log at `/home/user/cloud-migration/migration-check.log`.

The verification log must contain exactly four lines in this format:

```text
active_env=/home/user/cloud-migration/current/.env
legacy_env_retired=yes
endpoint_version=v2
ledger_v2_enabled=yes
```

Before finishing, verify the final state by inspecting the new dotenv file, not the retired legacy path. The automated checker will validate the file locations, dotenv contents, retirement of the old path, and the exact contents of the verification log.
