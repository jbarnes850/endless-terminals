# test_final_state.py
from pathlib import Path
import os
import re
import stat

import pytest


BASE = Path("/home/user/log-audit")
DAILY = Path("/home/user/log-audit/daily")
CURRENT = Path("/home/user/log-audit/current.log")
REPORT = Path("/home/user/log-audit/current-pattern-report.txt")
EXPECTED_TARGET = Path("/home/user/log-audit/daily/web-2024-03-21.log")

EXPECTED_REPORT_TEXT = (
    "current_link=/home/user/log-audit/current.log\n"
    "resolved_target=/home/user/log-audit/daily/web-2024-03-21.log\n"
    "error_count=2\n"
    "warning_count=1\n"
)

LOG_NAME_RE = re.compile(r"^web-(\d{4}-\d{2}-\d{2})\.log$")


def _canonical(path: Path) -> Path:
    return Path(os.path.realpath(os.fspath(path)))


def _daily_logs_by_filename_date():
    assert DAILY.exists(), f"Missing daily log directory: {DAILY}"
    assert DAILY.is_dir(), f"Daily log path is not a directory: {DAILY}"

    logs = []
    for child in DAILY.iterdir():
        match = LOG_NAME_RE.fullmatch(child.name)
        if match:
            logs.append((match.group(1), child))

    assert logs, (
        f"No daily logs matching the required filename format "
        f"'web-YYYY-MM-DD.log' were found in {DAILY}"
    )
    return sorted(logs, key=lambda item: item[0])


def test_latest_daily_log_by_filename_date_is_expected_file():
    logs = _daily_logs_by_filename_date()
    latest_date, latest_path = logs[-1]

    assert latest_path == EXPECTED_TARGET, (
        "The latest daily log must be selected by the greatest date in the "
        "filename, not by filesystem modification time.\n"
        f"Latest matching filename found: {latest_path} with date {latest_date}\n"
        f"Expected latest log: {EXPECTED_TARGET}"
    )
    assert latest_path.is_file(), f"Expected latest daily log is not a regular file: {latest_path}"


def test_current_log_exists_and_is_symbolic_link_to_latest_daily_log():
    assert os.path.lexists(CURRENT), f"Missing required current log path: {CURRENT}"

    try:
        link_stat = CURRENT.lstat()
    except FileNotFoundError:
        pytest.fail(f"Missing required current log path: {CURRENT}")

    assert stat.S_ISLNK(link_stat.st_mode), (
        f"{CURRENT} must be a symbolic link. It must not be a copied regular "
        "file, hard link, or directory."
    )
    assert CURRENT.is_symlink(), f"{CURRENT} is not recognized as a symbolic link"

    raw_target = os.readlink(CURRENT)
    assert raw_target, f"{CURRENT} is a symlink but has an empty target"

    try:
        resolved_target = CURRENT.resolve(strict=True)
    except FileNotFoundError as exc:
        pytest.fail(
            f"{CURRENT} is a symlink but its target cannot be resolved. "
            f"Raw link target is {raw_target!r}. Error: {exc}"
        )

    assert resolved_target == EXPECTED_TARGET, (
        f"{CURRENT} resolves to the wrong log file.\n"
        f"Raw symlink target: {raw_target!r}\n"
        f"Resolved target: {resolved_target}\n"
        f"Expected resolved target: {EXPECTED_TARGET}\n"
        "The link must point to the latest daily log by filename date."
    )


def test_report_exists_as_regular_utf8_text_file():
    assert REPORT.exists(), f"Missing required report file: {REPORT}"
    assert REPORT.is_file(), f"Report path must be a regular file: {REPORT}"

    try:
        REPORT.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Report is not valid UTF-8 text: {REPORT}. Decode error: {exc}")


def test_report_contents_are_exact_required_four_lines():
    assert REPORT.exists(), f"Missing required report file: {REPORT}"

    try:
        actual_text = REPORT.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Report is not valid UTF-8 text: {REPORT}. Decode error: {exc}")

    assert actual_text == EXPECTED_REPORT_TEXT, (
        f"Report contents are not exactly correct: {REPORT}\n"
        "Expected exactly four lines, no extra spaces, comments, blank lines, "
        "or additional output.\n"
        f"Expected repr: {EXPECTED_REPORT_TEXT!r}\n"
        f"Actual repr:   {actual_text!r}"
    )

    lines = actual_text.splitlines()
    assert len(lines) == 4, (
        f"Report must contain exactly 4 lines, but contains {len(lines)} lines: {lines!r}"
    )

    expected_labels = ["current_link", "resolved_target", "error_count", "warning_count"]
    for index, (line, expected_label) in enumerate(zip(lines, expected_labels), start=1):
        assert line.count("=") == 1, (
            f"Report line {index} must contain exactly one '=' separator with no extra "
            f"separators: {line!r}"
        )
        label, value = line.split("=", 1)
        assert label == expected_label, (
            f"Report line {index} has wrong label. "
            f"Expected {expected_label!r}, got {label!r}. Full line: {line!r}"
        )
        assert not label.endswith(" ") and not value.startswith(" "), (
            f"Report line {index} must not contain spaces around '=': {line!r}"
        )


