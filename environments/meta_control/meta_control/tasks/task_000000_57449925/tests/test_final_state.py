# test_final_state.py
from pathlib import Path
import csv

REPORT_PATH = Path("/home/user/config_manager/out/change_report.tsv")
LOG_PATH = Path("/home/user/config_manager/out/verification.log")

EXPECTED_REPORT = (
    "component\tkey\tchange_type\tbaseline_value\tcurrent_value\n"
    "api\tfeature_payments\tmodified\tfalse\ttrue\n"
    "api\tlegacy_mode\tremoved\tenabled\t\n"
    "api\tport\tmodified\t8080\t8081\n"
    "api\trate_limit_per_minute\tadded\t\t1200\n"
    "api\ttimeout\tmodified\t30\t45\n"
    "db\tbackup_window\tmodified\t02:00-03:00\t01:00-02:00\n"
    "db\thost\tmodified\tdb01.internal.local\tdb02.internal.local\n"
    "db\tpool_max\tmodified\t30\t50\n"
    "db\tread_replica\tremoved\tdb-read-01.internal.local\t\n"
    "db\tsslmode\tmodified\trequire\tverify-full\n"
    "db\tstatement_timeout\tadded\t\t60s\n"
    "worker\tconcurrency\tmodified\t4\t6\n"
    "worker\tdead_letter_queue\tmodified\tworker-dlq\tworker-dlq-v2\n"
    "worker\timage_tag\tmodified\tworker:1.7.2\tworker:1.8.0\n"
    "worker\tmetrics_enabled\tmodified\tfalse\ttrue\n"
    "worker\tprefetch_count\tadded\t\t25\n"
)

EXPECTED_LOG = (
    "report_path=/home/user/config_manager/out/change_report.tsv\n"
    "row_count=16\n"
    "verification=passed\n"
)

EXPECTED_HEADER = [
    "component",
    "key",
    "change_type",
    "baseline_value",
    "current_value",
]

EXPECTED_ROWS = [
    ["api", "feature_payments", "modified", "false", "true"],
    ["api", "legacy_mode", "removed", "enabled", ""],
    ["api", "port", "modified", "8080", "8081"],
    ["api", "rate_limit_per_minute", "added", "", "1200"],
    ["api", "timeout", "modified", "30", "45"],
    ["db", "backup_window", "modified", "02:00-03:00", "01:00-02:00"],
    ["db", "host", "modified", "db01.internal.local", "db02.internal.local"],
    ["db", "pool_max", "modified", "30", "50"],
    ["db", "read_replica", "removed", "db-read-01.internal.local", ""],
    ["db", "sslmode", "modified", "require", "verify-full"],
    ["db", "statement_timeout", "added", "", "60s"],
    ["worker", "concurrency", "modified", "4", "6"],
    ["worker", "dead_letter_queue", "modified", "worker-dlq", "worker-dlq-v2"],
    ["worker", "image_tag", "modified", "worker:1.7.2", "worker:1.8.0"],
    ["worker", "metrics_enabled", "modified", "false", "true"],
    ["worker", "prefetch_count", "added", "", "25"],
]


def read_bytes(path: Path) -> bytes:
    assert path.exists(), f"Required output file is missing: {path}"
    assert path.is_file(), f"Required output path is not a regular file: {path}"
    return path.read_bytes()


def test_change_report_exists_and_is_exact_authoritative_tsv():
    actual_bytes = read_bytes(REPORT_PATH)
    expected_bytes = EXPECTED_REPORT.encode("utf-8")

    assert actual_bytes == expected_bytes, (
        f"{REPORT_PATH} does not match the required final TSV byte-for-byte. "
        "The stale partial report must be replaced with the full normalized, sorted "
        "16-row change report using the exact header, tab separators, UTF-8 text, "
        "Unix newlines, and no extra or missing rows."
    )


