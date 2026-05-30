# test_final_state.py
import json
from pathlib import Path


REPORT_PATH = Path("/home/user/alert_env_audit/out/alert_matrix.json")
VERIFICATION_LOG_PATH = Path("/home/user/alert_env_audit/out/verification.log")

EXPECTED_TOP_LEVEL_KEYS = [
    "service",
    "generated_from",
    "effective_environment",
    "alerts",
    "summary",
]

EXPECTED_GENERATED_FROM = [
    "/home/user/alert_env_audit/env/.env.base",
    "/home/user/alert_env_audit/env/.env.shared",
    "/home/user/alert_env_audit/env/.env.production",
    "/home/user/alert_env_audit/env/.env.local",
]

EXPECTED_EFFECTIVE_ENVIRONMENT_KEYS = [
    "ALERT_CHANNELS",
    "ALERT_CRITICAL_THRESHOLD",
    "ALERT_LATENCY_MS",
    "ALERT_OWNER",
    "ALERT_WARNING_THRESHOLD",
    "ENVIRONMENT",
    "ESCALATION_MINUTES",
    "LOG_LEVEL",
    "METRICS_BACKEND",
    "PAGER_ROTATION",
    "SERVICE_NAME",
]

EXPECTED_EFFECTIVE_ENVIRONMENT = {
    "ALERT_CHANNELS": "pagerduty, slack-checkout, email",
    "ALERT_CRITICAL_THRESHOLD": "0.97",
    "ALERT_LATENCY_MS": "375",
    "ALERT_OWNER": "checkout-oncall",
    "ALERT_WARNING_THRESHOLD": "0.82",
    "ENVIRONMENT": "production",
    "ESCALATION_MINUTES": "10",
    "LOG_LEVEL": "error",
    "METRICS_BACKEND": "managed-prometheus",
    "PAGER_ROTATION": "checkout-prod",
    "SERVICE_NAME": "checkout-api",
}

EXPECTED_ALERT_KEYS = [
    "name",
    "metric",
    "threshold",
    "severity",
    "channels",
    "owner",
    "escalation_minutes",
    "pager_rotation",
]

EXPECTED_ALERTS = [
    {
        "name": "High error ratio",
        "metric": "http_error_ratio",
        "threshold": 0.97,
        "severity": "critical",
        "channels": ["pagerduty", "slack-checkout", "email"],
        "owner": "checkout-oncall",
        "escalation_minutes": 10,
        "pager_rotation": "checkout-prod",
    },
    {
        "name": "Warning error ratio",
        "metric": "http_error_ratio",
        "threshold": 0.82,
        "severity": "warning",
        "channels": ["pagerduty", "slack-checkout", "email"],
        "owner": "checkout-oncall",
        "escalation_minutes": 10,
        "pager_rotation": "checkout-prod",
    },
    {
        "name": "Checkout latency p95",
        "metric": "http_request_duration_p95_ms",
        "threshold": 375,
        "severity": "warning",
        "channels": ["pagerduty", "slack-checkout", "email"],
        "owner": "checkout-oncall",
        "escalation_minutes": 10,
        "pager_rotation": "checkout-prod",
    },
    {
        "name": "Queue saturation",
        "metric": "checkout_queue_saturation",
        "threshold": 0.82,
        "severity": "warning",
        "channels": ["pagerduty", "slack-checkout", "email"],
        "owner": "checkout-oncall",
        "escalation_minutes": 10,
        "pager_rotation": "checkout-prod",
    },
]

EXPECTED_SUMMARY_KEYS = [
    "enabled_alert_count",
    "disabled_rule_count",
    "critical_alert_count",
    "warning_alert_count",
    "channels_count",
    "uses_local_override",
]

EXPECTED_SUMMARY = {
    "enabled_alert_count": 4,
    "disabled_rule_count": 1,
    "critical_alert_count": 1,
    "warning_alert_count": 3,
    "channels_count": 3,
    "uses_local_override": True,
}

