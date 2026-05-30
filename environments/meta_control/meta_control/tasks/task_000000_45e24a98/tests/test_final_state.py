# test_final_state.py
from pathlib import Path

import pytest


REPORT_PATH = Path("/home/user/backup_api_verification.log")

EXPECTED_LINES = [
    "endpoint=http://127.0.0.1:48731/api/v1/backups/latest",
    "http_status=200",
    "backup_id=bk-20240517-023000-prod",
    "database=customer_ledger",
    "verified=yes",
]

EXPECTED_TEXT_WITH_FINAL_NEWLINE = "\n".join(EXPECTED_LINES) + "\n"
EXPECTED_TEXT_WITHOUT_FINAL_NEWLINE = "\n".join(EXPECTED_LINES)


def _read_report_bytes() -> bytes:
    assert REPORT_PATH.exists(), (
        f"Required verification report does not exist at absolute path: {REPORT_PATH}"
    )
    assert REPORT_PATH.is_file(), (
        f"Required verification report exists but is not a regular file: {REPORT_PATH}"
    )

    try:
        return REPORT_PATH.read_bytes()
    except PermissionError as exc:
        pytest.fail(f"Verification report is not readable by the test runner: {REPORT_PATH}: {exc}")


def _read_report_text() -> str:
    raw = _read_report_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(
            f"Verification report must be valid UTF-8 text, but decoding failed: {exc}"
        )


def test_report_file_exists_is_regular_and_readable():
    _read_report_bytes()


def test_report_contains_exact_expected_bytes_allowing_single_optional_final_newline():
    text = _read_report_text()

    assert text in {EXPECTED_TEXT_WITH_FINAL_NEWLINE, EXPECTED_TEXT_WITHOUT_FINAL_NEWLINE}, (
        "Verification report content is not exactly the required five-line ledger.\n"
        "Expected exactly either:\n"
        f"{EXPECTED_TEXT_WITH_FINAL_NEWLINE!r}\n"
        "or the same text without the final newline.\n"
        f"Actual content was:\n{text!r}"
    )


def test_report_has_exactly_five_non_empty_lines_no_extra_blank_or_trailing_content():
    text = _read_report_text()

    assert not text.startswith("\n"), (
        "Verification report has extra blank content before the first required line."
    )
    assert "\n\n" not in text, (
        "Verification report contains an extra blank line; it must contain exactly five "
        "non-empty lines and no blank lines."
    )
    assert not text.endswith("\n\n"), (
        "Verification report has an extra blank line after the fifth required line."
    )

    lines = text.splitlines()
    assert len(lines) == 5, (
        f"Verification report must contain exactly 5 lines, but found {len(lines)} "
        f"line(s): {lines!r}"
    )

    empty_line_numbers = [index + 1 for index, line in enumerate(lines) if line == ""]
    assert not empty_line_numbers, (
        "Verification report must contain exactly five non-empty lines; empty line(s) "
        f"found at line number(s): {empty_line_numbers}"
    )

    whitespace_errors = [
        (index + 1, line)
        for index, line in enumerate(lines)
        if line != line.strip()
    ]
    assert not whitespace_errors, (
        "No line may have leading or trailing whitespace. Offending line(s): "
        f"{whitespace_errors!r}"
    )


@pytest.mark.parametrize(
    ("line_number", "expected"),
    list(enumerate(EXPECTED_LINES, start=1)),
)
def test_each_report_line_matches_required_value_in_order(line_number, expected):
    text = _read_report_text()
    lines = text.splitlines()

    assert len(lines) >= line_number, (
        f"Verification report is missing required line {line_number}: {expected!r}. "
        f"Actual lines were: {lines!r}"
    )

    actual = lines[line_number - 1]
    assert actual == expected, (
        f"Line {line_number} is incorrect.\n"
        f"Expected: {expected!r}\n"
        f"Actual:   {actual!r}"
    )


def test_verified_line_is_yes_and_earlier_values_were_not_regressed():
    text = _read_report_text()
    lines = text.splitlines()

    assert lines == EXPECTED_LINES, (
        "The final report must preserve all earlier exact values while setting the "
        "final verification result correctly.\n"
        f"Expected ordered lines: {EXPECTED_LINES!r}\n"
        f"Actual ordered lines:   {lines!r}"
    )

    assert lines[4] == "verified=yes", (
        "The final line must be exactly 'verified=yes' because the API returned HTTP "
        "200 with state='completed', checksum_verified=true, and "
        "storage_redundancy='multi_az'."
    )