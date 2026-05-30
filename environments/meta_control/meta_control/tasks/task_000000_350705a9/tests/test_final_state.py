# test_final_state.py
from pathlib import Path
import json
import math
import pytest


OUTPUT_FILE = Path("/home/user/capacity_planner/outputs/overloaded_services.json")

EXPECTED_FIELDS = {"service", "team", "tier", "cpu_ratio", "memory_ratio", "reason"}

EXPECTED_REPORT = [
    {
        "service": "api-gateway",
        "team": "platform",
        "tier": "gold",
        "cpu_ratio": 0.8,
        "memory_ratio": 0.732,
        "reason": "cpu",
    },
    {
        "service": "billing-worker",
        "team": "finance",
        "tier": "silver",
        "cpu_ratio": 0.6,
        "memory_ratio": 0.928,
        "reason": "memory",
    },
    {
        "service": "catalog-search",
        "team": "commerce",
        "tier": "gold",
        "cpu_ratio": 0.775,
        "memory_ratio": 0.854,
        "reason": "memory",
    },
    {
        "service": "email-sender",
        "team": "growth",
        "tier": "bronze",
        "cpu_ratio": 0.81,
        "memory_ratio": 0.586,
        "reason": "cpu",
    },
    {
        "service": "image-resizer",
        "team": "media",
        "tier": "silver",
        "cpu_ratio": 0.84,
        "memory_ratio": 0.846,
        "reason": "cpu",
    },
    {
        "service": "metrics-rollup",
        "team": "platform",
        "tier": "bronze",
        "cpu_ratio": 0.813,
        "memory_ratio": 0.911,
        "reason": "cpu,memory",
    },
    {
        "service": "recommendation-api",
        "team": "ml",
        "tier": "gold",
        "cpu_ratio": 0.75,
        "memory_ratio": 0.895,
        "reason": "memory",
    },
    {
        "service": "session-store",
        "team": "platform",
        "tier": "gold",
        "cpu_ratio": 0.867,
        "memory_ratio": 0.814,
        "reason": "cpu",
    },
]


@pytest.fixture(scope="module")
def parsed_output():
    assert OUTPUT_FILE.exists(), f"Expected output file was not created: {OUTPUT_FILE}"
    assert OUTPUT_FILE.is_file(), f"Expected output path exists but is not a file: {OUTPUT_FILE}"

    try:
        text = OUTPUT_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise AssertionError(f"Output file exists but is not readable: {OUTPUT_FILE}: {exc}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Output file is not valid parseable JSON: {OUTPUT_FILE}: {exc}") from exc

    return data


def test_output_exists_and_root_is_array(parsed_output):
    assert isinstance(parsed_output, list), (
        "Output JSON top-level value must be an array/list, not "
        f"{type(parsed_output).__name__}"
    )


def test_output_has_exact_number_of_services(parsed_output):
    expected_services = [item["service"] for item in EXPECTED_REPORT]
    actual_services = [
        item.get("service") if isinstance(item, dict) else None for item in parsed_output
    ]

    assert len(parsed_output) == len(EXPECTED_REPORT), (
        "Output array has the wrong number of service objects. "
        f"Expected exactly {len(EXPECTED_REPORT)} services {expected_services}, "
        f"but found {len(parsed_output)} entries {actual_services}. "
        "Do not include non-overloaded services, orphan usage-only services, or omit overloaded services."
    )


def test_every_item_is_object_with_exact_required_fields(parsed_output):
    for index, item in enumerate(parsed_output):
        assert isinstance(item, dict), (
            f"Output array item at index {index} must be a JSON object, "
            f"but found {type(item).__name__}: {item!r}"
        )

        actual_fields = set(item)
        assert actual_fields == EXPECTED_FIELDS, (
            f"Object for service {item.get('service', '<missing service>')!r} has incorrect fields. "
            f"Expected exactly {sorted(EXPECTED_FIELDS)}, found {sorted(actual_fields)}. "
            "Do not add metadata, omit required fields, or use alternate field names."
        )


def test_services_are_sorted_alphabetically_and_exactly_expected(parsed_output):
    actual_services = [item["service"] for item in parsed_output]
    expected_services = [item["service"] for item in EXPECTED_REPORT]

    assert actual_services == sorted(actual_services), (
        "Output array is not sorted by service in ascending alphabetical order. "
        f"Actual order: {actual_services}"
    )

    assert actual_services == expected_services, (
        "Output contains the wrong services or wrong service ordering. "
        f"Expected {expected_services}, found {actual_services}. "
        "Remember to ignore orphan-debug-job and exclude inventory-sync and report-export."
    )


def test_orphan_and_non_overloaded_services_are_absent(parsed_output):
    actual_services = {item["service"] for item in parsed_output}

    forbidden_services = {
        "orphan-debug-job": "it is missing from services.csv and must not be joined into the report",
        "inventory-sync": "both raw CPU and memory ratios are below the required thresholds",
        "report-export": "both raw CPU and memory ratios are below the required thresholds",
    }

    for service, reason in forbidden_services.items():
        assert service not in actual_services, (
            f"{service!r} must not appear in the output because {reason}."
        )


def test_exact_report_semantics(parsed_output):
    assert parsed_output == EXPECTED_REPORT, (
        "Parsed output JSON does not exactly match the expected final report. "
        "Check service filtering, ordering, field names, team/tier values, rounded ratios, and reason strings."
    )


def test_ratio_fields_are_json_numbers_not_strings_or_other_types(parsed_output):
    for item in parsed_output:
        service = item["service"]
        for field in ("cpu_ratio", "memory_ratio"):
            value = item[field]
            assert isinstance(value, (int, float)) and not isinstance(value, bool), (
                f"{field} for service {service!r} must be a JSON number, "
                f"not {type(value).__name__}: {value!r}"
            )
            assert math.isfinite(value), (
                f"{field} for service {service!r} must be a finite JSON number, found {value!r}"
            )


def test_expected_reason_edge_cases(parsed_output):
    by_service = {item["service"]: item for item in parsed_output}

    assert by_service["image-resizer"]["reason"] == "cpu", (
        "image-resizer reason must be 'cpu'. Its raw memory ratio is below 0.85 "
        "even though the rounded memory_ratio is 0.846; threshold membership must be based on raw ratios."
    )

    assert by_service["catalog-search"]["reason"] == "memory", (
        "catalog-search reason must be 'memory' because its raw memory ratio meets the threshold "
        "and its raw CPU ratio does not."
    )

    assert by_service["metrics-rollup"]["reason"] == "cpu,memory", (
        "metrics-rollup reason must be 'cpu,memory' because both raw CPU and memory ratios meet thresholds."
    )