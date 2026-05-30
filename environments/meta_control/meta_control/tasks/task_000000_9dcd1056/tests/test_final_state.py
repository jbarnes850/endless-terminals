# test_final_state.py
from pathlib import Path
import csv
import io

CANONICAL_DIR = Path("/home/user/netops/inventory/current/edge-a")
CANONICAL_DEVICES = Path("/home/user/netops/inventory/current/edge-a/devices.csv")
CANONICAL_ENDPOINT = Path("/home/user/netops/inventory/current/edge-a/endpoint.conf")
CANONICAL_VERIFY_LOG = Path("/home/user/netops/inventory/current/edge-a/migration_verify.log")

LEGACY_STATE_DIR = Path("/home/user/netops/sites/edge-a/state")
LEGACY_ACTIVE_DEVICES = Path("/home/user/netops/sites/edge-a/state/devices.csv")
RETIRED_MARKER = Path("/home/user/netops/sites/edge-a/state.RETIRED")

PREVIOUS_DEVICES = Path("/home/user/netops/inventory/previous/edge-a/devices.csv")

EXPECTED_DEVICES = (
    "device,mgmt_ip,role,status,last_checked\n"
    "edge-a-fw01,10.42.10.1,firewall,reachable,2025-02-14T09:15:00Z\n"
    "edge-a-rtr01,10.42.10.254,router,reachable,2025-02-14T09:17:45Z\n"
    "edge-a-sw02,10.42.10.12,switch,unreachable,2025-02-14T09:16:30Z\n"
)

EXPECTED_ENDPOINT = (
    "site=edge-a\n"
    "source=canonical\n"
    "inventory_dir=/home/user/netops/inventory/current/edge-a\n"
    "devices_file=/home/user/netops/inventory/current/edge-a/devices.csv\n"
)

EXPECTED_RETIRED_MARKER = (
    "retired_path=/home/user/netops/sites/edge-a/state\n"
    "canonical_path=/home/user/netops/inventory/current/edge-a\n"
    "reason=migrated-to-canonical-inventory\n"
)

EXPECTED_VERIFY_LOG = (
    "CHECKPOINT old_state_scanned\n"
    "CHECKPOINT canonical_created\n"
    "CHECKPOINT data_preserved\n"
    "CHECKPOINT old_path_retired\n"
    "CHECKPOINT endpoint_rotated\n"
    "CANONICAL_DEVICE_COUNT=3\n"
    "CANONICAL_DEVICE_LIST=edge-a-fw01|edge-a-rtr01|edge-a-sw02\n"
)

EXPECTED_HEADER = ["device", "mgmt_ip", "role", "status", "last_checked"]

EXPECTED_DEVICE_ROWS = [
    {
        "device": "edge-a-fw01",
        "mgmt_ip": "10.42.10.1",
        "role": "firewall",
        "status": "reachable",
        "last_checked": "2025-02-14T09:15:00Z",
    },
    {
        "device": "edge-a-rtr01",
        "mgmt_ip": "10.42.10.254",
        "role": "router",
        "status": "reachable",
        "last_checked": "2025-02-14T09:17:45Z",
    },
    {
        "device": "edge-a-sw02",
        "mgmt_ip": "10.42.10.12",
        "role": "switch",
        "status": "unreachable",
        "last_checked": "2025-02-14T09:16:30Z",
    },
]


def read_text(path: Path) -> str:
    assert path.exists(), f"Missing required final file: {path}"
    assert path.is_file(), f"Required final path is not a regular file: {path}"
    return path.read_text()


def assert_exact_file(path: Path, expected: str, description: str) -> None:
    actual = read_text(path)
    assert actual == expected, (
        f"{description} content is wrong for {path}\n"
        f"Expected exactly:\n{expected!r}\n"
        f"Got:\n{actual!r}"
    )
    assert actual.endswith("\n"), f"{description} must end with a newline: {path}"


def parse_canonical_devices():
    text = read_text(CANONICAL_DEVICES)
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return reader.fieldnames, rows


def test_canonical_directory_exists_as_final_source_of_truth():
    assert CANONICAL_DIR.exists(), (
        "Canonical inventory directory was not created: "
        "/home/user/netops/inventory/current/edge-a"
    )
    assert CANONICAL_DIR.is_dir(), (
        "Canonical inventory path exists but is not a directory: "
        "/home/user/netops/inventory/current/edge-a"
    )


def test_canonical_devices_csv_matches_exact_migrated_sorted_inventory():
    assert_exact_file(
        CANONICAL_DEVICES,
        EXPECTED_DEVICES,
        "Canonical devices.csv",
    )


