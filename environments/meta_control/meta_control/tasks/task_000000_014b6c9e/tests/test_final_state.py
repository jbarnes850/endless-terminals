# test_final_state.py
from pathlib import Path

BASE = Path("/home/user/site-admin")
ACCOUNTS = Path("/home/user/site-admin/incoming/accounts")
USERS = Path("/home/user/site-admin/public/users")
ARCHIVED_DIR = Path("/home/user/site-admin/public/users/archived")

ARCHIVED_SAMUEL = Path("/home/user/site-admin/public/users/archived/samuel.lee.json")
ACTIVE_MAYA = Path("/home/user/site-admin/public/users/maya.chen.json")
ORIGINAL_SAMUEL = Path("/home/user/site-admin/incoming/accounts/samuel.lee.json")
ORIGINAL_MAYA = Path("/home/user/site-admin/incoming/accounts/maya.chen.json")
README = Path("/home/user/site-admin/incoming/accounts/README.txt")
VERIFICATION_LOG = Path("/home/user/site-admin/account_migration_check.txt")

EXPECTED_SAMUEL = (
    '{"username":"samuel.lee","full_name":"Samuel Lee","status":"stale","role":"editor"}\n'
)
EXPECTED_MAYA = (
    '{"username":"maya.chen","full_name":"Maya Chen","status":"active","role":"publisher"}\n'
)
EXPECTED_README = "Drop staged account JSON exports here before publication.\n"
EXPECTED_LOG = (
    "account migration check\n"
    "archived_exists: yes\n"
    "active_exists: yes\n"
    "incoming_json_count: 0\n"
    "verified: yes\n"
)


def read_text_exact(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"File is not valid UTF-8 text: {path}") from exc


def assert_directory(path: Path, description: str) -> None:
    assert path.exists(), f"{description} is missing: {path}"
    assert path.is_dir(), f"{description} exists but is not a directory: {path}"


def assert_file(path: Path, description: str) -> None:
    assert path.exists(), f"{description} is missing: {path}"
    assert path.is_file(), f"{description} exists but is not a regular file: {path}"


def assert_exact_file_content(path: Path, expected: str, description: str) -> None:
    assert_file(path, description)
    actual = read_text_exact(path)
    assert actual == expected, (
        f"{description} has incorrect contents: {path}\n"
        f"Expected exactly: {expected!r}\n"
        f"Actual: {actual!r}"
    )


def test_archived_directory_exists_at_required_absolute_path():
    assert_directory(
        ARCHIVED_DIR,
        "Archived users directory /home/user/site-admin/public/users/archived/",
    )


def test_account_files_were_moved_to_required_destinations():
    assert_file(
        ARCHIVED_SAMUEL,
        "Stale Samuel Lee account file at archived destination",
    )
    assert_file(
        ACTIVE_MAYA,
        "Active Maya Chen account file at public users destination",
    )

    assert not ORIGINAL_SAMUEL.exists(), (
        "Stale Samuel Lee account file still exists in incoming accounts; "
        f"it should have been moved away from: {ORIGINAL_SAMUEL}"
    )
    assert not ORIGINAL_MAYA.exists(), (
        "Active Maya Chen account file still exists in incoming accounts; "
        f"it should have been moved away from: {ORIGINAL_MAYA}"
    )


def test_incoming_accounts_directory_remains_but_contains_no_direct_json_files():
    assert_directory(
        ACCOUNTS,
        "Incoming accounts directory /home/user/site-admin/incoming/accounts/",
    )

    json_files = sorted(path.name for path in ACCOUNTS.glob("*.json"))
    assert json_files == [], (
        "Incoming accounts directory should contain zero direct .json files after migration. "
        f"Found: {json_files}"
    )


def test_moved_account_file_contents_are_preserved_exactly():
    assert_exact_file_content(
        ARCHIVED_SAMUEL,
        EXPECTED_SAMUEL,
        "Archived Samuel Lee account file",
    )
    assert_exact_file_content(
        ACTIVE_MAYA,
        EXPECTED_MAYA,
        "Active Maya Chen account file",
    )


def test_readme_remains_in_incoming_accounts_with_original_contents():
    assert_exact_file_content(
        README,
        EXPECTED_README,
        "Incoming accounts README.txt",
    )


def test_verification_log_exists_with_exact_required_five_lines_and_trailing_newline():
    assert_exact_file_content(
        VERIFICATION_LOG,
        EXPECTED_LOG,
        "Verification artifact /home/user/site-admin/account_migration_check.txt",
    )

    log_lines = read_text_exact(VERIFICATION_LOG).splitlines()
    assert len(log_lines) == 5, (
        "Verification artifact must contain exactly 5 lines. "
        f"Found {len(log_lines)} lines: {log_lines!r}"
    )


def test_verification_log_values_match_actual_final_filesystem_state():
    assert_file(
        VERIFICATION_LOG,
        "Verification artifact /home/user/site-admin/account_migration_check.txt",
    )

    actual_archived_exists = "yes" if ARCHIVED_SAMUEL.exists() else "no"
    actual_active_exists = "yes" if ACTIVE_MAYA.exists() else "no"
    actual_incoming_json_count = len(list(ACCOUNTS.glob("*.json"))) if ACCOUNTS.exists() else None

    expected_lines_from_actual_state = [
        "account migration check",
        f"archived_exists: {actual_archived_exists}",
        f"active_exists: {actual_active_exists}",
        f"incoming_json_count: {actual_incoming_json_count}",
        "verified: yes",
    ]

    actual_lines = read_text_exact(VERIFICATION_LOG).splitlines()
    assert actual_lines == expected_lines_from_actual_state, (
        "Verification artifact does not reflect the actual final filesystem state.\n"
        f"Expected lines from actual state: {expected_lines_from_actual_state!r}\n"
        f"Actual log lines: {actual_lines!r}"
    )