EXPECTED_VERIFICATION_LOG = (
    "artifact_exists=yes\n"
    "json_valid=yes\n"
    "top_level_keys=service,generated_from,effective_environment,alerts,summary\n"
    "enabled_alert_count=4\n"
    "verified=yes\n"
)


def load_report():
    assert REPORT_PATH.exists(), f"Final audit report is missing: {REPORT_PATH}"
    assert REPORT_PATH.is_file(), f"Final audit report path exists but is not a file: {REPORT_PATH}"

    try:
        with REPORT_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Final audit report is not valid JSON: {REPORT_PATH}: {exc}") from exc


def test_report_file_exists_and_is_valid_single_json_object():
    report = load_report()
    assert isinstance(report, dict), (
        f"Final audit report must be a single JSON object at top level, got {type(report).__name__}."
    )


def test_top_level_keys_are_exact_and_in_required_order():
    report = load_report()
    actual_keys = list(report.keys())
    assert actual_keys == EXPECTED_TOP_LEVEL_KEYS, (
        "Top-level JSON keys are wrong or out of order.\n"
        f"Expected: {EXPECTED_TOP_LEVEL_KEYS}\n"
        f"Actual:   {actual_keys}"
    )


def test_service_and_generated_from_are_exact():
    report = load_report()

    assert report["service"] == "checkout-api", (
        "The report service must come from the final effective SERVICE_NAME value."
    )

    assert report["generated_from"] == EXPECTED_GENERATED_FROM, (
        "generated_from must contain exactly the four absolute dotenv input paths in load order.\n"
        f"Expected: {EXPECTED_GENERATED_FROM}\n"
        f"Actual:   {report['generated_from']!r}"
    )


def test_effective_environment_has_only_required_keys_in_sorted_order_with_later_overrides():
    report = load_report()
    effective_environment = report["effective_environment"]

    assert isinstance(effective_environment, dict), (
        "effective_environment must be a JSON object."
    )

    actual_keys = list(effective_environment.keys())
    assert actual_keys == EXPECTED_EFFECTIVE_ENVIRONMENT_KEYS, (
        "effective_environment keys are wrong or out of order. It must contain only the required "
        "keys sorted alphabetically.\n"
        f"Expected keys: {EXPECTED_EFFECTIVE_ENVIRONMENT_KEYS}\n"
        f"Actual keys:   {actual_keys}"
    )

    assert effective_environment == EXPECTED_EFFECTIVE_ENVIRONMENT, (
        "effective_environment does not match the expected dotenv result using later-file "
        "override precedence.\n"
        f"Expected: {EXPECTED_EFFECTIVE_ENVIRONMENT}\n"
        f"Actual:   {effective_environment}"
    )

    for key, value in effective_environment.items():
        assert isinstance(value, str), (
            f"effective_environment value for {key} must be a string, got {type(value).__name__}."
        )


def test_alerts_array_matches_enabled_csv_rules_in_order_with_exact_key_order_and_values():
    report = load_report()
    alerts = report["alerts"]

    assert isinstance(alerts, list), "alerts must be a JSON array."
    assert len(alerts) == 4, (
        "alerts must contain four enabled rules. Only the row whose trimmed enabled value is "
        "exactly 'false' should be skipped; the ' TRUE ' Queue saturation row is enabled."
    )

    for index, alert in enumerate(alerts):
        assert isinstance(alert, dict), (
            f"Alert at index {index} must be a JSON object, got {type(alert).__name__}."
        )
        actual_keys = list(alert.keys())
        assert actual_keys == EXPECTED_ALERT_KEYS, (
            f"Alert at index {index} has wrong keys or key order.\n"
            f"Expected: {EXPECTED_ALERT_KEYS}\n"
            f"Actual:   {actual_keys}"
        )

    assert alerts == EXPECTED_ALERTS, (
        "alerts array does not match the required enabled CSV rules, thresholds, channels, "
        "owner, escalation, pager rotation, or order.\n"
        f"Expected: {EXPECTED_ALERTS}\n"
        f"Actual:   {alerts}"
    )

    assert isinstance(alerts[0]["threshold"], float), (
        "Critical threshold '0.97' should be converted to a floating-point number."
    )
    assert isinstance(alerts[1]["threshold"], float), (
        "Warning threshold '0.82' should be converted to a floating-point number."
    )
    assert isinstance(alerts[2]["threshold"], int), (
        "Latency threshold '375' should be converted to an integer."
    )
    assert isinstance(alerts[3]["threshold"], float), (
        "Queue saturation warning threshold '0.82' should be converted to a floating-point number."
    )

    for index, alert in enumerate(alerts):
        assert isinstance(alert["channels"], list), (
            f"Alert at index {index} has channels as {type(alert['channels']).__name__}; "
            "channels must be a split array, not the raw comma-separated string."
        )


