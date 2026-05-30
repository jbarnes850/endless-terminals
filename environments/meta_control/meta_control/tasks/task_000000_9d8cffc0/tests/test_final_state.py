# test_final_state.py
import csv
import subprocess
from pathlib import Path



ROLLOUT = Path("/home/user/rollout")
INCOMING_EVENTS = Path("/home/user/rollout/incoming/events.csv")
NORMALIZED = Path("/home/user/rollout/staging/events.normalized.csv")
REJECTED = Path("/home/user/rollout/staging/events.rejected.csv")
CHECKER = Path("/home/user/rollout/bin/check_rollout.py")
VERIFY_LOG = Path("/home/user/rollout/logs/rollout_verify.log")

EXPECTED_INCOMING = (
    "event_id,user_id,event_type,event_ts,amount\n"
    "1001,u-17,purchase,2025-02-17T09:00:00Z,42.50\n"
    "1002,u-18,unknown,2025-02-17T09:01:15Z,0\n"
    "1003,u-19,signup,2025-02-17T09:03:21Z,0\n"
    "1004,u-20,purchase,2025-02-17T09:05:00Z,18.75\n"
)

EXPECTED_NORMALIZED = (
    "release_id,event_id,user_id,event_type,event_ts,amount_cents\n"
    "2025-02-17-a,1001,u-17,purchase,2025-02-17T09:00:00Z,4250\n"
    "2025-02-17-a,1002,u-18,unknown,2025-02-17T09:01:15Z,0\n"
    "2025-02-17-a,1003,u-19,signup,2025-02-17T09:03:21Z,0\n"
    "2025-02-17-a,1004,u-20,purchase,2025-02-17T09:05:00Z,1875\n"
)

EXPECTED_REJECTED = (
    "event_id,user_id,event_type,event_ts,amount,reject_reason\n"
)

EXPECTED_VERIFY_LOG = (
    "deployment_status=ok\n"
    "normalized_rows=4\n"
    "rejected_rows=0\n"
)


def _assert_file_exists(path: Path) -> None:
    assert path.exists(), f"Missing required final file: {path}"
    assert path.is_file(), f"Required final path is not a regular file: {path}"


def _read_text(path: Path) -> str:
    _assert_file_exists(path)
    return path.read_text(encoding="utf-8")


