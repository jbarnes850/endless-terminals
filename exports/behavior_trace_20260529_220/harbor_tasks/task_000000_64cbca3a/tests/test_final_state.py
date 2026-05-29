# test_final_state.py
from pathlib import Path

import pytest

REPORT_PATH = Path("/home/user/observability/dashboard-baseline-report.txt")
SNAPSHOT_DIR = Path("/home/user/observability/snapshots")

EXPECTED_REPORT_CONTENT = (
    "baseline_candidate=candidate-c.prom\n"
    "candidate_count=7\n"
    "usable_count=4\n"
    "rejected=candidate-a.prom:stale,candidate-b.prom:startup-reset,candidate-d.prom:unhealthy,candidate-e.prom:traffic-anomaly,candidate-f.prom:missing-metric,candidate-g.prom:scrape-error\n"
    "selected_http_requests_total=11913\n"
    "selected_up=1\n"
    "verification=passed\n"
)

EXPECTED_LINES = EXPECTED_REPORT_CONTENT.rstrip("\n").split("\n")

EXPECTED_CANDIDATES = [
    "candidate-a.prom",
    "candidate-b.prom",
    "candidate-c.prom",
    "candidate-d.prom",
    "candidate-e.prom",
    "candidate-f.prom",
    "candidate-g.prom",
]

EXPECTED_REJECTIONS = {
    "candidate-a.prom": "stale",
    "candidate-b.prom": "startup-reset",
    "candidate-d.prom": "unhealthy",
    "candidate-e.prom": "traffic-anomaly",
    "candidate-f.prom": "missing-metric",
    "candidate-g.prom": "scrape-error",
}


def _read_report_bytes() -> bytes:
    assert REPORT_PATH.exists(), (
        f"Missing diagnostic report: {REPORT_PATH}. "
        "The task requires creating exactly one report at this absolute path."
    )
    assert REPORT_PATH.is_file(), f"Diagnostic report path is not a regular file: {REPORT_PATH}"
    return REPORT_PATH.read_bytes()


def _read_report_text() -> str:
    raw = _read_report_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"Diagnostic report is not valid UTF-8 text: {REPORT_PATH}") from exc


def _parse_report_lines() -> list[str]:
    text = _read_report_text()

    assert text.endswith("\n"), (
        f"Report should end with a single final newline after 'verification=passed': {REPORT_PATH}"
    )
    assert not text.endswith("\n\n"), (
        f"Report contains an extra blank line at the end: {REPORT_PATH}"
    )

    logical_lines = text.rstrip("\n").split("\n")
    assert len(logical_lines) == 7, (
        f"Report must contain exactly seven logical lines with no extra blank lines. "
        f"Found {len(logical_lines)} lines: {logical_lines!r}"
    )
    assert all(line != "" for line in logical_lines), (
        f"Report must not contain blank lines. Found lines: {logical_lines!r}"
    )
    return logical_lines


def _parse_key_value_report() -> dict[str, str]:
    lines = _parse_report_lines()
    parsed = {}
    for line_number, line in enumerate(lines, start=1):
        assert "=" in line, f"Line {line_number} is not formatted as key=value: {line!r}"
        key, value = line.split("=", 1)
        assert key, f"Line {line_number} has an empty key: {line!r}"
        assert key not in parsed, f"Duplicate report key {key!r} found on line {line_number}"
        parsed[key] = value
    return parsed


def test_report_file_exists_at_exact_required_absolute_path_and_is_utf8():
    text = _read_report_text()
    assert text, f"Diagnostic report exists but is empty: {REPORT_PATH}"


def test_report_contents_match_expected_byte_for_byte():
    actual = _read_report_text()
    assert actual == EXPECTED_REPORT_CONTENT, (
        f"Diagnostic report contents do not match the required final state byte-for-byte.\n"
        f"Expected exactly:\n{EXPECTED_REPORT_CONTENT!r}\n"
        f"Actual:\n{actual!r}"
    )


def test_report_has_exact_required_line_order_and_keys():
    lines = _parse_report_lines()
    assert lines == EXPECTED_LINES, (
        "Report lines are not exactly the required seven lines in the required order. "
        f"Expected {EXPECTED_LINES!r}, got {lines!r}."
    )

    expected_keys = [
        "baseline_candidate",
        "candidate_count",
        "usable_count",
        "rejected",
        "selected_http_requests_total",
        "selected_up",
        "verification",
    ]
    actual_keys = [line.split("=", 1)[0] for line in lines]
    assert actual_keys == expected_keys, (
        f"Report keys are in the wrong order or missing. "
        f"Expected {expected_keys!r}, got {actual_keys!r}."
    )