def test_report_target_matches_final_symlink_canonical_resolution():
    assert CURRENT.is_symlink(), f"{CURRENT} must be a symbolic link before checking report agreement"
    assert REPORT.exists(), f"Missing required report file: {REPORT}"

    resolved_current = _canonical(CURRENT)
    assert resolved_current == EXPECTED_TARGET, (
        f"{CURRENT} resolves to {resolved_current}, expected {EXPECTED_TARGET}"
    )

    report_lines = REPORT.read_text(encoding="utf-8").splitlines()
    assert len(report_lines) == 4, (
        f"Cannot verify report/symlink agreement because report should have exactly "
        f"4 lines but has {len(report_lines)}"
    )

    report_values = {}
    for line in report_lines:
        assert "=" in line, f"Malformed report line missing '=' separator: {line!r}"
        key, value = line.split("=", 1)
        report_values[key] = value

    assert report_values.get("current_link") == os.fspath(CURRENT), (
        f"Report current_link value is wrong. "
        f"Expected {CURRENT}, got {report_values.get('current_link')!r}"
    )
    assert report_values.get("resolved_target") == os.fspath(resolved_current), (
        "Report resolved_target must equal the canonical resolved target of "
        f"{CURRENT}.\n"
        f"Symlink resolves to: {resolved_current}\n"
        f"Report says: {report_values.get('resolved_target')!r}"
    )


def test_report_counts_are_computed_from_final_resolved_log_case_sensitively():
    assert CURRENT.is_symlink(), f"{CURRENT} must be a symbolic link"
    resolved_target = CURRENT.resolve(strict=True)
    assert resolved_target == EXPECTED_TARGET, (
        f"Cannot validate counts because {CURRENT} resolves to {resolved_target}, "
        f"not the expected latest log {EXPECTED_TARGET}"
    )

    log_text = resolved_target.read_text(encoding="utf-8")
    log_lines = log_text.splitlines()

    actual_error_count = sum(1 for line in log_lines if "ERROR" in line)
    actual_warning_count = sum(1 for line in log_lines if "WARN" in line)

    assert actual_error_count == 2, (
        f"The resolved latest log should contain exactly 2 lines with substring "
        f"'ERROR', but computed {actual_error_count} from {resolved_target}"
    )
    assert actual_warning_count == 1, (
        f"The resolved latest log should contain exactly 1 line with substring "
        f"'WARN', but computed {actual_warning_count} from {resolved_target}"
    )

    lowercase_error_lines = [line for line in log_lines if "error" in line and "ERROR" not in line]
    lowercase_warn_lines = [line for line in log_lines if "warn" in line and "WARN" not in line]
    assert lowercase_error_lines, (
        "Expected latest log fixture to include lowercase 'error' line to ensure "
        "case-sensitive counting is tested."
    )
    assert lowercase_warn_lines, (
        "Expected latest log fixture to include lowercase 'warn' line to ensure "
        "case-sensitive counting is tested."
    )

    report_lines = REPORT.read_text(encoding="utf-8").splitlines()
    report_values = dict(line.split("=", 1) for line in report_lines)

    assert report_values.get("error_count") == str(actual_error_count), (
        f"Report error_count is wrong. It must be computed from the final resolved "
        f"log {resolved_target} using exact uppercase substring 'ERROR'.\n"
        f"Expected: {actual_error_count}\n"
        f"Reported: {report_values.get('error_count')!r}"
    )
    assert report_values.get("warning_count") == str(actual_warning_count), (
        f"Report warning_count is wrong. It must be computed from the final resolved "
        f"log {resolved_target} using exact uppercase substring 'WARN'.\n"
        f"Expected: {actual_warning_count}\n"
        f"Reported: {report_values.get('warning_count')!r}"
    )