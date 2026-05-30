# test_final_state.py
import os
import stat
import subprocess
from pathlib import Path

import pytest


QA_ENV_DIR = Path("/home/user/qa-env")
SNIPPET_PATH = Path("/home/user/qa-env/time-locale.sh")
VERIFICATION_LOG_PATH = Path("/home/user/qa-env/verification.log")

EXPECTED_SNIPPET_LINES = [
    "export TZ=America/New_York",
    "export LANG=en_US.UTF-8",
    "export LC_ALL=en_US.UTF-8",
]

EXPECTED_VERIFICATION_LINES = [
    "QA time/locale verification",
    "TZ=America/New_York",
    "LANG=en_US.UTF-8",
    "LC_ALL=en_US.UTF-8",
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"{path} is not valid UTF-8 text: {exc}")
    except OSError as exc:
        pytest.fail(f"Could not read {path}: {exc}")


def _assert_readable_regular_file(path: Path, description: str) -> None:
    assert path.exists(), f"{description} is missing at {path}."
    assert path.is_file(), f"{description} exists at {path}, but it is not a regular file."

    try:
        mode = path.stat().st_mode
    except OSError as exc:
        pytest.fail(f"Could not stat {description} at {path}: {exc}")

    assert stat.S_ISREG(mode), f"{description} at {path} must be a regular file."
    assert os.access(path, os.R_OK), (
        f"{description} at {path} is not readable by the current user."
    )


def _logical_lines_allowing_single_trailing_newline(text: str, path: Path) -> list[str]:
    """
    Return logical lines while allowing EOF to be either immediately after the final
    line or after one trailing newline. Extra blank lines remain visible and fail.
    """
    if text.endswith("\n"):
        text_without_one_final_newline = text[:-1]
        assert not text_without_one_final_newline.endswith("\n"), (
            f"{path} has extra trailing blank lines; only a single final newline is acceptable."
        )
        text = text_without_one_final_newline

    return text.split("\n") if text else []


def test_qa_env_directory_exists_and_is_accessible():
    assert QA_ENV_DIR.exists(), "Required directory /home/user/qa-env does not exist."
    assert QA_ENV_DIR.is_dir(), "/home/user/qa-env exists but is not a directory."

    try:
        mode = QA_ENV_DIR.stat().st_mode
    except OSError as exc:
        pytest.fail(f"Could not stat /home/user/qa-env: {exc}")

    assert stat.S_ISDIR(mode), "/home/user/qa-env must be a directory."
    assert os.access(QA_ENV_DIR, os.R_OK), (
        "/home/user/qa-env is not readable by the current user."
    )
    assert os.access(QA_ENV_DIR, os.X_OK), (
        "/home/user/qa-env is not traversable/executable by the current user."
    )


def test_time_locale_snippet_exists_readable_and_has_exact_contents():
    _assert_readable_regular_file(SNIPPET_PATH, "Shell snippet")

    text = _read_text(SNIPPET_PATH)
    actual_lines = _logical_lines_allowing_single_trailing_newline(text, SNIPPET_PATH)

    assert actual_lines == EXPECTED_SNIPPET_LINES, (
        "Shell snippet /home/user/qa-env/time-locale.sh has incorrect contents.\n"
        "It must contain exactly these three lines, in order, with no comments, "
        "blank lines, quotes, semicolons, shebang, set commands, or extra exports:\n"
        f"{EXPECTED_SNIPPET_LINES!r}\n"
        f"Actual logical lines were:\n{actual_lines!r}"
    )


def test_snippet_sets_effective_values_when_sourced_by_posix_shell():
    _assert_readable_regular_file(SNIPPET_PATH, "Shell snippet")

    result = subprocess.run(
        [
            "/bin/sh",
            "-c",
            (
                ". /home/user/qa-env/time-locale.sh\n"
                "printf 'TZ=%s\\nLANG=%s\\nLC_ALL=%s\\n' "
                "\"$TZ\" \"$LANG\" \"$LC_ALL\""
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    expected_stdout = (
        "TZ=America/New_York\n"
        "LANG=en_US.UTF-8\n"
        "LC_ALL=en_US.UTF-8\n"
    )

    assert result.returncode == 0, (
        "Sourcing /home/user/qa-env/time-locale.sh with /bin/sh failed. "
        f"returncode={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert result.stdout == expected_stdout, (
        "After sourcing /home/user/qa-env/time-locale.sh, the effective environment "
        "values are not the required values. "
        f"Expected stdout {expected_stdout!r}, got {result.stdout!r}. "
        f"stderr={result.stderr!r}"
    )


def test_verification_log_exists_readable_and_has_exact_four_line_structure():
    _assert_readable_regular_file(VERIFICATION_LOG_PATH, "Verification log")

    text = _read_text(VERIFICATION_LOG_PATH)
    actual_lines = _logical_lines_allowing_single_trailing_newline(
        text, VERIFICATION_LOG_PATH
    )

    assert actual_lines == EXPECTED_VERIFICATION_LINES, (
        "Verification log /home/user/qa-env/verification.log is missing, stale, "
        "malformed, or inconsistent with the required sourced environment values.\n"
        "It must contain exactly these four lines, in order, with no timestamp, "
        "hostname, command transcript, shell prompt, warnings, diagnostics, extra "
        "whitespace, or blank lines:\n"
        f"{EXPECTED_VERIFICATION_LINES!r}\n"
        f"Actual logical lines were:\n{actual_lines!r}"
    )


def test_verification_log_matches_values_produced_by_sourcing_snippet():
    """
    Ensure the verification artifact is not merely present, but is consistent with
    what /bin/sh observes after dot-sourcing the snippet.
    """
    _assert_readable_regular_file(SNIPPET_PATH, "Shell snippet")
    _assert_readable_regular_file(VERIFICATION_LOG_PATH, "Verification log")

    result = subprocess.run(
        [
            "/bin/sh",
            "-c",
            (
                ". /home/user/qa-env/time-locale.sh\n"
                "printf 'QA time/locale verification\\n'\n"
                "printf 'TZ=%s\\n' \"$TZ\"\n"
                "printf 'LANG=%s\\n' \"$LANG\"\n"
                "printf 'LC_ALL=%s\\n' \"$LC_ALL\"\n"
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        "Could not independently verify /home/user/qa-env/verification.log by "
        "sourcing /home/user/qa-env/time-locale.sh with /bin/sh. "
        f"returncode={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
    )

    log_text = _read_text(VERIFICATION_LOG_PATH)
    normalized_log_text = log_text if log_text.endswith("\n") else log_text + "\n"

    assert normalized_log_text == result.stdout, (
        "Verification log does not match the values produced by sourcing the "
        "snippet in /bin/sh. This suggests the task stopped too early, the log is "
        "stale, or the values were not generated from the effective environment.\n"
        f"Expected log text based on sourcing snippet:\n{result.stdout!r}\n"
        f"Actual log text:\n{log_text!r}\n"
        f"stderr from verification shell: {result.stderr!r}"
    )