def _read_csv_rows(path: Path):
    _assert_file_exists(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _assert_exact_file_contents(path: Path, expected: str, description: str) -> None:
    actual = _read_text(path)
    assert actual == expected, (
        f"{description} has incorrect final contents: {path}\n"
        f"Expected exact contents:\n{expected!r}\n"
        f"Actual contents:\n{actual!r}"
    )


def test_source_events_csv_has_recoverable_record_fixed_to_unknown():
    _assert_exact_file_contents(
        INCOMING_EVENTS,
        EXPECTED_INCOMING,
        "Source events CSV",
    )

    rows = _read_csv_rows(INCOMING_EVENTS)
    row_1002 = next((row for row in rows if row.get("event_id") == "1002"), None)
    assert row_1002 is not None, (
        f"{INCOMING_EVENTS} must still contain source record event_id=1002"
    )
    assert row_1002.get("event_type") == "unknown", (
        f"{INCOMING_EVENTS} must have event_type='unknown' for event_id=1002, "
        f"but found {row_1002.get('event_type')!r}. The recoverable bad source "
        "record was not fixed correctly."
    )


def test_staging_outputs_match_expected_final_regenerated_deployment_state():
    _assert_exact_file_contents(
        NORMALIZED,
        EXPECTED_NORMALIZED,
        "Normalized staging output",
    )
    _assert_exact_file_contents(
        REJECTED,
        EXPECTED_REJECTED,
        "Rejected staging output",
    )

    normalized_rows = _read_csv_rows(NORMALIZED)
    rejected_rows = _read_csv_rows(REJECTED)

    assert len(normalized_rows) == 4, (
        f"{NORMALIZED} must contain exactly 4 data rows after final deployment, "
        f"but contains {len(normalized_rows)}."
    )
    assert len(rejected_rows) == 0, (
        f"{REJECTED} must contain 0 data rows after the source fix and rerun, "
        f"but contains {len(rejected_rows)}."
    )

    row_1002 = next((row for row in normalized_rows if row.get("event_id") == "1002"), None)
    assert row_1002 is not None, (
        f"{NORMALIZED} must contain normalized record event_id=1002 after rerun."
    )
    assert row_1002 == {
        "release_id": "2025-02-17-a",
        "event_id": "1002",
        "user_id": "u-18",
        "event_type": "unknown",
        "event_ts": "2025-02-17T09:01:15Z",
        "amount_cents": "0",
    }, (
        f"{NORMALIZED} has incorrect normalized event_id=1002 row. "
        f"Expected event_type unknown and release_id 2025-02-17-a; got {row_1002!r}."
    )


def test_final_rollout_checker_succeeds():
    assert CHECKER.exists(), f"Missing targeted verification checker: {CHECKER}"
    assert CHECKER.is_file(), f"Targeted verification checker is not a file: {CHECKER}"

    result = subprocess.run(
        [str(CHECKER)],
        cwd=str(ROLLOUT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, (
        f"Final targeted checker {CHECKER} must succeed, but exited with "
        f"{result.returncode}.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
        "This usually means staging was not regenerated after fixing event_id=1002, "
        "or rejected rows remain."
    )


def test_rollout_verification_log_exists_with_exact_three_line_format_and_values():
    logs_dir = Path("/home/user/rollout/logs")
    assert logs_dir.exists(), f"Missing required log directory: {logs_dir}"
    assert logs_dir.is_dir(), f"Log path exists but is not a directory: {logs_dir}"

    _assert_file_exists(VERIFY_LOG)
    actual = _read_text(VERIFY_LOG)

    assert actual == EXPECTED_VERIFY_LOG, (
        f"{VERIFY_LOG} must contain exactly three lines and a normal final newline:\n"
        "deployment_status=ok\n"
        "normalized_rows=4\n"
        "rejected_rows=0\n"
        "No extra fields, blank lines, or different values are allowed.\n"
        f"Actual contents:\n{actual!r}"
    )

    lines = actual.splitlines()
    assert lines == [
        "deployment_status=ok",
        "normalized_rows=4",
        "rejected_rows=0",
    ], (
        f"{VERIFY_LOG} has incorrect line structure. Expected exactly three "
        f"nonblank key=value lines, got {lines!r}."
    )

    for line in lines:
        assert line.count("=") == 1, (
            f"{VERIFY_LOG} line {line!r} must contain exactly one '=' separator."
        )
        key, value = line.split("=")
        assert key in {"deployment_status", "normalized_rows", "rejected_rows"}, (
            f"{VERIFY_LOG} contains unexpected field {key!r}."
        )
        if key in {"normalized_rows", "rejected_rows"}:
            assert value.isdecimal(), (
                f"{VERIFY_LOG} field {key!r} must be a decimal integer, got {value!r}."
            )


def test_verification_log_counts_match_final_staging_data_rows():
    log_text = _read_text(VERIFY_LOG)
    log_values = dict(line.split("=", 1) for line in log_text.splitlines())

    normalized_rows = _read_csv_rows(NORMALIZED)
    rejected_rows = _read_csv_rows(REJECTED)

    assert log_values.get("deployment_status") == "ok", (
        f"{VERIFY_LOG} must report deployment_status=ok only after the final "
        "checker succeeds."
    )
    assert log_values.get("normalized_rows") == str(len(normalized_rows)), (
        f"{VERIFY_LOG} normalized_rows={log_values.get('normalized_rows')!r} "
        f"does not match actual normalized data-row count {len(normalized_rows)} "
        f"in {NORMALIZED}."
    )
    assert log_values.get("rejected_rows") == str(len(rejected_rows)), (
        f"{VERIFY_LOG} rejected_rows={log_values.get('rejected_rows')!r} "
        f"does not match actual rejected data-row count {len(rejected_rows)} "
        f"in {REJECTED}."
    )