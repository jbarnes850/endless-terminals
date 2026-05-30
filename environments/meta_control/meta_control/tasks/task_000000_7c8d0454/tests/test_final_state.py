# test_final_state.py
from pathlib import Path
import os
import py_compile
import subprocess
import sys


BASE = Path("/home/user/clockutil")
ENV_FILE = Path("/home/user/clockutil/deadline.env")
SCRIPT = Path("/home/user/clockutil/format_deadline.py")
OUT_DIR = Path("/home/user/clockutil/out")
REPORT = Path("/home/user/clockutil/out/deadline_report.txt")
VERIFY_LOG = Path("/home/user/clockutil/out/verification.log")

EXPECTED_ENV_TEXT = (
    "APP_TZ=Europe/Berlin\n"
    "APP_LOCALE=C\n"
    "DEADLINE_EPOCH=1704067200\n"
)

EXPECTED_REPORT_TEXT = (
    "timezone=Europe/Berlin\n"
    "locale=C\n"
    "deadline=Mon 2024-01-01 01:00:00 CET\n"
)

EXPECTED_VERIFY_LOG_TEXT = (
    "artifact=/home/user/clockutil/out/deadline_report.txt\n"
    "exists=yes\n"
    "format=valid\n"
    "status=verified\n"
)


def _read_bytes(path: Path) -> bytes:
    assert path.is_file(), f"Missing required file: {path}"
    return path.read_bytes()


def _assert_exact_text_file(path: Path, expected: str, description: str) -> None:
    actual_bytes = _read_bytes(path)
    expected_bytes = expected.encode("utf-8")

    assert actual_bytes == expected_bytes, (
        f"{description} at {path} does not match the exact required final contents.\n"
        f"Expected bytes/text:\n{expected_bytes!r}\n"
        f"Actual bytes/text:\n{actual_bytes!r}"
    )


