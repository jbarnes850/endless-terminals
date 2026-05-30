# test_final_state.py
import json
import math
from pathlib import Path

import pytest


REPORT_PATH = Path("/home/user/sre-uptime-check/uptime_report.json")
LOG_PATH = Path("/home/user/sre-uptime-check/verification.log")

EXPECTED_TOP_LEVEL_KEYS = {
    "service",
    "base_url",
    "overall_status",
    "checked_endpoints",
    "version",
    "metrics",
    "recent_incidents",
    "verification",
}

EXPECTED_VERSION = {
    "name": "catalog-api",
    "version": "2.7.4",
    "git_sha": "9f4c1b8",
    "build_time": "2025-02-14T11:06:22Z",
}

EXPECTED_RECENT_INCIDENTS = [
    {
        "id": "INC-1042",
        "severity": "minor",
        "summary": "search index lag above threshold",
        "opened_at": "2025-02-14T10:58:03Z",
        "resolved": False,
    }
]

EXPECTED_LOG_TEXT = (
    "curl probes completed\n"
    "report file created\n"
    "json syntax verified\n"
    "semantic status verified\n"
)


def _load_report():
    assert REPORT_PATH.exists(), (
        "Missing final report file: /home/user/sre-uptime-check/uptime_report.json"
    )
    assert REPORT_PATH.is_file(), (
        "Expected /home/user/sre-uptime-check/uptime_report.json to be a regular file"
    )

    raw = REPORT_PATH.read_text(encoding="utf-8")
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(
            "Final report /home/user/sre-uptime-check/uptime_report.json is not valid JSON: "
            f"{exc}"
        )
    return report


def _assert_exact_keys(obj, expected_keys, context):
    assert isinstance(obj, dict), f"{context} must be a JSON object, got {type(obj).__name__}"
    actual_keys = set(obj.keys())
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    assert actual_keys == expected_keys, (
        f"{context} has incorrect keys. "
        f"Missing keys: {sorted(missing)}; extra keys: {sorted(extra)}; "
        f"actual keys: {sorted(actual_keys)}"
    )


def _assert_json_number(value, context):
    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
        f"{context} must be a JSON number, not {type(value).__name__}: {value!r}"
    )
    if isinstance(value, float):
        assert math.isfinite(value), f"{context} must be finite, got {value!r}"


def test_uptime_report_exists_is_valid_json_object_and_has_exact_top_level_keys():
    report = _load_report()
    _assert_exact_keys(report, EXPECTED_TOP_LEVEL_KEYS, "uptime_report.json top-level object")


def test_uptime_report_required_scalar_values_indicate_degraded_catalog_api():
    report = _load_report()

    assert report["service"] == "catalog-api", (
        "report.service must be exactly 'catalog-api'"
    )
    assert report["base_url"] == "http://127.0.0.1:8097", (
        "report.base_url must be exactly 'http://127.0.0.1:8097'"
    )
    assert report["overall_status"] == "degraded", (
        "report.overall_status must be 'degraded' because /ready returned HTTP 503 "
        "with api_status 'not_ready' and request_error_total is 7"
    )


