# test_final_state.py
from pathlib import Path
import stat


BASE = Path("/home/user/net-triage")
INPUT = Path("/home/user/net-triage/input")
REPORTS = Path("/home/user/net-triage/reports")
ARCHIVE = Path("/home/user/net-triage/archive")

PING_RESULTS = Path("/home/user/net-triage/input/ping-results.csv")
INTERFACE_NOTES = Path("/home/user/net-triage/input/interface-notes.txt")
README = Path("/home/user/net-triage/input/README.txt")

ARCHIVED_PING_RESULTS = Path("/home/user/net-triage/archive/ping-results.csv")
ARCHIVED_INTERFACE_NOTES = Path("/home/user/net-triage/archive/interface-notes.txt")
ARCHIVED_README = Path("/home/user/net-triage/archive/README.txt")

DOWN_HOSTS_REPORT = Path("/home/user/net-triage/reports/down-hosts.txt")
VERIFICATION_LOG = Path("/home/user/net-triage/reports/verification.log")


EXPECTED_PING_RESULTS = """hostname,ip_address,vlan,status,last_seen,notes
core-rtr-01,10.40.0.1,10,UP,2026-02-18T09:01:00Z,baseline gateway reachable
dist-sw-02,10.40.2.12,20,DOWN,2026-02-18T08:44:12Z,no arp response
cam-lobby-01,10.40.7.44,70,UP,2026-02-18T09:00:19Z,previously DOWN during maintenance window
ap-east-03,10.40.3.33,30,DEGRADED,2026-02-18T08:59:02Z,packet loss but not DOWN
printer-hr-02,10.40.5.22,50,DOWN,2026-02-18T08:41:55Z,icmp timeout
badge-reader-7,10.40.5.87,50,UNKNOWN,2026-02-18T08:35:10Z,status page says DOWN? needs manual check
lab-sensor-14,10.40.9.14,90,DOWN,2026-02-18T08:38:44Z,switchport err-disabled
voip-conf-2,10.40.4.62,40,UP,2026-02-18T09:02:11Z,contains text DOWN in ticket title
camera-dock-09,10.40.7.109,70,DOWN,2026-02-18T08:39:31Z,no dhcp renewal
nas-backup-01,10.40.6.10,60,UP,2026-02-18T09:04:18Z,healthy
"""

EXPECTED_INTERFACE_NOTES = """Switch interface notes from access layer:
Gi1/0/12 dist-sw-02 VLAN20 link DOWN
Gi1/0/22 printer-hr-02 VLAN50 link DOWN
Gi1/0/44 cam-lobby-01 VLAN70 historical DOWN cleared
Gi1/0/87 badge-reader-7 VLAN50 admin state DOWN but ping status UNKNOWN
Gi1/0/14 lab-sensor-14 VLAN90 link DOWN
Gi1/0/109 camera-dock-09 VLAN70 link DOWN
Gi1/0/62 voip-conf-2 VLAN40 ticket text contains DOWN but interface is up
"""

EXPECTED_README = """Connectivity triage inputs.
Use ping-results.csv as the source of truth for host status.
interface-notes.txt is advisory only and includes historical or administrative DOWN text.
"""

EXPECTED_DOWN_HOSTS_REPORT = """Connectivity Triage Report
Generated from /home/user/net-triage/input/ping-results.csv
Down hosts: 4
---
dist-sw-02|10.40.2.12|20|2026-02-18T08:44:12Z
printer-hr-02|10.40.5.22|50|2026-02-18T08:41:55Z
camera-dock-09|10.40.7.109|70|2026-02-18T08:39:31Z
lab-sensor-14|10.40.9.14|90|2026-02-18T08:38:44Z
"""

EXPECTED_VERIFICATION_LOG = """check:reports_dir=present
check:archive_dir=present
check:input_files_archived=present
check:report_file=present
check:report_format=verified
check:down_host_count=verified
"""


def assert_directory(path: Path) -> None:
    assert path.exists(), f"Required directory is missing: {path}"
    assert path.is_dir(), f"Required path exists but is not a directory: {path}"


def assert_regular_file(path: Path) -> None:
    assert path.exists(), f"Required file is missing: {path}"
    assert path.is_file(), f"Required path exists but is not a regular file: {path}"
    assert stat.S_ISREG(path.stat().st_mode), f"Required path is not a regular file: {path}"


def assert_file_exact_text(path: Path, expected: str, description: str) -> None:
    assert_regular_file(path)
    actual = path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"{description} has incorrect content: {path}\n"
        f"Expected exact content length {len(expected)} characters, got {len(actual)} characters.\n"
        "This task requires byte-for-byte/plain-text exact final content."
    )


def assert_file_exact_bytes(path: Path, expected: bytes, description: str) -> None:
    assert_regular_file(path)
    actual = path.read_bytes()
    assert actual == expected, (
        f"{description} is not byte-identical as required: {path}\n"
        f"Expected {len(expected)} bytes, got {len(actual)} bytes."
    )


def test_required_final_directories_exist():
    assert_directory(BASE)
    assert_directory(INPUT)
    assert_directory(REPORTS)
    assert_directory(ARCHIVE)