def _assert_no_trailing_spaces(path: Path, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        assert not line.endswith((" ", "\t")), (
            f"{description} at {path} has trailing whitespace on line {line_number}: {line!r}"
        )


def test_project_files_and_directories_exist_after_completion():
    assert BASE.is_dir(), "Missing required project directory after task completion: /home/user/clockutil"
    assert OUT_DIR.is_dir(), "Missing required output directory after task completion: /home/user/clockutil/out"
    assert ENV_FILE.is_file(), "Missing required config file after task completion: /home/user/clockutil/deadline.env"
    assert SCRIPT.is_file(), "Missing required script after task completion: /home/user/clockutil/format_deadline.py"

    for path in (BASE, OUT_DIR):
        assert os.access(path, os.R_OK), f"Directory is not readable: {path}"
        assert os.access(path, os.W_OK), f"Directory is not writable: {path}"
        assert os.access(path, os.X_OK), f"Directory is not searchable/executable: {path}"

    for path in (ENV_FILE, SCRIPT):
        assert os.access(path, os.R_OK), f"File is not readable: {path}"
        assert os.access(path, os.W_OK), f"File is not writable: {path}"


def test_config_file_remains_exactly_the_required_configuration():
    _assert_exact_text_file(
        ENV_FILE,
        EXPECTED_ENV_TEXT,
        "Config file /home/user/clockutil/deadline.env",
    )


def test_format_deadline_script_is_valid_python_and_runs_cleanly():
    try:
        py_compile.compile(str(SCRIPT), doraise=True)
    except py_compile.PyCompileError as exc:
        raise AssertionError(
            "Script /home/user/clockutil/format_deadline.py is not valid parseable Python"
        ) from exc

    result = subprocess.run(
        [sys.executable, "/home/user/clockutil/format_deadline.py"],
        cwd="/home/user/clockutil",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, (
        "Running /home/user/clockutil/format_deadline.py with Python must complete "
        "without an unhandled exception.\n"
        f"Exit code: {result.returncode}\n"
        f"stdout:\n{result.stdout!r}\n"
        f"stderr:\n{result.stderr!r}"
    )


def test_report_artifact_exists_and_has_exact_required_three_line_format():
    assert REPORT.is_file(), (
        "Report artifact was not created at the required absolute path: "
        "/home/user/clockutil/out/deadline_report.txt"
    )

    actual = REPORT.read_text(encoding="utf-8")
    assert actual.endswith("\n"), (
        "Report artifact must be newline-terminated: "
        "/home/user/clockutil/out/deadline_report.txt"
    )

    lines = actual.splitlines()
    assert len(lines) == 3, (
        "Report artifact must contain exactly three newline-terminated lines "
        "with no extra blank lines or debug text.\n"
        f"Actual line count: {len(lines)}\n"
        f"Actual contents: {actual!r}"
    )

    expected_prefixes = ["timezone=", "locale=", "deadline="]
    for index, expected_prefix in enumerate(expected_prefixes):
        assert lines[index].startswith(expected_prefix), (
            f"Report line {index + 1} must begin exactly with {expected_prefix!r}.\n"
            f"Actual line {index + 1}: {lines[index]!r}\n"
            f"Full report: {actual!r}"
        )

    _assert_no_trailing_spaces(REPORT, "Report artifact")

    assert actual == EXPECTED_REPORT_TEXT, (
        "Report artifact exists and is syntactically shaped like a report, but its "
        "semantic time zone / locale output is still wrong. The script must use "
        "APP_TZ=Europe/Berlin, APP_LOCALE=C, and DEADLINE_EPOCH=1704067200 to produce "
        "the Berlin/CET local deadline.\n"
        f"Expected exact report:\n{EXPECTED_REPORT_TEXT!r}\n"
        f"Actual report:\n{actual!r}"
    )


def test_report_is_not_the_known_initial_buggy_utc_default_output():
    actual = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    known_buggy_output = (
        "timezone=UTC\n"
        "locale=default\n"
        "deadline=Mon 2024-01-01 00:00:00 UTC\n"
    )

    assert actual != known_buggy_output, (
        "Report is still the known initial buggy output. Command success and artifact "
        "existence are not sufficient; /home/user/clockutil/format_deadline.py must be "
        "fixed to use APP_TZ and APP_LOCALE from /home/user/clockutil/deadline.env."
    )


def test_verification_log_exists_and_matches_exact_required_contents():
    assert VERIFY_LOG.is_file(), (
        "Verification log was not created at the required absolute path: "
        "/home/user/clockutil/out/verification.log"
    )

    actual = VERIFY_LOG.read_text(encoding="utf-8")
    assert actual.endswith("\n"), (
        "Verification log must be newline-terminated: "
        "/home/user/clockutil/out/verification.log"
    )

    lines = actual.splitlines()
    assert len(lines) == 4, (
        "Verification log must contain exactly four newline-terminated lines "
        "with no extra blank lines, comments, or debug text.\n"
        f"Actual line count: {len(lines)}\n"
        f"Actual contents: {actual!r}"
    )

    _assert_no_trailing_spaces(VERIFY_LOG, "Verification log")

    assert actual == EXPECTED_VERIFY_LOG_TEXT, (
        "Verification log does not match the exact required final contents.\n"
        f"Expected exact verification log:\n{EXPECTED_VERIFY_LOG_TEXT!r}\n"
        f"Actual verification log:\n{actual!r}"
    )


def test_final_verified_stop_state_both_artifacts_match_exactly():
    report_text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else None
    verify_text = VERIFY_LOG.read_text(encoding="utf-8") if VERIFY_LOG.exists() else None

    assert report_text == EXPECTED_REPORT_TEXT and verify_text == EXPECTED_VERIFY_LOG_TEXT, (
        "Final verified stop state has not been reached. Both final files must match "
        "exactly at the same time:\n"
        "- /home/user/clockutil/out/deadline_report.txt\n"
        "- /home/user/clockutil/out/verification.log\n"
        f"Actual report: {report_text!r}\n"
        f"Actual verification log: {verify_text!r}"
    )