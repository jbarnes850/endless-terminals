# test_final_state.py
import json
import math
from pathlib import Path

import pytest


DBADMIN = Path("/home/user/dbadmin")
PROGRESS_LOG = Path("/home/user/dbadmin/progress.log")
DECISION_JSON = Path("/home/user/dbadmin/optimization_decision.json")

EXPECTED_CANDIDATES = [
    "idx_tickets_status_created",
    "idx_tickets_customer_status",
    "idx_tickets_assignee_created",
]

EXPECTED_MEASUREMENTS = {
    "idx_tickets_status_created": 18.742,
    "idx_tickets_customer_status": 11.386,
    "idx_tickets_assignee_created": 26.913,
}

EXPECTED_CHOSEN_INDEX = "idx_tickets_customer_status"
EXPECTED_REJECTED_INDEXES = [
    "idx_tickets_assignee_created",
    "idx_tickets_status_created",
]


def assert_file_exists(path: Path) -> None:
    assert path.exists(), f"Required artifact {path} does not exist"
    assert path.is_file(), f"Required artifact {path} exists but is not a regular file"


def read_utf8_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Required artifact {path} is not valid UTF-8 text: {exc}")


def assert_exact_float(actual, expected: float, context: str) -> None:
    assert isinstance(actual, (int, float)) and not isinstance(actual, bool), (
        f"{context} must be a JSON numeric value equal to {expected}, "
        f"but got {actual!r} of type {type(actual).__name__}"
    )
    assert math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1e-12), (
        f"{context} has wrong measured median latency. "
        f"Expected {expected}, got {actual!r}"
    )


def load_decision_json() -> dict:
    assert_file_exists(DECISION_JSON)
    raw = read_utf8_text(DECISION_JSON)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"Required artifact {DECISION_JSON} is not valid JSON: {exc}\n"
            f"File contents were:\n{raw}"
        )
    assert isinstance(data, dict), (
        f"{DECISION_JSON} must contain a top-level JSON object, "
        f"but parsed as {type(data).__name__}"
    )
    return data


def test_progress_log_exists_and_has_exact_four_non_empty_lines():
    assert_file_exists(PROGRESS_LOG)
    text = read_utf8_text(PROGRESS_LOG)

    all_lines = text.splitlines()
    non_empty_lines = [line for line in all_lines if line.strip()]

    assert len(non_empty_lines) == 4, (
        f"{PROGRESS_LOG} must contain exactly four non-empty lines, "
        f"but found {len(non_empty_lines)} non-empty lines: {non_empty_lines!r}"
    )

    assert all(line == line.strip() for line in non_empty_lines), (
        f"{PROGRESS_LOG} should be a compact plain-text log without leading or "
        f"trailing whitespace on non-empty lines. Lines were: {non_empty_lines!r}"
    )


def test_progress_log_hypothesis_line_lists_all_candidates_in_required_format():
    lines = [line for line in read_utf8_text(PROGRESS_LOG).splitlines() if line.strip()]
    hypothesis = lines[0]

    assert hypothesis.startswith("hypothesis: "), (
        f"Line 1 of {PROGRESS_LOG} must start exactly with 'hypothesis: ', "
        f"but was: {hypothesis!r}"
    )

    expected_line = "hypothesis: " + ", ".join(EXPECTED_CANDIDATES)
    assert hypothesis == expected_line, (
        f"Line 1 of {PROGRESS_LOG} must list the three candidate index names "
        f"separated by commas and spaces in the task order.\n"
        f"Expected: {expected_line!r}\n"
        f"Actual:   {hypothesis!r}"
    )


@pytest.mark.parametrize(
    "line_number,candidate,median_text",
    [
        (2, "idx_tickets_status_created", "median_ms=18.742"),
        (3, "idx_tickets_customer_status", "median_ms=11.386"),
        (4, "idx_tickets_assignee_created", "median_ms=26.913"),
    ],
)
def test_progress_log_evidence_lines_contain_required_measurements(
    line_number, candidate, median_text
):
    lines = [line for line in read_utf8_text(PROGRESS_LOG).splitlines() if line.strip()]
    line = lines[line_number - 1]

    assert line.startswith("evidence: "), (
        f"Line {line_number} of {PROGRESS_LOG} must start with 'evidence: ', "
        f"but was: {line!r}"
    )
    assert candidate in line, (
        f"Line {line_number} of {PROGRESS_LOG} must summarize evidence for "
        f"{candidate}, but the candidate name was missing. Line was: {line!r}"
    )
    assert median_text in line, (
        f"Line {line_number} of {PROGRESS_LOG} must include the measured latency "
        f"{median_text} reported by the probe. Line was: {line!r}"
    )


