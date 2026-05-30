# test_final_state.py
import json
import math
import sqlite3
from pathlib import Path

import pytest


BASE_DIR = Path("/home/user/observability_dashboard")
DB_PATH = Path("/home/user/observability_dashboard/metrics.db")
SUMMARY_PATH = Path("/home/user/observability_dashboard/dashboard_summary.json")
VERIFICATION_LOG_PATH = Path("/home/user/observability_dashboard/verification.log")

EXPECTED_TOP_LEVEL_KEYS = {
    "generated_for",
    "time_window",
    "services",
    "dashboard_widgets",
    "verification",
}

EXPECTED_TIME_WINDOW_KEYS = {"start", "end", "sample_count"}
EXPECTED_SERVICE_KEYS = {
    "service",
    "samples",
    "avg_latency_ms",
    "p95_latency_ms",
    "error_rate",
}
EXPECTED_WIDGET_KEYS = {"widget_id", "title", "service", "metric"}
EXPECTED_VERIFICATION_KEYS = {"checked", "notes"}

EXPECTED_VERIFICATION_LOG_LINES = [
    "command_completed=true",
    "artifact_exists=true",
    "artifact_valid_json=true",
    "semantic_checks_passed=true",
]


def _connect_db():
    assert DB_PATH.exists(), f"Required SQLite source database is missing: {DB_PATH}"
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as exc:
        pytest.fail(f"Could not open SQLite database at {DB_PATH}: {exc}")


def _load_summary_json():
    assert SUMMARY_PATH.exists(), (
        f"Final artifact is missing: {SUMMARY_PATH}. "
        "Generate dashboard_summary.json before finishing."
    )
    assert SUMMARY_PATH.is_file(), f"Final artifact path exists but is not a file: {SUMMARY_PATH}"

    try:
        return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"Final artifact is not valid JSON: {SUMMARY_PATH}. "
            f"JSON parser error at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        )


def _nearest_rank_p95(latencies):
    assert latencies, "Cannot compute p95 for an empty latency list"
    sorted_latencies = sorted(latencies)
    rank = math.ceil(0.95 * len(sorted_latencies))
    return sorted_latencies[rank - 1]


def _round_numeric(value, places):
    return round(float(value), places)


def _expected_summary_from_database():
    with _connect_db() as conn:
        metadata_rows = conn.execute("SELECT key, value FROM metadata").fetchall()
        metadata = {row["key"]: row["value"] for row in metadata_rows}

        assert metadata.get("dashboard_owner") == "observability-engineering", (
            f"Unexpected dashboard_owner in {DB_PATH}: "
            f"{metadata.get('dashboard_owner')!r}"
        )
        assert "cutoff_ts" in metadata, f"metadata.cutoff_ts is missing from {DB_PATH}"

        cutoff_ts = metadata["cutoff_ts"]

        included_rows = conn.execute(
            """
            SELECT ts, service, latency_ms, status
            FROM latency_samples
            WHERE environment = 'prod' AND ts >= ?
            ORDER BY ts, id
            """,
            (cutoff_ts,),
        ).fetchall()

        widget_rows = conn.execute(
            """
            SELECT widget_id, title, service, metric
            FROM dashboard_widgets
            WHERE enabled = 1
            ORDER BY widget_id ASC
            """
        ).fetchall()

    assert included_rows, (
        f"No production latency samples at or after cutoff {cutoff_ts!r} "
        f"were found in {DB_PATH}"
    )

    service_names = sorted({row["service"] for row in included_rows})
    services = []
    for service_name in service_names:
        service_rows = [row for row in included_rows if row["service"] == service_name]
        latencies = [float(row["latency_ms"]) for row in service_rows]
        error_count = sum(1 for row in service_rows if row["status"] != "ok")
        sample_count = len(service_rows)

        services.append(
            {
                "service": service_name,
                "samples": sample_count,
                "avg_latency_ms": _round_numeric(sum(latencies) / sample_count, 2),
                "p95_latency_ms": _round_numeric(_nearest_rank_p95(latencies), 2),
                "error_rate": _round_numeric(error_count / sample_count, 4),
            }
        )

    return {
        "generated_for": metadata["dashboard_owner"],
        "time_window": {
            "start": min(row["ts"] for row in included_rows),
            "end": max(row["ts"] for row in included_rows),
            "sample_count": len(included_rows),
        },
        "services": services,
        "dashboard_widgets": [
            {
                "widget_id": row["widget_id"],
                "title": row["title"],
                "service": row["service"],
                "metric": row["metric"],
            }
            for row in widget_rows
        ],
        "verification": {
            "checked": True,
            "notes": "artifact compared against sqlite source rows",
        },
    }


