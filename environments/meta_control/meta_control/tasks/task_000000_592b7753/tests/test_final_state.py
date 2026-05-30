# test_final_state.py
from pathlib import Path
import tarfile

BASE = Path("/home/user/iot_gateway_deploy")
DEVICE_CONFIG = Path("/home/user/iot_gateway_deploy/device_config")
OUT = Path("/home/user/iot_gateway_deploy/out")
ARCHIVE = Path("/home/user/iot_gateway_deploy/out/gateway-edge-backup.tar.gz")
LOG = Path("/home/user/iot_gateway_deploy/out/backup_verification.log")

EXPECTED_RELATIVE_FILES = {
    "config.yaml",
    "network/interfaces.conf",
    "services/mqtt.env",
    "services/sensor-sampler.env",
    "certs/device.crt",
    "certs/device.key",
    "manifest.txt",
}

EXPECTED_SOURCE_CONTENTS = {
    "config.yaml": (
        b"device_id: edge-gw-014\n"
        b"site: pump-station-west\n"
        b"sample_interval_seconds: 30\n"
        b"uplink: mqtt\n"
        b"log_level: info\n"
    ),
    "network/interfaces.conf": (
        b"[eth0]\n"
        b"mode=dhcp\n"
        b"metric=100\n"
        b"\n"
        b"[wlan0]\n"
        b"mode=disabled\n"
    ),
    "services/mqtt.env": (
        b"MQTT_HOST=broker.internal\n"
        b"MQTT_PORT=1883\n"
        b"MQTT_CLIENT_ID=edge-gw-014\n"
        b"MQTT_TLS=false\n"
    ),
    "services/sensor-sampler.env": (
        b"SENSOR_BUS=i2c-1\n"
        b"SENSOR_PROFILE=vibration-basic\n"
        b"SAMPLER_BATCH_SIZE=20\n"
    ),
    "certs/device.crt": (
        b"-----BEGIN CERTIFICATE-----\n"
        b"MIIBszCCAVmgAwIBAgIUEDGEGW014CERTFORTRAININGONLYwCgYIKoZIzj0EAwIw\n"
        b"EzERMA8GA1UEAwwIZWRnZS1ndzAeFw0yNDAxMDEwMDAwMDBaFw0yNzAxMDEwMDAw\n"
        b"MDBaMBMxETAPBgNVBAMMCGVkZ2UtZ3cwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNC\n"
        b"AATRAININGCERTDATAEDGEGW014ONLY0000000000000000000000000000000000\n"
        b"-----END CERTIFICATE-----\n"
    ),
    "certs/device.key": (
        b"-----BEGIN PRIVATE KEY-----\n"
        b"TRAINING-ONLY-NOT-A-REAL-PRIVATE-KEY-EDGE-GW-014\n"
        b"-----END PRIVATE KEY-----\n"
    ),
    "manifest.txt": (
        b"config.yaml\n"
        b"network/interfaces.conf\n"
        b"services/mqtt.env\n"
        b"services/sensor-sampler.env\n"
        b"certs/device.crt\n"
        b"certs/device.key\n"
    ),
}

EXPECTED_LOG_TEXT = (
    "archive=/home/user/iot_gateway_deploy/out/gateway-edge-backup.tar.gz\n"
    "exists=yes\n"
    "format=gzip-compressed-tar\n"
    "root_prefix=none\n"
    "file_count=7\n"
    "status=verified\n"
)


def _read_archive_members():
    assert ARCHIVE.exists(), f"Required archive is missing: {ARCHIVE}"
    assert ARCHIVE.is_file(), f"Archive path exists but is not a regular file: {ARCHIVE}"
    assert ARCHIVE.stat().st_size > 0, f"Archive exists but is empty: {ARCHIVE}"

    try:
        with tarfile.open(ARCHIVE, mode="r:gz") as tf:
            return tf.getmembers()
    except tarfile.ReadError as exc:
        raise AssertionError(
            f"{ARCHIVE} is not readable as a gzip-compressed tar archive: {exc}"
        ) from exc
    except tarfile.TarError as exc:
        raise AssertionError(
            f"{ARCHIVE} could not be read successfully as a tar archive: {exc}"
        ) from exc


