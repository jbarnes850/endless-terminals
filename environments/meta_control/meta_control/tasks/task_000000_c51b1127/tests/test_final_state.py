# test_final_state.py
from pathlib import Path

import pytest


SUMMARY_PATH = Path("/home/user/log-investigation/incident_summary.txt")

EXPECTED_LINES = [
    "incident_window=2024-04-18T14:00:00,2024-04-18T14:09:59",
    "top_error_path=/api/report/export",
    "error_count=9",
    "checked_candidates=4",
]

EXPECTED_CONTENT_NO_TRAILING_NEWLINE = "\n".join(EXPECTED_LINES)
EXPECTED_CONTENT_WITH_TRAILING_NEWLINE = EXPECTED_CONTENT_NO_TRAILING_NEWLINE + "\n"


def _read_summary_bytes():
    assert SUMMARY_PATH.exists(), (
        "Verification report is missing. Expected file to exist at absolute path: "
        f"{SUMMARY_PATH}"
    )
    assert SUMMARY_PATH.is_file(), (
        "Verification report path exists but is not a regular file: "
        f"{SUMMARY_PATH}"
    )
    try:
        return SUMMARY_PATH.read_bytes()
    except OSError as exc:
        pytest.fail(f"Could not read verification report at {SUMMARY_PATH}: {exc}")


def test_incident_summary_file_exists_and_is_readable():
    data = _read_summary_bytes()
    assert data is not None, f"Could not read report file at {SUMMARY_PATH}"


def test_incident_summary_is_valid_utf8_text():
    data = _read_summary_bytes()
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(
            f"Report file {SUMMARY_PATH} must be UTF-8/plain text, but decoding failed: {exc}"
        )


def test_incident_summary_has_exactly_four_nonblank_lines():
    text = _read_summary_bytes().decode("utf-8")

    lines = text.splitlines()
    assert len(lines) == 4, (
        f"Report must contain exactly 4 lines. Observed {len(lines)} line(s): "
        f"{lines!r}. Do not include headings, blank lines, or extra output."
    )

    blank_line_numbers = [
        index
        for index, line in enumerate(lines, start=1)
        if line == ""
    ]
    assert not blank_line_numbers, (
        "Report must not contain blank lines. Blank line number(s): "
        f"{blank_line_numbers!r}"
    )


def test_incident_summary_has_no_extra_trailing_blank_lines_or_content():
    text = _read_summary_bytes().decode("utf-8")

    assert text in {
        EXPECTED_CONTENT_NO_TRAILING_NEWLINE,
        EXPECTED_CONTENT_WITH_TRAILING_NEWLINE,
    }, (
        "Report content must be exactly the expected four lines. A single trailing "
        "newline after line 4 is acceptable, but extra blank lines, whitespace, "
        "headings, or explanations are not.\n"
        f"Expected exactly:\n{EXPECTED_CONTENT_NO_TRAILING_NEWLINE!r}\n"
        f"Observed:\n{text!r}"
    )


def test_incident_summary_line_1_incident_window_is_exact():
    lines = _read_summary_bytes().decode("utf-8").splitlines()
    assert len(lines) >= 1, "Report is missing line 1 for incident_window."

    assert lines[0] == EXPECTED_LINES[0], (
        "Line 1 must use the exact inclusive incident window timestamps shown in "
        "the task description.\n"
        f"Expected: {EXPECTED_LINES[0]!r}\n"
        f"Observed: {lines[0]!r}"
    )


def test_incident_summary_line_2_top_error_path_is_exact():
    lines = _read_summary_bytes().decode("utf-8").splitlines()
    assert len(lines) >= 2, "Report is missing line 2 for top_error_path."

    assert lines[1] == EXPECTED_LINES[1], (
        "Line 2 must identify the request path with the highest number of HTTP "
        "500 responses in the incident window. The correct leader is "
        "/api/report/export, not outside-window or non-500 distractors.\n"
        f"Expected: {EXPECTED_LINES[1]!r}\n"
        f"Observed: {lines[1]!r}"
    )


def test_incident_summary_line_3_error_count_is_exact():
    lines = _read_summary_bytes().decode("utf-8").splitlines()
    assert len(lines) >= 3, "Report is missing line 3 for error_count."

    assert lines[2] == EXPECTED_LINES[2], (
        "Line 3 must contain the exact count of HTTP 500 responses for "
        "/api/report/export within 2024-04-18T14:00:00 through "
        "2024-04-18T14:09:59 inclusive.\n"
        f"Expected: {EXPECTED_LINES[2]!r}\n"
        f"Observed: {lines[2]!r}"
    )


def test_incident_summary_line_4_checked_candidates_is_exact():
    lines = _read_summary_bytes().decode("utf-8").splitlines()
    assert len(lines) >= 4, "Report is missing line 4 for checked_candidates."

    assert lines[3] == EXPECTED_LINES[3], (
        "Line 4 must contain the number of distinct request paths with at least "
        "one HTTP 500 response in the incident window. The correct candidate "
        "count is 4.\n"
        f"Expected: {EXPECTED_LINES[3]!r}\n"
        f"Observed: {lines[3]!r}"
    )


def test_incident_summary_has_no_leading_or_trailing_whitespace_on_any_line():
    lines = _read_summary_bytes().decode("utf-8").splitlines()

    bad_lines = [
        (index, line)
        for index, line in enumerate(lines, start=1)
        if line != line.strip()
    ]
    assert not bad_lines, (
        "Report lines must not contain leading or trailing whitespace. "
        f"Offending line(s): {bad_lines!r}"
    )