def test_candidate_count_reflects_only_candidate_prom_files():
    actual_candidates = sorted(path.name for path in SNAPSHOT_DIR.glob("candidate-*.prom"))
    assert actual_candidates == EXPECTED_CANDIDATES, (
        f"Unexpected candidate snapshot set under {SNAPSHOT_DIR}. "
        f"Expected {EXPECTED_CANDIDATES!r}, got {actual_candidates!r}."
    )

    report = _parse_key_value_report()
    assert report["candidate_count"] == str(len(EXPECTED_CANDIDATES)), (
        "candidate_count must count only files matching "
        f"{SNAPSHOT_DIR}/candidate-*.prom. Expected 7, got {report['candidate_count']!r}."
    )


def test_selected_baseline_and_metric_values_are_correct():
    report = _parse_key_value_report()

    assert report["baseline_candidate"] == "candidate-c.prom", (
        "Wrong baseline candidate selected. The stable healthy baseline should be "
        "candidate-c.prom, not "
        f"{report['baseline_candidate']!r}."
    )
    assert "/" not in report["baseline_candidate"], (
        "baseline_candidate must be only the basename, not a full or relative path."
    )

    assert report["selected_http_requests_total"] == "11913", (
        "selected_http_requests_total must be the sum of all http_requests_total samples "
        "in candidate-c.prom: 11888 + 25 = 11913."
    )
    assert report["selected_up"] == "1", (
        "selected_up must be the numeric up metric value from candidate-c.prom."
    )
    assert report["verification"] == "passed", (
        "The final line must record that the student verified the report: verification=passed."
    )


def test_usable_count_is_before_final_baseline_filtering():
    report = _parse_key_value_report()
    assert report["usable_count"] == "4", (
        "usable_count must count candidates passing required metric-family, up-health, "
        "and scrape-error checks before final baseline-quality filtering. "
        "Expected usable candidates are a, b, c, and e, so usable_count=4."
    )


def test_rejected_line_includes_every_nonselected_candidate_sorted_with_exact_reasons():
    report = _parse_key_value_report()
    rejected_value = report["rejected"]

    expected_rejected_value = (
        "candidate-a.prom:stale,"
        "candidate-b.prom:startup-reset,"
        "candidate-d.prom:unhealthy,"
        "candidate-e.prom:traffic-anomaly,"
        "candidate-f.prom:missing-metric,"
        "candidate-g.prom:scrape-error"
    )
    assert rejected_value == expected_rejected_value, (
        "Rejected line is incorrect. It must include every non-selected candidate, "
        "sorted alphabetically by filename, with the exact short lowercase reason. "
        f"Expected {expected_rejected_value!r}, got {rejected_value!r}."
    )

    entries = rejected_value.split(",")
    filenames = []
    reasons = {}
    for entry in entries:
        assert ":" in entry, f"Rejected entry is not formatted as filename:reason: {entry!r}"
        filename, reason = entry.split(":", 1)
        filenames.append(filename)
        reasons[filename] = reason

        assert filename in EXPECTED_REJECTIONS, (
            f"Rejected entry contains unexpected filename {filename!r}. "
            "Only non-selected candidate snapshots should be listed."
        )
        assert "/" not in filename, (
            f"Rejected filename must be only a basename, not a path: {filename!r}"
        )
        assert reason == EXPECTED_REJECTIONS[filename], (
            f"Wrong rejection reason for {filename}. "
            f"Expected {EXPECTED_REJECTIONS[filename]!r}, got {reason!r}."
        )
        assert reason == reason.lower() and " " not in reason and "_" not in reason, (
            f"Rejection reason must be short lowercase hyphenated text: {entry!r}"
        )

    assert filenames == sorted(filenames), (
        f"Rejected entries must be sorted alphabetically by filename. Got order: {filenames!r}"
    )
    assert set(filenames) == set(EXPECTED_REJECTIONS), (
        "Rejected entries must include exactly every candidate except the selected "
        f"candidate-c.prom. Expected {sorted(EXPECTED_REJECTIONS)!r}, got {sorted(filenames)!r}."
    )
    assert "candidate-c.prom" not in filenames, (
        "The selected baseline candidate-c.prom must not appear in the rejected line."
    )


def test_no_additional_dashboard_baseline_reports_were_created():
    assert REPORT_PATH.parent.exists(), f"Missing observability directory: {REPORT_PATH.parent}"

    report_like_files = sorted(
        path
        for path in REPORT_PATH.parent.iterdir()
        if path.is_file()
        and (
            path.name == "dashboard-baseline-report.txt"
            or path.name.startswith("dashboard-baseline-report")
            or "baseline-report" in path.name
        )
    )

    assert report_like_files == [REPORT_PATH], (
        "The task requires exactly one diagnostic report at "
        f"{REPORT_PATH}. Found report-like files: {[str(path) for path in report_like_files]!r}."
    )