You are helping a deployment engineer finish a small certificate rollout in a staging workspace. The application used to read its TLS certificate metadata from an old PEM bundle, but the rollout now requires the active certificate record to live in a new deployment manifest location. Your job is to migrate the certificate metadata, retire the stale source, and write a verification log that proves you checked the new source of truth.

The working directory is `/home/user/cert-rollout`. You may inspect files there. The relevant paths are:

- Old source path: `/home/user/cert-rollout/legacy/live-api.pem`
- New source path to create/update: `/home/user/cert-rollout/deploy/current-cert.env`
- Verification log to create: `/home/user/cert-rollout/deploy/rollout-verification.log`

The old PEM file contains comment lines with the certificate metadata needed by the deployment system. Preserve the active certificate metadata exactly, but move the deployment source of truth to the new env-style file. The new file `/home/user/cert-rollout/deploy/current-cert.env` must contain exactly these four keys, one per line, in this order:

1. `CERT_COMMON_NAME=...`
2. `CERT_SERIAL=...`
3. `CERT_NOT_AFTER=...`
4. `CERT_SOURCE=deploy/current-cert.env`

Use the values for common name, serial, and expiration from the active certificate metadata in the legacy PEM comments. Do not include quotes, extra spaces around `=`, blank lines, PEM blocks, or legacy comment markers in the new env file.

After creating the new source of truth, retire the old certificate path so that the deployment cannot accidentally keep validating stale state. The old path `/home/user/cert-rollout/legacy/live-api.pem` must no longer exist as a regular file when you are done.

Finally, create `/home/user/cert-rollout/deploy/rollout-verification.log`. The automated check will verify this file’s exact structure. It must contain exactly six lines in this order:

1. `rollout=certificate-metadata-migration`
2. `new_source=/home/user/cert-rollout/deploy/current-cert.env`
3. `legacy_source_retired=yes`
4. `verified_common_name=<the common name value from the new env file>`
5. `verified_serial=<the serial value from the new env file>`
6. `verified_not_after=<the expiration value from the new env file>`

Important: the verification log must reflect the values as read from `/home/user/cert-rollout/deploy/current-cert.env` after the migration, not from the retired legacy file. Before you finish, verify that the new env file is the active source and that the old PEM file has been retired.
