# test_final_state.py
import json
import sqlite3
import subprocess
from pathlib import Path

import pytest


BASE_DIR = Path("/home/user/monitoring-migration")
DB_PATH = Path("/home/user/monitoring-migration/alerts.db")
MIGRATION_PATH = Path("/home/user/monitoring-migration/migrations/002_add_alert_metadata.sql")
VALIDATOR_PATH = Path("/home/user/monitoring-migration/validate_alerts.py")
LOG_PATH = Path("/home/user/monitoring-migration/migration_validation.log")

EXPECTED_LOG_TEXT = (
    "MIGRATION_APPLIED=yes\n"
    "SCHEMA_OK=yes\n"
    "ROW_COUNT_OK=yes\n"
    "CRITICAL_ALERTS_OK=yes\n"
    "VALIDATION_STATUS=pass\n"
    "CHECKLIST=migration:ok,schema:ok,row_count:ok,critical_alerts:ok"
)

EXPECTED_LOG_LINES = EXPECTED_LOG_TEXT.splitlines()

EXPECTED_VALIDATION_JSON = {
    "migration_applied": True,
    "schema_ok": True,
    "row_count_ok": True,
    "critical_alerts_ok": True,
    "validation_status": "pass",
    "checklist": {
        "migration": "ok",
        "schema": "ok",
        "row_count": "ok",
        "critical_alerts": "ok",
    },
}

EXPECTED_ALERTS_AFTER_MIGRATION = [
    (
        1,
        "High CPU saturation",
        "critical",
        "cpu_usage_percent",
        95.0,
        1,
        "pagerduty",
        "https://runbooks.internal/alerts/default",
    ),
    (
        2,
        "Disk space warning",
        "warning",
        "disk_used_percent",
        85.0,
        1,
        "pagerduty",
        "https://runbooks.internal/alerts/default",
    ),
    (
        3,
        "API latency critical",
        "critical",
        "api_latency_ms",
        1200.0,
        1,
        "pagerduty",
        "https://runbooks.internal/alerts/default",
    ),
    (
        4,
        "Memory pressure",
        "warning",
        "memory_used_percent",
        90.0,
        0,
        "pagerduty",
        "https://runbooks.internal/alerts/default",
    ),
]

EXPECTED_METADATA_ROWS = [
    (1, "platform-monitoring", 5),
    (2, "storage-monitoring", 30),
    (3, "api-monitoring", 10),
    (4, "platform-monitoring", 60),
]

EXPECTED_MIGRATION_HISTORY = [
    ("002_add_alert_metadata", "2025-02-14T10:00:00Z"),
]


