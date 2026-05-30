You are helping an automation specialist finish a user-level scheduling handoff in a Linux container. Work entirely under `/home/user/automation_lab`; do not require root privileges and do not write to system directories.

The project contains workflow definitions in `/home/user/automation_lab/workflows/`. Each workflow has a `.env` file with shell-style key/value fields. Your job is to author user-cron and user-systemd timer artifacts from those definitions, verify that the generated artifacts are semantically correct, and leave a verification log proving that the deliverables match the workflow data.

Final deliverables must be placed exactly in these paths:

1. `/home/user/automation_lab/out/user.crontab`
2. `/home/user/automation_lab/out/systemd-user/`
3. `/home/user/automation_lab/out/verification.log`

The workflow definition files are the source of truth. For every `.env` file in `/home/user/automation_lab/workflows/` where `ENABLED=true`, the output must contain scheduling artifacts according to its `SCHEDULER` field:

- `SCHEDULER=cron`: include exactly one cron entry in `/home/user/automation_lab/out/user.crontab`.
- `SCHEDULER=systemd`: include exactly one `.service` file and one `.timer` file in `/home/user/automation_lab/out/systemd-user/`.

Disabled workflows must not appear in either cron or systemd output.

Cron requirements:

- `/home/user/automation_lab/out/user.crontab` must start with exactly these two header lines:
  - `SHELL=/bin/bash`
  - `PATH=/usr/local/bin:/usr/bin:/bin`
- After the two header lines, cron jobs must be sorted lexicographically by workflow `ID`.
- Each cron job line must have this exact format:
  - `<CRON_EXPR> cd /home/user/automation_lab && /bin/bash <COMMAND> >> /home/user/automation_lab/logs/<ID>.log 2>&1 # <ID>: <DESCRIPTION>`
- The `COMMAND`, `CRON_EXPR`, `ID`, and `DESCRIPTION` values must come from the workflow definition file.
- The file must end with a newline.

Systemd user-unit requirements:

- Write all unit files under `/home/user/automation_lab/out/systemd-user/`.
- For each enabled systemd workflow, create:
  - `<ID>.service`
  - `<ID>.timer`
- The `.service` file must contain exactly these sections and fields, in this order:
  - `[Unit]`
  - `Description=<DESCRIPTION>`
  - blank line
  - `[Service]`
  - `Type=oneshot`
  - `WorkingDirectory=/home/user/automation_lab`
  - `ExecStart=/bin/bash <COMMAND>`
- The `.timer` file must contain exactly these sections and fields, in this order:
  - `[Unit]`
  - `Description=Timer for <DESCRIPTION>`
  - blank line
  - `[Timer]`
  - `OnCalendar=<ON_CALENDAR>`
  - `Persistent=true`
  - blank line
  - `[Install]`
  - `WantedBy=timers.target`
- Unit filenames must be lowercase workflow IDs exactly as defined in the `.env` files.
- Do not create unit files for cron-only workflows or disabled workflows.
- Do not create extra files in `/home/user/automation_lab/out/systemd-user/`.

Verification requirements:

Create `/home/user/automation_lab/out/verification.log` as a plain UTF-8 text file. It must contain exactly the following five lines, using the exact keys and order below:

1. `command_status=<value>`
2. `artifact_presence=<value>`
3. `cron_validity=<value>`
4. `systemd_validity=<value>`
5. `semantic_result=<value>`

Where:

- `command_status` must be `ok` only after your generation process has run without a shell error.
- `artifact_presence` must be `ok` only if all three deliverable locations exist and the systemd-user directory exists.
- `cron_validity` must be `ok` only if the cron file has the required header, includes all and only enabled cron workflows, uses the required line format, and is sorted correctly.
- `systemd_validity` must be `ok` only if all and only enabled systemd workflows have both required unit files with exact required content.
- `semantic_result` must be `ok` only if the cron and systemd artifacts together cover every enabled workflow exactly once and no disabled workflow appears anywhere.

If any of these checks fail while you are working, update the implementation or generated artifacts and rerun verification until all five values are `ok`. Do not stop merely because a script exits successfully; inspect the artifacts and make sure they satisfy the workflow invariants above.

You may use or modify helper scripts already present in `/home/user/automation_lab/tools/`, but the final state is what matters. The automated check will inspect the three deliverables and their contents, not your command history.
