# test_final_state.py
import os
import stat
import subprocess
from pathlib import Path

import pytest


BASE = Path("/home/user/backup-restore-firewall")
RESTORED_RULES = Path("/home/user/backup-restore-firewall/restored/iptables-restore.rules")
ACTIVE_POLICY = Path("/home/user/backup-restore-firewall/active/firewall.policy")
CHECK_FIREWALL = Path("/home/user/backup-restore-firewall/bin/check-firewall")
VERIFY_LOG = Path("/home/user/backup-restore-firewall/verify/firewall-restore-check.log")

REQUIRED_ACTIVE_RULE = "ALLOW tcp 28731 from 10.42.18.0/24"

PRESERVED_ACTIVE_LINES = [
    "# active simulated firewall policy",
    "ALLOW tcp 22 from 10.42.0.0/16",
    "ALLOW tcp 873 from 10.42.18.0/24",
    "DENY all",
]

EXPECTED_VERIFY_LOG = (
    "active_policy=/home/user/backup-restore-firewall/active/firewall.policy\n"
    "stale_policy_retired=yes\n"
    "backup_restore_listener=allowed\n"
    "service_check=PASS\n"
)

EXPECTED_CHECK_STDOUT = "PASS active firewall allows backup restore listener\n"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"File is not valid UTF-8 text: {path}: {exc}")


def test_stale_restored_policy_original_path_is_retired():
    assert not RESTORED_RULES.exists(), (
        "The stale restored policy must be retired so the original source-of-truth-looking "
        f"path no longer exists: {RESTORED_RULES}. Move or rename it after migrating the rule."
    )


def test_active_policy_exists_and_contains_converted_allow_rule_as_exact_line():
    assert ACTIVE_POLICY.exists(), f"Missing active firewall policy file: {ACTIVE_POLICY}"
    assert ACTIVE_POLICY.is_file(), f"Active policy path is not a regular file: {ACTIVE_POLICY}"

    content = _read_text(ACTIVE_POLICY)
    lines = content.splitlines()

    assert REQUIRED_ACTIVE_RULE in lines, (
        f"{ACTIVE_POLICY} does not contain the migrated backup restore listener rule as an "
        f"exact full line: {REQUIRED_ACTIVE_RULE!r}. The service reads this active policy, "
        "not the retired restored iptables file."
    )

    assert content.count(REQUIRED_ACTIVE_RULE) == 1, (
        f"{ACTIVE_POLICY} should contain exactly one copy of the migrated rule "
        f"{REQUIRED_ACTIVE_RULE!r}, but found {content.count(REQUIRED_ACTIVE_RULE)} copies."
    )


def test_active_policy_preserves_existing_policy_semantics():
    assert ACTIVE_POLICY.exists(), f"Missing active firewall policy file: {ACTIVE_POLICY}"
    content = _read_text(ACTIVE_POLICY)
    lines = content.splitlines()

    for required_line in PRESERVED_ACTIVE_LINES:
        assert required_line in lines, (
            f"{ACTIVE_POLICY} no longer preserves required existing active policy line: "
            f"{required_line!r}. Preserve the existing active policy while adding the new allow rule."
        )

    deny_index = lines.index("DENY all")
    existing_allow_22_index = lines.index("ALLOW tcp 22 from 10.42.0.0/16")
    existing_allow_873_index = lines.index("ALLOW tcp 873 from 10.42.18.0/24")

    assert existing_allow_22_index < deny_index, (
        "Existing SSH allow rule must remain before 'DENY all' to preserve active policy semantics."
    )
    assert existing_allow_873_index < deny_index, (
        "Existing rsync allow rule must remain before 'DENY all' to preserve active policy semantics."
    )

    new_rule_index = lines.index(REQUIRED_ACTIVE_RULE)
    assert new_rule_index < deny_index, (
        f"The migrated listener allow rule {REQUIRED_ACTIVE_RULE!r} must appear before "
        "'DENY all' so it is allowed by the line-oriented active policy."
    )


