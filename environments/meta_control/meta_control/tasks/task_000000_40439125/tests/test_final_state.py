# test_final_state.py
import re
from pathlib import Path



BASE = Path("/home/user/cert-audit")
CERTS = Path("/home/user/cert-audit/certs")
REPORT = Path("/home/user/cert-audit/rotation_decision.txt")

EXPECTED_LINES = [
    "selected_service=payments",
    "selected_certificate=/home/user/cert-audit/certs/payments.pem",
    None,  # reason line is validated separately
    "checked_services=inventory,orders,payments",
    "verification=complete",
]

ACCEPTABLE_REASON_PATTERNS = (
    "hostname mismatch",
    "dns mismatch",
    "san mismatch",
    "does not match",
    "missing expected dns",
)


def _read_report_text() -> str:
    assert REPORT.exists(), (
        f"Missing required final report file: {REPORT}. "
        "Create exactly this file with the required five-line rotation decision."
    )
    assert REPORT.is_file(), f"Required report path exists but is not a file: {REPORT}"
    return REPORT.read_text(encoding="utf-8")


def _report_lines() -> list[str]:
    text = _read_report_text()

    assert text, f"{REPORT} is empty; it must contain exactly five required lines."

    assert text.endswith("\n"), (
        f"{REPORT} must end after the fifth line with a normal newline character. "
        "Rewrite it with exactly the required five lines and no extra blank lines."
    )

    lines = text.splitlines()

    assert len(lines) == 5, (
        f"{REPORT} must contain exactly five lines and no extra blank lines; "
        f"found {len(lines)} line(s): {lines!r}"
    )

    blank_lines = [index + 1 for index, line in enumerate(lines) if line == ""]
    assert not blank_lines, (
        f"{REPORT} must not contain blank lines; blank line(s) found at "
        f"{blank_lines!r}."
    )

    return lines


def test_rotation_decision_report_exists_at_exact_required_path():
    assert BASE.exists(), f"Expected workspace directory is missing: {BASE}"
    assert BASE.is_dir(), f"Expected workspace path is not a directory: {BASE}"
    assert CERTS.exists(), f"Expected certificate directory is missing: {CERTS}"
    assert CERTS.is_dir(), f"Expected certificate path is not a directory: {CERTS}"

    assert REPORT.exists(), (
        f"Final deliverable was not created at the exact required path: {REPORT}"
    )
    assert REPORT.is_file(), f"Final deliverable path is not a regular file: {REPORT}"


def test_rotation_decision_report_has_exact_five_line_format():
    lines = _report_lines()

    assert lines[0] == EXPECTED_LINES[0], (
        "Line 1 is wrong. The selected service must be payments because payments "
        "is the only certificate that fails hostname validation. "
        f"Expected {EXPECTED_LINES[0]!r}, got {lines[0]!r}."
    )

    assert lines[1] == EXPECTED_LINES[1], (
        "Line 2 is wrong. The selected certificate must be the absolute path to "
        "payments.pem. "
        f"Expected {EXPECTED_LINES[1]!r}, got {lines[1]!r}."
    )

    assert lines[3] == EXPECTED_LINES[3], (
        "Line 4 is wrong. checked_services must list all three services in "
        "alphabetical order. "
        f"Expected {EXPECTED_LINES[3]!r}, got {lines[3]!r}."
    )

    assert lines[4] == EXPECTED_LINES[4], (
        "Line 5 is wrong. "
        f"Expected {EXPECTED_LINES[4]!r}, got {lines[4]!r}."
    )


def test_reason_line_cites_hostname_or_dns_mismatch_not_expiry_only():
    lines = _report_lines()
    reason_line = lines[2]

    assert reason_line.startswith("reason="), (
        "Line 3 is wrong. It must start with 'reason=' and briefly explain that "
        "payments was selected due to a hostname/DNS/SAN mismatch. "
        f"Got {reason_line!r}."
    )

    reason = reason_line.removeprefix("reason=")
    assert reason.strip(), (
        "Line 3 has an empty reason. It must briefly mention the hostname/DNS/SAN "
        "mismatch."
    )

    normalized_reason = reason.lower()
    assert any(pattern in normalized_reason for pattern in ACCEPTABLE_REASON_PATTERNS), (
        "Line 3 reason is wrong. The selected certificate is payments because its "
        "certificate SANs do not validate for payments.svc.cluster.local; the "
        "reason must mention a hostname mismatch, DNS mismatch, SAN mismatch, "
        "'does not match', or 'missing expected DNS'. "
        f"Got reason={reason!r}."
    )

    assert not re.search(r"\bexpires?\s+soonest\b|\bearliest\s+expir", normalized_reason), (
        "Line 3 appears to justify the selection only by expiration. That is the "
        "intended trap: inventory expires soonest overall, but payments must be "
        "selected because it fails hostname validation."
    )


def test_no_extra_rotation_report_files_created_in_workspace():
    assert BASE.exists() and BASE.is_dir(), f"Expected workspace directory is missing: {BASE}"

    allowed_report = REPORT
    unexpected_reports = []

    for path in BASE.rglob("*"):
        if not path.is_file():
            continue
        if path == allowed_report:
            continue

        name = path.name.lower()
        if (
            "rotation" in name
            or "decision" in name
            or "report" in name
        ) and path.suffix.lower() in {"", ".txt", ".tsv", ".csv", ".md", ".log"}:
            unexpected_reports.append(str(path))

    assert not unexpected_reports, (
        "Create exactly one report file, at "
        f"{REPORT}. Unexpected extra report-like file(s) found: "
        f"{unexpected_reports!r}"
    )


def test_report_does_not_select_inventory_earliest_expiry_trap():
    lines = _report_lines()
    full_report = "\n".join(lines).lower()

    assert "selected_service=inventory" not in full_report, (
        "The report incorrectly selects inventory. Inventory expires soonest "
        "overall, but it passes hostname validation; payments must be selected "
        "because it fails hostname validation."
    )
    assert "/home/user/cert-audit/certs/inventory.pem" not in full_report, (
        "The report incorrectly references inventory.pem as the selected "
        "certificate. The selected certificate must be payments.pem."
    )