def test_change_report_uses_unix_newlines_and_no_carriage_returns():
    actual_bytes = read_bytes(REPORT_PATH)

    assert b"\r" not in actual_bytes, (
        f"{REPORT_PATH} contains carriage return bytes. "
        "The report must use Unix '\\n' newlines only."
    )
    assert actual_bytes.endswith(b"\n"), (
        f"{REPORT_PATH} must end with a final Unix newline."
    )
    assert actual_bytes.count(b"\n") == 17, (
        f"{REPORT_PATH} must contain exactly 17 lines total: "
        "one header plus sixteen data rows."
    )


def test_change_report_is_valid_five_column_tab_separated_data():
    actual_text = read_bytes(REPORT_PATH).decode("utf-8")
    rows = list(csv.reader(actual_text.splitlines(), delimiter="\t"))

    assert rows, f"{REPORT_PATH} is empty; expected a header and 16 data rows."
    assert rows[0] == EXPECTED_HEADER, (
        f"{REPORT_PATH} has the wrong header. "
        f"Expected exactly {EXPECTED_HEADER!r}, found {rows[0]!r}."
    )

    data_rows = rows[1:]
    assert len(data_rows) == 16, (
        f"{REPORT_PATH} must contain exactly 16 data rows, excluding the header; "
        f"found {len(data_rows)}."
    )

    bad_width_rows = [
        (line_number, row)
        for line_number, row in enumerate(rows, start=1)
        if len(row) != 5
    ]
    assert not bad_width_rows, (
        f"{REPORT_PATH} must have exactly 5 tab-separated columns on every line. "
        f"Rows with the wrong column count: {bad_width_rows!r}"
    )

    assert data_rows == EXPECTED_ROWS, (
        f"{REPORT_PATH} data rows are not the expected normalized changes."
    )


def test_change_report_rows_are_sorted_and_unique():
    actual_text = read_bytes(REPORT_PATH).decode("utf-8")
    rows = list(csv.reader(actual_text.splitlines(), delimiter="\t"))
    data_rows = rows[1:]

    sorted_rows = sorted(data_rows, key=lambda row: (row[0], row[1], row[2]))
    assert data_rows == sorted_rows, (
        f"{REPORT_PATH} rows must be sorted lexicographically by "
        "component, then key, then change_type."
    )

    row_tuples = [tuple(row) for row in data_rows]
    duplicates = sorted({row for row in row_tuples if row_tuples.count(row) > 1})
    assert not duplicates, (
        f"{REPORT_PATH} contains duplicate change rows: {duplicates!r}"
    )


def test_change_report_is_not_the_stale_partial_artifact():
    actual_text = read_bytes(REPORT_PATH).decode("utf-8")

    assert "api\tport\tmodified\t8080\t8081\n" in actual_text, (
        "The api port modification should still be present in the final report."
    )
    assert actual_text != (
        "component\tkey\tchange_type\tbaseline_value\tcurrent_value\n"
        "api\tport\tmodified\t8080\t8081\n"
    ), (
        f"{REPORT_PATH} is still the initial stale partial artifact. "
        "It must be regenerated from the baseline and current snapshots."
    )


def test_verification_log_exists_and_is_exact():
    actual_bytes = read_bytes(LOG_PATH)
    expected_bytes = EXPECTED_LOG.encode("utf-8")

    assert actual_bytes == expected_bytes, (
        f"{LOG_PATH} does not match the required verification log byte-for-byte. "
        "It must contain exactly report_path, row_count=16, and verification=passed "
        "with Unix newlines."
    )


def test_verification_log_consistent_with_report_row_count():
    report_text = read_bytes(REPORT_PATH).decode("utf-8")
    log_text = read_bytes(LOG_PATH).decode("utf-8")

    report_line_count = len(report_text.splitlines())
    data_row_count = report_line_count - 1

    assert data_row_count == 16, (
        f"The final report must have 16 data rows; found {data_row_count}."
    )
    assert f"row_count={data_row_count}\n" in log_text, (
        f"{LOG_PATH} row_count does not match the actual report data-row count "
        f"of {data_row_count}."
    )
    assert "verification=passed\n" in log_text, (
        f"{LOG_PATH} must record verification=passed after checking the final report."
    )