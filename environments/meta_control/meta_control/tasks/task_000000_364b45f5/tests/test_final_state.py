# test_final_state.py
from pathlib import Path


BASE_DIR = Path("/home/user/process_audit")
LOG_PATH = Path("/home/user/process_audit/worker_events.log")
SUMMARY_PATH = Path("/home/user/process_audit/active_worker_summary.txt")
VERIFICATION_PATH = Path("/home/user/process_audit/verification.log")

EXPECTED_SUMMARY_CONTENT = (
    "ACTIVE_WORKER_SUMMARY\n"
    "source=/home/user/process_audit/worker_events.log\n"
    "active_count=3\n"
    "PID=2407 WORKER=metrics-epsilon STARTED_AT=2026-02-14T09:23:40Z DETAIL=batch=monitor queue=metrics\n"
    "PID=2408 WORKER=enricher-gamma STARTED_AT=2026-02-14T09:26:35Z DETAIL=batch=recover queue=enrich\n"
    "PID=2409 WORKER=shipper-delta STARTED_AT=2026-02-14T09:29:30Z DETAIL=batch=late queue=ship\n"
    "verification=manual_artifact_checked\n"
)

EXPECTED_VERIFICATION_CONTENT = (
    "checked_input=/home/user/process_audit/worker_events.log\n"
    "checked_output=/home/user/process_audit/active_worker_summary.txt\n"
    "status=verified\n"
)

EXPECTED_ACTIVE_PIDS = ["2407", "2408", "2409"]
STOPPED_PIDS = ["2401", "2402", "2403", "2404", "2405", "2406"]


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        raise AssertionError(f"Required file is missing: {path}") from None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AssertionError(f"Required file is missing: {path}") from None


def _assert_regular_file(path: Path) -> None:
    assert path.exists(), f"Required file is missing: {path}"
    assert path.is_file(), f"Required path exists but is not a regular file: {path}"


def _derive_active_workers_from_log() -> list[tuple[int, str, str, str]]:
    """
    Return active PID records from the authoritative lifecycle log.

    A PID is active only when its most recent event is START.  For active PIDs,
    the timestamp/detail must come from that most recent START event.
    """
    _assert_regular_file(LOG_PATH)

    active_by_pid: dict[int, tuple[str, str, str]] = {}

    log_text = _read_text(LOG_PATH)
    assert log_text.endswith("\n"), f"{LOG_PATH} must end with a newline"

    for line_number, line in enumerate(log_text.splitlines(), start=1):
        fields = line.split("|")
        assert len(fields) == 5, (
            f"{LOG_PATH} line {line_number} should have exactly 5 pipe-delimited "
            f"fields, but got {len(fields)} fields in {line!r}"
        )

        timestamp, pid_text, worker_name, event, detail = fields
        try:
            pid = int(pid_text)
        except ValueError:
            raise AssertionError(
                f"{LOG_PATH} line {line_number} has a non-numeric PID: {pid_text!r}"
            ) from None

        if event == "START":
            active_by_pid[pid] = (worker_name, timestamp, detail)
        elif event == "STOP":
            active_by_pid.pop(pid, None)
        else:
            raise AssertionError(
                f"{LOG_PATH} line {line_number} has an unexpected lifecycle event: {event!r}"
            )

    return [
        (pid, worker_name, timestamp, detail)
        for pid, (worker_name, timestamp, detail) in sorted(active_by_pid.items())
    ]


def test_required_output_files_exist_as_regular_files():
    assert BASE_DIR.exists(), f"Required directory is missing: {BASE_DIR}"
    assert BASE_DIR.is_dir(), f"Required path exists but is not a directory: {BASE_DIR}"

    _assert_regular_file(SUMMARY_PATH)
    _assert_regular_file(VERIFICATION_PATH)


def test_summary_file_matches_exact_required_final_contents_byte_for_byte():
    _assert_regular_file(SUMMARY_PATH)

    actual = _read_bytes(SUMMARY_PATH)
    expected = EXPECTED_SUMMARY_CONTENT.encode("utf-8")

    assert actual == expected, (
        f"{SUMMARY_PATH} does not exactly match the required final report. "
        "It must contain only the required lines, with active_count=3, active "
        "PIDs 2407/2408/2409 in ascending numeric order, no stopped PIDs, no "
        "blank lines, no trailing spaces, and a final newline."
    )