def _assert_exact_keys(obj, expected_keys, location):
    assert isinstance(obj, dict), f"{location} must be a JSON object, got {type(obj).__name__}"
    actual_keys = set(obj.keys())
    assert actual_keys == expected_keys, (
        f"{location} has wrong keys.\n"
        f"Expected exactly: {sorted(expected_keys)}\n"
        f"Actual:           {sorted(actual_keys)}"
    )


def _assert_numeric_json_value(value, location):
    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
        f"{location} must be a numeric JSON value, not {value!r} "
        f"of type {type(value).__name__}"
    )


def test_dashboard_summary_exists_and_is_valid_json_object_with_exact_top_level_keys():
    summary = _load_summary_json()
    _assert_exact_keys(summary, EXPECTED_TOP_LEVEL_KEYS, "top-level dashboard_summary.json")


def test_dashboard_summary_exact_semantics_match_sqlite_source_rows():
    summary = _load_summary_json()
    expected = _expected_summary_from_database()

    _assert_exact_keys(summary, EXPECTED_TOP_LEVEL_KEYS, "top-level dashboard_summary.json")
    _assert_exact_keys(summary["time_window"], EXPECTED_TIME_WINDOW_KEYS, "time_window")
    _assert_exact_keys(summary["verification"], EXPECTED_VERIFICATION_KEYS, "verification")

    assert isinstance(summary["services"], list), "services must be a JSON array"
    assert isinstance(summary["dashboard_widgets"], list), "dashboard_widgets must be a JSON array"

    for index, service_obj in enumerate(summary["services"]):
        _assert_exact_keys(service_obj, EXPECTED_SERVICE_KEYS, f"services[{index}]")
        assert isinstance(service_obj["samples"], int) and not isinstance(
            service_obj["samples"], bool
        ), f"services[{index}].samples must be an integer"
        _assert_numeric_json_value(
            service_obj["avg_latency_ms"], f"services[{index}].avg_latency_ms"
        )
        _assert_numeric_json_value(
            service_obj["p95_latency_ms"], f"services[{index}].p95_latency_ms"
        )
        _assert_numeric_json_value(service_obj["error_rate"], f"services[{index}].error_rate")

    for index, widget_obj in enumerate(summary["dashboard_widgets"]):
        _assert_exact_keys(widget_obj, EXPECTED_WIDGET_KEYS, f"dashboard_widgets[{index}]")

    assert summary == expected, (
        "dashboard_summary.json does not exactly match the expected final summary "
        "computed from SQLite source rows using prod-only cutoff filtering, "
        "alphabetical service sorting, nearest-rank p95, enabled-widget filtering, "
        "and required verification fields.\n"
        f"Expected:\n{json.dumps(expected, indent=2, sort_keys=False)}\n"
        f"Actual:\n{json.dumps(summary, indent=2, sort_keys=False)}"
    )


