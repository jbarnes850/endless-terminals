# test_final_state.py
import os
import sqlite3
import stat
import subprocess
from pathlib import Path

import pytest


TICKET_DIR = Path("/home/user/tickets/TK-2048")
DB_PATH = Path("/home/user/tickets/TK-2048/asset_cache.db")
HELPER_PATH = Path("/home/user/tickets/TK-2048/check_lookup.sh")
LOG_PATH = Path("/home/user/tickets/TK-2048/resolution.log")

EXPECTED_HELPER_OUTPUT = "lookup=ws-finance-042 result=ok plan=index"
EXPECTED_LOG_CONTENT = (
    "ticket=TK-2048\n"
    "status=optimized\n"
    f"verification={EXPECTED_HELPER_OUTPUT}"
)


def _open_db_readonly():
    try:
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        pytest.fail(f"Could not open database as SQLite: {DB_PATH}: {exc}")


def _quote_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def test_ticket_workspace_database_and_helper_still_exist():
    assert TICKET_DIR.exists(), f"Missing ticket workspace directory: {TICKET_DIR}"
    assert TICKET_DIR.is_dir(), f"Ticket workspace path is not a directory: {TICKET_DIR}"

    assert DB_PATH.exists(), f"Missing SQLite database file: {DB_PATH}"
    assert DB_PATH.is_file(), f"Database path is not a file: {DB_PATH}"
    assert os.access(DB_PATH, os.R_OK), f"Database file is not readable: {DB_PATH}"
    assert os.access(DB_PATH, os.W_OK), f"Database file is not writable: {DB_PATH}"

    assert HELPER_PATH.exists(), f"Missing verification helper script: {HELPER_PATH}"
    assert HELPER_PATH.is_file(), f"Helper path is not a file: {HELPER_PATH}"
    mode = HELPER_PATH.stat().st_mode
    assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), (
        f"Helper script is not executable by anyone: {HELPER_PATH}"
    )
    assert os.access(HELPER_PATH, os.X_OK), (
        f"Helper script is not executable by the current user without root: {HELPER_PATH}"
    )


def test_database_is_valid_and_assets_table_schema_was_not_broken():
    conn = _open_db_readonly()
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        assert integrity is not None, f"SQLite integrity check returned no result for: {DB_PATH}"
        assert integrity[0] == "ok", (
            f"SQLite database integrity check failed for {DB_PATH}: {integrity[0]}"
        )

        table_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='assets'"
        ).fetchone()
        assert table_row is not None, "Missing required table after task completion: assets"

        columns = conn.execute("PRAGMA table_info(assets)").fetchall()
    finally:
        conn.close()

    actual_columns = [
        {
            "name": row[1],
            "type": row[2].upper(),
            "notnull": row[3],
            "pk": row[5],
        }
        for row in columns
    ]
    expected_columns = [
        {"name": "asset_id", "type": "INTEGER", "notnull": 0, "pk": 1},
        {"name": "hostname", "type": "TEXT", "notnull": 1, "pk": 0},
        {"name": "owner", "type": "TEXT", "notnull": 1, "pk": 0},
        {"name": "location", "type": "TEXT", "notnull": 1, "pk": 0},
        {"name": "status", "type": "TEXT", "notnull": 1, "pk": 0},
        {"name": "last_seen", "type": "TEXT", "notnull": 1, "pk": 0},
    ]

    assert actual_columns == expected_columns, (
        "The assets table schema should remain unchanged except for adding an index. "
        f"Expected columns {expected_columns}, found {actual_columns}"
    )


def test_required_asset_data_is_still_present_and_unique():
    conn = _open_db_readonly()
    try:
        row_count = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        assert row_count >= 8000, (
            f"assets table should still contain at least 8000 rows; found {row_count}. "
            "The database may have been replaced or data may have been removed."
        )

        target_rows = conn.execute(
            """
            SELECT asset_id, owner, location, status, last_seen
            FROM assets
            WHERE hostname = ?
            """,
            ("ws-finance-042",),
        ).fetchall()

        exact_match_count = sum(
            1
            for row in target_rows
            if row[1:] == (
                "finance-support",
                "floor-3-west",
                "active",
                "2024-05-17T09:35:00Z",
            )
        )
    finally:
        conn.close()

    assert exact_match_count == 1, (
        "Expected exactly one matching finance workstation row to remain: "
        "hostname='ws-finance-042', owner='finance-support', "
        "location='floor-3-west', status='active', "
        "last_seen='2024-05-17T09:35:00Z'. "
        f"Found {exact_match_count} exact matches among {len(target_rows)} rows with that hostname."
    )


