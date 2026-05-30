# test_final_state.py
import os
import pwd
from pathlib import Path

import pytest


BASE_DIR = Path("/home/user/release-prep")
DEPLOY_ENV = Path("/home/user/release-prep/deploy.env")
RELEASE_LEDGER = Path("/home/user/release-prep/release_ledger.log")

EXPECTED_DEPLOY_LINES = [
    "APP_NAME=inventory-api",
    "DEPLOY_ENV=production",
    "RELEASE_CHANNEL=stable",
    "REGION=us-east-2",
    "CANARY_PERCENT=10",
    "FEATURE_FLAGS=audit_logging,metrics_v2,safe_shutdown",
]

EXPECTED_LEDGER_LINES = [
    "CHECK 1 app_name_preserved=YES",
    "CHECK 2 deploy_env_production=YES",
    "CHECK 3 release_channel_stable=YES",
    "CHECK 4 region_us_east_2=YES",
    "CHECK 5 canary_percent_10=YES",
    "CHECK 6 feature_flags_valid=YES",
    "READY production_deployment_env=YES",
]

EXPECTED_DEPLOY_CONTENT = "\n".join(EXPECTED_DEPLOY_LINES) + "\n"
EXPECTED_LEDGER_CONTENT = "\n".join(EXPECTED_LEDGER_LINES) + "\n"

REQUIRED_VARIABLE_ORDER = [
    "APP_NAME",
    "DEPLOY_ENV",
    "RELEASE_CHANNEL",
    "REGION",
    "CANARY_PERCENT",
    "FEATURE_FLAGS",
]


def _user_uid_gid(username: str = "user") -> tuple[int, int]:
    try:
        entry = pwd.getpwnam(username)
    except KeyError:
        pytest.fail(f"Required OS user {username!r} does not exist")
    return entry.pw_uid, entry.pw_gid


def _user_group_ids(username: str = "user") -> set[int]:
    uid, gid = _user_uid_gid(username)
    groups = {gid}
    try:
        groups.update(os.getgrouplist(username, gid))
    except OSError as exc:
        pytest.fail(f"Could not determine group membership for user {username!r}: {exc}")
    return groups


def _is_readable_by_user(path: Path, username: str = "user") -> bool:
    uid, _gid = _user_uid_gid(username)
    groups = _user_group_ids(username)
    stat_result = path.stat()
    mode = stat_result.st_mode

    if stat_result.st_uid == uid and mode & 0o400:
        return True
    if stat_result.st_gid in groups and mode & 0o040:
        return True
    if mode & 0o004:
        return True
    return False


def _is_writable_by_user(path: Path, username: str = "user") -> bool:
    uid, _gid = _user_uid_gid(username)
    groups = _user_group_ids(username)
    stat_result = path.stat()
    mode = stat_result.st_mode

    if stat_result.st_uid == uid and mode & 0o200:
        return True
    if stat_result.st_gid in groups and mode & 0o020:
        return True
    if mode & 0o002:
        return True
    return False


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"File is not valid UTF-8 text: {path}: {exc}")
    except OSError as exc:
        pytest.fail(f"Could not read required file {path}: {exc}")


def _split_lines_allow_single_trailing_newline(text: str) -> list[str]:
    if text.endswith("\n"):
        text = text[:-1]
    return text.split("\n") if text else []


def _assert_exact_text_allow_single_trailing_newline(path: Path, expected: str) -> None:
    actual = _read_text(path)
    normalized_actual = actual[:-1] if actual.endswith("\n") else actual
    normalized_expected = expected[:-1] if expected.endswith("\n") else expected

    assert normalized_actual == normalized_expected, (
        f"{path} does not match the required final content exactly "
        "(except that one trailing newline at EOF is allowed).\n"
        f"Expected content:\n{expected!r}\n"
        f"Actual content:\n{actual!r}"
    )


def _parse_assignment_lines(lines: list[str]) -> dict[str, str]:
    parsed = {}
    for line_number, line in enumerate(lines, start=1):
        assert "=" in line, (
            f"{DEPLOY_ENV} line {line_number} is not a shell-style assignment line: {line!r}"
        )
        name, value = line.split("=", 1)
        parsed[name] = value
    return parsed


def test_release_prep_directory_still_exists():
    assert BASE_DIR.exists(), f"Required directory is missing: {BASE_DIR}"
    assert BASE_DIR.is_dir(), f"Required path exists but is not a directory: {BASE_DIR}"


def test_deploy_env_exists_regular_file_and_user_read_write():
    assert DEPLOY_ENV.exists(), f"Required final file is missing: {DEPLOY_ENV}"
    assert DEPLOY_ENV.is_file(), f"Required path exists but is not a regular file: {DEPLOY_ENV}"
    assert _is_readable_by_user(
        DEPLOY_ENV, "user"
    ), f"{DEPLOY_ENV} must be readable by the /home/user account"
    assert _is_writable_by_user(
        DEPLOY_ENV, "user"
    ), f"{DEPLOY_ENV} must be writable by the /home/user account"


def test_deploy_env_has_no_comments_blank_lines_or_extra_variables():
    content = _read_text(DEPLOY_ENV)
    lines = _split_lines_allow_single_trailing_newline(content)

    assert len(lines) == 6, (
        f"{DEPLOY_ENV} must contain exactly six assignment lines and no extra text; "
        f"found {len(lines)} lines: {lines!r}"
    )

    for line_number, line in enumerate(lines, start=1):
        assert line, f"{DEPLOY_ENV} contains a blank line at line {line_number}; remove it"
        assert not line.lstrip().startswith("#"), (
            f"{DEPLOY_ENV} contains a comment at line {line_number}: {line!r}; "
            "comments are not allowed in the final file"
        )
        assert "=" in line, (
            f"{DEPLOY_ENV} line {line_number} is not an assignment line: {line!r}"
        )
        name, _value = line.split("=", 1)
        assert name in REQUIRED_VARIABLE_ORDER, (
            f"{DEPLOY_ENV} contains an extra or invalid variable {name!r} at line "
            f"{line_number}; allowed variables are exactly {REQUIRED_VARIABLE_ORDER!r}"
        )


