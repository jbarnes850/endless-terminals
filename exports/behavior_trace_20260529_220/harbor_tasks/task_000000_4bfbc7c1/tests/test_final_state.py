# test_final_state.py
import os
import sqlite3
from pathlib import Path

import pytest


CANONICAL_DB = Path("/home/user/pentest/current/vulnscan.sqlite")
REPORT_FILE = Path("/home/user/pentest/current/migration_report.txt")
LEGACY_DB_OLD_PATH = Path("/home/user/pentest/legacy/vulnscan_old.sqlite")
LEGACY_DB_RETIRED_PATH = Path("/home/user/pentest/legacy/vulnscan_old.sqlite.retired")

EXPECTED_COLUMNS = [
    ("id", "INTEGER", 1),
    ("host", "TEXT", 0),
    ("port", "INTEGER", 0),
    ("service", "TEXT", 0),
    ("severity", "TEXT", 0),
    ("cve", "TEXT", 0),
    ("status", "TEXT", 0),
]

EXPECTED_ROWS = [
    (101, "10.10.14.21", 22, "ssh", "medium", "CVE-2023-38408", "open"),
    (102, "10.10.14.21", 80, "http", "critical", "CVE-2021-41773", "open"),
    (104, "10.10.14.23", 445, "smb", "critical", "CVE-2020-0796", "open"),
    (106, "10.10.14.25", 8080, "http-proxy", "low", "CVE-2019-0220", "open"),
]

EXPECTED_REPORT_LINES = [
    "canonical_db=/home/user/pentest/current/vulnscan.sqlite",
    "legacy_db_retired=yes",
    "open_findings=4",
    "critical_open_findings=2",
    "verification_source=current",
]


def connect_readonly(path: Path) -> sqlite3.Connection:
    assert path.is_absolute(), f"Test path must be absolute, got: {path}"
    try:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.DatabaseError as exc:
        pytest.fail(f"Could not open SQLite database read-only at {path}: {exc}")


def test_legacy_database_old_path_has_been_retired():
    assert not LEGACY_DB_OLD_PATH.exists(), (
        "The legacy database is still present at the old active path. "
        f"Expected this path to be renamed/removed after migration: {LEGACY_DB_OLD_PATH}"
    )

    assert LEGACY_DB_RETIRED_PATH.exists(), (
        "The retired legacy database path does not exist. "
        f"Expected legacy database to be renamed to: {LEGACY_DB_RETIRED_PATH}"
    )
    assert LEGACY_DB_RETIRED_PATH.is_file(), (
        "The retired legacy database path exists but is not a regular file: "
        f"{LEGACY_DB_RETIRED_PATH}"
    )


def test_retired_legacy_database_is_still_valid_sqlite_if_present():
    with connect_readonly(LEGACY_DB_RETIRED_PATH) as conn:
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.DatabaseError as exc:
            pytest.fail(
                f"Retired legacy database is not a valid SQLite database at "
                f"{LEGACY_DB_RETIRED_PATH}: {exc}"
            )

    assert integrity == ("ok",), (
        f"Retired legacy database failed SQLite integrity_check at "
        f"{LEGACY_DB_RETIRED_PATH}: {integrity!r}"
    )


def test_canonical_database_exists_as_regular_readable_file():
    assert CANONICAL_DB.exists(), (
        "Canonical SQLite database was not created at the required path: "
        f"{CANONICAL_DB}"
    )
    assert CANONICAL_DB.is_file(), (
        "Canonical database path exists but is not a regular file: "
        f"{CANONICAL_DB}"
    )
    assert os.access(CANONICAL_DB, os.R_OK), (
        "Canonical database is not readable by the current user: "
        f"{CANONICAL_DB}"
    )


def test_canonical_database_is_valid_sqlite_and_contains_findings_table():
    with connect_readonly(CANONICAL_DB) as conn:
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'findings'"
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            pytest.fail(
                f"Canonical database is not a valid readable SQLite database at "
                f"{CANONICAL_DB}: {exc}"
            )

    assert integrity == ("ok",), (
        f"Canonical database failed SQLite integrity_check at {CANONICAL_DB}: "
        f"{integrity!r}"
    )
    assert table == ("findings",), (
        f"Canonical database must contain a table named 'findings' at {CANONICAL_DB}"
    )


def test_canonical_findings_schema_has_exact_required_columns_in_order():
    with connect_readonly(CANONICAL_DB) as conn:
        schema = conn.execute("PRAGMA table_info(findings)").fetchall()

    actual_columns = [(row[1], row[2].upper(), row[5]) for row in schema]

    assert actual_columns == EXPECTED_COLUMNS, (
        "Canonical findings table does not have the exact required column order, "
        "declared types, and primary-key definition.\n"
        f"Database: {CANONICAL_DB}\n"
        f"Expected columns (name, type, pk): {EXPECTED_COLUMNS!r}\n"
        f"Actual columns   (name, type, pk): {actual_columns!r}\n"
        f"Full PRAGMA table_info output: {schema!r}"
    )


