You are helping troubleshoot a connectivity inventory issue for a network engineering lab. The lab previously tracked device reachability under an old per-site directory, but the team has standardized on a new canonical state location. Your job is to migrate the current device state, retire the stale path, and produce verification artifacts that prove you checked the new source of truth rather than the old one.

All work must be done under `/home/user/netops`. You do not need root access.

Current situation:
- The legacy directory is `/home/user/netops/sites/edge-a/state`.
- The new canonical directory must be `/home/user/netops/inventory/current/edge-a`.
- Device input files may already exist under the legacy directory.
- Some files or directories may already exist under `/home/user/netops/inventory`, but treat `/home/user/netops/inventory/current/edge-a` as the only final source of truth.
- Do not leave the active device state in the legacy directory when you are done.

Please complete the following end-to-end workflow:

1. Create the new canonical directory `/home/user/netops/inventory/current/edge-a` if it does not already exist.

2. Migrate the device inventory data from the legacy state directory to the new canonical directory while preserving the device semantics:
   - The final canonical file `/home/user/netops/inventory/current/edge-a/devices.csv` must exist.
   - It must be a comma-separated file with exactly this header line:
     `device,mgmt_ip,role,status,last_checked`
   - It must contain one data row per device from the legacy device inventory.
   - Preserve each device name, management IP, role, status, and last-checked value from the migrated source data.
   - Do not include duplicate device rows.
   - Do not add extra columns.
   - The rows should be sorted alphabetically by the `device` field.
   - The file must end with a newline.

3. Create a rotated endpoint configuration at `/home/user/netops/inventory/current/edge-a/endpoint.conf`.
   - It must contain exactly four non-empty lines in this order:
     1. `site=edge-a`
     2. `source=canonical`
     3. `inventory_dir=/home/user/netops/inventory/current/edge-a`
     4. `devices_file=/home/user/netops/inventory/current/edge-a/devices.csv`
   - The file must end with a newline.

4. Retire the old active state path so that future tooling cannot accidentally read stale data:
   - The old directory `/home/user/netops/sites/edge-a/state` must no longer contain the active `devices.csv` file.
   - Leave behind a retirement marker file at `/home/user/netops/sites/edge-a/state.RETIRED`.
   - The marker file must contain exactly these three lines, in this order:
     1. `retired_path=/home/user/netops/sites/edge-a/state`
     2. `canonical_path=/home/user/netops/inventory/current/edge-a`
     3. `reason=migrated-to-canonical-inventory`
   - The marker file must end with a newline.

5. Produce a final verification log at `/home/user/netops/inventory/current/edge-a/migration_verify.log`.
   This log is the main artifact the automated checker will inspect. It must demonstrate that you validated the new source of truth after the migration, not the old path.
   
   The log must contain exactly the following seven lines, in this order:
   1. `CHECKPOINT old_state_scanned`
   2. `CHECKPOINT canonical_created`
   3. `CHECKPOINT data_preserved`
   4. `CHECKPOINT old_path_retired`
   5. `CHECKPOINT endpoint_rotated`
   6. `CANONICAL_DEVICE_COUNT=<number>`
   7. `CANONICAL_DEVICE_LIST=<device1>|<device2>|<device3>...`

   Requirements for the last two lines:
   - `<number>` must be the number of device data rows in `/home/user/netops/inventory/current/edge-a/devices.csv`, excluding the header.
   - `<device1>|<device2>|...` must be the alphabetically sorted list of device names from the canonical `devices.csv`, joined with a literal pipe character `|`.
   - The device list must be derived from the canonical file after migration.
   - The log must end with a newline.

Before finishing, verify the final state by inspecting `/home/user/netops/inventory/current/edge-a/devices.csv`, `/home/user/netops/inventory/current/edge-a/endpoint.conf`, `/home/user/netops/sites/edge-a/state.RETIRED`, and `/home/user/netops/inventory/current/edge-a/migration_verify.log`. Be careful not to validate success from the old legacy directory after you have migrated the data.