def test_canonical_devices_csv_has_required_csv_semantics_only():
    fieldnames, rows = parse_canonical_devices()

    assert fieldnames == EXPECTED_HEADER, (
        "Canonical devices.csv must have exactly the header "
        "'device,mgmt_ip,role,status,last_checked' with no extra or missing columns; "
        f"got {fieldnames!r}"
    )

    assert len(rows) == 3, (
        "Canonical devices.csv must contain exactly three device data rows "
        "from the legacy source, excluding the header"
    )

    assert rows == EXPECTED_DEVICE_ROWS, (
        "Canonical devices.csv rows do not preserve the required legacy device "
        "semantics in alphabetic device order"
    )

    device_names = [row["device"] for row in rows]
    assert device_names == sorted(device_names), (
        f"Canonical devices.csv rows must be sorted alphabetically by device; got {device_names!r}"
    )
    assert len(device_names) == len(set(device_names)), (
        f"Canonical devices.csv must not contain duplicate device rows; got {device_names!r}"
    )

    for row in rows:
        assert set(row) == set(EXPECTED_HEADER), (
            f"Canonical devices.csv row has unexpected columns: {row!r}"
        )
        assert None not in row, (
            f"Canonical devices.csv contains extra unnamed columns in row: {row!r}"
        )

    canonical_text = CANONICAL_DEVICES.read_text()
    assert "2025-02-13T" not in canonical_text, (
        "Canonical devices.csv appears to contain stale timestamps from "
        "/home/user/netops/inventory/previous/edge-a/devices.csv instead of current legacy data"
    )
    assert "edge-a-sw02,10.42.10.12,switch,unreachable,2025-02-14T09:16:30Z" in canonical_text, (
        "Canonical devices.csv is missing edge-a-sw02 from the legacy active state source"
    )


def test_endpoint_conf_is_rotated_to_canonical_paths_exactly():
    assert_exact_file(
        CANONICAL_ENDPOINT,
        EXPECTED_ENDPOINT,
        "Canonical endpoint.conf",
    )

    endpoint_text = CANONICAL_ENDPOINT.read_text()
    assert "/home/user/netops/sites/edge-a/state" not in endpoint_text, (
        "Canonical endpoint.conf must not point tooling back to the retired legacy state path"
    )
    assert "source=legacy" not in endpoint_text, (
        "Canonical endpoint.conf must declare source=canonical, not source=legacy"
    )


def test_legacy_active_devices_csv_has_been_retired():
    assert not LEGACY_ACTIVE_DEVICES.exists(), (
        "Legacy active devices file still exists at "
        "/home/user/netops/sites/edge-a/state/devices.csv; "
        "future tooling could still read stale active state from the old path"
    )

    if LEGACY_STATE_DIR.exists():
        assert LEGACY_STATE_DIR.is_dir(), (
            "Legacy state path exists but is no longer a directory; if retained, "
            "it should not contain the active devices.csv file"
        )


def test_retirement_marker_exists_with_exact_required_content():
    assert_exact_file(
        RETIRED_MARKER,
        EXPECTED_RETIRED_MARKER,
        "Retirement marker state.RETIRED",
    )


def test_canonical_migration_verify_log_exists_with_exact_required_content():
    assert_exact_file(
        CANONICAL_VERIFY_LOG,
        EXPECTED_VERIFY_LOG,
        "Canonical migration_verify.log",
    )

    lines = CANONICAL_VERIFY_LOG.read_text().splitlines()
    assert len(lines) == 7, (
        "Canonical migration_verify.log must contain exactly seven lines"
    )
    assert lines[:5] == [
        "CHECKPOINT old_state_scanned",
        "CHECKPOINT canonical_created",
        "CHECKPOINT data_preserved",
        "CHECKPOINT old_path_retired",
        "CHECKPOINT endpoint_rotated",
    ], (
        "Canonical migration_verify.log checkpoint lines are missing or in the wrong order"
    )


def test_verify_log_count_and_list_are_consistent_with_canonical_devices_csv():
    fieldnames, rows = parse_canonical_devices()
    assert fieldnames == EXPECTED_HEADER, (
        "Cannot validate verify log derivation because canonical devices.csv header is wrong"
    )

    device_names = [row["device"] for row in rows]
    expected_count_line = f"CANONICAL_DEVICE_COUNT={len(rows)}"
    expected_list_line = f"CANONICAL_DEVICE_LIST={'|'.join(device_names)}"

    verify_lines = read_text(CANONICAL_VERIFY_LOG).splitlines()

    assert verify_lines[5] == expected_count_line, (
        "CANONICAL_DEVICE_COUNT in canonical migration_verify.log does not match "
        f"the row count read from {CANONICAL_DEVICES}; expected {expected_count_line!r}, "
        f"got {verify_lines[5]!r}"
    )
    assert verify_lines[6] == expected_list_line, (
        "CANONICAL_DEVICE_LIST in canonical migration_verify.log does not match "
        f"the device list read from {CANONICAL_DEVICES}; expected {expected_list_line!r}, "
        f"got {verify_lines[6]!r}"
    )


def test_final_state_does_not_depend_on_misleading_previous_inventory():
    assert CANONICAL_DEVICES.exists(), (
        "Canonical devices.csv is missing; final state must be based on the migrated legacy inventory"
    )

    canonical_text = CANONICAL_DEVICES.read_text()

    if PREVIOUS_DEVICES.exists():
        previous_text = PREVIOUS_DEVICES.read_text()
        assert canonical_text != previous_text, (
            "Canonical devices.csv exactly matches the misleading previous inventory; "
            "it must instead preserve the active legacy state data"
        )

    assert "edge-a-rtr01,10.42.10.254,router,reachable,2025-02-14T09:17:45Z" in canonical_text, (
        "Canonical inventory must contain the current 2025-02-14 router timestamp "
        "from the legacy active state, not stale previous inventory data"
    )
    assert "edge-a-rtr01,10.42.10.254,router,reachable,2025-02-13T09:17:45Z" not in canonical_text, (
        "Canonical inventory contains stale router timestamp from the misleading previous inventory"
    )