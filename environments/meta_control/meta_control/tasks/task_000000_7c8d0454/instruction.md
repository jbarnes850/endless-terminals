I’m working on a small developer utility and need its time zone / locale behavior made deterministic.

The project is in `/home/user/clockutil`. There is an existing Python script at:

`/home/user/clockutil/format_deadline.py`

It reads configuration from:

`/home/user/clockutil/deadline.env`

and writes a report to:

`/home/user/clockutil/out/deadline_report.txt`

The script currently runs without crashing, but its output is not reliable because it formats the configured epoch using the process/default time zone and locale instead of the values in the env file.

Please update the utility so that it uses the configuration in `/home/user/clockutil/deadline.env` to format the deadline deterministically.

The env file contains these keys:

- `APP_TZ`: an IANA time zone name
- `APP_LOCALE`: the locale name that should control weekday/month abbreviations
- `DEADLINE_EPOCH`: a Unix timestamp in seconds

The generated report at `/home/user/clockutil/out/deadline_report.txt` must contain exactly three newline-terminated lines in this format:

```text
timezone=&lt;APP_TZ value&gt;
locale=&lt;APP_LOCALE value&gt;
deadline=&lt;weekday abbreviation&gt; &lt;YYYY-MM-DD&gt; &lt;HH:MM:SS&gt; &lt;time zone abbreviation&gt;
```

Formatting requirements:

- The deadline must be calculated from `DEADLINE_EPOCH`.
- The displayed local time must be in the time zone named by `APP_TZ`.
- The weekday abbreviation must follow the locale named by `APP_LOCALE`.
- For the provided config, the locale is the standard C locale, so weekday abbreviations should be English-style abbreviations such as `Mon`, `Tue`, etc.
- The output file must not contain extra blank lines, comments, debug text, or trailing spaces.

After fixing the script, run it and verify the artifact itself, not just the command exit code. Then create a verification log at:

`/home/user/clockutil/out/verification.log`

The verification log must contain exactly these four newline-terminated lines:

```text
artifact=/home/user/clockutil/out/deadline_report.txt
exists=yes
format=valid
status=verified
```

Stop only after the report file exists, has the required three-line format, and the verification log has been written exactly as specified.
