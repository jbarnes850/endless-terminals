# test_final_state.py
from pathlib import Path

IOT_EDGE_DIR = Path("/home/user/iot-edge")
POLICY_FILE = Path("/home/user/iot-edge/device-policy.env")
FIREWALL_LOG = Path("/home/user/iot-edge/firewall.apply.log")

EXPECTED_POLICY_CONTENT = (
    "DEVICE_ID=edge-sensor-a17\n"
    "INTERFACE=wlan0\n"
    "ALLOW_CIDR=10.42.8.0/24\n"
    "ALLOW_TCP_PORT=1883\n"
    "DEFAULT_INPUT_POLICY=drop\n"
    "RULESET_NAME=mqtt-ingress-v4\n"
)

EXPECTED_LOG_LINE = (
    "APPLY|device=edge-sensor-a17|ruleset=mqtt-ingress-v4|action=allow|"
    "iface=wlan0|src=10.42.8.0/24|proto=tcp|dport=1883|"
    "default_input=drop|status=ready"
)
EXPECTED_LOG_CONTENT = EXPECTED_LOG_LINE + "\n"


def _read_log_bytes():
    assert FIREWALL_LOG.exists(), (
        "Checkpoint 1 failed: required deployment artifact does not exist.\n"
        f"Expected file: {FIREWALL_LOG}"
    )
    assert FIREWALL_LOG.is_file(), (
        "Checkpoint 1 failed: deployment artifact path exists but is not a regular file.\n"
        f"Path: {FIREWALL_LOG}"
    )
    return FIREWALL_LOG.read_bytes()


def test_checkpoint_1_firewall_apply_log_exists():
    assert IOT_EDGE_DIR.exists(), f"Required directory is missing: {IOT_EDGE_DIR}"
    assert IOT_EDGE_DIR.is_dir(), f"Required path is not a directory: {IOT_EDGE_DIR}"
    assert FIREWALL_LOG.exists(), (
        "Checkpoint 1 failed: /home/user/iot-edge/firewall.apply.log was not created."
    )
    assert FIREWALL_LOG.is_file(), (
        "Checkpoint 1 failed: /home/user/iot-edge/firewall.apply.log exists but is not a regular file."
    )


def test_checkpoint_2_log_contains_exactly_one_line_and_ends_with_newline():
    content = _read_log_bytes()

    assert content.endswith(b"\n"), (
        "Checkpoint 2 failed: firewall.apply.log must end with exactly one trailing newline."
    )

    newline_count = content.count(b"\n")
    assert newline_count == 1, (
        "Checkpoint 2 failed: firewall.apply.log must contain exactly one line.\n"
        f"Expected exactly 1 newline byte; found {newline_count}.\n"
        f"Actual bytes: {content!r}"
    )

    assert content != b"\n", (
        "Checkpoint 2 failed: firewall.apply.log contains an empty line instead of the required record."
    )


def test_checkpoint_3_line_begins_with_exact_required_prefix():
    content = _read_log_bytes()
    line = content.decode("utf-8", errors="replace").rstrip("\n")

    expected_prefix = "APPLY|device=edge-sensor-a17|ruleset=mqtt-ingress-v4|"
    assert line.startswith(expected_prefix), (
        "Checkpoint 3 failed: log line does not begin with the exact required prefix.\n"
        f"Expected prefix: {expected_prefix!r}\n"
        f"Actual line:     {line!r}"
    )


def test_checkpoint_4_line_contains_exact_action_and_interface_segment():
    content = _read_log_bytes()
    line = content.decode("utf-8", errors="replace").rstrip("\n")

    expected_segment = "action=allow|iface=wlan0|"
    assert expected_segment in line, (
        "Checkpoint 4 failed: log line is missing the exact action/interface segment.\n"
        f"Expected segment: {expected_segment!r}\n"
        f"Actual line:      {line!r}"
    )


def test_checkpoint_5_line_contains_exact_source_protocol_port_segment():
    content = _read_log_bytes()
    line = content.decode("utf-8", errors="replace").rstrip("\n")

    expected_segment = "src=10.42.8.0/24|proto=tcp|dport=1883|"
    assert expected_segment in line, (
        "Checkpoint 5 failed: log line is missing the exact source/protocol/port segment.\n"
        f"Expected segment: {expected_segment!r}\n"
        f"Actual line:      {line!r}"
    )


def test_checkpoint_6_line_ends_with_exact_required_suffix():
    content = _read_log_bytes()
    line = content.decode("utf-8", errors="replace").rstrip("\n")

    expected_suffix = "default_input=drop|status=ready"
    assert line.endswith(expected_suffix), (
        "Checkpoint 6 failed: log line does not end with the exact required suffix.\n"
        f"Expected suffix: {expected_suffix!r}\n"
        f"Actual line:     {line!r}"
    )


def test_final_firewall_apply_log_is_byte_for_byte_exact():
    content = _read_log_bytes()

    assert content == EXPECTED_LOG_CONTENT.encode("utf-8"), (
        "Final invariant failed: firewall.apply.log is not byte-for-byte equal to the required "
        "one-line deployment record, including the trailing newline.\n"
        f"File: {FIREWALL_LOG}\n"
        f"Expected bytes: {EXPECTED_LOG_CONTENT.encode('utf-8')!r}\n"
        f"Actual bytes:   {content!r}\n"
        f"Expected text:  {EXPECTED_LOG_CONTENT!r}"
    )


def test_device_policy_file_remains_unchanged():
    assert POLICY_FILE.exists(), (
        "Final invariant failed: original policy file is missing; it must not be removed or renamed.\n"
        f"Expected file: {POLICY_FILE}"
    )
    assert POLICY_FILE.is_file(), (
        "Final invariant failed: original policy path exists but is not a regular file.\n"
        f"Path: {POLICY_FILE}"
    )

    actual = POLICY_FILE.read_text(encoding="utf-8")
    assert actual == EXPECTED_POLICY_CONTENT, (
        "Final invariant failed: /home/user/iot-edge/device-policy.env was changed, but it must "
        "remain byte-for-byte identical to the prepared input policy.\n"
        f"Expected exact contents:\n{EXPECTED_POLICY_CONTENT!r}\n"
        f"Actual contents:\n{actual!r}"
    )


def test_only_expected_artifact_created_in_iot_edge_directory():
    assert IOT_EDGE_DIR.exists() and IOT_EDGE_DIR.is_dir(), (
        f"Cannot inspect directory because required directory is missing or invalid: {IOT_EDGE_DIR}"
    )

    expected_paths = {POLICY_FILE, FIREWALL_LOG}
    actual_paths = set(IOT_EDGE_DIR.iterdir())
    unexpected_paths = sorted(str(path) for path in actual_paths - expected_paths)
    missing_paths = sorted(str(path) for path in expected_paths - actual_paths)

    assert not missing_paths, (
        "Final invariant failed: expected files are missing from /home/user/iot-edge.\n"
        f"Missing: {missing_paths}"
    )
    assert not unexpected_paths, (
        "Final invariant failed: task should create exactly one artifact, firewall.apply.log, "
        "and should not create extra files or directories in /home/user/iot-edge.\n"
        f"Unexpected paths: {unexpected_paths}"
    )