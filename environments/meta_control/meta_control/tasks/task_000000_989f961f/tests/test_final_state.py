# test_final_state.py
import sqlite3
from pathlib import Path

import pytest


RELEASES_DIR = Path("/home/user/releases")
LEGACY_DB = Path("/home/user/releases/releases_legacy.sqlite")
ACTIVE_DB = Path("/home/user/releases/releases_active.sqlite")
VERIFICATION_LOG = Path("/home/user/releases/deployment_verification.log")

EXPECTED_SCHEMA = [
    ("service", "TEXT"),
    ("version", "TEXT"),
    ("environment", "TEXT"),
    ("approved", "INTEGER"),
]

EXPECTED_ACTIVE_ROWS_SORTED = [
    ("api-gateway", "2026.05.29", "production", 1),
    ("billing-worker", "2026.05.29", "production", 1),
    ("reporting-ui", "2026.05.29", "production", 1),
]

EXPECTED_LOG_LINES = [
    "ACTIVE_DB=/home/user/releases/releases_active.sqlite",
    "LEGACY_DB_RETIRED=yes",
    "ACTIVE_ROW_COUNT=3",
    "ACTIVE_APPROVED_PRODUCTION=3",
]


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _assert_valid_sqlite_database(db_path: Path) -> None:
    try:
        with _connect_readonly(db_path) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError as exc:
        pytest.fail(f"{db_path} is not a readable valid SQLite database: {exc}")

    assert result is not None, f"Could not run PRAGMA integrity_check on {db_path}"
    assert result[0] == "ok", f"SQLite integrity check failed for {db_path}: {result[0]}"


