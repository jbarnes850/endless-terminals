# test_final_state.py
from pathlib import Path
import os
import re

REPORT_FILE = Path("/home/user/edge_diagnostics/reports/connectivity_report.txt")
INVENTORY_FILE = Path("/home/user/edge_diagnostics/device_inventory.txt")
REPORTS_DIR = Path("/home/user/edge_diagnostics/reports")

EXPECTED_LINES = [
    "EDGE CONNECTIVITY REPORT",
    "Inventory: /home/user/edge_diagnostics/device_inventory.txt",
    "Devices checked: 4",
    "Reachable: 2",
    "Unreachable: 2",
]

EXPECTED_CONTENT = "\n".join(EXPECTED_LINES) + "\n"


def _read_report_bytes():
    assert REPORT_FILE.exists(), (
        "Diagnostic report was not created. "
        f"Expected file at exactly: {REPORT_FILE}"
    )
    assert REPORT_FILE.is_file(), (
        "Diagnostic report path exists but is not a regular file. "
        f"Path checked: {REPORT_FILE}"
    )
    return REPORT_FILE.read_bytes()


def _read_report_text():
    data = _read_report_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(
            "Diagnostic report is not valid plain UTF-8 text. "
            f"Path checked: {REPORT_FILE}"
        ) from exc


def _parse_count_line(line, label):
    prefix = f"{label}: "
    assert line.startswith(prefix), (
        f"Report line for {label!r} has the wrong format. "
        f"Expected prefix {prefix!r}, got line {line!r}."
    )
    value_text = line[len(prefix):]
    assert re.fullmatch(r"\d+", value_text), (
        f"Report count for {label!r} must be a non-negative integer, "
        f"got {value_text!r} in line {line!r}."
    )
    return int(value_text)


def test_report_file_exists_at_exact_required_path():
    assert REPORTS_DIR.exists(), (
        f"Reports directory is missing: {REPORTS_DIR}. "
        "The final report cannot be considered complete without this directory."
    )
    assert REPORTS_DIR.is_dir(), (
        f"Reports path exists but is not a directory: {REPORTS_DIR}"
    )

    assert REPORT_FILE.exists(), (
        "The agent appears to have stopped before creating the required diagnostic report. "
        f"Missing file: {REPORT_FILE}"
    )
    assert REPORT_FILE.is_file(), (
        f"The required report path exists but is not a regular file: {REPORT_FILE}"
    )


def test_report_is_valid_utf8_plain_text_with_exactly_five_lines():
    text = _read_report_text()

    assert "\x00" not in text, (
        "Diagnostic report contains NUL bytes, so it is not plain text as required. "
        f"Path checked: {REPORT_FILE}"
    )

    lines = text.splitlines()
    assert len(lines) == 5, (
        "Diagnostic report must contain exactly 5 lines and no additional lines. "
        f"Found {len(lines)} line(s) in {REPORT_FILE}: {lines!r}"
    )

    assert text.endswith("\n") or text == "\n".join(EXPECTED_LINES), (
        "Diagnostic report must be plain text with exactly the required five logical lines; "
        "unexpected trailing data or line termination was found."
    )


def test_report_contents_match_required_final_deliverable_exactly():
    text = _read_report_text()
    lines = text.splitlines()

    assert lines == EXPECTED_LINES, (
        "Diagnostic report contents do not match the required final state exactly.\n"
        f"Path checked: {REPORT_FILE}\n"
        f"Expected lines: {EXPECTED_LINES!r}\n"
        f"Actual lines:   {lines!r}"
    )


def test_report_has_no_extra_leading_or_trailing_spaces_on_any_line():
    text = _read_report_text()
    lines = text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        assert line == line.strip(" \t\r"), (
            f"Report line {line_number} has extra leading or trailing whitespace: {line!r}"
        )


def test_report_individual_lines_are_exactly_correct():
    text = _read_report_text()
    lines = text.splitlines()

    assert len(lines) == 5, (
        f"Cannot validate individual report lines because expected 5 lines, found {len(lines)}."
    )

    for index, expected in enumerate(EXPECTED_LINES, start=1):
        actual = lines[index - 1]
        assert actual == expected, (
            f"Report line {index} is incorrect.\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {actual!r}"
        )


def test_report_counts_are_internally_consistent():
    text = _read_report_text()
    lines = text.splitlines()

    assert len(lines) == 5, (
        f"Cannot check count consistency because report must have exactly 5 lines, found {len(lines)}."
    )

    devices_checked = _parse_count_line(lines[2], "Devices checked")
    reachable = _parse_count_line(lines[3], "Reachable")
    unreachable = _parse_count_line(lines[4], "Unreachable")

    assert reachable + unreachable == devices_checked, (
        "Report counts are internally inconsistent: "
        f"Reachable ({reachable}) + Unreachable ({unreachable}) "
        f"does not equal Devices checked ({devices_checked})."
    )

    assert devices_checked == 4, (
        f"Devices checked count is wrong. Expected 4 valid inventory entries, got {devices_checked}."
    )
    assert reachable == 2, (
        f"Reachable count is wrong. Expected 2 reachable endpoints, got {reachable}."
    )
    assert unreachable == 2, (
        f"Unreachable count is wrong. Expected 2 unreachable endpoints, got {unreachable}."
    )


def test_inventory_still_exists_and_supports_expected_counts():
    assert INVENTORY_FILE.exists(), (
        f"Inventory file is missing after task completion: {INVENTORY_FILE}"
    )
    assert INVENTORY_FILE.is_file(), (
        f"Inventory path is not a regular file after task completion: {INVENTORY_FILE}"
    )
    assert os.access(INVENTORY_FILE, os.R_OK), (
        f"Inventory file is not readable after task completion: {INVENTORY_FILE}"
    )

    try:
        inventory_text = INVENTORY_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f"Inventory file is not valid UTF-8 after task completion: {INVENTORY_FILE}"
        ) from exc

    entries = [
        line.split()
        for line in inventory_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    expected_entries = [
        ["gateway-alpha", "127.0.0.1"],
        ["sensor-temp-01", "localhost"],
        ["camera-yard-03", "192.0.2.77"],
        ["meter-east-09", "198.51.100.42"],
    ]

    assert entries == expected_entries, (
        "Inventory entries do not match the truth data used to compute the required report. "
        f"Expected {expected_entries!r}, found {entries!r}."
    )