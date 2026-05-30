# test_final_state.py
from pathlib import Path

import pytest


LAB = Path("/home/user/automation_lab")
OUT = LAB / "out"
CRONTAB = OUT / "user.crontab"
SYSTEMD_USER = OUT / "systemd-user"
VERIFICATION_LOG = OUT / "verification.log"

EXPECTED_CRONTAB = (
    "SHELL=/bin/bash\n"
    "PATH=/usr/local/bin:/usr/bin:/bin\n"
    "17 2 * * * cd /home/user/automation_lab && /bin/bash scripts/backup_reports.sh >> "
    "/home/user/automation_lab/logs/backup_reports.log 2>&1 # backup_reports: "
    "Archive generated reporting CSV files\n"
    "*/20 8-18 * * 1-5 cd /home/user/automation_lab && /bin/bash scripts/partner_sync.sh >> "
    "/home/user/automation_lab/logs/partner_sync.log 2>&1 # partner_sync: "
    "Synchronize partner feed during business hours\n"
)

EXPECTED_SYSTEMD_FILES = {
    "cache_warm.service": (
        "[Unit]\n"
        "Description=Warm API cache before morning traffic\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        "WorkingDirectory=/home/user/automation_lab\n"
        "ExecStart=/bin/bash scripts/cache_warm.sh\n"
    ),
    "cache_warm.timer": (
        "[Unit]\n"
        "Description=Timer for Warm API cache before morning traffic\n"
        "\n"
        "[Timer]\n"
        "OnCalendar=*-*-* 04:45:00\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    ),
    "inventory_snapshot.service": (
        "[Unit]\n"
        "Description=Capture weekday inventory snapshot\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        "WorkingDirectory=/home/user/automation_lab\n"
        "ExecStart=/bin/bash scripts/inventory_snapshot.sh\n"
    ),
    "inventory_snapshot.timer": (
        "[Unit]\n"
        "Description=Timer for Capture weekday inventory snapshot\n"
        "\n"
        "[Timer]\n"
        "OnCalendar=Mon..Fri 06:10\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    ),
}

EXPECTED_VERIFICATION_LOG = (
    "command_status=ok\n"
    "artifact_presence=ok\n"
    "cron_validity=ok\n"
    "systemd_validity=ok\n"
    "semantic_result=ok\n"
)

ENABLED_WORKFLOW_IDS = {
    "backup_reports",
    "cache_warm",
    "inventory_snapshot",
    "partner_sync",
}
CRON_WORKFLOW_IDS = {"backup_reports", "partner_sync"}
SYSTEMD_WORKFLOW_IDS = {"cache_warm", "inventory_snapshot"}
DISABLED_WORKFLOW_ID = "legacy_cleanup"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"{path} must be a valid UTF-8 text file, but decoding failed: {exc}")


def test_required_deliverable_locations_exist_with_correct_types() -> None:
    assert CRONTAB.exists(), f"Missing required cron deliverable: {CRONTAB}"
    assert CRONTAB.is_file(), f"Cron deliverable exists but is not a regular file: {CRONTAB}"

    assert SYSTEMD_USER.exists(), f"Missing required systemd-user directory: {SYSTEMD_USER}"
    assert SYSTEMD_USER.is_dir(), (
        f"Systemd deliverable path exists but is not a directory: {SYSTEMD_USER}"
    )

    assert VERIFICATION_LOG.exists(), (
        f"Missing required verification log deliverable: {VERIFICATION_LOG}"
    )
    assert VERIFICATION_LOG.is_file(), (
        f"Verification log exists but is not a regular file: {VERIFICATION_LOG}"
    )


def test_user_crontab_content_is_exactly_expected() -> None:
    assert CRONTAB.exists(), f"Missing required cron deliverable: {CRONTAB}"
    actual = _read_text(CRONTAB)

    assert actual == EXPECTED_CRONTAB, (
        f"{CRONTAB} does not exactly match the expected final cron content. "
        "It must have the exact two-line header, exactly the enabled cron workflows "
        "backup_reports and partner_sync, sorted lexicographically by ID, with the "
        "required command/log/comment format and a trailing newline."
    )


def test_user_crontab_has_no_disabled_or_systemd_only_workflows() -> None:
    assert CRONTAB.exists(), f"Missing required cron deliverable: {CRONTAB}"
    actual = _read_text(CRONTAB)

    forbidden_ids = {DISABLED_WORKFLOW_ID, "cache_warm", "inventory_snapshot"}
    present_forbidden = sorted(workflow_id for workflow_id in forbidden_ids if workflow_id in actual)

    assert not present_forbidden, (
        f"{CRONTAB} contains workflow IDs that must not appear in cron output: "
        + ", ".join(present_forbidden)
    )


def test_systemd_user_directory_contains_exact_expected_files_only() -> None:
    assert SYSTEMD_USER.exists(), f"Missing required systemd-user directory: {SYSTEMD_USER}"
    assert SYSTEMD_USER.is_dir(), (
        f"Systemd deliverable path exists but is not a directory: {SYSTEMD_USER}"
    )

    actual_files = {
        path.name
        for path in SYSTEMD_USER.iterdir()
        if path.is_file()
    }
    expected_files = set(EXPECTED_SYSTEMD_FILES)

    missing = sorted(expected_files - actual_files)
    extra = sorted(actual_files - expected_files)

    assert not missing, (
        f"Missing required systemd user unit files under {SYSTEMD_USER}: "
        + ", ".join(missing)
    )
    assert not extra, (
        f"Unexpected extra files under {SYSTEMD_USER}; only enabled systemd workflows "
        "may have .service/.timer files: "
        + ", ".join(extra)
    )


@pytest.mark.parametrize("filename, expected_content", EXPECTED_SYSTEMD_FILES.items())
def test_systemd_unit_file_content_is_exactly_expected(
    filename: str, expected_content: str
) -> None:
    path = SYSTEMD_USER / filename

    assert path.exists(), f"Missing required systemd unit file: {path}"
    assert path.is_file(), f"Systemd unit path exists but is not a regular file: {path}"

    actual = _read_text(path)
    assert actual == expected_content, (
        f"{path} does not exactly match the expected final content. "
        "Check section order, field order, descriptions, commands, OnCalendar values, "
        "blank lines, and trailing newline."
    )


def test_systemd_outputs_do_not_include_disabled_or_cron_only_workflows() -> None:
    assert SYSTEMD_USER.exists(), f"Missing required systemd-user directory: {SYSTEMD_USER}"

    forbidden_ids = {DISABLED_WORKFLOW_ID, "backup_reports", "partner_sync"}
    offenders = []

    for path in SYSTEMD_USER.iterdir():
        if not path.is_file():
            continue

        if any(workflow_id in path.name for workflow_id in forbidden_ids):
            offenders.append(str(path))
            continue

        content = _read_text(path)
        for workflow_id in forbidden_ids:
            if workflow_id in content:
                offenders.append(f"{path} contains {workflow_id}")

    assert not offenders, (
        "Systemd output contains disabled or cron-only workflows, which must not be "
        "rendered as user units: " + "; ".join(offenders)
    )


def test_verification_log_content_is_exactly_expected() -> None:
    assert VERIFICATION_LOG.exists(), (
        f"Missing required verification log deliverable: {VERIFICATION_LOG}"
    )
    actual = _read_text(VERIFICATION_LOG)

    assert actual == EXPECTED_VERIFICATION_LOG, (
        f"{VERIFICATION_LOG} must contain exactly the five required ok lines in order: "
        "command_status, artifact_presence, cron_validity, systemd_validity, "
        "semantic_result."
    )


def test_disabled_workflow_appears_nowhere_in_final_deliverables() -> None:
    paths_to_check = [CRONTAB, VERIFICATION_LOG]
    if SYSTEMD_USER.exists() and SYSTEMD_USER.is_dir():
        paths_to_check.extend(path for path in SYSTEMD_USER.rglob("*") if path.is_file())

    offenders = []
    for path in paths_to_check:
        assert path.exists(), f"Required deliverable path is missing while checking semantics: {path}"
        if DISABLED_WORKFLOW_ID in path.name:
            offenders.append(str(path))
            continue
        content = _read_text(path)
        if DISABLED_WORKFLOW_ID in content:
            offenders.append(str(path))

    assert not offenders, (
        f"Disabled workflow {DISABLED_WORKFLOW_ID!r} must not appear in any final "
        "deliverable, but it was found in: " + ", ".join(offenders)
    )


def test_enabled_workflows_are_covered_exactly_once_by_expected_scheduler_outputs() -> None:
    cron_content = _read_text(CRONTAB)

    cron_counts = {
        workflow_id: cron_content.count(f"# {workflow_id}:")
        for workflow_id in ENABLED_WORKFLOW_IDS
    }

    systemd_filenames = {
        path.name
        for path in SYSTEMD_USER.iterdir()
        if path.is_file()
    }

    systemd_counts = {
        workflow_id: (
            int(f"{workflow_id}.service" in systemd_filenames)
            + int(f"{workflow_id}.timer" in systemd_filenames)
        )
        for workflow_id in ENABLED_WORKFLOW_IDS
    }

    assert cron_counts["backup_reports"] == 1, (
        "Enabled cron workflow backup_reports must appear exactly once in user.crontab"
    )
    assert cron_counts["partner_sync"] == 1, (
        "Enabled cron workflow partner_sync must appear exactly once in user.crontab"
    )
    assert cron_counts["cache_warm"] == 0, (
        "Systemd workflow cache_warm must not appear as a cron entry"
    )
    assert cron_counts["inventory_snapshot"] == 0, (
        "Systemd workflow inventory_snapshot must not appear as a cron entry"
    )

    assert systemd_counts["cache_warm"] == 2, (
        "Enabled systemd workflow cache_warm must have exactly one .service and one .timer"
    )
    assert systemd_counts["inventory_snapshot"] == 2, (
        "Enabled systemd workflow inventory_snapshot must have exactly one .service and one .timer"
    )
    assert systemd_counts["backup_reports"] == 0, (
        "Cron workflow backup_reports must not have systemd unit files"
    )
    assert systemd_counts["partner_sync"] == 0, (
        "Cron workflow partner_sync must not have systemd unit files"
    )