def test_original_input_files_remain_present_and_unchanged():
    assert_file_exact_text(
        PING_RESULTS,
        EXPECTED_PING_RESULTS,
        "Original ping-results.csv must remain present and unchanged",
    )
    assert_file_exact_text(
        INTERFACE_NOTES,
        EXPECTED_INTERFACE_NOTES,
        "Original interface-notes.txt must remain present and unchanged",
    )
    assert_file_exact_text(
        README,
        EXPECTED_README,
        "Original README.txt must remain present and unchanged",
    )


def test_archive_contains_exactly_the_required_regular_file_copies():
    assert_directory(ARCHIVE)

    expected_names = {"ping-results.csv", "interface-notes.txt", "README.txt"}
    actual_regular_names = {p.name for p in ARCHIVE.iterdir() if p.is_file()}
    assert actual_regular_names == expected_names, (
        f"Archive directory must contain regular-file copies of exactly "
        f"{sorted(expected_names)}. Found regular files: {sorted(actual_regular_names)} "
        f"in {ARCHIVE}"
    )

    unexpected_entries = {p.name for p in ARCHIVE.iterdir()} - expected_names
    assert not unexpected_entries, (
        f"Archive directory contains unexpected extra entries: "
        f"{sorted(unexpected_entries)} in {ARCHIVE}"
    )

    assert_file_exact_bytes(
        ARCHIVED_PING_RESULTS,
        PING_RESULTS.read_bytes(),
        "Archived ping-results.csv",
    )
    assert_file_exact_bytes(
        ARCHIVED_INTERFACE_NOTES,
        INTERFACE_NOTES.read_bytes(),
        "Archived interface-notes.txt",
    )
    assert_file_exact_bytes(
        ARCHIVED_README,
        README.read_bytes(),
        "Archived README.txt",
    )


def test_down_hosts_report_exists_with_exact_required_content():
    assert_file_exact_text(
        DOWN_HOSTS_REPORT,
        EXPECTED_DOWN_HOSTS_REPORT,
        "Final down-hosts report",
    )


def test_down_hosts_report_structure_and_semantics_are_correct():
    assert_regular_file(DOWN_HOSTS_REPORT)
    actual = DOWN_HOSTS_REPORT.read_text(encoding="utf-8")

    assert actual.endswith("\n"), (
        f"Report must end with a single final newline and no truncated final line: "
        f"{DOWN_HOSTS_REPORT}"
    )

    lines = actual.splitlines()
    assert len(lines) == 8, (
        f"Report must have exactly 8 lines: 4 header/separator lines plus 4 down hosts. "
        f"Found {len(lines)} lines in {DOWN_HOSTS_REPORT}: {lines!r}"
    )

    assert lines[:4] == [
        "Connectivity Triage Report",
        "Generated from /home/user/net-triage/input/ping-results.csv",
        "Down hosts: 4",
        "---",
    ], (
        f"Report header/count/separator is wrong in {DOWN_HOSTS_REPORT}. "
        f"Found first four lines: {lines[:4]!r}"
    )

    host_lines = lines[4:]
    for line_number, line in enumerate(host_lines, start=5):
        fields = line.split("|")
        assert len(fields) == 4, (
            f"Host line {line_number} must contain exactly four pipe-separated fields "
            f"hostname|ip_address|vlan|last_seen. Found: {line!r}"
        )
        assert all(field != "" for field in fields), (
            f"Host line {line_number} contains an empty field, which is not allowed: {line!r}"
        )

    expected_host_lines = [
        "dist-sw-02|10.40.2.12|20|2026-02-18T08:44:12Z",
        "printer-hr-02|10.40.5.22|50|2026-02-18T08:41:55Z",
        "camera-dock-09|10.40.7.109|70|2026-02-18T08:39:31Z",
        "lab-sensor-14|10.40.9.14|90|2026-02-18T08:38:44Z",
    ]
    assert host_lines == expected_host_lines, (
        "Report host lines are incorrect. Only records whose CSV status field "
        "is exactly DOWN may be included, sorted by numeric VLAN then hostname. "
        f"Expected {expected_host_lines!r}, found {host_lines!r}."
    )

    included_hosts = {line.split("|", 1)[0] for line in host_lines}
    forbidden_hosts = {"cam-lobby-01", "ap-east-03", "badge-reader-7", "voip-conf-2"}
    wrongly_included = included_hosts & forbidden_hosts
    assert not wrongly_included, (
        "Report includes host(s) that merely contain misleading DOWN text or have "
        f"non-DOWN status and must be excluded: {sorted(wrongly_included)}"
    )


def test_verification_log_exists_with_exact_required_content():
    assert_file_exact_text(
        VERIFICATION_LOG,
        EXPECTED_VERIFICATION_LOG,
        "Verification log",
    )


def test_reports_directory_contains_required_report_artifacts():
    assert_directory(REPORTS)

    expected_required = {"down-hosts.txt", "verification.log"}
    actual_regular_names = {p.name for p in REPORTS.iterdir() if p.is_file()}
    missing = expected_required - actual_regular_names
    assert not missing, (
        f"Reports directory is missing required report artifact(s): "
        f"{sorted(missing)} in {REPORTS}"
    )