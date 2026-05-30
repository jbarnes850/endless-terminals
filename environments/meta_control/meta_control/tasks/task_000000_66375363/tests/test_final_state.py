# test_final_state.py
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPORT = Path("/home/user/backup_audit/integrity_process_report.tsv")
WORKER = Path("/home/user/backup_audit/backup-integrity-worker")
MANIFEST_DIR = Path("/home/user/backup_audit/manifests")

HEADER = "timestamp_utc\tpid\tstatus\tevidence"
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")

EXPECTED_PRODUCTION_ARGS = [
    str(WORKER),
    "--role",
    "verifier",
    "--dataset",
    "vault-prod-west",
    "--epoch",
    "2024Q4",
    "--manifest",
    str(MANIFEST_DIR / "vault-prod-west-2024Q4.sha256"),
    "--mode",
    "verify",
    "--require-online",
    "true",
]

REQUIRED_CMD_FRAGMENTS = [
    "backup-integrity-worker",
    "--role",
    "verifier",
    "--dataset",
    "vault-prod-west",
    "--epoch",
    "2024Q4",
    "--mode",
    "verify",
]

FORBIDDEN_CMD_SEQUENCES = [
    ["--mode", "dry-run"],
    ["--role", "helper"],
    ["--dataset", "vault-prod-east"],
    ["--epoch", "2024Q3"],
]

EVIDENCE_LABELS = [
    "selected_cmd=",
    "accepted_dataset=",
    "accepted_epoch=",
    "rejected=",
]

REJECTION_REASON_SUBSTRINGS = [
    "wrong-dataset",
    "dry-run",
    "stale-epoch",
    "helper",
]


def _read_cmdline_for_pid(pid: int):
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None

    if not raw:
        return None

    parts = [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]
    return parts or None


def _iter_user_process_cmdlines():
    current_uid = os.getuid()

    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue

        try:
            st = pid_dir.stat()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue

        if st.st_uid != current_uid:
            continue

        cmdline = _read_cmdline_for_pid(int(pid_dir.name))
        if cmdline:
            yield int(pid_dir.name), cmdline


def _contains_contiguous_sequence(items, sequence):
    n = len(sequence)
    return any(items[i : i + n] == sequence for i in range(0, len(items) - n + 1))


def _process_matches_expected_args(cmdline, expected_args):
    """
    The worker is a shell script, so cmdline may be either:
      ['/home/user/.../backup-integrity-worker', ...]
    or:
      ['/bin/sh', '/home/user/.../backup-integrity-worker', ...]
    Accept the expected script path and argument sequence wherever it appears
    contiguously in argv.
    """
    return _contains_contiguous_sequence(cmdline, expected_args)


@pytest.fixture(scope="module")
def report_lines():
    assert REPORT.exists(), f"Missing required final report file: {REPORT}"
    assert REPORT.is_file(), f"Report path exists but is not a regular file: {REPORT}"

    raw = REPORT.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Report file {REPORT} is not valid UTF-8 text: {exc}")

    assert text, f"Report file {REPORT} is empty"
    assert text.endswith("\n"), (
        f"Report file {REPORT} should end with a newline after the single data line"
    )

    lines = text.splitlines()
    assert len(lines) == 2, (
        f"Report file {REPORT} must contain exactly two lines: "
        f"the header and one data line. Found {len(lines)} line(s): {lines!r}"
    )
    assert all(line.strip() == line for line in lines), (
        f"Report lines must not have leading/trailing whitespace: {lines!r}"
    )
    assert all(line for line in lines), (
        f"Report file {REPORT} must not contain blank lines: {lines!r}"
    )

    return lines


@pytest.fixture(scope="module")
def report_fields(report_lines):
    header, data = report_lines

    assert header == HEADER, (
        "Report header is incorrect.\n"
        f"Expected exactly: {HEADER!r}\n"
        f"Actual:           {header!r}"
    )

    fields = data.split("\t")
    assert len(fields) == 4, (
        "Report data line must have exactly four tab-separated fields: "
        "timestamp_utc, pid, status, evidence.\n"
        f"Actual field count: {len(fields)}\n"
        f"Data line: {data!r}"
    )

    timestamp_utc, pid_text, status, evidence = fields
    return {
        "timestamp_utc": timestamp_utc,
        "pid_text": pid_text,
        "status": status,
        "evidence": evidence,
    }


def test_report_has_exact_two_line_tsv_shape(report_lines):
    assert report_lines[0] == HEADER
    assert len(report_lines[1].split("\t")) == 4