def test_deploy_env_required_variables_appear_once_and_in_order():
    lines = _split_lines_allow_single_trailing_newline(_read_text(DEPLOY_ENV))
    actual_names = [line.split("=", 1)[0] if "=" in line else line for line in lines]

    assert actual_names == REQUIRED_VARIABLE_ORDER, (
        f"{DEPLOY_ENV} must contain the six required variable names exactly once and "
        "in the required order.\n"
        f"Expected order: {REQUIRED_VARIABLE_ORDER!r}\n"
        f"Actual order:   {actual_names!r}"
    )


def test_app_name_is_preserved_exactly():
    lines = _split_lines_allow_single_trailing_newline(_read_text(DEPLOY_ENV))
    assignments = _parse_assignment_lines(lines)

    assert assignments.get("APP_NAME") == "inventory-api", (
        f"APP_NAME must preserve the original value 'inventory-api'; "
        f"found {assignments.get('APP_NAME')!r}"
    )


def test_production_rollout_settings_are_exact():
    lines = _split_lines_allow_single_trailing_newline(_read_text(DEPLOY_ENV))
    assignments = _parse_assignment_lines(lines)

    expected_values = {
        "DEPLOY_ENV": "production",
        "RELEASE_CHANNEL": "stable",
        "REGION": "us-east-2",
        "CANARY_PERCENT": "10",
    }

    for name, expected_value in expected_values.items():
        actual_value = assignments.get(name)
        assert actual_value == expected_value, (
            f"{name} must be {expected_value!r} for the production rollout; "
            f"found {actual_value!r}"
        )


def test_feature_flags_are_canonical_complete_no_spaces_or_duplicates():
    lines = _split_lines_allow_single_trailing_newline(_read_text(DEPLOY_ENV))
    assignments = _parse_assignment_lines(lines)
    actual = assignments.get("FEATURE_FLAGS")

    assert actual == "audit_logging,metrics_v2,safe_shutdown", (
        "FEATURE_FLAGS must be the canonical comma-separated value "
        "'audit_logging,metrics_v2,safe_shutdown'; "
        f"found {actual!r}"
    )
    assert " " not in actual, f"FEATURE_FLAGS must not contain spaces; found {actual!r}"

    flags = actual.split(",")
    assert len(flags) == len(set(flags)), (
        f"FEATURE_FLAGS must not contain duplicate flags; found {flags!r}"
    )
    for required_flag in ["audit_logging", "metrics_v2", "safe_shutdown"]:
        assert required_flag in flags, (
            f"FEATURE_FLAGS is missing required flag {required_flag!r}; found {flags!r}"
        )


def test_release_ledger_exists_and_is_regular_file():
    assert RELEASE_LEDGER.exists(), f"Required ledger file is missing: {RELEASE_LEDGER}"
    assert RELEASE_LEDGER.is_file(), (
        f"Required ledger path exists but is not a regular file: {RELEASE_LEDGER}"
    )


def test_release_ledger_has_exact_seven_required_lines_only():
    content = _read_text(RELEASE_LEDGER)
    lines = _split_lines_allow_single_trailing_newline(content)

    assert lines == EXPECTED_LEDGER_LINES, (
        f"{RELEASE_LEDGER} must contain exactly the seven required ledger lines, "
        "in order, with no extra explanatory text.\n"
        f"Expected lines: {EXPECTED_LEDGER_LINES!r}\n"
        f"Actual lines:   {lines!r}"
    )


def test_deploy_env_final_content_matches_exact_ground_truth():
    _assert_exact_text_allow_single_trailing_newline(DEPLOY_ENV, EXPECTED_DEPLOY_CONTENT)


def test_release_ledger_final_content_matches_exact_ground_truth():
    _assert_exact_text_allow_single_trailing_newline(RELEASE_LEDGER, EXPECTED_LEDGER_CONTENT)


def test_stop_condition_both_files_match_exact_final_state():
    deploy_actual = _read_text(DEPLOY_ENV)
    ledger_actual = _read_text(RELEASE_LEDGER)

    deploy_normalized = deploy_actual[:-1] if deploy_actual.endswith("\n") else deploy_actual
    ledger_normalized = ledger_actual[:-1] if ledger_actual.endswith("\n") else ledger_actual
    expected_deploy_normalized = EXPECTED_DEPLOY_CONTENT[:-1]
    expected_ledger_normalized = EXPECTED_LEDGER_CONTENT[:-1]

    assert deploy_normalized == expected_deploy_normalized and ledger_normalized == expected_ledger_normalized, (
        "Final stop condition not met: both deliverable files must match the exact "
        "ground-truth final state, allowing only a single trailing newline at EOF.\n"
        f"Expected {DEPLOY_ENV}: {EXPECTED_DEPLOY_CONTENT!r}\n"
        f"Actual   {DEPLOY_ENV}: {deploy_actual!r}\n"
        f"Expected {RELEASE_LEDGER}: {EXPECTED_LEDGER_CONTENT!r}\n"
        f"Actual   {RELEASE_LEDGER}: {ledger_actual!r}"
    )