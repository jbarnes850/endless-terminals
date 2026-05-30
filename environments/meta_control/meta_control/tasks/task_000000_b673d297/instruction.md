You are preparing a QA test environment under `/home/user` for applications that must run with a fixed time zone and locale. Please configure the environment by creating a small shell snippet and a verification artifact.

Create the file `/home/user/qa-env/time-locale.sh`. The directory `/home/user/qa-env` may or may not already exist, so ensure it exists. The file must be a POSIX-compatible shell snippet containing exactly these three export assignments, one per line, in this order:

1. `export TZ=America/New_York`
2. `export LANG=en_US.UTF-8`
3. `export LC_ALL=en_US.UTF-8`

After creating the snippet, verify it by running a shell that sources `/home/user/qa-env/time-locale.sh` and prints the effective values of `TZ`, `LANG`, and `LC_ALL`. Do not assume the file is correct just because the creation command produced little or no output.

Write the verification result to `/home/user/qa-env/verification.log`. The log file must contain exactly four lines in this format:

```text
QA time/locale verification
TZ=<effective TZ value>
LANG=<effective LANG value>
LC_ALL=<effective LC_ALL value>
```

For example, the second through fourth lines must use the actual environment values observed after sourcing the snippet, not manually invented text. The automated check will verify the exact file paths, exact assignment lines in `/home/user/qa-env/time-locale.sh`, and the exact four-line structure of `/home/user/qa-env/verification.log`.

When you are finished, make sure both files are readable by the current user and leave them in `/home/user/qa-env`.
