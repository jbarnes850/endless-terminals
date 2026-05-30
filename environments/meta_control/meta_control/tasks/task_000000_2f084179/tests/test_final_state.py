# test_final_state.py
import csv
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest


BASE = Path("/home/user/monitoring")
CSV_PATH = Path("/home/user/monitoring/data/alert_windows.csv")
OUT_PATH = Path("/home/user/monitoring/out/alert_windows.log")

EXPECTED_BYTES = (
    b"ALERT_WINDOWS tz=America/New_York locale=C.UTF-8\n"
    b"checkout-api|Mon|2026-01-12 09:30 EST|severity=page\n"
    b"billing-worker|Mon|2026-01-12 11:00 EST|severity=ticket\n"
    b"search-indexer|Mon|2026-01-12 21:15 EST|severity=page\n"
)

EXPECTED_TEXT = EXPECTED_BYTES.decode("utf-8")
EXPECTED_LINES = EXPECTED_TEXT.splitlines()

HEADER = "ALERT_WINDOWS tz=America/New_York locale=C.UTF-8"
ALERT_LINE_RE = re.compile(
    r"^(?P<service>[^|]+)\|"
    r"(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun)\|"
    r"(?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2} EST)\|"
    r"severity=(?P<severity>[^|]+)$"
)


def _read_output_bytes() -> bytes:
    assert OUT_PATH.exists(), (
        f"Required final artifact is missing: {OUT_PATH}. "
        "Run/fix the renderer so it creates this file."
    )
    assert OUT_PATH.is_file(), f"Required final artifact is not a regular file: {OUT_PATH}"
    return OUT_PATH.read_bytes()


def _read_output_text() -> str:
    data = _read_output_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"{OUT_PATH} must be plain UTF-8 text, but decoding failed: {exc}")


def _source_rows_sorted_by_utc():
    assert CSV_PATH.exists(), f"Source CSV is missing: {CSV_PATH}"
    assert CSV_PATH.is_file(), f"Source CSV path is not a regular file: {CSV_PATH}"

    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    required_columns = {"service", "utc_start", "severity"}
    assert rows, f"{CSV_PATH} must contain the source alert rows"
    for index, row in enumerate(rows, start=2):
        missing = required_columns - set(row)
        assert not missing, (
            f"{CSV_PATH} row {index} is missing required column(s): {sorted(missing)}"
        )
        assert row["service"], f"{CSV_PATH} row {index} has an empty service"
        assert row["utc_start"], f"{CSV_PATH} row {index} has an empty utc_start"
        assert row["severity"], f"{CSV_PATH} row {index} has an empty severity"

    def parse_utc(row):
        return datetime.strptime(row["utc_start"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=ZoneInfo("UTC")
        )

    return sorted(((parse_utc(row), row) for row in rows), key=lambda item: item[0])


def _expected_lines_from_source():
    lines = [HEADER]
    ny_tz = ZoneInfo("America/New_York")
    for dt_utc, row in _source_rows_sorted_by_utc():
        local_dt = dt_utc.astimezone(ny_tz)
        weekday = local_dt.strftime("%a")
        stamp = local_dt.strftime("%Y-%m-%d %H:%M %Z")
        lines.append(f"{row['service']}|{weekday}|{stamp}|severity={row['severity']}")
    return lines


def test_final_artifact_exists_and_is_utf8_text() -> None:
    text = _read_output_text()
    assert text, f"{OUT_PATH} exists but is empty"


def test_final_artifact_has_exact_required_bytes_including_single_trailing_newline() -> None:
    actual = _read_output_bytes()
    assert actual == EXPECTED_BYTES, (
        f"{OUT_PATH} does not match the required final artifact byte-for-byte.\n"
        "It must contain exactly:\n"
        f"{EXPECTED_TEXT!r}\n"
        "Common wrong states include UTC output, locale=C header, missing final newline, "
        "extra blank lines, or incorrectly converted New York timestamps."
    )


def test_final_artifact_line_count_header_and_blank_lines_are_correct() -> None:
    text = _read_output_text()

    assert text.endswith("\n"), f"{OUT_PATH} must end with a single trailing newline"
    assert not text.endswith("\n\n"), f"{OUT_PATH} must not contain blank lines after the last line"

    lines = text.split("\n")
    assert lines[-1] == "", (
        f"{OUT_PATH} must have exactly one trailing newline after the last required line"
    )
    content_lines = lines[:-1]

    assert len(content_lines) == 4, (
        f"{OUT_PATH} must contain exactly 4 non-empty content lines; "
        f"found {len(content_lines)} content line(s): {content_lines!r}"
    )

    empty_line_numbers = [
        line_number for line_number, line in enumerate(content_lines, start=1) if line == ""
    ]
    assert not empty_line_numbers, (
        f"{OUT_PATH} must not contain blank lines before or between required lines; "
        f"blank content line(s): {empty_line_numbers}"
    )

    assert content_lines[0] == HEADER, (
        f"Line 1 of {OUT_PATH} is wrong. Expected exactly {HEADER!r}, "
        f"found {content_lines[0]!r}. The artifact must use tz=America/New_York "
        "and locale=C.UTF-8."
    )


def test_alert_lines_have_required_pipe_delimited_format() -> None:
    lines = _read_output_text().splitlines()
    assert len(lines) >= 4, (
        f"{OUT_PATH} must have header plus 3 alert lines before format can be checked"
    )

    for line_number, line in enumerate(lines[1:], start=2):
        match = ALERT_LINE_RE.match(line)
        assert match is not None, (
            f"Line {line_number} of {OUT_PATH} has the wrong format: {line!r}. "
            "Expected '<service>|<weekday>|YYYY-MM-DD HH:MM EST|severity=<severity>' "
            "with English abbreviated weekday and EST timezone abbreviation."
        )


def test_alert_lines_are_sorted_by_original_utc_and_semantically_correct() -> None:
    actual_lines = _read_output_text().splitlines()
    expected_lines = _expected_lines_from_source()

    assert actual_lines == expected_lines, (
        f"{OUT_PATH} does not correctly render the source CSV sorted by original UTC "
        "timestamp and converted to America/New_York with EST timestamps.\n"
        f"Expected lines: {expected_lines!r}\n"
        f"Actual lines:   {actual_lines!r}"
    )


def test_no_utc_or_wrong_locale_false_success_remains_in_artifact() -> None:
    text = _read_output_text()

    assert "tz=UTC" not in text, (
        f"{OUT_PATH} still appears to contain the initial false-success UTC header/output"
    )
    assert "locale=C\n" not in text and "locale=C\r\n" not in text, (
        f"{OUT_PATH} still appears to contain the wrong locale=C header; "
        "it must be locale=C.UTF-8"
    )
    assert " UTC" not in text, (
        f"{OUT_PATH} still contains UTC timestamps; all rendered timestamps must be "
        "converted to America/New_York and end in EST"
    )
    assert "search-indexer|Tue|" not in text, (
        f"{OUT_PATH} still contains the UTC weekday for search-indexer. "
        "After conversion to America/New_York it must be Monday."
    )