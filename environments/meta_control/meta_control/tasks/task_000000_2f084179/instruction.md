You are helping a monitoring specialist prepare alert-window text that will be consumed by an older pager integration. Work in the existing writable project directory `/home/user/monitoring`.

The source data is already present at `/home/user/monitoring/data/alert_windows.csv`. It contains UTC alert start times. Your job is to configure and run the rendering job so that the final artifact uses the operations team’s required time zone and locale.

Required final artifact:

* Create or overwrite `/home/user/monitoring/out/alert_windows.log`.
* The file must be plain UTF-8 text.
* It must contain exactly 4 non-empty lines.
* Line 1 must be exactly:

```text
ALERT_WINDOWS tz=America/New_York locale=C.UTF-8
```

* Lines 2 through 4 must be sorted by the original UTC timestamp ascending.
* Each alert line must use this exact pipe-delimited format:

```text
<service>|<weekday>|<local_timestamp>|severity=<severity>
```

Where:

* `<service>` and `<severity>` come from `/home/user/monitoring/data/alert_windows.csv`.
* `<weekday>` is the English abbreviated weekday name produced for the converted local time, such as `Mon`, `Tue`, etc.
* `<local_timestamp>` must be the UTC timestamp converted to the `America/New_York` time zone and formatted exactly as:

```text
YYYY-MM-DD HH:MM EST
```

For this dataset, all rendered local timestamps should use the `EST` abbreviation.

Important verification requirement: do not treat a successful command exit as sufficient. The existing renderer may run cleanly while producing an artifact in the wrong time zone or locale. Before finishing, inspect `/home/user/monitoring/out/alert_windows.log` and make sure the header and every rendered timestamp match the required time zone, locale, sort order, and format above.

You may update files under `/home/user/monitoring` as needed, including the renderer or its environment/configuration files, but do not use root-level system time zone or locale changes. Stop when the final log file exists and its contents satisfy the specification exactly.
