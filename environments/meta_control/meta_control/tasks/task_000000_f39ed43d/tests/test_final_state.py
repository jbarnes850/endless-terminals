# test_final_state.py
from pathlib import Path

BASE = Path("/home/user/build_staging")
LEGACY = Path("/home/user/build_staging/legacy_artifacts")
RELEASE = Path("/home/user/build_staging/release_artifacts")
LOG = Path("/home/user/build_staging/artifact_migration.log")

EXPECTED_ARTIFACTS = {
    "api-server-1.4.2-linux-amd64.tar.gz": "artifact api-server 1.4.2 linux amd64\n",
    "api-server-1.4.2-linux-arm64.tar.gz": "artifact api-server 1.4.2 linux arm64\n",
    "worker-1.4.2-linux-amd64.tar.gz": "artifact worker 1.4.2 linux amd64\n",
    "worker-1.4.2-linux-arm64.tar.gz": "artifact worker 1.4.2 linux arm64\n",
}

EXPECTED_LEGACY_NON_ARTIFACTS = {
    "checksums.txt": "legacy checksum file - do not migrate\n",
    "build-notes.md": "# Build notes\nThese notes stay in the legacy directory.\n",
}

EXPECTED_DESTINATION_FILES = sorted(EXPECTED_ARTIFACTS)
EXPECTED_LOG_LINES = [
    "SOURCE_RETIRED=yes",
    "DESTINATION_COUNT=4",
    "DESTINATION_FILES="
    + ",".join(EXPECTED_DESTINATION_FILES),
]


def _direct_regular_files(directory: Path):
    assert directory.exists(), f"Required directory is missing: {directory}"
    assert directory.is_dir(), f"Required path is not a directory: {directory}"
    return [path for path in directory.iterdir() if path.is_file()]


def _direct_tar_gz_files(directory: Path):
    return sorted(
        path for path in _direct_regular_files(directory)
        if path.name.endswith(".tar.gz")
    )


def test_legacy_source_is_retired_and_contains_no_direct_tar_gz_files():
    legacy_tarballs = [path.name for path in _direct_tar_gz_files(LEGACY)]

    assert legacy_tarballs == [], (
        "The old legacy artifact directory must no longer contain any direct "
        f"*.tar.gz files after migration. Remaining files in {LEGACY}: "
        f"{legacy_tarballs!r}. This usually means artifacts were copied instead "
        "of moved, or the source was not fully retired."
    )


def test_release_directory_contains_exact_expected_migrated_artifact_filenames():
    release_tarballs = sorted(path.name for path in _direct_tar_gz_files(RELEASE))

    assert release_tarballs == EXPECTED_DESTINATION_FILES, (
        "The new canonical artifact directory must contain exactly the four "
        "expected migrated .tar.gz files directly inside it, with filenames "
        "preserved exactly. "
        f"Expected in {RELEASE}: {EXPECTED_DESTINATION_FILES!r}; "
        f"found: {release_tarballs!r}."
    )


def test_release_artifact_contents_are_preserved_exactly():
    for filename, expected_content in EXPECTED_ARTIFACTS.items():
        artifact_path = RELEASE / filename

        assert artifact_path.exists(), (
            f"Expected migrated artifact is missing from canonical directory: "
            f"{artifact_path}"
        )
        assert artifact_path.is_file(), (
            f"Expected migrated artifact path is not a regular file: "
            f"{artifact_path}"
        )

        actual_content = artifact_path.read_text()
        assert actual_content == expected_content, (
            f"Migrated artifact content mismatch for {artifact_path}. "
            f"Expected {expected_content!r}, got {actual_content!r}."
        )


def test_legacy_non_artifact_files_remain_with_exact_contents():
    for filename, expected_content in EXPECTED_LEGACY_NON_ARTIFACTS.items():
        legacy_path = LEGACY / filename

        assert legacy_path.exists(), (
            f"Non-artifact file should have remained in the legacy directory "
            f"but is missing: {legacy_path}"
        )
        assert legacy_path.is_file(), (
            f"Legacy non-artifact path should be a regular file: {legacy_path}"
        )

        actual_content = legacy_path.read_text()
        assert actual_content == expected_content, (
            f"Legacy non-artifact file content changed unexpectedly for "
            f"{legacy_path}. Expected {expected_content!r}, got "
            f"{actual_content!r}."
        )


def test_release_directory_has_no_unexpected_direct_regular_files():
    actual_regular_names = sorted(path.name for path in _direct_regular_files(RELEASE))

    assert actual_regular_names == EXPECTED_DESTINATION_FILES, (
        "The canonical artifact directory should contain only the expected "
        "direct regular artifact files. "
        f"Expected files in {RELEASE}: {EXPECTED_DESTINATION_FILES!r}; "
        f"found: {actual_regular_names!r}."
    )


def test_artifact_migration_log_exists_with_exact_final_state_format():
    assert LOG.exists(), f"Verification log was not created: {LOG}"
    assert LOG.is_file(), f"Verification log path is not a regular file: {LOG}"

    raw_log = LOG.read_text()

    assert not raw_log.endswith("\n\n"), (
        f"Verification log {LOG} has an extra trailing blank line. The log may "
        "end with one final newline or no final newline, but must not contain "
        "additional blank lines."
    )

    normalized_log = raw_log[:-1] if raw_log.endswith("\n") else raw_log
    actual_lines = normalized_log.split("\n")

    assert actual_lines == EXPECTED_LOG_LINES, (
        "Verification log content is incorrect. It must reflect the final state "
        f"of the canonical destination directory {RELEASE}, not a stale listing "
        f"from {LEGACY}. "
        f"Expected exact lines: {EXPECTED_LOG_LINES!r}; got: {actual_lines!r}."
    )


def test_log_destination_count_and_files_match_actual_release_directory_state():
    """
    Redundant consistency check with a focused failure message: the log must be
    derived from /home/user/build_staging/release_artifacts after migration.
    """
    assert LOG.exists(), f"Verification log was not created: {LOG}"

    raw_log = LOG.read_text()
    normalized_log = raw_log[:-1] if raw_log.endswith("\n") else raw_log
    lines = normalized_log.split("\n")

    assert len(lines) == 3, (
        f"Verification log must contain exactly three lines and no extra text. "
        f"Got {len(lines)} lines: {lines!r}."
    )

    log_map = {}
    for line in lines:
        assert "=" in line, f"Malformed log line missing '=': {line!r}"
        key, value = line.split("=", 1)
        log_map[key] = value

    actual_destination_files = sorted(
        path.name for path in _direct_tar_gz_files(RELEASE)
    )
    actual_destination_files_csv = ",".join(actual_destination_files)

    assert log_map.get("SOURCE_RETIRED") == "yes", (
        "SOURCE_RETIRED must be 'yes' because the legacy directory contains "
        f"zero direct .tar.gz files. Got: {log_map.get('SOURCE_RETIRED')!r}."
    )
    assert log_map.get("DESTINATION_COUNT") == str(len(actual_destination_files)), (
        "DESTINATION_COUNT must equal the number of direct .tar.gz files in "
        f"{RELEASE}. Expected {len(actual_destination_files)!r}, got "
        f"{log_map.get('DESTINATION_COUNT')!r}."
    )
    assert log_map.get("DESTINATION_FILES") == actual_destination_files_csv, (
        "DESTINATION_FILES must be the sorted comma-separated filenames of "
        f"direct .tar.gz files in {RELEASE}. Expected "
        f"{actual_destination_files_csv!r}, got "
        f"{log_map.get('DESTINATION_FILES')!r}."
    )