def test_canonical_findings_rows_are_exactly_active_legacy_findings():
    with connect_readonly(CANONICAL_DB) as conn:
        rows = conn.execute(
            """
            SELECT id, host, port, service, severity, cve, status
            FROM findings
            ORDER BY id
            """
        ).fetchall()

    assert rows == EXPECTED_ROWS, (
        "Canonical findings table must contain exactly the four original active "
        "findings with status='open', preserving all values, and no inactive rows.\n"
        f"Database: {CANONICAL_DB}\n"
        f"Expected rows: {EXPECTED_ROWS!r}\n"
        f"Actual rows:   {rows!r}"
    )


def test_canonical_database_contains_no_non_open_findings():
    with connect_readonly(CANONICAL_DB) as conn:
        non_open_rows = conn.execute(
            """
            SELECT id, host, port, service, severity, cve, status
            FROM findings
            WHERE status <> 'open' OR status IS NULL
            ORDER BY id
            """
        ).fetchall()

    assert non_open_rows == [], (
        "Canonical database contains findings that are not active/open. "
        "Rows with status other than exactly 'open' must not be migrated.\n"
        f"Unexpected rows in {CANONICAL_DB}: {non_open_rows!r}"
    )


def test_canonical_counts_are_calculated_from_new_database():
    with connect_readonly(CANONICAL_DB) as conn:
        total_findings = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        open_findings = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE status = 'open'"
        ).fetchone()[0]
        critical_open_findings = conn.execute(
            """
            SELECT COUNT(*)
            FROM findings
            WHERE severity = 'critical' AND status = 'open'
            """
        ).fetchone()[0]

    assert total_findings == 4, (
        f"Canonical database should contain exactly four migrated active findings, "
        f"but found {total_findings} in {CANONICAL_DB}"
    )
    assert open_findings == 4, (
        f"Canonical database should contain four open findings, "
        f"but found {open_findings} in {CANONICAL_DB}"
    )
    assert critical_open_findings == 2, (
        f"Canonical database should contain two critical open findings, "
        f"but found {critical_open_findings} in {CANONICAL_DB}"
    )


def test_migration_report_exists_and_has_exact_required_content():
    assert REPORT_FILE.exists(), (
        "Migration verification report was not created at the required path: "
        f"{REPORT_FILE}"
    )
    assert REPORT_FILE.is_file(), (
        "Migration report path exists but is not a regular file: "
        f"{REPORT_FILE}"
    )

    raw_content = REPORT_FILE.read_bytes()

    assert b"\r" not in raw_content, (
        "Migration report must use plain LF newlines only; carriage returns were found."
    )

    try:
        content = raw_content.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Migration report is not valid UTF-8 text at {REPORT_FILE}: {exc}")

    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    assert lines == EXPECTED_REPORT_LINES, (
        "Migration report content is not exactly correct. It must contain exactly "
        "five lines, no extra spaces, comments, alternate paths, or extra lines, "
        "and counts must reflect the canonical current database.\n"
        f"Report path: {REPORT_FILE}\n"
        f"Expected lines: {EXPECTED_REPORT_LINES!r}\n"
        f"Actual lines:   {lines!r}\n"
        f"Raw content:    {content!r}"
    )


def test_migration_report_counts_match_canonical_database_state():
    with connect_readonly(CANONICAL_DB) as conn:
        open_findings = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE status = 'open'"
        ).fetchone()[0]
        critical_open_findings = conn.execute(
            """
            SELECT COUNT(*)
            FROM findings
            WHERE severity = 'critical' AND status = 'open'
            """
        ).fetchone()[0]

    report_content = REPORT_FILE.read_text(encoding="utf-8")
    report_lines = report_content.split("\n")
    if report_lines and report_lines[-1] == "":
        report_lines = report_lines[:-1]

    report_values = {}
    for line in report_lines:
        if "=" in line:
            key, value = line.split("=", 1)
            report_values[key] = value

    assert report_values.get("canonical_db") == str(CANONICAL_DB), (
        "Report canonical_db line must point to the new current database, not the "
        f"retired legacy database. Actual value: {report_values.get('canonical_db')!r}"
    )
    assert report_values.get("legacy_db_retired") == "yes", (
        "Report must state legacy_db_retired=yes after the old path has been retired."
    )
    assert report_values.get("verification_source") == "current", (
        "Report must state verification_source=current to demonstrate verification "
        "was performed from the canonical database."
    )
    assert report_values.get("open_findings") == str(open_findings), (
        "Report open_findings value does not match the count queried from the "
        f"canonical database {CANONICAL_DB}. "
        f"Expected {open_findings}, got {report_values.get('open_findings')!r}"
    )
    assert report_values.get("critical_open_findings") == str(critical_open_findings), (
        "Report critical_open_findings value does not match the count queried from "
        f"the canonical database {CANONICAL_DB}. "
        f"Expected {critical_open_findings}, "
        f"got {report_values.get('critical_open_findings')!r}"
    )