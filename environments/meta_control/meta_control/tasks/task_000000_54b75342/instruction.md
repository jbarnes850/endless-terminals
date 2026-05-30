You are helping harden a Linux container used by systems engineers. A preliminary audit found that the application account configuration under `/home/user/hardening-lab` is incomplete. Please make the smallest safe changes needed and verify the result before you stop.

The working directory is `/home/user/hardening-lab`. The relevant files are:

- `/home/user/hardening-lab/accounts/appsvc.passwd`
- `/home/user/hardening-lab/accounts/appsvc.shadow`
- `/home/user/hardening-lab/audit/`

This lab uses file-based account records rather than the real system user database, so do not attempt to modify `/etc/passwd`, `/etc/shadow`, or real system users.

Required final state:

1. The file `/home/user/hardening-lab/accounts/appsvc.passwd` must remain present and readable by the owner.
2. The file `/home/user/hardening-lab/accounts/appsvc.shadow` must remain present and readable/writable only by the owner.
3. Set permissions so that:
   - `/home/user/hardening-lab/accounts/appsvc.passwd` has mode `0644`
   - `/home/user/hardening-lab/accounts/appsvc.shadow` has mode `0600`
4. Create the verification log file `/home/user/hardening-lab/audit/permission-check.log`.
5. The verification log must contain exactly three lines in this order, with no extra blank lines:
   - line 1: the text `permission hardening verification`
   - line 2: the symbolic permission string, numeric mode, and full path for `/home/user/hardening-lab/accounts/appsvc.passwd`
   - line 3: the symbolic permission string, numeric mode, and full path for `/home/user/hardening-lab/accounts/appsvc.shadow`

For lines 2 and 3, use this exact whitespace-separated format:

`SYMBOLIC_MODE NUMERIC_MODE FULL_PATH`

For example, the symbolic mode field should look like a normal long-listing permission string such as `-rw-r--r--`, and the numeric mode field should be four octal digits such as `0644`.

Before finishing, inspect the verification log and make sure it proves the final permissions. Some commands may succeed silently; do not treat silent success alone as enough verification.