def _table_exists(db_path: Path, table_name: str) -> bool:
    with _connect_readonly(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
    return row is not None


def _deployment_manifest_schema(db_path: Path):
    with _connect_readonly(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(deployment_manifest)").fetchall()

    return [(row[1], row[2].upper()) for row in rows]


def _active_manifest_rows_sorted():
    with _connect_readonly(ACTIVE_DB) as conn:
        return conn.execute(
            """
            SELECT service, version, environment, approved
            FROM deployment_manifest
            ORDER BY service
            """
        ).fetchall()


def _active_manifest_count() -> int:
    with _connect_readonly(ACTIVE_DB) as conn:
        return conn.execute("SELECT COUNT(*) FROM deployment_manifest").fetchone()[0]


def _active_approved_production_count() -> int:
    with _connect_readonly(ACTIVE_DB) as conn:
        return conn.execute(
            """
            SELECT COUNT(*)
            FROM deployment_manifest
            WHERE environment = 'production'
              AND approved = 1
            """
        ).fetchone()[0]


def test_required_release_paths_exist_after_task():
    assert RELEASES_DIR.exists(), f"Required releases directory is missing: {RELEASES_DIR}"
    assert RELEASES_DIR.is_dir(), f"Required releases path is not a directory: {RELEASES_DIR}"

    assert ACTIVE_DB.exists(), f"Active SQLite database is missing: {ACTIVE_DB}"
    assert ACTIVE_DB.is_file(), f"Active database path is not a file: {ACTIVE_DB}"

    assert LEGACY_DB.exists(), (
        f"Legacy SQLite database file should still exist but have deployment_manifest retired: {LEGACY_DB}"
    )
    assert LEGACY_DB.is_file(), f"Legacy database path is not a file: {LEGACY_DB}"


@pytest.mark.parametrize("db_path", [ACTIVE_DB, LEGACY_DB])
def test_database_files_are_valid_sqlite_databases(db_path):
    _assert_valid_sqlite_database(db_path)


def test_active_database_contains_deployment_manifest_table():
    assert _table_exists(ACTIVE_DB, "deployment_manifest"), (
        f"{ACTIVE_DB} must contain table deployment_manifest as the authoritative manifest"
    )


def test_active_deployment_manifest_schema_is_exact():
    actual_schema = _deployment_manifest_schema(ACTIVE_DB)

    assert actual_schema == EXPECTED_SCHEMA, (
        f"{ACTIVE_DB} deployment_manifest schema is incorrect. "
        f"Expected columns/types in order {EXPECTED_SCHEMA}, got {actual_schema}"
    )


def test_active_deployment_manifest_rows_are_exact_and_no_extras():
    actual_rows = _active_manifest_rows_sorted()

    assert actual_rows == EXPECTED_ACTIVE_ROWS_SORTED, (
        f"{ACTIVE_DB} deployment_manifest rows are incorrect. "
        f"Expected exactly {EXPECTED_ACTIVE_ROWS_SORTED} ordered by service, got {actual_rows}. "
        "The active database must contain all three approved production 2026.05.29 services and no extra rows."
    )


def test_active_deployment_manifest_counts_are_verified_from_active_database():
    actual_total = _active_manifest_count()
    actual_approved_production = _active_approved_production_count()

    assert actual_total == 3, (
        f"{ACTIVE_DB} deployment_manifest must contain exactly 3 rows, got {actual_total}"
    )
    assert actual_approved_production == 3, (
        f"{ACTIVE_DB} deployment_manifest must contain exactly 3 rows where "
        f"environment='production' and approved=1, got {actual_approved_production}"
    )


def test_legacy_database_no_longer_has_queryable_deployment_manifest_table():
    assert not _table_exists(LEGACY_DB, "deployment_manifest"), (
        f"{LEGACY_DB} must no longer contain a usable/queryable table named deployment_manifest. "
        "Drop or retire the legacy manifest table so the active database is the only current source of truth."
    )

    with _connect_readonly(LEGACY_DB) as conn:
        with pytest.raises(sqlite3.DatabaseError, match="no such table"):
            conn.execute("SELECT COUNT(*) FROM deployment_manifest").fetchone()


def test_verification_log_exists_and_is_plain_file():
    assert VERIFICATION_LOG.exists(), f"Verification log is missing: {VERIFICATION_LOG}"
    assert VERIFICATION_LOG.is_file(), f"Verification log path is not a regular file: {VERIFICATION_LOG}"


def test_verification_log_contents_are_exact():
    raw_bytes = VERIFICATION_LOG.read_bytes()

    assert b"\x00" not in raw_bytes, (
        f"{VERIFICATION_LOG} must be a plain text file, but it contains NUL bytes"
    )

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"{VERIFICATION_LOG} must be UTF-8/plain text readable: {exc}")

    actual_lines = content.splitlines()

    assert actual_lines == EXPECTED_LOG_LINES, (
        f"{VERIFICATION_LOG} contents are incorrect. "
        f"Expected exactly these four lines with no extra leading/trailing lines: "
        f"{EXPECTED_LOG_LINES!r}, got {actual_lines!r}"
    )

    assert content in ("\n".join(EXPECTED_LOG_LINES), "\n".join(EXPECTED_LOG_LINES) + "\n"), (
        f"{VERIFICATION_LOG} must contain exactly the four required lines; "
        "only a single trailing newline after the fourth line is acceptable"
    )


def test_verification_log_values_match_active_database_not_legacy():
    total_from_active = _active_manifest_count()
    approved_production_from_active = _active_approved_production_count()

    log_lines = VERIFICATION_LOG.read_text(encoding="utf-8").splitlines()
    log_values = dict(line.split("=", 1) for line in log_lines)

    assert log_values.get("ACTIVE_DB") == str(ACTIVE_DB), (
        f"{VERIFICATION_LOG} must identify the active database as {ACTIVE_DB}"
    )
    assert log_values.get("LEGACY_DB_RETIRED") == "yes", (
        f"{VERIFICATION_LOG} must record LEGACY_DB_RETIRED=yes after retiring {LEGACY_DB}"
    )
    assert log_values.get("ACTIVE_ROW_COUNT") == str(total_from_active), (
        f"{VERIFICATION_LOG} ACTIVE_ROW_COUNT must match a query against {ACTIVE_DB}; "
        f"expected {total_from_active}, got {log_values.get('ACTIVE_ROW_COUNT')!r}"
    )
    assert log_values.get("ACTIVE_APPROVED_PRODUCTION") == str(approved_production_from_active), (
        f"{VERIFICATION_LOG} ACTIVE_APPROVED_PRODUCTION must match a query against {ACTIVE_DB}; "
        f"expected {approved_production_from_active}, got {log_values.get('ACTIVE_APPROVED_PRODUCTION')!r}"
    )