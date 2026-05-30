# test_final_state.py
import stat
from pathlib import Path

PASSWD_FILE = Path("/home/user/hardening-lab/accounts/appsvc.passwd")
SHADOW_FILE = Path("/home/user/hardening-lab/accounts/appsvc.shadow")
LOG_FILE = Path("/home/user/hardening-lab/audit/permission-check.log")

EXPECTED_PASSWD_CONTENT = (
    "appsvc:x:1501:1501:Application Service Account:/srv/appsvc:/usr/sbin/nologin\n"
)
EXPECTED_SHADOW_CONTENT = "appsvc:!:19876:0:99999:7:::\n"

EXPECTED_LOG_CONTENT = (
    "permission hardening verification\n"
    "-rw-r--r-- 0644 /home/user/hardening-lab/accounts/appsvc.passwd\n"
    "-rw------- 0600 /home/user/hardening-lab/accounts/appsvc.shadow\n"
)


def numeric_mode(path: Path) -> str:
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def symbolic_mode(path: Path) -> str:
    return stat.filemode(path.stat().st_mode)


def assert_regular_file_with_content(path: Path, expected_content: str) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Required path exists but is not a regular file: {path}"

    actual_content = path.read_text()
    assert actual_content == expected_content, (
        f"{path} content was changed or is incomplete.\n"
        f"Expected exact content: {expected_content!r}\n"
        f"Actual content:         {actual_content!r}"
    )


def test_appsvc_passwd_exists_is_regular_and_content_is_unchanged():
    assert_regular_file_with_content(PASSWD_FILE, EXPECTED_PASSWD_CONTENT)


def test_appsvc_shadow_exists_is_regular_and_content_is_unchanged():
    assert_regular_file_with_content(SHADOW_FILE, EXPECTED_SHADOW_CONTENT)


def test_appsvc_passwd_final_mode_is_0644():
    assert PASSWD_FILE.exists(), f"Cannot check mode because file is missing: {PASSWD_FILE}"
    assert PASSWD_FILE.is_file(), f"Cannot check mode because path is not a regular file: {PASSWD_FILE}"

    actual_numeric = numeric_mode(PASSWD_FILE)
    actual_symbolic = symbolic_mode(PASSWD_FILE)
    assert actual_numeric == "0644", (
        f"{PASSWD_FILE} has the wrong final permissions. "
        f"Expected numeric mode 0644 / symbolic mode -rw-r--r--; "
        f"found numeric mode {actual_numeric} / symbolic mode {actual_symbolic}."
    )


def test_appsvc_shadow_final_mode_is_0600():
    assert SHADOW_FILE.exists(), f"Cannot check mode because file is missing: {SHADOW_FILE}"
    assert SHADOW_FILE.is_file(), f"Cannot check mode because path is not a regular file: {SHADOW_FILE}"

    actual_numeric = numeric_mode(SHADOW_FILE)
    actual_symbolic = symbolic_mode(SHADOW_FILE)
    assert actual_numeric == "0600", (
        f"{SHADOW_FILE} has the wrong final permissions. "
        f"Expected numeric mode 0600 / symbolic mode -rw-------; "
        f"found numeric mode {actual_numeric} / symbolic mode {actual_symbolic}."
    )


def test_verification_log_exists_and_is_regular_file():
    assert LOG_FILE.exists(), f"Missing required verification log file: {LOG_FILE}"
    assert LOG_FILE.is_file(), f"Verification log path exists but is not a regular file: {LOG_FILE}"


def test_verification_log_has_exact_required_three_line_content():
    assert LOG_FILE.exists(), f"Missing required verification log file: {LOG_FILE}"
    assert LOG_FILE.is_file(), f"Verification log path exists but is not a regular file: {LOG_FILE}"

    actual_content = LOG_FILE.read_text()
    assert actual_content == EXPECTED_LOG_CONTENT, (
        f"{LOG_FILE} must contain exactly three lines proving the final permissions, "
        f"with symbolic mode, numeric mode, and full path, and no extra blank lines.\n"
        f"Expected exact content:\n{EXPECTED_LOG_CONTENT!r}\n"
        f"Actual content:\n{actual_content!r}"
    )

    actual_lines = actual_content.splitlines()
    assert actual_lines == [
        "permission hardening verification",
        "-rw-r--r-- 0644 /home/user/hardening-lab/accounts/appsvc.passwd",
        "-rw------- 0600 /home/user/hardening-lab/accounts/appsvc.shadow",
    ], (
        f"{LOG_FILE} does not have the exact required three lines in order. "
        f"Found lines: {actual_lines!r}"
    )


def test_verification_log_matches_actual_final_file_modes():
    assert LOG_FILE.exists(), f"Missing required verification log file: {LOG_FILE}"
    assert LOG_FILE.is_file(), f"Verification log path exists but is not a regular file: {LOG_FILE}"

    expected_passwd_line = f"{symbolic_mode(PASSWD_FILE)} {numeric_mode(PASSWD_FILE)} {PASSWD_FILE}"
    expected_shadow_line = f"{symbolic_mode(SHADOW_FILE)} {numeric_mode(SHADOW_FILE)} {SHADOW_FILE}"

    lines = LOG_FILE.read_text().splitlines()
    assert len(lines) == 3, (
        f"{LOG_FILE} must contain exactly three lines and no extra blank lines. "
        f"Found {len(lines)} line(s): {lines!r}"
    )

    assert lines[1] == expected_passwd_line, (
        f"Line 2 of {LOG_FILE} does not match the actual final permissions for {PASSWD_FILE}.\n"
        f"Expected from filesystem: {expected_passwd_line!r}\n"
        f"Actual line 2:             {lines[1]!r}"
    )
    assert lines[2] == expected_shadow_line, (
        f"Line 3 of {LOG_FILE} does not match the actual final permissions for {SHADOW_FILE}.\n"
        f"Expected from filesystem: {expected_shadow_line!r}\n"
        f"Actual line 3:             {lines[2]!r}"
    )