def test_timestamp_pid_and_status_fields_are_valid(report_fields):
    timestamp_utc = report_fields["timestamp_utc"]
    pid_text = report_fields["pid_text"]
    status = report_fields["status"]

    assert TIMESTAMP_RE.match(timestamp_utc), (
        "timestamp_utc must be in ISO-8601 UTC basic form "
        "YYYY-MM-DDTHH:MM:SSZ.\n"
        f"Actual timestamp: {timestamp_utc!r}"
    )

    try:
        parsed = datetime.strptime(timestamp_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        pytest.fail(f"timestamp_utc has invalid date/time values: {timestamp_utc!r}: {exc}")

    now = datetime.now(timezone.utc)
    assert parsed <= now, (
        f"timestamp_utc should not be in the future. "
        f"Report timestamp: {timestamp_utc!r}; current UTC: {now:%Y-%m-%dT%H:%M:%SZ}"
    )

    assert pid_text.isdigit(), f"pid field must be numeric, got: {pid_text!r}"
    assert int(pid_text) > 0, f"pid field must be a positive process id, got: {pid_text!r}"

    assert status == "verified", (
        f"status field must be exactly 'verified', got: {status!r}"
    )


def test_report_pid_is_live_correct_production_verifier_process(report_fields):
    pid = int(report_fields["pid_text"])
    cmdline = _read_cmdline_for_pid(pid)

    assert cmdline is not None, (
        f"Reported PID {pid} is not a readable live process. "
        "The PID in the report must still belong to the selected running verifier."
    )

    assert _process_matches_expected_args(cmdline, EXPECTED_PRODUCTION_ARGS), (
        f"Reported PID {pid} does not have the exact expected production verifier argv.\n"
        f"Expected contiguous argv sequence: {EXPECTED_PRODUCTION_ARGS!r}\n"
        f"Actual cmdline: {' '.join(cmdline)!r}"
    )

    cmd_text = " ".join(cmdline)

    for fragment in REQUIRED_CMD_FRAGMENTS:
        assert fragment in cmd_text, (
            f"Reported PID {pid} is missing required command fragment {fragment!r}.\n"
            f"Actual cmdline: {cmd_text!r}"
        )

    for sequence in FORBIDDEN_CMD_SEQUENCES:
        assert not _contains_contiguous_sequence(cmdline, sequence), (
            f"Reported PID {pid} appears to be a decoy because argv contains "
            f"forbidden sequence {sequence!r}.\n"
            f"Actual cmdline: {cmdline!r}"
        )


def test_only_one_live_user_process_matches_the_reported_production_identity(report_fields):
    reported_pid = int(report_fields["pid_text"])

    matches = [
        (pid, cmdline)
        for pid, cmdline in _iter_user_process_cmdlines()
        if _process_matches_expected_args(cmdline, EXPECTED_PRODUCTION_ARGS)
    ]

    assert len(matches) == 1, (
        "There must be exactly one live user-owned process matching the production "
        "verifier identity at final verification time.\n"
        f"Found {len(matches)} match(es):\n"
        + "\n".join(f"{pid}: {' '.join(cmd)}" for pid, cmd in matches)
    )

    actual_pid = matches[0][0]
    assert reported_pid == actual_pid, (
        "Report PID does not identify the single live production verifier.\n"
        f"Reported PID: {reported_pid}\n"
        f"Actual production verifier PID: {actual_pid}\n"
        f"Actual cmdline: {' '.join(matches[0][1])}"
    )


def test_evidence_contains_required_labels_exactly_once_with_nonempty_values(report_fields):
    evidence = report_fields["evidence"]

    assert evidence, "evidence field must be non-empty"
    assert "\t" not in evidence and "\n" not in evidence, (
        f"evidence must be a compact single TSV field, got: {evidence!r}"
    )

    for label in EVIDENCE_LABELS:
        count = evidence.count(label)
        assert count == 1, (
            f"evidence must contain label {label!r} exactly once; found {count} time(s).\n"
            f"Evidence: {evidence!r}"
        )

    label_positions = sorted((evidence.index(label), label) for label in EVIDENCE_LABELS)

    for idx, (start, label) in enumerate(label_positions):
        value_start = start + len(label)
        value_end = label_positions[idx + 1][0] if idx + 1 < len(label_positions) else len(evidence)
        value = evidence[value_start:value_end].strip(" ;,")

        assert value, (
            f"evidence label {label!r} must have a non-empty value after '='.\n"
            f"Evidence: {evidence!r}"
        )


def test_evidence_demonstrates_correct_selection_and_rejection_reasoning(report_fields):
    evidence = report_fields["evidence"]
    evidence_lower = evidence.lower()

    assert "vault-prod-west" in evidence, (
        "evidence must indicate the accepted production dataset vault-prod-west.\n"
        f"Evidence: {evidence!r}"
    )
    assert "2024Q4" in evidence, (
        "evidence must indicate the accepted production epoch 2024Q4.\n"
        f"Evidence: {evidence!r}"
    )
    assert "backup-integrity-worker" in evidence, (
        "evidence selected_cmd value should identify the backup-integrity-worker command.\n"
        f"Evidence: {evidence!r}"
    )

    rejection_hits = [
        reason for reason in REJECTION_REASON_SUBSTRINGS if reason in evidence_lower
    ]
    assert len(rejection_hits) >= 2, (
        "evidence rejected= value must mention at least two rejected candidate reasons "
        "from: wrong-dataset, dry-run, stale-epoch, helper.\n"
        f"Matched reasons: {rejection_hits!r}\n"
        f"Evidence: {evidence!r}"
    )