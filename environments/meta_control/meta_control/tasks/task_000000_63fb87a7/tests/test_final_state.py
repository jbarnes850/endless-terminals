# test_final_state.py
from pathlib import Path
import json

LAB_DIR = Path("/home/user/firewall-lab")
CANDIDATES_DIR = Path("/home/user/firewall-lab/candidates")
MONITOR_PROBE = Path("/home/user/firewall-lab/monitor_probe.json")
ACTIVE_POLICY = Path("/home/user/firewall-lab/active_policy.nft")
VERIFICATION_LOG = Path("/home/user/firewall-lab/verification.log")

CORRECT_CANDIDATE_NAME = "allow-monitor-8443.nft"
CORRECT_CANDIDATE = Path("/home/user/firewall-lab/candidates/allow-monitor-8443.nft")

EXPECTED_ACTIVE_POLICY_BYTES = (
    b"# candidate: allow uptime checker to checkout-api HTTPS-alt\n"
    b'add rule inet filter input ip saddr 198.51.100.42 tcp dport 8443 accept comment "uptime checker checkout-api"\n'
)

EXPECTED_VERIFICATION_LOG_TEXT_WITH_NEWLINE = (
    "probe_source=198.51.100.42\n"
    "probe_port=8443\n"
    "selected_candidate=allow-monitor-8443.nft\n"
    "status=verified\n"
)

EXPECTED_VERIFICATION_LOG_TEXT_NO_TRAILING_NEWLINE = EXPECTED_VERIFICATION_LOG_TEXT_WITH_NEWLINE.rstrip("\n")

EXPECTED_PROBE = {
    "source_ipv4": "198.51.100.42",
    "protocol": "tcp",
    "destination_port": 8443,
}


def _assert_regular_file(path: Path) -> None:
    assert path.exists(), f"Required file is missing: {path}"
    assert path.is_file(), f"Required path exists but is not a regular file: {path}"


def _read_bytes(path: Path) -> bytes:
    _assert_regular_file(path)
    return path.read_bytes()


def _read_text(path: Path) -> str:
    _assert_regular_file(path)
    return path.read_text(encoding="utf-8")


def test_monitor_probe_still_contains_expected_evidence_values():
    """The final choice must be based on the probe source IP and destination port."""
    _assert_regular_file(MONITOR_PROBE)

    with MONITOR_PROBE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    probe = data.get("probe")
    assert isinstance(probe, dict), (
        f"{MONITOR_PROBE} must contain a JSON object at key 'probe'; "
        "cannot verify the firewall choice without the probe definition."
    )

    assert probe.get("source_ipv4") == EXPECTED_PROBE["source_ipv4"], (
        f"{MONITOR_PROBE} probe.source_ipv4 is wrong. "
        f"Expected {EXPECTED_PROBE['source_ipv4']!r}, got {probe.get('source_ipv4')!r}."
    )
    assert probe.get("protocol") == EXPECTED_PROBE["protocol"], (
        f"{MONITOR_PROBE} probe.protocol is wrong. "
        f"Expected {EXPECTED_PROBE['protocol']!r}, got {probe.get('protocol')!r}."
    )
    assert probe.get("destination_port") == EXPECTED_PROBE["destination_port"], (
        f"{MONITOR_PROBE} probe.destination_port is wrong. "
        f"Expected {EXPECTED_PROBE['destination_port']!r}, got {probe.get('destination_port')!r}."
    )


def test_correct_candidate_file_is_present_and_unmodified():
    """The selected candidate must remain available exactly as provided."""
    actual = _read_bytes(CORRECT_CANDIDATE)
    assert actual == EXPECTED_ACTIVE_POLICY_BYTES, (
        f"The correct candidate file has been modified or is not the expected production-ready rule: "
        f"{CORRECT_CANDIDATE}\n"
        f"Expected bytes: {EXPECTED_ACTIVE_POLICY_BYTES!r}\n"
        f"Actual bytes:   {actual!r}"
    )


def test_active_policy_exists_and_byte_for_byte_matches_correct_candidate():
    """active_policy.nft must be an exact copy of candidates/allow-monitor-8443.nft."""
    active_bytes = _read_bytes(ACTIVE_POLICY)
    correct_candidate_bytes = _read_bytes(CORRECT_CANDIDATE)

    assert active_bytes == correct_candidate_bytes, (
        f"{ACTIVE_POLICY} does not byte-for-byte match the required selected candidate "
        f"{CORRECT_CANDIDATE}.\n"
        "Do not concatenate candidates, invent a new rule, edit comments, change whitespace, "
        "or alter the final newline.\n"
        f"Expected bytes from selected candidate: {correct_candidate_bytes!r}\n"
        f"Actual active policy bytes:          {active_bytes!r}"
    )

    assert active_bytes == EXPECTED_ACTIVE_POLICY_BYTES, (
        f"{ACTIVE_POLICY} is not the exact expected final policy for the uptime monitor.\n"
        "The only acceptable final policy is the allow-monitor-8443.nft candidate, which "
        "restricts source to 198.51.100.42 and destination TCP port to 8443.\n"
        f"Expected bytes: {EXPECTED_ACTIVE_POLICY_BYTES!r}\n"
        f"Actual bytes:   {active_bytes!r}"
    )


