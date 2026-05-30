# test_final_state.py
import hashlib
import os
import stat
from pathlib import Path



ROTATION_DIR = Path("/home/user/rotation")
SECRET_DIR = Path("/home/user/rotation/current.secret.d")
TOKEN_FILE = Path("/home/user/rotation/current.secret.d/token.txt")
AUDIT_DIR = Path("/home/user/rotation/audit")
AUDIT_LOG = Path("/home/user/rotation/audit/credential-rotation.log")

EXPECTED_TOKEN_BYTES = b"rotated-service-token:tb-simple-perm-pivot-2026\n"
EXPECTED_TOKEN_SHA256 = hashlib.sha256(EXPECTED_TOKEN_BYTES).hexdigest()

EXPECTED_AUDIT_BYTES = (
    b"ROTATION_AUDIT v1\n"
    b"/home/user/rotation/current.secret.d mode=700\n"
    b"/home/user/rotation/current.secret.d/token.txt mode=600\n"
)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _mode_str(path: Path) -> str:
    return f"{_mode(path):04o}"


def _assert_owned_by_current_user(path: Path) -> None:
    current_uid = os.getuid()
    actual_uid = path.stat().st_uid
    assert actual_uid == current_uid, (
        f"{path} must be owned by the current unprivileged user uid={current_uid}, "
        f"but it is owned by uid={actual_uid}"
    )


def test_required_workspace_paths_exist_and_are_expected_types():
    assert ROTATION_DIR.exists(), f"Workspace directory is missing: {ROTATION_DIR}"
    assert ROTATION_DIR.is_dir(), f"Workspace path exists but is not a directory: {ROTATION_DIR}"
    _assert_owned_by_current_user(ROTATION_DIR)

    assert SECRET_DIR.exists(), f"Credential directory is missing: {SECRET_DIR}"
    assert SECRET_DIR.is_dir(), (
        f"Credential path must remain a directory, but it is not: {SECRET_DIR}"
    )
    _assert_owned_by_current_user(SECRET_DIR)

    assert TOKEN_FILE.exists(), f"Credential token file is missing: {TOKEN_FILE}"
    assert TOKEN_FILE.is_file(), (
        f"Credential token path must remain a regular file, but it is not: {TOKEN_FILE}"
    )
    _assert_owned_by_current_user(TOKEN_FILE)

    assert AUDIT_DIR.exists(), f"Audit directory is missing: {AUDIT_DIR}"
    assert AUDIT_DIR.is_dir(), f"Audit path exists but is not a directory: {AUDIT_DIR}"
    _assert_owned_by_current_user(AUDIT_DIR)


def test_secret_directory_mode_is_exactly_0700():
    assert SECRET_DIR.exists(), f"Credential directory is missing: {SECRET_DIR}"
    assert SECRET_DIR.is_dir(), f"Credential path is not a directory: {SECRET_DIR}"

    actual_mode = _mode(SECRET_DIR)
    assert actual_mode == 0o700, (
        f"{SECRET_DIR} must have exact final mode 0700 so only the owner can "
        f"read, write, and enter it. Actual mode is {_mode_str(SECRET_DIR)}. "
        f"If it is still 0600, the owner execute/search bit is still missing; "
        f"if group/other bits are present, the directory is still exposed."
    )

    assert actual_mode & stat.S_IRUSR, f"{SECRET_DIR} is missing owner read permission"
    assert actual_mode & stat.S_IWUSR, f"{SECRET_DIR} is missing owner write permission"
    assert actual_mode & stat.S_IXUSR, f"{SECRET_DIR} is missing owner execute/enter permission"
    assert actual_mode & (stat.S_IRWXG | stat.S_IRWXO) == 0, (
        f"{SECRET_DIR} must grant no permissions to group or others, "
        f"but actual mode is {_mode_str(SECRET_DIR)}"
    )