def test_decision_json_has_exact_required_top_level_structure():
    data = load_decision_json()

    expected_keys = {
        "chosen_index",
        "rejected_indexes",
        "decision_basis",
        "verified",
    }
    assert set(data.keys()) == expected_keys, (
        f"{DECISION_JSON} must contain exactly the top-level keys "
        f"{sorted(expected_keys)}, but found {sorted(data.keys())}"
    )

    assert isinstance(data["decision_basis"], dict), (
        f"{DECISION_JSON} field 'decision_basis' must be a JSON object, "
        f"but got {type(data['decision_basis']).__name__}"
    )

    expected_basis_keys = {"metric", "lower_is_better", "measurements"}
    actual_basis_keys = set(data["decision_basis"].keys())
    assert actual_basis_keys == expected_basis_keys, (
        f"{DECISION_JSON} field 'decision_basis' must contain exactly the keys "
        f"{sorted(expected_basis_keys)}, but found {sorted(actual_basis_keys)}"
    )

    measurements = data["decision_basis"]["measurements"]
    assert isinstance(measurements, dict), (
        f"{DECISION_JSON} field 'decision_basis.measurements' must be a JSON "
        f"object, but got {type(measurements).__name__}"
    )
    assert set(measurements.keys()) == set(EXPECTED_CANDIDATES), (
        f"{DECISION_JSON} field 'decision_basis.measurements' must contain "
        f"exactly the three candidate keys {EXPECTED_CANDIDATES}, "
        f"but found {sorted(measurements.keys())}"
    )


def test_decision_json_records_exact_probe_measurements_and_metric_semantics():
    data = load_decision_json()
    basis = data["decision_basis"]

    assert basis["metric"] == "median_ms", (
        f"{DECISION_JSON} decision_basis.metric must be exactly 'median_ms', "
        f"but was {basis['metric']!r}"
    )
    assert basis["lower_is_better"] is True, (
        f"{DECISION_JSON} decision_basis.lower_is_better must be JSON boolean "
        f"true, but was {basis['lower_is_better']!r}"
    )

    measurements = basis["measurements"]
    for candidate, expected_value in EXPECTED_MEASUREMENTS.items():
        assert_exact_float(
            measurements[candidate],
            expected_value,
            f"{DECISION_JSON} decision_basis.measurements.{candidate}",
        )


def test_decision_json_selects_lowest_median_candidate_and_rejects_others_sorted():
    data = load_decision_json()

    assert data["chosen_index"] == EXPECTED_CHOSEN_INDEX, (
        f"{DECISION_JSON} chosen_index is wrong. The lowest measured median_ms "
        f"is 11.386 for {EXPECTED_CHOSEN_INDEX}, so chosen_index must be "
        f"{EXPECTED_CHOSEN_INDEX!r}; got {data['chosen_index']!r}"
    )

    assert data["rejected_indexes"] == EXPECTED_REJECTED_INDEXES, (
        f"{DECISION_JSON} rejected_indexes must contain the two non-winning "
        f"candidates sorted alphabetically.\n"
        f"Expected: {EXPECTED_REJECTED_INDEXES!r}\n"
        f"Actual:   {data['rejected_indexes']!r}"
    )

    assert data["verified"] is True, (
        f"{DECISION_JSON} verified must be JSON boolean true, "
        f"but was {data['verified']!r}"
    )

    measurements = data["decision_basis"]["measurements"]
    chosen_latency = measurements[data["chosen_index"]]
    losing_latencies = {
        index: measurements[index]
        for index in EXPECTED_CANDIDATES
        if index != data["chosen_index"]
    }

    assert all(chosen_latency < latency for latency in losing_latencies.values()), (
        f"{DECISION_JSON} chosen_index is not justified by the measured median_ms "
        f"values. Chosen {data['chosen_index']!r} has median_ms={chosen_latency!r}; "
        f"other measurements are {losing_latencies!r}"
    )