def test_preferred_hostname_index_exists_with_exact_definition():
    conn = _open_db_readonly()
    try:
        preferred = conn.execute(
            """
            SELECT name, tbl_name, sql
            FROM sqlite_master
            WHERE type = 'index' AND name = 'idx_assets_hostname'
            """
        ).fetchone()
        assert preferred is not None, (
            "Missing preferred final index named 'idx_assets_hostname'. "
            "Create the database-level optimization with: "
            "CREATE INDEX idx_assets_hostname ON assets(hostname);"
        )
        assert preferred[1] == "assets", (
            "Index 'idx_assets_hostname' exists but is not on table assets; "
            f"found table {preferred[1]!r}."
        )
        assert preferred[2] is not None, (
            "Index 'idx_assets_hostname' appears to be an internal/auto index, "
            "not the expected user-created index on assets(hostname)."
        )

        index_info = conn.execute(
            f"PRAGMA index_info({_quote_identifier('idx_assets_hostname')})"
        ).fetchall()
        indexed_columns = [row[2] for row in index_info]
    finally:
        conn.close()

    assert indexed_columns == ["hostname"], (
        "Index 'idx_assets_hostname' must index exactly one column, assets(hostname). "
        f"Found indexed columns: {indexed_columns}"
    )


def test_query_plan_uses_hostname_index_for_required_lookup():
    conn = _open_db_readonly()
    try:
        plan_rows = conn.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT asset_id, owner, location, status
            FROM assets
            WHERE hostname = 'ws-finance-042'
            """
        ).fetchall()
    finally:
        conn.close()

    plan_text = " | ".join(str(row[-1]) for row in plan_rows)
    assert "SCAN assets" not in plan_text.upper(), (
        "Required hostname lookup is still doing a full table scan instead of using an index. "
        f"Query plan: {plan_text}"
    )
    assert "INDEX" in plan_text.upper() or "idx_assets_hostname" in plan_text, (
        "Required hostname lookup does not appear to use an index. "
        f"Query plan: {plan_text}"
    )


def test_verification_helper_succeeds_after_optimization_with_exact_output():
    result = subprocess.run(
        [str(HELPER_PATH)],
        cwd=str(TICKET_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        "Verification helper should exit 0 after the hostname index optimization. "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}, exit_code={result.returncode}"
    )
    assert result.stdout.splitlines() == [EXPECTED_HELPER_OUTPUT], (
        "Verification helper should emit exactly the optimized indexed-plan line. "
        f"Expected {EXPECTED_HELPER_OUTPUT!r}; "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert result.stderr == "", (
        "Verification helper should not emit stderr during successful verification. "
        f"stderr={result.stderr!r}"
    )


def test_resolution_log_exists_and_has_exact_required_three_line_content():
    assert LOG_PATH.exists(), f"Missing required final ticket log file: {LOG_PATH}"
    assert LOG_PATH.is_file(), f"Resolution log path is not a regular file: {LOG_PATH}"

    raw = LOG_PATH.read_bytes()
    assert raw, f"Resolution log is empty: {LOG_PATH}"

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Resolution log must be valid UTF-8 text: {LOG_PATH}: {exc}")

    assert content in (EXPECTED_LOG_CONTENT, EXPECTED_LOG_CONTENT + "\n"), (
        "Resolution log content is not exactly the required three-line format. "
        "It must contain no leading/trailing spaces, comments, or extra blank lines. "
        f"Expected {EXPECTED_LOG_CONTENT!r} with optional final newline; found {content!r}"
    )

    lines = content.splitlines()
    assert lines == [
        "ticket=TK-2048",
        "status=optimized",
        f"verification={EXPECTED_HELPER_OUTPUT}",
    ], (
        "Resolution log must contain exactly three required lines using the "
        "post-optimization helper output. "
        f"Found lines: {lines!r}"
    )