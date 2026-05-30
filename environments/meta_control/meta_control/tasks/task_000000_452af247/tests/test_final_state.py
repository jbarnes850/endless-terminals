# test_final_state.py
from pathlib import Path
from collections import Counter
import os
import re


ACCESS_LOG = Path("/home/user/projects/shopsite/logs/access.log")
REPORT = Path("/home/user/projects/shopsite/reports/error_summary.txt")
HELPER_SCRIPT = Path("/home/user/projects/shopsite/scripts/summarize_checkout_errors.sh")

EXPECTED_REPORT_TEXT = (
    "TOTAL_FAILED_CHECKOUTS=10\n"
    "FIRST_FAILED_CHECKOUT=2026-02-14T09:02:44Z\n"
    "LAST_FAILED_CHECKOUT=2026-02-14T09:17:49Z\n"
    "STATUS_COUNTS=500:3,501:1,502:2,503:2,504:1,599:1\n"
)

EXPECTED_MATCHING_EVENTS = [
    ("2026-02-14T09:02:44Z", 500),
    ("2026-02-14T09:03:12Z", 502),
    ("2026-02-14T09:07:26Z", 500),
    ("2026-02-14T09:08:45Z", 503),
    ("2026-02-14T09:09:14Z", 504),
    ("2026-02-14T09:11:33Z", 502),
    ("2026-02-14T09:13:07Z", 500),
    ("2026-02-14T09:14:44Z", 599),
    ("2026-02-14T09:16:03Z", 503),
    ("2026-02-14T09:17:49Z", 501),
]


def _read_report_bytes():
    assert REPORT.exists(), f"Required deliverable file is missing: {REPORT}"
    assert REPORT.is_file(), f"Deliverable path exists but is not a regular file: {REPORT}"
    assert os.access(REPORT, os.R_OK), f"Deliverable file is not readable: {REPORT}"
    return REPORT.read_bytes()


def _parse_failed_checkout_events_from_log():
    assert ACCESS_LOG.exists(), f"Required input log file is missing: {ACCESS_LOG}"
    assert ACCESS_LOG.is_file(), f"Required input log path is not a regular file: {ACCESS_LOG}"
    assert os.access(ACCESS_LOG, os.R_OK), f"Required input log file is not readable: {ACCESS_LOG}"

    events = []
    for line_number, line in enumerate(ACCESS_LOG.read_text(encoding="utf-8").splitlines(), start=1):
        fields = line.split()
        assert len(fields) >= 5, f"Log line {line_number} is malformed and has fewer than 5 fields: {line!r}"

        timestamp = fields[0]
        path_without_query = fields[3].split("?", 1)[0]

        try:
            status = int(fields[4])
        except ValueError:
            raise AssertionError(f"Log line {line_number} has a non-integer status code: {fields[4]!r}")

        if path_without_query == "/api/checkout" and 500 <= status <= 599:
            events.append((timestamp, status))

    return events


def _expected_report_from_log():
    events = _parse_failed_checkout_events_from_log()
    assert events == EXPECTED_MATCHING_EVENTS, (
        "The input log no longer yields the expected failed checkout events. "
        "The final report must be derived from the original task log data."
    )

    counts = Counter(status for _, status in events)
    counts_text = ",".join(f"{status}:{counts[status]}" for status in sorted(counts))
    return (
        f"TOTAL_FAILED_CHECKOUTS={len(events)}\n"
        f"FIRST_FAILED_CHECKOUT={events[0][0]}\n"
        f"LAST_FAILED_CHECKOUT={events[-1][0]}\n"
        f"STATUS_COUNTS={counts_text}\n"
    )


def test_optional_helper_script_still_available_if_present():
    assert HELPER_SCRIPT.exists(), f"Expected helper script is missing: {HELPER_SCRIPT}"
    assert HELPER_SCRIPT.is_file(), f"Helper script path is not a regular file: {HELPER_SCRIPT}"
    assert os.access(HELPER_SCRIPT, os.R_OK), f"Helper script is not readable: {HELPER_SCRIPT}"


def test_report_exists_and_has_exact_four_line_format():
    raw = _read_report_bytes()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"Deliverable file is not valid UTF-8 text: {REPORT}") from exc

    assert text, f"Deliverable file is empty: {REPORT}"
    assert not text.startswith("\n"), "Report has an extra blank line before the first required line."
    assert text.endswith("\n"), "Report should end with one normal newline after the fourth line."
    assert not text.endswith("\n\n"), "Report has an extra trailing blank line after the fourth line."

    lines = text.splitlines()
    assert len(lines) == 4, (
        f"Report must contain exactly four lines, but found {len(lines)} line(s): {lines!r}"
    )

    expected_key_patterns = [
        r"^TOTAL_FAILED_CHECKOUTS=\d+$",
        r"^FIRST_FAILED_CHECKOUT=\S+$",
        r"^LAST_FAILED_CHECKOUT=\S+$",
        r"^STATUS_COUNTS=\d{3}:\d+(?:,\d{3}:\d+)*$",
    ]
    for index, (line, pattern) in enumerate(zip(lines, expected_key_patterns), start=1):
        assert re.fullmatch(pattern, line), (
            f"Report line {index} has the wrong key, order, or format: {line!r}"
        )


def test_report_contents_match_failed_checkout_summary_derived_from_log():
    actual = _read_report_bytes().decode("utf-8")
    expected_from_log = _expected_report_from_log()

    assert actual == expected_from_log, (
        "Report contents do not match the failed /api/checkout 5xx summary derived from "
        f"{ACCESS_LOG}. The report must include /api/checkout requests with query strings, "
        "exclude checkout-like paths such as /api/checkout-preview and /api/checkout/refund, "
        "exclude non-5xx statuses, and sort STATUS_COUNTS by numeric status code.\n\n"
        f"Expected exactly:\n{expected_from_log!r}\n\n"
        f"Actual:\n{actual!r}"
    )


def test_report_matches_required_final_deliverable_exactly():
    actual = _read_report_bytes().decode("utf-8")
    assert actual == EXPECTED_REPORT_TEXT, (
        "Final deliverable does not exactly match the required contents at "
        f"{REPORT}. This commonly means the misleading helper script output was accepted "
        "without correcting query-string checkout failures or sorted status counts.\n\n"
        f"Expected exactly:\n{EXPECTED_REPORT_TEXT!r}\n\n"
        f"Actual:\n{actual!r}"
    )