def _connect_db():
    assert DB_PATH.is_file(), f"SQLite database is missing at required absolute path: {DB_PATH}"
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _run_validator():
    assert VALIDATOR_PATH.is_file(), f"Validation helper is missing: {VALIDATOR_PATH}"
    result = subprocess.run(
        ["python3", str(VALIDATOR_PATH), str(DB_PATH)],
        cwd=str(BASE_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = result.stdout.strip()
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(
            "Validation helper stdout is not valid JSON after migration. "
            f"returncode={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}, error={exc}"
        )
    return result, parsed


def test_required_paths_still_exist():
    assert BASE_DIR.is_dir(), f"Required working directory is missing: {BASE_DIR}"
    assert DB_PATH.is_file(), (
        f"Required SQLite database is missing; do not replace/remove it: {DB_PATH}"
    )
    assert MIGRATION_PATH.is_file(), f"Required migration SQL file is missing: {MIGRATION_PATH}"
    assert VALIDATOR_PATH.is_file(), f"Required validation helper is missing: {VALIDATOR_PATH}"
    assert LOG_PATH.is_file(), (
        f"Required validation report was not created at exact path: {LOG_PATH}"
    )


def test_database_schema_and_migration_history_are_final():
    with _connect_db() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "alerts" in tables, f"Database is missing required table 'alerts': {DB_PATH}"
        assert "migration_history" in tables, (
            f"Database is missing required table 'migration_history': {DB_PATH}"
        )
        assert "alert_metadata" in tables, (
            "Migration has not fully applied: table 'alert_metadata' is missing"
        )

        alert_columns = conn.execute("PRAGMA table_info(alerts)").fetchall()
        alert_column_names = [col[1] for col in alert_columns]
        for required_column in ("notification_channel", "runbook_url"):
            assert required_column in alert_column_names, (
                f"Migration has not fully applied: alerts.{required_column} column is missing"
            )

        notification_column = next(
            col for col in alert_columns if col[1] == "notification_channel"
        )
        runbook_column = next(col for col in alert_columns if col[1] == "runbook_url")
        assert notification_column[2].upper() == "TEXT", (
            "alerts.notification_channel should be a TEXT column"
        )
        assert notification_column[3] == 1, (
            "alerts.notification_channel should be NOT NULL"
        )
        assert runbook_column[2].upper() == "TEXT", (
            "alerts.runbook_url should be a TEXT column"
        )
        assert runbook_column[3] == 1, "alerts.runbook_url should be NOT NULL"

        metadata_columns = conn.execute("PRAGMA table_info(alert_metadata)").fetchall()
        metadata_column_defs = [(col[1], col[2], col[3], col[5]) for col in metadata_columns]
        assert metadata_column_defs == [
            ("alert_id", "INTEGER", 0, 1),
            ("owner_team", "TEXT", 1, 0),
            ("escalation_minutes", "INTEGER", 1, 0),
        ], "alert_metadata schema does not match the expected migrated schema"

        migration_history = conn.execute(
            "SELECT version, applied_at FROM migration_history ORDER BY version"
        ).fetchall()
        assert migration_history == EXPECTED_MIGRATION_HISTORY, (
            "migration_history must contain exactly the applied "
            "'002_add_alert_metadata' migration row with the expected timestamp"
        )


def test_database_data_survived_and_metadata_was_inserted():
    with _connect_db() as conn:
        alerts = conn.execute(
            """
            SELECT id, name, severity, metric, threshold, enabled,
                   notification_channel, runbook_url
            FROM alerts
            ORDER BY id
            """
        ).fetchall()
        assert alerts == EXPECTED_ALERTS_AFTER_MIGRATION, (
            "Alert rows were not preserved with the expected migrated default metadata columns"
        )

        metadata_rows = conn.execute(
            """
            SELECT alert_id, owner_team, escalation_minutes
            FROM alert_metadata
            ORDER BY alert_id
            """
        ).fetchall()
        assert metadata_rows == EXPECTED_METADATA_ROWS, (
            "alert_metadata rows do not match the expected migration output"
        )

        critical_alerts = conn.execute(
            """
            SELECT a.id, a.severity, a.enabled, a.notification_channel, a.runbook_url,
                   m.owner_team, m.escalation_minutes
            FROM alerts AS a
            JOIN alert_metadata AS m ON m.alert_id = a.id
            WHERE a.severity = 'critical' AND a.enabled = 1
            ORDER BY a.id
            """
        ).fetchall()
        assert critical_alerts == [
            (
                1,
                "critical",
                1,
                "pagerduty",
                "https://runbooks.internal/alerts/default",
                "platform-monitoring",
                5,
            ),
            (
                3,
                "critical",
                1,
                "pagerduty",
                "https://runbooks.internal/alerts/default",
                "api-monitoring",
                10,
            ),
        ], (
            "Critical enabled alerts are not valid after migration; expected exactly "
            "alerts 1 and 3 with pagerduty, runbook URLs, and matching metadata"
        )


def test_validation_helper_passes_with_exact_expected_json():
    result, parsed = _run_validator()

    assert result.returncode == 0, (
        "Validation helper must exit 0 after a correct migration. "
        f"Exited {result.returncode}. stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert parsed == EXPECTED_VALIDATION_JSON, (
        "Validation helper did not report the exact expected passing post-migration state"
    )


def test_validation_log_is_utf8_exact_six_non_empty_lines_in_required_order():
    try:
        raw_bytes = LOG_PATH.read_bytes()
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Validation report is not valid UTF-8 text: {LOG_PATH}; error={exc}")

    assert text, f"Validation report is empty: {LOG_PATH}"
    assert not text.startswith("\n"), (
        "Validation report must not have blank lines before the first KEY=VALUE line"
    )
    assert "\n\n" not in text, (
        "Validation report must not contain blank lines between KEY=VALUE lines"
    )

    stripped_once = text[:-1] if text.endswith("\n") else text
    assert not stripped_once.endswith("\n"), (
        "Validation report has extra trailing blank line(s); only one final newline is acceptable"
    )

    lines = stripped_once.split("\n")
    assert len(lines) == 6, (
        f"Validation report must contain exactly 6 non-empty lines, found {len(lines)}: {lines!r}"
    )
    assert all(line.strip() == line and line for line in lines), (
        "Each validation report line must be non-empty with no surrounding whitespace"
    )
    assert all(line.count("=") == 1 for line in lines), (
        "Each validation report line must be in KEY=VALUE format with exactly one '='"
    )

    actual_keys = [line.split("=", 1)[0] for line in lines]
    expected_keys = [
        "MIGRATION_APPLIED",
        "SCHEMA_OK",
        "ROW_COUNT_OK",
        "CRITICAL_ALERTS_OK",
        "VALIDATION_STATUS",
        "CHECKLIST",
    ]
    assert actual_keys == expected_keys, (
        "Validation report keys are missing or out of order. "
        f"Expected {expected_keys}, got {actual_keys}"
    )

    assert lines == EXPECTED_LOG_LINES, (
        "Validation report contents do not exactly match the required final report"
    )


def test_validation_log_values_match_actual_validator_result():
    result, parsed = _run_validator()
    assert result.returncode == 0, (
        "Cannot accept validation log because the actual database validation is failing. "
        f"returncode={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
    )

    text = LOG_PATH.read_text(encoding="utf-8")
    stripped_once = text[:-1] if text.endswith("\n") else text
    log_values = dict(line.split("=", 1) for line in stripped_once.split("\n"))

    expected_from_validation = {
        "MIGRATION_APPLIED": "yes" if parsed.get("migration_applied") is True else "no",
        "SCHEMA_OK": "yes" if parsed.get("schema_ok") is True else "no",
        "ROW_COUNT_OK": "yes" if parsed.get("row_count_ok") is True else "no",
        "CRITICAL_ALERTS_OK": "yes" if parsed.get("critical_alerts_ok") is True else "no",
        "VALIDATION_STATUS": parsed.get("validation_status"),
        "CHECKLIST": ",".join(
            [
                f"migration:{parsed.get('checklist', {}).get('migration')}",
                f"schema:{parsed.get('checklist', {}).get('schema')}",
                f"row_count:{parsed.get('checklist', {}).get('row_count')}",
                f"critical_alerts:{parsed.get('checklist', {}).get('critical_alerts')}",
            ]
        ),
    }

    assert log_values == expected_from_validation, (
        "Validation report values do not accurately map the actual validator JSON result. "
        f"Expected from validator: {expected_from_validation}, got log values: {log_values}"
    )