def test_summary_semantics_match_worker_lifecycle_log():
    derived = _derive_active_workers_from_log()
    expected_derived = [
        (2407, "metrics-epsilon", "2026-02-14T09:23:40Z", "batch=monitor queue=metrics"),
        (2408, "enricher-gamma", "2026-02-14T09:26:35Z", "batch=recover queue=enrich"),
        (2409, "shipper-delta", "2026-02-14T09:29:30Z", "batch=late queue=ship"),
    ]

    assert derived == expected_derived, (
        f"The authoritative lifecycle log indicates active workers {expected_derived!r}, "
        f"but derived {derived!r}. The summary must be based on PIDs whose most "
        "recent lifecycle event is START."
    )

    summary_text = _read_text(SUMMARY_PATH)
    expected_lines_from_log = [
        "ACTIVE_WORKER_SUMMARY",
        "source=/home/user/process_audit/worker_events.log",
        f"active_count={len(derived)}",
        *[
            f"PID={pid} WORKER={worker_name} STARTED_AT={timestamp} DETAIL={detail}"
            for pid, worker_name, timestamp, detail in derived
        ],
        "verification=manual_artifact_checked",
    ]

    assert summary_text.splitlines() == expected_lines_from_log, (
        f"{SUMMARY_PATH} is not consistent with the lifecycle pattern in {LOG_PATH}. "
        "Only PIDs whose most recent event is START should be listed, using the "
        "timestamp and detail from that START event, sorted by numeric PID."
    )


def test_summary_contains_no_stopped_pids_and_active_pids_are_sorted():
    _assert_regular_file(SUMMARY_PATH)
    lines = _read_text(SUMMARY_PATH).splitlines()

    pid_lines = [line for line in lines if line.startswith("PID=")]
    actual_pids = [line.split(" ", 1)[0].removeprefix("PID=") for line in pid_lines]

    assert actual_pids == EXPECTED_ACTIVE_PIDS, (
        f"{SUMMARY_PATH} has the wrong active PID list or order. Expected exactly "
        f"{EXPECTED_ACTIVE_PIDS} sorted by numeric PID, but found {actual_pids}."
    )

    for stopped_pid in STOPPED_PIDS:
        assert f"PID={stopped_pid} " not in _read_text(SUMMARY_PATH), (
            f"{SUMMARY_PATH} incorrectly includes stopped PID {stopped_pid}. "
            "A PID with a later STOP event is not active."
        )


def test_summary_format_has_no_blank_lines_extra_whitespace_or_extra_columns():
    _assert_regular_file(SUMMARY_PATH)
    content = _read_text(SUMMARY_PATH)

    assert content.endswith("\n"), f"{SUMMARY_PATH} must end with a newline"
    assert "\n\n" not in content, f"{SUMMARY_PATH} must not contain blank lines"

    lines = content.splitlines()
    assert len(lines) == 7, (
        f"{SUMMARY_PATH} must contain exactly 7 lines: header, source, active_count, "
        "3 active PID lines, and verification footer"
    )

    for index, line in enumerate(lines, start=1):
        assert line == line.rstrip(" \t"), (
            f"{SUMMARY_PATH} line {index} has trailing whitespace: {line!r}"
        )
        assert line == line.lstrip(" \t"), (
            f"{SUMMARY_PATH} line {index} has leading whitespace: {line!r}"
        )

    assert lines[0] == "ACTIVE_WORKER_SUMMARY", (
        f"{SUMMARY_PATH} line 1 must be exactly 'ACTIVE_WORKER_SUMMARY'"
    )
    assert lines[1] == "source=/home/user/process_audit/worker_events.log", (
        f"{SUMMARY_PATH} line 2 must identify the exact source log path"
    )
    assert lines[2] == "active_count=3", (
        f"{SUMMARY_PATH} line 3 must be exactly 'active_count=3'"
    )
    assert lines[-1] == "verification=manual_artifact_checked", (
        f"{SUMMARY_PATH} final line must be exactly "
        "'verification=manual_artifact_checked'"
    )


def test_verification_log_matches_exact_required_contents_byte_for_byte():
    _assert_regular_file(VERIFICATION_PATH)

    actual = _read_bytes(VERIFICATION_PATH)
    expected = EXPECTED_VERIFICATION_CONTENT.encode("utf-8")

    assert actual == expected, (
        f"{VERIFICATION_PATH} does not exactly match the required verification note. "
        "It must contain exactly the three required lines, no blank lines, no extra "
        "spaces, and a final newline."
    )