def test_dashboard_summary_matches_known_required_final_values():
    summary = _load_summary_json()

    expected_known_final = {
        "generated_for": "observability-engineering",
        "time_window": {
            "start": "2026-02-14T11:31:00Z",
            "end": "2026-02-14T11:59:00Z",
            "sample_count": 15,
        },
        "services": [
            {
                "service": "api-gateway",
                "samples": 5,
                "avg_latency_ms": 149.0,
                "p95_latency_ms": 300.0,
                "error_rate": 0.2,
            },
            {
                "service": "checkout",
                "samples": 5,
                "avg_latency_ms": 247.0,
                "p95_latency_ms": 400.0,
                "error_rate": 0.4,
            },
            {
                "service": "inventory",
                "samples": 5,
                "avg_latency_ms": 170.0,
                "p95_latency_ms": 500.0,
                "error_rate": 0.2,
            },
        ],
        "dashboard_widgets": [
            {
                "widget_id": 10,
                "title": "API Gateway Latency",
                "service": "api-gateway",
                "metric": "p95_latency_ms",
            },
            {
                "widget_id": 11,
                "title": "Checkout Error Rate",
                "service": "checkout",
                "metric": "error_rate",
            },
            {
                "widget_id": 12,
                "title": "Inventory Average Latency",
                "service": "inventory",
                "metric": "avg_latency_ms",
            },
        ],
        "verification": {
            "checked": True,
            "notes": "artifact compared against sqlite source rows",
        },
    }

    assert summary == expected_known_final, (
        "dashboard_summary.json does not match the exact required final artifact. "
        "This usually means the exporter still includes the old prod row, includes "
        "non-prod rows, uses interpolated p95 instead of nearest-rank p95, includes "
        "disabled widgets, has wrong ordering, or has incorrect verification fields."
    )


def test_services_are_sorted_and_exclude_filtered_out_samples():
    summary = _load_summary_json()
    services = summary.get("services")

    assert isinstance(services, list), "services must be a JSON array"

    service_names = [service_obj.get("service") for service_obj in services]
    assert service_names == sorted(service_names), (
        f"services must be sorted alphabetically by service name. Actual order: {service_names}"
    )

    assert summary.get("time_window", {}).get("sample_count") == 15, (
        "time_window.sample_count must be 15, counting only prod rows with "
        "ts >= metadata.cutoff_ts. The old 11:20 prod sample and non-prod samples "
        "must be excluded."
    )

    api_gateway = next(
        (service_obj for service_obj in services if service_obj.get("service") == "api-gateway"),
        None,
    )
    assert api_gateway is not None, "Missing api-gateway service summary"
    assert api_gateway["samples"] == 5, (
        "api-gateway must have exactly 5 included samples. "
        "If it has 6, the old 11:20 prod row was incorrectly included."
    )
    assert api_gateway["avg_latency_ms"] == 149.0, (
        "api-gateway average latency must be 149.0 after excluding the old 900ms row."
    )
    assert api_gateway["p95_latency_ms"] == 300.0, (
        "api-gateway p95 must use nearest-rank percentile over the 5 included samples, "
        "selecting the 5th sorted value: 300.0."
    )


def test_dashboard_widgets_are_enabled_only_and_sorted_by_widget_id():
    summary = _load_summary_json()
    widgets = summary.get("dashboard_widgets")

    assert isinstance(widgets, list), "dashboard_widgets must be a JSON array"

    widget_ids = [widget.get("widget_id") for widget in widgets]
    assert widget_ids == sorted(widget_ids), (
        f"dashboard_widgets must be sorted by widget_id ascending. Actual order: {widget_ids}"
    )
    assert widget_ids == [10, 11, 12], (
        "dashboard_widgets must include only enabled widgets with IDs [10, 11, 12]. "
        f"Actual widget IDs: {widget_ids}. Disabled widget 13 must not be present."
    )


def test_verification_log_exists_and_has_exact_required_lines():
    assert VERIFICATION_LOG_PATH.exists(), (
        f"Verification log is missing: {VERIFICATION_LOG_PATH}. "
        "Create it only after semantic checks pass."
    )
    assert VERIFICATION_LOG_PATH.is_file(), (
        f"Verification log path exists but is not a file: {VERIFICATION_LOG_PATH}"
    )

    content = VERIFICATION_LOG_PATH.read_text(encoding="utf-8")
    actual_lines = content.splitlines()

    assert actual_lines == EXPECTED_VERIFICATION_LOG_LINES, (
        f"verification.log must contain exactly four required lines in order.\n"
        f"Expected lines: {EXPECTED_VERIFICATION_LOG_LINES}\n"
        f"Actual lines:   {actual_lines}\n"
        f"Raw content was:\n{content!r}"
    )

    assert content.endswith("\n") or content == "\n".join(EXPECTED_VERIFICATION_LOG_LINES), (
        "verification.log has the correct logical lines but unusual trailing content handling. "
        "It should be plain text containing only the required four lines."
    )