def _normalize_tar_name(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    return name


def test_final_archive_artifact_exists_and_is_gzip_compressed_tar():
    members = _read_archive_members()
    assert members, f"Archive is readable but contains no entries: {ARCHIVE}"


def test_archive_paths_are_relative_to_device_config_without_forbidden_prefixes():
    members = _read_archive_members()
    names = [_normalize_tar_name(member.name) for member in members]

    forbidden_absolute = [name for name in names if name.startswith("/")]
    assert not forbidden_absolute, (
        "Archive must not contain absolute paths beginning with '/'. "
        f"Forbidden entries found: {forbidden_absolute}"
    )

    forbidden_device_config = [
        name
        for name in names
        if name == "device_config" or name == "device_config/" or name.startswith("device_config/")
    ]
    assert not forbidden_device_config, (
        "Archive entries must be relative to /home/user/iot_gateway_deploy/device_config "
        "and must not include a leading device_config/ component. "
        f"Forbidden entries found: {forbidden_device_config}"
    )

    forbidden_out_or_scripts = [
        name
        for name in names
        if (
            name == "out"
            or name.startswith("out/")
            or name == "scripts"
            or name.startswith("scripts/")
            or "/out/" in name
            or "/scripts/" in name
        )
    ]
    assert not forbidden_out_or_scripts, (
        "Archive must not include files from /home/user/iot_gateway_deploy/out or "
        f"/home/user/iot_gateway_deploy/scripts. Forbidden entries found: {forbidden_out_or_scripts}"
    )


def test_archive_contains_exactly_the_expected_seven_regular_files_no_more_no_less():
    members = _read_archive_members()

    regular_file_names = {
        _normalize_tar_name(member.name)
        for member in members
        if member.isfile()
    }

    assert regular_file_names == EXPECTED_RELATIVE_FILES, (
        "Archive regular file members are not exactly the seven required paths relative to "
        "/home/user/iot_gateway_deploy/device_config.\n"
        f"Missing files: {sorted(EXPECTED_RELATIVE_FILES - regular_file_names)}\n"
        f"Unexpected files: {sorted(regular_file_names - EXPECTED_RELATIVE_FILES)}\n"
        f"Actual regular files: {sorted(regular_file_names)}"
    )

    assert len(regular_file_names) == 7, (
        "Archive must contain exactly 7 regular files; directory entries must not be counted. "
        f"Actual regular file count: {len(regular_file_names)}"
    )


def test_archive_file_contents_match_device_config_sources_byte_for_byte():
    assert DEVICE_CONFIG.exists(), f"Source directory is missing: {DEVICE_CONFIG}"
    assert DEVICE_CONFIG.is_dir(), f"Source path is not a directory: {DEVICE_CONFIG}"

    with tarfile.open(ARCHIVE, mode="r:gz") as tf:
        for relative_name in sorted(EXPECTED_RELATIVE_FILES):
            source_path = DEVICE_CONFIG / relative_name
            assert source_path.exists(), f"Expected source file is missing: {source_path}"
            assert source_path.is_file(), f"Expected source path is not a regular file: {source_path}"

            expected_bytes = EXPECTED_SOURCE_CONTENTS[relative_name]
            actual_source_bytes = source_path.read_bytes()
            assert actual_source_bytes == expected_bytes, (
                f"Source file contents changed unexpectedly for {source_path}; "
                "the archive must match the required device_config source bytes."
            )

            try:
                extracted = tf.extractfile(relative_name)
            except KeyError as exc:
                raise AssertionError(
                    f"Archive is missing required regular file member: {relative_name}"
                ) from exc

            assert extracted is not None, (
                f"Archive member exists but cannot be extracted as a regular file: {relative_name}"
            )

            archived_bytes = extracted.read()
            assert archived_bytes == actual_source_bytes, (
                f"Archived contents for {relative_name} do not byte-for-byte match "
                f"the source file {source_path}."
            )


def test_archive_contains_no_non_directory_special_entries():
    members = _read_archive_members()

    special_entries = [
        _normalize_tar_name(member.name)
        for member in members
        if not member.isfile() and not member.isdir()
    ]
    assert not special_entries, (
        "Archive should contain only regular files and optional directory entries. "
        f"Unexpected special entries found: {special_entries}"
    )


def test_verification_log_exists_and_matches_required_six_lines_exactly():
    assert LOG.exists(), f"Required verification log is missing: {LOG}"
    assert LOG.is_file(), f"Verification log path exists but is not a regular file: {LOG}"

    raw = LOG.read_bytes()
    try:
        actual_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"Verification log is not valid UTF-8 text: {LOG}") from exc

    assert actual_text == EXPECTED_LOG_TEXT, (
        "Verification log must contain exactly the required six lines, with "
        "root_prefix=none, file_count=7, and status=verified. A single trailing newline "
        "after status=verified is expected.\n"
        f"Expected:\n{EXPECTED_LOG_TEXT!r}\n"
        f"Actual:\n{actual_text!r}"
    )

    assert actual_text.splitlines() == [
        "archive=/home/user/iot_gateway_deploy/out/gateway-edge-backup.tar.gz",
        "exists=yes",
        "format=gzip-compressed-tar",
        "root_prefix=none",
        "file_count=7",
        "status=verified",
    ], "Verification log lines are not exactly the required six lines in the required order."


def test_final_out_directory_contains_exactly_the_required_deliverables_as_regular_files():
    assert OUT.exists(), f"Output directory is missing: {OUT}"
    assert OUT.is_dir(), f"Output path exists but is not a directory: {OUT}"

    expected_outputs = {ARCHIVE, LOG}
    actual_regular_files = {path for path in OUT.iterdir() if path.is_file()}

    assert actual_regular_files == expected_outputs, (
        "Output directory must contain exactly one compressed tar archive and one verification log "
        "as regular files.\n"
        f"Missing: {sorted(str(path) for path in expected_outputs - actual_regular_files)}\n"
        f"Unexpected regular files: {sorted(str(path) for path in actual_regular_files - expected_outputs)}"
    )