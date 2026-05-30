# test_final_state.py
import ast
import csv
import re
from pathlib import Path

import pytest
import yaml


BASE = Path("/home/user/alerting-lab")
SERVICES_CSV = Path("/home/user/alerting-lab/input/services.csv")
GENERATOR = Path("/home/user/alerting-lab/tools/generate_alerts.py")
ALERT_RULES = Path("/home/user/alerting-lab/output/service_alerts.yml")
VERIFICATION_LOG = Path("/home/user/alerting-lab/output/verification.log")


EXPECTED_OBJECT = {
    "groups": [
        {
            "name": "generated-service-alerts",
            "rules": [
                {
                    "alert": "ServiceDown_checkout-api",
                    "expr": 'up{job="checkout-api"} == 0',
                    "for": "5m",
                    "labels": {
                        "severity": "critical",
                        "team": "payments",
                        "environment": "prod",
                    },
                    "annotations": {
                        "summary": "checkout-api is down",
                        "description": (
                            "Service checkout-api in prod has been down for 5m. "
                            "Notify payments."
                        ),
                    },
                },
                {
                    "alert": "ServiceDown_catalog-worker",
                    "expr": 'up{job="catalog-worker"} == 0',
                    "for": "10m",
                    "labels": {
                        "severity": "warning",
                        "team": "retail",
                        "environment": "prod",
                    },
                    "annotations": {
                        "summary": "catalog-worker is down",
                        "description": (
                            "Service catalog-worker in prod has been down for 10m. "
                            "Notify retail."
                        ),
                    },
                },
                {
                    "alert": "ServiceDown_fraud-scanner",
                    "expr": 'up{job="fraud-scanner"} == 0',
                    "for": "3m",
                    "labels": {
                        "severity": "critical",
                        "team": "risk",
                        "environment": "prod",
                    },
                    "annotations": {
                        "summary": "fraud-scanner is down",
                        "description": (
                            "Service fraud-scanner in prod has been down for 3m. "
                            "Notify risk."
                        ),
                    },
                },
                {
                    "alert": "ServiceDown_email-dispatcher",
                    "expr": 'up{job="email-dispatcher"} == 0',
                    "for": "15m",
                    "labels": {
                        "severity": "warning",
                        "team": "growth",
                        "environment": "staging",
                    },
                    "annotations": {
                        "summary": "email-dispatcher is down",
                        "description": (
                            "Service email-dispatcher in staging has been down for 15m. "
                            "Notify growth."
                        ),
                    },
                },
                {
                    "alert": "ServiceDown_inventory-sync",
                    "expr": 'up{job="inventory-sync"} == 0',
                    "for": "7m",
                    "labels": {
                        "severity": "critical",
                        "team": "supply",
                        "environment": "prod",
                    },
                    "annotations": {
                        "summary": "inventory-sync is down",
                        "description": (
                            "Service inventory-sync in prod has been down for 7m. "
                            "Notify supply."
                        ),
                    },
                },
            ],
        }
    ]
}

EXPECTED_VERIFICATION_LOG_LINES = [
    "command_completed=true",
    "artifact_exists=true",
    "yaml_valid=true",
    "rule_count=5",
    "semantic_check=passed",
]


def _read_csv_rows():
    assert SERVICES_CSV.exists(), f"Input CSV is missing: {SERVICES_CSV}"
    assert SERVICES_CSV.is_file(), f"Input CSV path exists but is not a file: {SERVICES_CSV}"

    with SERVICES_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows, f"Input CSV {SERVICES_CSV} contains no data rows"
    return rows


def _expected_object_from_csv():
    rows = _read_csv_rows()
    return {
        "groups": [
            {
                "name": "generated-service-alerts",
                "rules": [
                    {
                        "alert": f"ServiceDown_{row['service_name']}",
                        "expr": f'up{{job="{row["service_name"]}"}} == 0',
                        "for": row["window"],
                        "labels": {
                            "severity": row["severity"],
                            "team": row["team"],
                            "environment": row["environment"],
                        },
                        "annotations": {
                            "summary": f"{row['service_name']} is down",
                            "description": (
                                f"Service {row['service_name']} in {row['environment']} "
                                f"has been down for {row['window']}. Notify {row['team']}."
                            ),
                        },
                    }
                    for row in rows
                ],
            }
        ]
    }


@pytest.fixture(scope="module")
def parsed_alert_rules():
    assert ALERT_RULES.exists(), (
        f"Final alert rules file was not created: {ALERT_RULES}"
    )
    assert ALERT_RULES.is_file(), (
        f"Final alert rules path exists but is not a file: {ALERT_RULES}"
    )

    try:
        content = ALERT_RULES.read_text(encoding="utf-8")
    except OSError as exc:
        pytest.fail(f"Could not read final alert rules file {ALERT_RULES}: {exc}")

    assert content.strip(), f"Final alert rules file is empty: {ALERT_RULES}"

    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as exc:
        pytest.fail(f"Final alert rules file {ALERT_RULES} is not valid YAML: {exc}")


def test_alert_rules_yaml_matches_exact_expected_object(parsed_alert_rules):
    expected_from_csv = _expected_object_from_csv()

    assert expected_from_csv == EXPECTED_OBJECT, (
        "Test fixture mismatch: CSV-derived expected object no longer matches the "
        "privileged expected final object"
    )

    assert parsed_alert_rules == EXPECTED_OBJECT, (
        f"Parsed YAML from {ALERT_RULES} does not exactly match the required "
        "CSV-driven Prometheus alert rules object. Ensure all five CSV rows are "
        "included, no filtering remains, fields are exact, and rule order is "
        "checkout-api, catalog-worker, fraud-scanner, email-dispatcher, "
        "inventory-sync."
    )


