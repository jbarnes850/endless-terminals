You are helping a security engineer finish a small credential-rotation cleanup in a user-owned workspace. The work is under `/home/user/rotation`, and you do not need root privileges.

The sensitive rotated credential is stored in the directory `/home/user/rotation/current.secret.d`. A previous hardening attempt focused only on the directory itself, but the security scanner is still expected to flag the exposed credential file inside it. Do not keep retrying a directory-only permission change if the file exposure remains unchanged; inspect or reason about the actual object that needs its permissions changed and use the appropriate permission operation.

Bring the credential area to this final state:

- `/home/user/rotation/current.secret.d` must be accessible only by its owner:
  - owner may read, write, and enter the directory
  - group and others must have no permissions
- `/home/user/rotation/current.secret.d/token.txt` must be readable and writable only by its owner:
  - owner may read and write
  - group and others must have no permissions
  - it must not be executable
- Do not delete, rename, truncate, or modify the contents of `/home/user/rotation/current.secret.d/token.txt`.

After applying the permission fix, create an audit log at:

`/home/user/rotation/audit/credential-rotation.log`

The log file must contain exactly these three lines, with no extra blank lines before or after:

`ROTATION_AUDIT v1`  
`/home/user/rotation/current.secret.d mode=700`  
`/home/user/rotation/current.secret.d/token.txt mode=600`

The automated check will verify both the permissions and the exact contents of the audit log. You may use any normal terminal tools available to you, but the final state above is what matters.