def test_active_policy_is_not_any_misleading_or_broad_candidate():
    """Catch common partial-success choices: wrong source, wrong port, or broad source."""
    active_text = _read_text(ACTIVE_POLICY)

    assert "ip saddr 198.51.100.42" in active_text, (
        f"{ACTIVE_POLICY} still does not restrict the rule to the uptime monitor source "
        "IP 198.51.100.42."
    )
    assert "tcp dport 8443" in active_text, (
        f"{ACTIVE_POLICY} still does not allow the probe destination TCP port 8443."
    )
    assert "tcp dport 443" not in active_text, (
        f"{ACTIVE_POLICY} appears to use the wrong destination port 443; the probe requires 8443."
    )
    assert "ip saddr 203.0.113.17" not in active_text, (
        f"{ACTIVE_POLICY} appears to allow the office VPN source 203.0.113.17 instead of "
        "the probe source 198.51.100.42."
    )
    assert 'temporary broad checkout-api access' not in active_text, (
        f"{ACTIVE_POLICY} appears to use the broad emergency candidate; it is not acceptable "
        "because it lacks the required source-IP restriction."
    )


def test_verification_log_exists_with_exact_four_line_contents():
    """verification.log must contain exactly the required four lines, in order."""
    log_text = _read_text(VERIFICATION_LOG)

    assert log_text in {
        EXPECTED_VERIFICATION_LOG_TEXT_WITH_NEWLINE,
        EXPECTED_VERIFICATION_LOG_TEXT_NO_TRAILING_NEWLINE,
    }, (
        f"{VERIFICATION_LOG} does not contain the exact required verification log.\n"
        "It must contain exactly these four lines, in this order, with no extra lines or text:\n"
        f"{EXPECTED_VERIFICATION_LOG_TEXT_WITH_NEWLINE!r}\n"
        "A single trailing newline after status=verified is acceptable.\n"
        f"Actual contents: {log_text!r}"
    )

    lines = log_text.splitlines()
    assert lines == [
        "probe_source=198.51.100.42",
        "probe_port=8443",
        "selected_candidate=allow-monitor-8443.nft",
        "status=verified",
    ], (
        f"{VERIFICATION_LOG} must have exactly four verification lines in the required order. "
        f"Actual split lines: {lines!r}"
    )


def test_verification_log_values_match_probe_and_selected_candidate():
    """The log must name the probe values and the exact selected candidate filename only."""
    log_text = _read_text(VERIFICATION_LOG)
    lines = log_text.splitlines()

    assert len(lines) == 4, (
        f"{VERIFICATION_LOG} must contain exactly four lines; found {len(lines)} line(s): {lines!r}"
    )

    parsed = {}
    for line in lines:
        assert "=" in line, (
            f"Every line in {VERIFICATION_LOG} must be in key=value format. Bad line: {line!r}"
        )
        key, value = line.split("=", 1)
        assert key not in parsed, f"Duplicate key {key!r} found in {VERIFICATION_LOG}."
        parsed[key] = value

    assert parsed.get("probe_source") == "198.51.100.42", (
        f"{VERIFICATION_LOG} has the wrong probe_source. "
        f"Expected '198.51.100.42', got {parsed.get('probe_source')!r}."
    )
    assert parsed.get("probe_port") == "8443", (
        f"{VERIFICATION_LOG} has the wrong probe_port. "
        f"Expected '8443', got {parsed.get('probe_port')!r}."
    )
    assert parsed.get("selected_candidate") == CORRECT_CANDIDATE_NAME, (
        f"{VERIFICATION_LOG} must record selected_candidate={CORRECT_CANDIDATE_NAME}; "
        f"got {parsed.get('selected_candidate')!r}."
    )
    assert "/" not in parsed.get("selected_candidate", ""), (
        f"{VERIFICATION_LOG} selected_candidate must be the filename only, not a path: "
        f"{parsed.get('selected_candidate')!r}."
    )
    assert parsed.get("status") == "verified", (
        f"{VERIFICATION_LOG} status must be 'verified'; got {parsed.get('status')!r}."
    )