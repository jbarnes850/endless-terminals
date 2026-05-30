You are helping administer a small static site account directory under `/home/user/site-admin`.

Please clean up the staged user-account export and leave behind a verification artifact. The shell commands you use may produce little or no output, so do not treat silence as proof that the job is complete. Inspect the files and verify the final state before stopping.

Starting data will be under:

- `/home/user/site-admin/incoming/accounts/`
- `/home/user/site-admin/public/users/`

Perform these file-management changes:

1. Ensure the directory `/home/user/site-admin/public/users/archived/` exists.
2. Move the stale account file `/home/user/site-admin/incoming/accounts/samuel.lee.json` into `/home/user/site-admin/public/users/archived/samuel.lee.json`.
3. Move the active account file `/home/user/site-admin/incoming/accounts/maya.chen.json` into `/home/user/site-admin/public/users/maya.chen.json`.
4. Leave `/home/user/site-admin/incoming/accounts/` present, but it should contain no `.json` files after the moves.

After making the changes, create a verification log at exactly:

`/home/user/site-admin/account_migration_check.txt`

The automated check will read this file, so format it exactly as follows:

- It must contain exactly 5 lines.
- Line 1: `account migration check`
- Line 2: `archived_exists: yes` if `/home/user/site-admin/public/users/archived/samuel.lee.json` exists, otherwise `archived_exists: no`
- Line 3: `active_exists: yes` if `/home/user/site-admin/public/users/maya.chen.json` exists, otherwise `active_exists: no`
- Line 4: `incoming_json_count: N` where `N` is the number of `.json` files directly inside `/home/user/site-admin/incoming/accounts/`
- Line 5: `verified: yes`

Before you finish, inspect the resulting directories or otherwise run a targeted check so that the values in `/home/user/site-admin/account_migration_check.txt` reflect the actual final state.