def test_summary_has_exact_keys_order_and_values():
    report = load_report()
    summary = report["summary"]

    assert isinstance(summary, dict), "summary must be a JSON object."

    actual_keys = list(summary.keys())
    assert actual_keys == EXPECTED_SUMMARY_KEYS, (
        "summary keys are wrong or out of order.\n"
        f"Expected: {EXPECTED_SUMMARY_KEYS}\n"
        f"Actual:   {actual_keys}"
    )

    assert summary == EXPECTED_SUMMARY, (
        "summary values are incorrect. Check enabled/disabled counts, severity counts, "
        "channels_count, and uses_local_override.\n"
        f"Expected: {EXPECTED_SUMMARY}\n"
        f"Actual:   {summary}"
    )

    assert summary["uses_local_override"] is True, (
        "uses_local_override must be true because .env.local changes LOG_LEVEL, "
        "ALERT_CRITICAL_THRESHOLD, ALERT_CHANNELS, ALERT_OWNER, and ESCALATION_MINUTES."
    )


def test_verification_log_exists_and_has_exact_required_contents():
    assert VERIFICATION_LOG_PATH.exists(), (
        f"Verification log is missing: {VERIFICATION_LOG_PATH}"
    )
    assert VERIFICATION_LOG_PATH.is_file(), (
        f"Verification log path exists but is not a file: {VERIFICATION_LOG_PATH}"
    )

    actual = VERIFICATION_LOG_PATH.read_text(encoding="utf-8")
    assert actual == EXPECTED_VERIFICATION_LOG, (
        "verification.log does not have the exact required five lines.\n"
        f"Expected:\n{EXPECTED_VERIFICATION_LOG!r}\n"
        f"Actual:\n{actual!r}"
    )


def test_verification_log_claims_match_actual_report_state():
    report = load_report()
    log_lines = VERIFICATION_LOG_PATH.read_text(encoding="utf-8").splitlines()

    parsed_log = {}
    for line in log_lines:
        assert "=" in line, f"Malformed verification.log line without '=': {line!r}"
        key, value = line.split("=", 1)
        parsed_log[key] = value

    assert parsed_log.get("artifact_exists") == "yes", (
        "verification.log must record artifact_exists=yes because alert_matrix.json exists."
    )
    assert parsed_log.get("json_valid") == "yes", (
        "verification.log must record json_valid=yes because alert_matrix.json parses as JSON."
    )
    assert parsed_log.get("top_level_keys") == ",".join(list(report.keys())), (
        "verification.log top_level_keys must reflect the actual top-level key order in "
        "alert_matrix.json."
    )
    assert parsed_log.get("enabled_alert_count") == str(report["summary"]["enabled_alert_count"]), (
        "verification.log enabled_alert_count must match summary.enabled_alert_count in "
        "alert_matrix.json."
    )
    assert parsed_log.get("verified") == "yes", (
        "verification.log must end with verified=yes only after the artifact is fully correct."
    )