def test_checked_endpoints_exactly_capture_health_and_ready_http_and_body_statuses():
    report = _load_report()
    checked = report["checked_endpoints"]

    assert isinstance(checked, list), "report.checked_endpoints must be a JSON array"
    assert len(checked) == 2, (
        f"report.checked_endpoints must contain exactly two entries, got {len(checked)}"
    )

    by_path = {}
    for index, entry in enumerate(checked):
        _assert_exact_keys(
            entry,
            {"path", "http_status", "api_status", "latency_ms"},
            f"checked_endpoints[{index}]",
        )

        path = entry["path"]
        assert path in {"/health", "/ready"}, (
            f"checked_endpoints[{index}].path must be either '/health' or '/ready', got {path!r}"
        )
        assert path not in by_path, (
            f"checked_endpoints contains duplicate entry for path {path!r}"
        )
        by_path[path] = entry

        assert isinstance(entry["http_status"], int) and not isinstance(entry["http_status"], bool), (
            f"checked endpoint {path} http_status must be an integer HTTP status code"
        )
        assert isinstance(entry["api_status"], str), (
            f"checked endpoint {path} api_status must be a string parsed from the JSON body"
        )
        _assert_json_number(entry["latency_ms"], f"checked endpoint {path} latency_ms")
        assert entry["latency_ms"] >= 0, (
            f"checked endpoint {path} latency_ms must be greater than or equal to 0"
        )

    assert set(by_path) == {"/health", "/ready"}, (
        f"checked_endpoints must contain exactly /health and /ready, got {sorted(by_path)}"
    )

    assert by_path["/health"]["http_status"] == 200, (
        "/health http_status must be 200 as returned by curl/HTTP response"
    )
    assert by_path["/health"]["api_status"] == "healthy", (
        "/health api_status must be 'healthy' from the JSON response body"
    )

    assert by_path["/ready"]["http_status"] == 503, (
        "/ready http_status must be 503; do not treat curl exit code 0 as HTTP success"
    )
    assert by_path["/ready"]["api_status"] == "not_ready", (
        "/ready api_status must be 'not_ready' from the JSON response body"
    )


def test_version_and_recent_incidents_match_api_ground_truth_exactly():
    report = _load_report()

    assert report["version"] == EXPECTED_VERSION, (
        "report.version must exactly match the parsed JSON body from /version"
    )
    assert report["recent_incidents"] == EXPECTED_RECENT_INCIDENTS, (
        "report.recent_incidents must exactly match the parsed JSON array from /incidents/recent"
    )


def test_metrics_contain_required_numeric_prometheus_values():
    report = _load_report()
    metrics = report["metrics"]

    assert isinstance(metrics, dict), "report.metrics must be a JSON object"

    required = {
        "uptime_seconds": 86442,
        "request_success_total": 128903,
        "request_error_total": 7,
    }
    for key, expected_value in required.items():
        assert key in metrics, f"report.metrics is missing required key {key!r}"
        _assert_json_number(metrics[key], f"report.metrics.{key}")
        assert metrics[key] == expected_value, (
            f"report.metrics.{key} must be numeric value {expected_value}, got {metrics[key]!r}"
        )

    assert metrics["request_error_total"] == 7, (
        "request_error_total must be 7, which is a semantic reason overall_status is degraded"
    )


def test_verification_object_has_exact_keys_and_required_truth_values():
    report = _load_report()
    verification = report["verification"]

    _assert_exact_keys(
        verification,
        {"checked_with_curl", "artifact_valid_json", "semantic_checks_passed", "notes"},
        "report.verification",
    )

    assert verification["checked_with_curl"] is True, (
        "report.verification.checked_with_curl must be true"
    )
    assert verification["artifact_valid_json"] is True, (
        "report.verification.artifact_valid_json must be true"
    )
    assert verification["semantic_checks_passed"] is True, (
        "report.verification.semantic_checks_passed must be true"
    )

    notes = verification["notes"]
    assert isinstance(notes, str) and notes.strip(), (
        "report.verification.notes must be a nonempty string"
    )
    assert "HTTP status" in notes, (
        "report.verification.notes must mention 'HTTP status'"
    )
    assert "response bodies" in notes, (
        "report.verification.notes must mention 'response bodies'"
    )


def test_verification_log_exists_and_contains_exactly_four_required_lines():
    assert LOG_PATH.exists(), (
        "Missing verification log: /home/user/sre-uptime-check/verification.log"
    )
    assert LOG_PATH.is_file(), (
        "Expected /home/user/sre-uptime-check/verification.log to be a regular file"
    )

    actual = LOG_PATH.read_text(encoding="utf-8")
    assert actual == EXPECTED_LOG_TEXT, (
        "verification.log must contain exactly four required lines with no extra or missing lines:\n"
        f"{EXPECTED_LOG_TEXT!r}\n"
        f"Actual content was:\n{actual!r}"
    )