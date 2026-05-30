# test_final_state.py
import csv
import json
import re
from pathlib import Path


BASE = Path("/home/user/netdebug")
PROBES = Path("/home/user/netdebug/probes.jsonl")
REPORT = Path("/home/user/netdebug/connectivity_report.txt")

EXPECTED_REPORT = """CONNECTIVITY FAILURE REPORT
source,target,port,error
api-1,db-primary.internal,5432,connection timed out
api-2,cache.internal,6379,no route to host
api-3,auth.internal,443,tls handshake timeout
worker-1,db-primary.internal,5432,connection timed out
worker-1,queue.internal,5672,connection refused
TOTAL_FAILURES=5
VERIFIED=yes
"""

EXPECTED_FAILURE_ROWS = [
    ("api-1", "db-primary.internal", 5432, "connection timed out"),
    ("api-2", "cache.internal", 6379, "no route to host"),
    ("api-3", "auth.internal", 443, "tls handshake timeout"),
    ("worker-1", "db-primary.internal", 5432, "connection timed out"),
    ("worker-1", "queue.internal", 5672, "connection refused"),
]


def _read_probe_records():
    assert PROBES.exists(), f"Probe data file is missing: {PROBES}"
    assert PROBES.is_file(), f"Probe data path is not a regular file: {PROBES}"

    records = []
    with PROBES.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    f"Probe data file {PROBES} contains invalid JSON on line {line_number}: {exc}"
                ) from exc
    return records


def _expected_rows_from_probe_data():
    records = _read_probe_records()
    rows = [
        (rec["source"], rec["target"], int(rec["port"]), rec["error"])
        for rec in records
        if rec.get("status") == "fail"
    ]
    return sorted(rows, key=lambda row: (row[0], row[1], row[2]))


def _read_report_lines():
    assert REPORT.exists(), f"Required final report is missing: {REPORT}"
    assert REPORT.is_file(), f"Report path exists but is not a regular file: {REPORT}"
    try:
        return REPORT.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AssertionError(f"Report file is not readable: {REPORT}: {exc}") from exc


def _parse_report_failure_rows(lines):
    assert len(lines) >= 4, (
        f"Report at {REPORT} is too short; expected title, CSV header, "
        "at least the TOTAL_FAILURES line, and VERIFIED=yes"
    )

    total_line_index = None
    for index, line in enumerate(lines):
        if line.startswith("TOTAL_FAILURES="):
            total_line_index = index
            break

    assert total_line_index is not None, (
        f"Report at {REPORT} is missing the required TOTAL_FAILURES=N line"
    )

    data_lines = lines[2:total_line_index]
    parsed_rows = []

    for offset, line in enumerate(data_lines, start=3):
        try:
            fields = next(csv.reader([line]))
        except csv.Error as exc:
            raise AssertionError(
                f"Failure row on report line {offset} is not valid CSV: {line!r}: {exc}"
            ) from exc

        assert len(fields) == 4, (
            f"Failure row on report line {offset} must contain exactly four "
            f"comma-separated fields source,target,port,error; got {len(fields)} fields: {line!r}"
        )

        source, target, port_text, error = fields
        assert port_text.isdigit(), (
            f"Port field on report line {offset} must be numeric; got {port_text!r}"
        )
        parsed_rows.append((source, target, int(port_text), error))

    return parsed_rows, total_line_index


def test_report_exists_at_required_absolute_path_and_is_readable():
    assert BASE.exists(), f"Required working directory is missing: {BASE}"
    assert BASE.is_dir(), f"Required working directory path is not a directory: {BASE}"
    lines = _read_report_lines()
    assert lines, f"Report exists but is empty: {REPORT}"


def test_report_exact_final_artifact_contents():
    actual = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    assert actual == EXPECTED_REPORT, (
        f"Final report at {REPORT} does not exactly match the required artifact.\n"
        "It must include all failed probes, preserve duplicate target failures from "
        "different sources, exclude successful probes, have TOTAL_FAILURES=5, and end "
        "with VERIFIED=yes."
    )


def test_report_required_headers_total_and_verification_lines():
    lines = _read_report_lines()

    assert lines[0] == "CONNECTIVITY FAILURE REPORT", (
        f"First line of {REPORT} is wrong; expected exactly "
        "'CONNECTIVITY FAILURE REPORT', got {lines[0]!r}"
    )
    assert lines[1] == "source,target,port,error", (
        f"Second line of {REPORT} is wrong; expected exactly "
        "'source,target,port,error', got {lines[1]!r}"
    )
    assert lines[-1] == "VERIFIED=yes", (
        f"Last line of {REPORT} must be exactly 'VERIFIED=yes'; got {lines[-1]!r}"
    )
    assert len(lines) >= 2 and re.fullmatch(r"TOTAL_FAILURES=\d+", lines[-2]), (
        f"Penultimate line of {REPORT} must match TOTAL_FAILURES=N; got {lines[-2]!r}"
    )


def test_failure_rows_are_valid_csv_and_sorted_by_source_target_numeric_port():
    lines = _read_report_lines()
    rows, total_line_index = _parse_report_failure_rows(lines)

    assert total_line_index == len(lines) - 2, (
        f"TOTAL_FAILURES line must appear immediately before final VERIFIED=yes line in {REPORT}"
    )

    sorted_rows = sorted(rows, key=lambda row: (row[0], row[1], row[2]))
    assert rows == sorted_rows, (
        "Failure rows are not sorted by ascending source, then ascending target, "
        f"then ascending numeric port. Actual rows: {rows!r}; expected order: {sorted_rows!r}"
    )


def test_report_semantically_matches_all_and_only_failed_probe_records():
    lines = _read_report_lines()
    rows, _ = _parse_report_failure_rows(lines)

    expected_rows = _expected_rows_from_probe_data()
    assert expected_rows == EXPECTED_FAILURE_ROWS, (
        f"Unexpected failure rows derived from probe data at {PROBES}: {expected_rows!r}"
    )

    assert rows == expected_rows, (
        f"Report rows do not exactly match all failed records from {PROBES}.\n"
        f"Expected failed rows: {expected_rows!r}\n"
        f"Actual report rows:   {rows!r}\n"
        "This commonly means the report was generated from the buggy helper output "
        "and omitted a duplicate target failure from a different source, or included "
        "successful probes."
    )


def test_total_failures_matches_probe_data_and_report_rows():
    lines = _read_report_lines()
    rows, _ = _parse_report_failure_rows(lines)

    total_line = lines[-2]
    total_count = int(total_line.split("=", 1)[1])
    expected_rows = _expected_rows_from_probe_data()

    assert total_count == len(expected_rows), (
        f"{total_line!r} is wrong; expected TOTAL_FAILURES={len(expected_rows)} "
        f"based on failed records in {PROBES}"
    )
    assert total_count == len(rows), (
        f"{total_line!r} does not match the number of failure rows in {REPORT}; "
        f"found {len(rows)} rows"
    )
    assert total_count == 5, (
        f"TOTAL_FAILURES must be 5 for the provided probe data; got {total_count}"
    )