def test_active_policy_uses_simple_policy_format_not_raw_iptables_restore_rule():
    assert ACTIVE_POLICY.exists(), f"Missing active firewall policy file: {ACTIVE_POLICY}"
    content = _read_text(ACTIVE_POLICY)
    lines = content.splitlines()

    stale_iptables_rule = "-A INPUT -p tcp --dport 28731 -s 10.42.18.0/24 -j ACCEPT"
    assert stale_iptables_rule not in lines, (
        f"{ACTIVE_POLICY} still contains the raw iptables restore-format rule. Convert it to "
        f"the active policy format exactly as {REQUIRED_ACTIVE_RULE!r}."
    )
    assert "COMMIT" not in lines, (
        f"{ACTIVE_POLICY} contains iptables restore syntax 'COMMIT'. The active policy should "
        "remain in the simple line-oriented firewall.policy format."
    )


def test_check_firewall_executable_succeeds_against_final_active_policy():
    assert CHECK_FIREWALL.exists(), f"Missing firewall checker executable: {CHECK_FIREWALL}"
    assert CHECK_FIREWALL.is_file(), f"Firewall checker path is not a regular file: {CHECK_FIREWALL}"

    st = CHECK_FIREWALL.stat()
    assert st.st_mode & stat.S_IXUSR, (
        f"Firewall checker is not marked executable by its owner: {CHECK_FIREWALL}"
    )
    assert os.access(CHECK_FIREWALL, os.X_OK), (
        f"Firewall checker is not executable by the current user: {CHECK_FIREWALL}"
    )

    result = subprocess.run(
        [str(CHECK_FIREWALL)],
        cwd=str(BASE),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        "The firewall service verifier must succeed after the active policy is updated and "
        f"the stale restored path is retired.\n"
        f"Command: {CHECK_FIREWALL}\n"
        f"Exit code: {result.returncode}\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert result.stdout == EXPECTED_CHECK_STDOUT, (
        "The firewall service verifier must print exactly the documented success message.\n"
        f"Expected stdout: {EXPECTED_CHECK_STDOUT!r}\n"
        f"Actual stdout:   {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert result.stderr == "", (
        f"The firewall service verifier should not emit stderr on success; got: {result.stderr!r}"
    )


def test_verification_log_exists_with_exact_required_four_lines():
    assert VERIFY_LOG.exists(), f"Missing required verification log: {VERIFY_LOG}"
    assert VERIFY_LOG.is_file(), f"Verification log path is not a regular file: {VERIFY_LOG}"

    actual = _read_text(VERIFY_LOG)

    assert actual == EXPECTED_VERIFY_LOG, (
        "Verification log must contain exactly the required four lines, with no extra "
        "whitespace, blank lines, or additional text.\n"
        f"Path: {VERIFY_LOG}\n"
        f"Expected: {EXPECTED_VERIFY_LOG!r}\n"
        f"Actual:   {actual!r}"
    )

    assert actual.splitlines() == [
        "active_policy=/home/user/backup-restore-firewall/active/firewall.policy",
        "stale_policy_retired=yes",
        "backup_restore_listener=allowed",
        "service_check=PASS",
    ], (
        "Verification log lines are not exactly in the required order or content."
    )


def test_final_state_is_not_a_stale_source_partial_success():
    assert not RESTORED_RULES.exists(), (
        f"Partial success detected: the old restored source {RESTORED_RULES} still exists. "
        "The active checker must not rely on this stale file."
    )

    active_lines = _read_text(ACTIVE_POLICY).splitlines()
    assert REQUIRED_ACTIVE_RULE in active_lines, (
        "Partial success detected: the migrated allow rule is absent from the active policy. "
        "Adding or validating the rule only in the restored iptables file is not sufficient."
    )

    log = _read_text(VERIFY_LOG)
    assert "active_policy=/home/user/backup-restore-firewall/active/firewall.policy\n" in log, (
        "Verification log does not prove the active firewall.policy was checked."
    )
    assert "/home/user/backup-restore-firewall/restored/iptables-restore.rules" not in log, (
        "Verification log references the stale restored rules path; it must document the active "
        "policy source of truth instead."
    )