def test_token_file_mode_is_exactly_0600_and_not_executable():
    assert TOKEN_FILE.exists(), f"Credential token file is missing: {TOKEN_FILE}"
    assert TOKEN_FILE.is_file(), (
        f"Credential token path must be a regular file, but it is not: {TOKEN_FILE}"
    )

    actual_mode = _mode(TOKEN_FILE)
    assert actual_mode == 0o600, (
        f"{TOKEN_FILE} must have exact final mode 0600: readable and writable "
        f"only by its owner, with no execute bits. Actual mode is {_mode_str(TOKEN_FILE)}. "
        f"If it is still 0644, the file exposure was not fixed."
    )

    assert actual_mode & stat.S_IRUSR, f"{TOKEN_FILE} is missing owner read permission"
    assert actual_mode & stat.S_IWUSR, f"{TOKEN_FILE} is missing owner write permission"
    assert not (actual_mode & stat.S_IXUSR), f"{TOKEN_FILE} must not be executable by owner"
    assert actual_mode & (stat.S_IRWXG | stat.S_IRWXO) == 0, (
        f"{TOKEN_FILE} must grant no permissions to group or others, "
        f"but actual mode is {_mode_str(TOKEN_FILE)}"
    )


def test_token_file_contents_are_unchanged_byte_for_byte():
    assert TOKEN_FILE.exists(), f"Credential token file is missing: {TOKEN_FILE}"
    assert TOKEN_FILE.is_file(), (
        f"Credential token path must be a regular file, but it is not: {TOKEN_FILE}"
    )

    actual_bytes = TOKEN_FILE.read_bytes()
    actual_sha256 = hashlib.sha256(actual_bytes).hexdigest()

    assert actual_bytes == EXPECTED_TOKEN_BYTES, (
        f"{TOKEN_FILE} contents must remain byte-for-byte unchanged. "
        f"Expected sha256={EXPECTED_TOKEN_SHA256}, actual sha256={actual_sha256}. "
        f"The token file must not be deleted, renamed, truncated, or modified."
    )


def test_audit_log_exists_as_regular_file_with_exact_contents():
    assert AUDIT_LOG.exists(), f"Required audit log was not created: {AUDIT_LOG}"
    assert AUDIT_LOG.is_file(), (
        f"Audit log path must be a regular file, but it is not: {AUDIT_LOG}"
    )
    _assert_owned_by_current_user(AUDIT_LOG)

    actual_bytes = AUDIT_LOG.read_bytes()
    assert actual_bytes == EXPECTED_AUDIT_BYTES, (
        f"{AUDIT_LOG} must contain exactly three lines with final modes and no "
        f"extra spaces, carriage returns, missing final newline, or blank lines. "
        f"Expected bytes: {EXPECTED_AUDIT_BYTES!r}; actual bytes: {actual_bytes!r}"
    )


def test_final_permission_and_audit_invariant_together():
    problems = []

    if not SECRET_DIR.exists():
        problems.append(f"{SECRET_DIR} is missing")
    elif not SECRET_DIR.is_dir():
        problems.append(f"{SECRET_DIR} is not a directory")
    elif _mode(SECRET_DIR) != 0o700:
        problems.append(
            f"{SECRET_DIR} mode is {_mode_str(SECRET_DIR)}, expected 0700"
        )

    if not TOKEN_FILE.exists():
        problems.append(f"{TOKEN_FILE} is missing")
    elif not TOKEN_FILE.is_file():
        problems.append(f"{TOKEN_FILE} is not a regular file")
    else:
        if _mode(TOKEN_FILE) != 0o600:
            problems.append(
                f"{TOKEN_FILE} mode is {_mode_str(TOKEN_FILE)}, expected 0600"
            )
        actual_token_bytes = TOKEN_FILE.read_bytes()
        if actual_token_bytes != EXPECTED_TOKEN_BYTES:
            problems.append(
                f"{TOKEN_FILE} content changed; expected sha256={EXPECTED_TOKEN_SHA256}, "
                f"actual sha256={hashlib.sha256(actual_token_bytes).hexdigest()}"
            )

    if not AUDIT_LOG.exists():
        problems.append(f"{AUDIT_LOG} is missing")
    elif not AUDIT_LOG.is_file():
        problems.append(f"{AUDIT_LOG} is not a regular file")
    else:
        actual_audit_bytes = AUDIT_LOG.read_bytes()
        if actual_audit_bytes != EXPECTED_AUDIT_BYTES:
            problems.append(
                f"{AUDIT_LOG} content is not exact; expected {EXPECTED_AUDIT_BYTES!r}, "
                f"actual {actual_audit_bytes!r}"
            )

    assert not problems, "Final credential-rotation state is incomplete:\n- " + "\n- ".join(problems)