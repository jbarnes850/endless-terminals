# test_final_state.py
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


BASE_DIR = Path("/home/user/ops-triage")
INCIDENTS_PATH = Path("/home/user/ops-triage/incidents.jsonl")
LINT_CONFIG_PATH = Path("/home/user/ops-triage/.markdownlint.json")
HELPER_PATH = Path("/home/user/ops-triage/check_markdown.py")
SUMMARY_PATH = Path("/home/user/ops-triage/INCIDENT_SUMMARY.md")
LOG_PATH = Path("/home/user/ops-triage/triage_doc_check.log")

EXPECTED_INCIDENTS = [
    {
        "incident_id": "INC-1042",
        "service": "checkout-api",
        "severity": "high",
        "started": "2026-02-14T09:12:00Z",
        "status": "investigating",
        "owner": "mira",
        "next_action": "compare error budget burn against the last deploy window",
    },
    {
        "incident_id": "INC-1043",
        "service": "search-indexer",
        "severity": "low",
        "started": "2026-02-14T09:40:00Z",
        "status": "resolved",
        "owner": "nolan",
        "next_action": "archive the temporary shard allocation notes",
    },
    {
        "incident_id": "INC-1044",
        "service": "billing-worker",
        "severity": "critical",
        "started": "2026-02-14T10:05:00Z",
        "status": "mitigating",
        "owner": "sana",
        "next_action": "confirm queue drain rate remains above the recovery threshold",
    },
    {
        "incident_id": "INC-1045",
        "service": "metrics-gateway",
        "severity": "medium",
        "started": "2026-02-14T10:22:00Z",
        "status": "monitoring",
        "owner": "devon",
        "next_action": "watch p95 ingest latency for two consecutive scrape intervals",
    },
    {
        "incident_id": "INC-1046",
        "service": "auth-session",
        "severity": "high",
        "started": "2026-02-14T10:31:00Z",
        "status": "investigating",
        "owner": "li",
        "next_action": "check whether token refresh failures correlate with cache evictions",
    },
]

EXPECTED_ACTIVE_ORDER = [
    {
        "incident_id": "INC-1044",
        "service": "billing-worker",
        "severity": "critical",
        "started": "2026-02-14T10:05:00Z",
        "status": "mitigating",
        "owner": "sana",
        "next_action": "confirm queue drain rate remains above the recovery threshold",
    },
    {
        "incident_id": "INC-1042",
        "service": "checkout-api",
        "severity": "high",
        "started": "2026-02-14T09:12:00Z",
        "status": "investigating",
        "owner": "mira",
        "next_action": "compare error budget burn against the last deploy window",
    },
    {
        "incident_id": "INC-1046",
        "service": "auth-session",
        "severity": "high",
        "started": "2026-02-14T10:31:00Z",
        "status": "investigating",
        "owner": "li",
        "next_action": "check whether token refresh failures correlate with cache evictions",
    },
    {
        "incident_id": "INC-1045",
        "service": "metrics-gateway",
        "severity": "medium",
        "started": "2026-02-14T10:22:00Z",
        "status": "monitoring",
        "owner": "devon",
        "next_action": "watch p95 ingest latency for two consecutive scrape intervals",
    },
]

EXPECTED_SUMMARY = """# Incident Summary

Generated triage summary for the current operations review.

## Active Incidents

| Incident | Service | Severity | Started | Status | Owner |
| --- | --- | --- | --- | --- | --- |
| INC-1044 | billing-worker | critical | 2026-02-14T10:05:00Z | mitigating | sana |
| INC-1042 | checkout-api | high | 2026-02-14T09:12:00Z | investigating | mira |
| INC-1046 | auth-session | high | 2026-02-14T10:31:00Z | investigating | li |
| INC-1045 | metrics-gateway | medium | 2026-02-14T10:22:00Z | monitoring | devon |

## Immediate Actions

- [ ] INC-1044: confirm queue drain rate remains above the recovery threshold
- [ ] INC-1042: compare error budget burn against the last deploy window
- [ ] INC-1046: check whether token refresh failures correlate with cache evictions
- [ ] INC-1045: watch p95 ingest latency for two consecutive scrape intervals

## Notes

Review unresolved incidents with assigned owners before the next handoff.
"""

EXPECTED_LOG = """generated=/home/user/ops-triage/INCIDENT_SUMMARY.md
lint=pass
active_incidents=4
"""


