# test_final_state.py
import hashlib
import re
from pathlib import Path

import pytest


BASE = Path("/home/user/finops/cloud-costs")
RAW = Path("/home/user/finops/cloud-costs/raw")
AUDIT = Path("/home/user/finops/cloud-costs/audit")
TMP = Path("/home/user/finops/cloud-costs/tmp")
MANIFEST = Path("/home/user/finops/cloud-costs/audit/cloud_cost_checksums.sha256")
VERIFICATION_LOG = Path("/home/user/finops/cloud-costs/audit/verification.log")

EXPECTED_CSV_NAMES = [
    "aws_costs_january.csv",
    "azure_costs_january.csv",
    "gcp_costs_january.csv",
]

MANIFEST_LINE_RE = re.compile(r"^[0-9a-f]{64}  raw/[^/]+\.csv$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest_bytes() -> bytes:
    assert MANIFEST.exists(), (
        f"Missing required checksum manifest: {MANIFEST}\n"
        "Create this file after computing SHA-256 checksums for direct CSV files in "
        f"{RAW}."
    )
    assert MANIFEST.is_file(), f"Checksum manifest path exists but is not a regular file: {MANIFEST}"
    return MANIFEST.read_bytes()


def parse_manifest_lines():
    data = read_manifest_bytes()

    assert data.endswith(b"\n"), (
        f"Checksum manifest must end with a trailing newline: {MANIFEST}"
    )
    assert not data.endswith(b"\n\n"), (
        f"Checksum manifest must end with exactly one trailing newline, not multiple: {MANIFEST}"
    )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Checksum manifest must be valid UTF-8 text: {MANIFEST}: {exc}")

    lines = text.splitlines()
    return lines


def expected_direct_csv_files():
    assert RAW.exists(), f"Missing required raw directory: {RAW}"
    assert RAW.is_dir(), f"Raw path is not a directory: {RAW}"

    return sorted(
        path
        for path in RAW.iterdir()
        if path.is_file() and path.suffix == ".csv"
    )


def expected_manifest_lines():
    return [
        f"{sha256_file(RAW / name)}  raw/{name}"
        for name in EXPECTED_CSV_NAMES
    ]


def test_required_output_files_exist_as_regular_files() -> None:
    assert AUDIT.exists(), f"Missing required audit directory: {AUDIT}"
    assert AUDIT.is_dir(), f"Audit path is not a directory: {AUDIT}"

    assert MANIFEST.exists(), f"Missing required checksum manifest: {MANIFEST}"
    assert MANIFEST.is_file(), f"Checksum manifest is not a regular file: {MANIFEST}"

    assert VERIFICATION_LOG.exists(), f"Missing required verification log: {VERIFICATION_LOG}"
    assert VERIFICATION_LOG.is_file(), f"Verification log is not a regular file: {VERIFICATION_LOG}"


def test_raw_direct_csv_file_set_is_exactly_expected() -> None:
    actual_names = [path.name for path in expected_direct_csv_files()]

    assert actual_names == EXPECTED_CSV_NAMES, (
        f"The direct regular .csv files under {RAW} are not the expected final input set.\n"
        f"Expected exactly: {EXPECTED_CSV_NAMES}\n"
        f"Found: {actual_names}"
    )


def test_manifest_has_exact_formatting_and_no_extra_lines() -> None:
    lines = parse_manifest_lines()

    assert len(lines) == 3, (
        f"Manifest must contain exactly one line for each direct CSV file in {RAW}.\n"
        f"Expected 3 lines; found {len(lines)} lines: {lines!r}"
    )

    for index, line in enumerate(lines, start=1):
        assert line != "", (
            f"Manifest must not contain blank lines; blank line found at line {index}."
        )
        assert MANIFEST_LINE_RE.fullmatch(line), (
            f"Manifest line {index} has the wrong format:\n"
            f"  {line!r}\n"
            "Expected exactly: <64 lowercase hex sha256> two spaces raw/<filename>.csv"
        )

        digest, path_field = line.split("  ", 1)

        assert len(digest) == 64, (
            f"Manifest line {index} digest must be 64 characters for SHA-256, "
            f"not {len(digest)} characters: {line!r}"
        )
        assert len(digest) != 32, (
            f"Manifest line {index} appears to contain an MD5-length digest: {line!r}"
        )
        assert path_field.startswith("raw/"), (
            f"Manifest line {index} path must start with 'raw/': {line!r}"
        )
        assert not path_field.startswith("/"), (
            f"Manifest line {index} must not use an absolute path: {line!r}"
        )
        assert "/" not in path_field[len("raw/"):], (
            f"Manifest line {index} must name only a file directly inside raw/: {line!r}"
        )

    assert all("README.txt" not in line for line in lines), (
        "Manifest must not include raw/README.txt or any README entry."
    )
    assert all("tmp/" not in line and "aws_costs_january_copy.csv" not in line for line in lines), (
        f"Manifest must not include files from {TMP} or temporary copies."
    )
    assert all("/home/user/finops/cloud-costs" not in line for line in lines), (
        "Manifest must not contain absolute project paths."
    )


def test_manifest_paths_are_sorted_and_match_exact_direct_csv_files() -> None:
    lines = parse_manifest_lines()
    path_fields = [line.split("  ", 1)[1] for line in lines]

    expected_paths = [f"raw/{name}" for name in EXPECTED_CSV_NAMES]

    assert path_fields == sorted(path_fields), (
        f"Manifest lines must be sorted lexicographically by the path field.\n"
        f"Found order: {path_fields}\n"
        f"Sorted order: {sorted(path_fields)}"
    )
    assert path_fields == expected_paths, (
        f"Manifest includes the wrong set of files.\n"
        f"Expected exactly: {expected_paths}\n"
        f"Found: {path_fields}\n"
        "Only regular .csv files directly inside the raw directory may be included."
    )


def test_manifest_digests_are_sha256_of_current_csv_contents() -> None:
    actual_lines = parse_manifest_lines()
    expected_lines = expected_manifest_lines()

    assert actual_lines == expected_lines, (
        "Manifest contents do not match the SHA-256 checksums of the current direct "
        f"CSV files in {RAW}.\n"
        f"Expected:\n" + "\n".join(expected_lines) + "\n"
        f"Actual:\n" + "\n".join(actual_lines) + "\n"
        "Regenerate the manifest with SHA-256, relative raw/<filename> paths, exactly "
        "two spaces as the separator, and sorted by path."
    )


def test_verification_log_exact_contents() -> None:
    expected_contents = (
        "artifact_exists=yes\n"
        "algorithm=sha256\n"
        "csv_file_count=3\n"
        "manifest_verified=yes\n"
    )

    assert VERIFICATION_LOG.exists(), f"Missing required verification log: {VERIFICATION_LOG}"
    assert VERIFICATION_LOG.is_file(), f"Verification log is not a regular file: {VERIFICATION_LOG}"

    actual_contents = VERIFICATION_LOG.read_text(encoding="utf-8")

    assert actual_contents == expected_contents, (
        f"Verification log has incorrect contents: {VERIFICATION_LOG}\n"
        f"Expected exactly:\n{expected_contents!r}\n"
        f"Actual:\n{actual_contents!r}"
    )


def test_verification_log_csv_count_matches_manifest_and_raw_directory() -> None:
    manifest_lines = parse_manifest_lines()
    direct_csv_count = len(expected_direct_csv_files())

    log_text = VERIFICATION_LOG.read_text(encoding="utf-8")
    count_line = next(
        (line for line in log_text.splitlines() if line.startswith("csv_file_count=")),
        None,
    )

    assert count_line is not None, (
        "Verification log must contain a csv_file_count=<number> line."
    )

    try:
        logged_count = int(count_line.split("=", 1)[1])
    except ValueError:
        pytest.fail(
            f"verification.log csv_file_count must be an integer; found: {count_line!r}"
        )

    assert logged_count == direct_csv_count == len(manifest_lines) == 3, (
        "verification.log csv_file_count must match both the number of direct CSV files "
        f"in {RAW} and the number of manifest entries.\n"
        f"Logged count: {logged_count}\n"
        f"Direct CSV count: {direct_csv_count}\n"
        f"Manifest line count: {len(manifest_lines)}"
    )