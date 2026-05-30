You are helping a security engineer rotate credentials in a small configuration repository. The repository is already present at `/home/user/credential-rotation`.

Your job is to apply the unified diff patch located at:

`/home/user/credential-rotation/patches/rotate-api-credentials.patch`

to the live configuration file:

`/home/user/credential-rotation/config/service.env`

The patch represents the approved credential rotation. Use the patch as the source of truth rather than manually inventing values.

After applying the patch, create a verification log at:

`/home/user/credential-rotation/rotation_verification.log`

The automated checker will validate both the patched configuration and the verification log, so please be exact.

The final `/home/user/credential-rotation/rotation_verification.log` must contain exactly four lines, in this exact order and format:

1. `PATCH_APPLIED=yes`
2. `SERVICE_ENV_EXISTS=yes`
3. `BACKUP_CREATED=yes`
4. `ROTATION_STATUS=complete`

Also ensure that a backup copy of the original configuration exists at:

`/home/user/credential-rotation/config/service.env.pre-rotation`

The backup must contain the pre-rotation contents of `service.env`, not the rotated contents.

Do not change unrelated files. Before finishing, verify that the patch has been applied cleanly, the backup exists, and the verification log has exactly the required four lines.