def read_text_required(path):
    assert path.exists(), f"Required final artifact is missing: {path}"
    assert path.is_file(), f"Required final artifact exists but is not a regular file: {path}"
    assert os.access(path, os.R_OK), f"Required final artifact is not readable: {path}"
    return path.read_text(encoding="utf-8")


def parse_markdown_table_row(line):
    assert line.startswith("|") and line.endswith("|"), f"Malformed Markdown table row: {line!r}"
    return [cell.strip() for cell in line.strip("|").split("|")]


def test_source_data_still_exists_and_was_not_corrupted():
    assert INCIDENTS_PATH.exists(), f"Source incident file is missing: {INCIDENTS_PATH}"
    assert INCIDENTS_PATH.is_file(), f"Source incident path is not a file: {INCIDENTS_PATH}"

    raw = INCIDENTS_PATH.read_text(encoding="utf-8")
    assert raw.endswith("\n"), f"Source incident file no longer ends with a newline: {INCIDENTS_PATH}"

    parsed = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError as exc:
            pytest.fail(f"Source incident file has invalid JSON at line {line_number}: {exc}")

    assert parsed == EXPECTED_INCIDENTS, (
        f"Source incident data in {INCIDENTS_PATH} was changed. The summary must be "
        "generated from the provided JSONL data without modifying it."
    )


def test_summary_file_exists_has_exact_required_content_and_final_newline():
    actual = read_text_required(SUMMARY_PATH)

    assert actual.endswith("\n"), (
        f"{SUMMARY_PATH} must end with a final newline to satisfy markdown lint rule MD047."
    )
    assert actual == EXPECTED_SUMMARY, (
        f"{SUMMARY_PATH} does not exactly match the required final Markdown runbook summary. "
        "Check headings, blank lines, table rows, unresolved incident ordering, bullet text, "
        "notes text, and trailing newline."
    )


def test_summary_omits_resolved_incident_and_contains_each_active_incident_once():
    text = read_text_required(SUMMARY_PATH)

    assert "INC-1043" not in text, (
        "Resolved incident INC-1043 appears in the final summary, but resolved incidents "
        "must be ignored entirely."
    )
    assert "search-indexer" not in text, (
        "Resolved service search-indexer appears in the final summary, but resolved "
        "incidents must be ignored entirely."
    )

    for incident in EXPECTED_ACTIVE_ORDER:
        incident_id = incident["incident_id"]
        occurrences = len(re.findall(rf"\b{re.escape(incident_id)}\b", text))
        assert occurrences == 2, (
            f"Active incident {incident_id} must appear exactly twice in {SUMMARY_PATH}: "
            f"once in the active-incidents table and once in the immediate-actions list. "
            f"Found {occurrences} occurrences."
        )


def test_active_incidents_table_has_exact_columns_rows_and_sort_order():
    lines = read_text_required(SUMMARY_PATH).splitlines()

    try:
        heading_index = lines.index("## Active Incidents")
    except ValueError:
        pytest.fail(f"{SUMMARY_PATH} is missing the '## Active Incidents' heading.")

    assert lines[heading_index + 1] == "", (
        "The Active Incidents heading must be followed by a blank line."
    )

    header_line = lines[heading_index + 2]
    separator_line = lines[heading_index + 3]
    data_lines = lines[heading_index + 4 : heading_index + 8]

    assert parse_markdown_table_row(header_line) == [
        "Incident",
        "Service",
        "Severity",
        "Started",
        "Status",
        "Owner",
    ], "The active-incidents table header columns are wrong or out of order."

    assert parse_markdown_table_row(separator_line) == ["---", "---", "---", "---", "---", "---"], (
        "The active-incidents table separator row must contain six '---' separator cells."
    )

    expected_rows = [
        [
            incident["incident_id"],
            incident["service"],
            incident["severity"],
            incident["started"],
            incident["status"],
            incident["owner"],
        ]
        for incident in EXPECTED_ACTIVE_ORDER
    ]
    actual_rows = [parse_markdown_table_row(line) for line in data_lines]

    assert actual_rows == expected_rows, (
        "The active-incidents table rows are incorrect. They must include exactly the four "
        "unresolved incidents sorted by severity critical, high, high, medium, preserving "
        "source order for the high-severity tie (INC-1042 before INC-1046), with all field "
        "values preserved exactly."
    )

    assert lines[heading_index + 8] == "", (
        "The active-incidents table must be followed by a blank line before the next heading."
    )
    assert lines[heading_index + 9] == "## Immediate Actions", (
        "Unexpected content after the active-incidents table; expected the Immediate Actions heading."
    )