def test_alert_rules_top_level_structure_is_exact(parsed_alert_rules):
    assert isinstance(parsed_alert_rules, dict), (
        f"Parsed YAML in {ALERT_RULES} must be a mapping at the top level"
    )
    assert set(parsed_alert_rules.keys()) == {"groups"}, (
        f"Top-level YAML keys in {ALERT_RULES} must be exactly {{'groups'}}"
    )

    groups = parsed_alert_rules["groups"]
    assert isinstance(groups, list), "Top-level 'groups' value must be a list"
    assert len(groups) == 1, (
        f"Expected exactly one alert group, found {len(groups)}"
    )

    group = groups[0]
    assert isinstance(group, dict), "The single group must be a mapping"
    assert set(group.keys()) == {"name", "rules"}, (
        "The single group must contain exactly the keys 'name' and 'rules'"
    )
    assert group["name"] == "generated-service-alerts", (
        "The alert group name must be exactly 'generated-service-alerts'"
    )
    assert isinstance(group["rules"], list), "Group 'rules' value must be a list"


def test_each_csv_service_appears_once_in_exact_csv_order(parsed_alert_rules):
    csv_rows = _read_csv_rows()
    expected_services = [row["service_name"] for row in csv_rows]
    rules = parsed_alert_rules["groups"][0]["rules"]
    actual_alerts = [rule.get("alert") for rule in rules]

    expected_alerts = [f"ServiceDown_{service}" for service in expected_services]
    assert actual_alerts == expected_alerts, (
        "Alert rules are missing services, include extras, or are in the wrong "
        f"order. Expected alerts in CSV order: {expected_alerts!r}; "
        f"actual alerts: {actual_alerts!r}"
    )

    assert len(actual_alerts) == len(set(actual_alerts)), (
        f"Each service must appear exactly once, but duplicate alerts were found: "
        f"{actual_alerts!r}"
    )


def test_each_rule_has_exact_required_fields_and_values(parsed_alert_rules):
    rules = parsed_alert_rules["groups"][0]["rules"]
    expected_rules = EXPECTED_OBJECT["groups"][0]["rules"]

    assert len(rules) == len(expected_rules), (
        f"Expected {len(expected_rules)} rules, found {len(rules)}"
    )

    for index, (actual, expected) in enumerate(zip(rules, expected_rules), start=1):
        assert isinstance(actual, dict), f"Rule #{index} must be a mapping"
        assert set(actual.keys()) == {
            "alert",
            "expr",
            "for",
            "labels",
            "annotations",
        }, (
            f"Rule #{index} has incorrect fields. Expected exactly "
            "'alert', 'expr', 'for', 'labels', and 'annotations'; "
            f"got {sorted(actual.keys())!r}"
        )

        assert actual == expected, (
            f"Rule #{index} for expected alert {expected['alert']!r} is incorrect. "
            f"Expected {expected!r}, got {actual!r}"
        )


def test_verification_log_exists_and_matches_exact_required_lines():
    assert VERIFICATION_LOG.exists(), (
        f"Verification log was not created: {VERIFICATION_LOG}"
    )
    assert VERIFICATION_LOG.is_file(), (
        f"Verification log path exists but is not a file: {VERIFICATION_LOG}"
    )

    actual_text = VERIFICATION_LOG.read_text(encoding="utf-8")
    actual_lines = actual_text.rstrip("\n").split("\n")

    assert actual_lines == EXPECTED_VERIFICATION_LOG_LINES, (
        f"Verification log {VERIFICATION_LOG} must contain exactly these five "
        f"lines: {EXPECTED_VERIFICATION_LOG_LINES!r}; got {actual_lines!r}"
    )

    assert "\r" not in actual_text, (
        f"Verification log {VERIFICATION_LOG} must be plain LF-delimited text, "
        "but CR characters were found"
    )


def test_verification_log_rule_count_matches_csv_data_rows():
    csv_row_count = len(_read_csv_rows())
    expected_rule_count_line = f"rule_count={csv_row_count}"

    actual_lines = VERIFICATION_LOG.read_text(encoding="utf-8").rstrip("\n").split("\n")

    assert actual_lines[3] == expected_rule_count_line, (
        f"Verification log rule count must match the number of CSV data rows. "
        f"Expected line 4 to be {expected_rule_count_line!r}; "
        f"got {actual_lines[3] if len(actual_lines) > 3 else '<missing>'!r}"
    )


def test_generator_no_longer_contains_enabled_or_priority_continue_filtering():
    assert GENERATOR.exists(), f"Generator script is missing: {GENERATOR}"
    assert GENERATOR.is_file(), f"Generator path exists but is not a file: {GENERATOR}"

    source = GENERATOR.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source, filename=str(GENERATOR))
    except SyntaxError as exc:
        pytest.fail(f"Generator script {GENERATOR} is not valid Python: {exc}")

    suspicious_filters = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            condition_source = ast.get_source_segment(source, node.test) or ""
            condition_mentions_filter_column = (
                re.search(r"\benabled\b", condition_source)
                or re.search(r"\bpriority\b", condition_source)
            )
            body_contains_continue = any(
                isinstance(child, ast.Continue) for child in ast.walk(ast.Module(body=node.body, type_ignores=[]))
            )
            if condition_mentions_filter_column and body_contains_continue:
                suspicious_filters.append(condition_source)

    assert not suspicious_filters, (
        f"Generator script {GENERATOR} still appears to skip CSV rows based on "
        f"'enabled' or 'priority': {suspicious_filters!r}. The final generator "
        "must include every CSV data row."
    )