def test_immediate_actions_are_exact_and_match_table_order():
    lines = read_text_required(SUMMARY_PATH).splitlines()

    try:
        heading_index = lines.index("## Immediate Actions")
    except ValueError:
        pytest.fail(f"{SUMMARY_PATH} is missing the '## Immediate Actions' heading.")

    assert lines[heading_index + 1] == "", (
        "The Immediate Actions heading must be followed by a blank line."
    )

    actual_bullets = lines[heading_index + 2 : heading_index + 6]
    expected_bullets = [
        f"- [ ] {incident['incident_id']}: {incident['next_action']}"
        for incident in EXPECTED_ACTIVE_ORDER
    ]

    assert actual_bullets == expected_bullets, (
        "The Immediate Actions bullet list is wrong. It must contain one unchecked bullet "
        "per active incident, in the same order as the table, using the exact format "
        "'- [ ] <incident_id>: <next_action>'."
    )

    assert lines[heading_index + 6] == "", (
        "The Immediate Actions bullet list must be followed by a blank line before Notes."
    )
    assert lines[heading_index + 7] == "## Notes", (
        "Unexpected content after the Immediate Actions list; expected the Notes heading."
    )


def test_verification_log_exists_and_matches_required_three_lines_exactly():
    actual = read_text_required(LOG_PATH)

    assert actual.endswith("\n"), (
        f"{LOG_PATH} must end with a final newline."
    )
    assert actual == EXPECTED_LOG, (
        f"{LOG_PATH} must contain exactly three lines:\n"
        "generated=/home/user/ops-triage/INCIDENT_SUMMARY.md\n"
        "lint=pass\n"
        "active_incidents=4\n"
    )

    lines = actual.splitlines()
    assert len(lines) == 3, (
        f"{LOG_PATH} must contain exactly three non-empty lines; found {len(lines)}."
    )


def test_markdown_passes_local_helper_lint_when_helper_is_available():
    if not HELPER_PATH.exists():
        pytest.skip(f"Optional local markdown helper is not present: {HELPER_PATH}")

    assert HELPER_PATH.is_file(), f"Local markdown helper exists but is not a file: {HELPER_PATH}"
    assert os.access(HELPER_PATH, os.X_OK), (
        f"Local markdown helper exists but is not executable: {HELPER_PATH}"
    )

    result = subprocess.run(
        [sys.executable, str(HELPER_PATH), str(SUMMARY_PATH)],
        cwd=str(BASE_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, (
        f"{SUMMARY_PATH} does not pass the local Markdown lint helper {HELPER_PATH}. "
        f"Exit code: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_markdown_structure_is_lint_friendly_independent_of_helper():
    lines = read_text_required(SUMMARY_PATH).splitlines()

    assert lines[0] == "# Incident Summary", (
        "Markdown lint rule MD041 requires the first line to be the top-level heading."
    )

    heading_indexes = [index for index, line in enumerate(lines) if line.startswith("#")]
    for index in heading_indexes:
        if index != 0:
            assert lines[index - 1] == "", (
                f"Heading {lines[index]!r} must be preceded by a blank line for MD022."
            )
        if index + 1 < len(lines):
            assert lines[index + 1] == "", (
                f"Heading {lines[index]!r} must be followed by a blank line for MD022."
            )

    table_header_index = lines.index("| Incident | Service | Severity | Started | Status | Owner |")
    assert table_header_index > 0 and lines[table_header_index - 1] == "", (
        "The Markdown table must be preceded by a blank line for MD058/MD032 compliance."
    )

    table_end_index = table_header_index + 5
    assert lines[table_end_index + 1] == "", (
        "The Markdown table must be followed by a blank line for MD058/MD032 compliance."
    )

    bullet_start_index = lines.index(
        "- [ ] INC-1044: confirm queue drain rate remains above the recovery threshold"
    )
    assert bullet_start_index > 0 and lines[bullet_start_index - 1] == "", (
        "The Immediate Actions list must be preceded by a blank line for MD032 compliance."
    )
    assert lines[bullet_start_index + 4] == "", (
        "The Immediate Actions list must be followed by a blank line for MD032 compliance."
    )