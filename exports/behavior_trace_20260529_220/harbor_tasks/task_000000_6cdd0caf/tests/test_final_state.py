# test_final_state.py
import datetime as _dt
import hashlib
import re
from pathlib import Path

import pytest


BASE = Path("/home/user/research_cluster")
RAW = BASE / "datasets" / "raw"
MANIFESTS = BASE / "datasets" / "manifests"
SHARDS = MANIFESTS / "shards"
FINAL_MANIFEST = MANIFESTS / "final_manifest.tsv"
VERIFICATION_LOG = BASE / "run_logs" / "verification.log"

HEADER = "dataset\tshard\trecord_id\tfilename\tsize_bytes\tsha256"

EXPECTED_RAW_FILES = {
    RAW / "alpha" / "a001.txt": b"alpha sample 001\ncondition=control\nvalue=17\n",
    RAW / "alpha" / "a002.txt": b"alpha sample 002\ncondition=treated\nvalue=23\n",
    RAW / "alpha" / "a003.txt": b"alpha sample 003\ncondition=control\nvalue=19\n",
    RAW / "alpha" / "a004.txt": b"alpha sample 004\ncondition=treated\nvalue=29\n",
    RAW / "beta" / "b001.txt": b"beta sample 001\ncondition=control\nvalue=31\n",
    RAW / "beta" / "b002.txt": b"beta sample 002\ncondition=treated\nvalue=37\n",
    RAW / "beta" / "b003.txt": b"beta sample 003\ncondition=control\nvalue=41\n",
    RAW / "gamma" / "g001.txt": b"gamma sample 001\ncondition=control\nvalue=43\n",
    RAW / "gamma" / "g002.txt": b"gamma sample 002\ncondition=treated\nvalue=47\n",
    RAW / "gamma" / "g003.txt": b"gamma sample 003\ncondition=control\nvalue=53\n",
    RAW / "gamma" / "g004.txt": b"gamma sample 004\ncondition=treated\nvalue=59\n",
    RAW / "gamma" / "g005.txt": b"gamma sample 005\ncondition=control\nvalue=61\n",
}

EXPECTED_SHARD_ASSIGNMENTS = {
    0: [
        RAW / "alpha" / "a001.txt",
        RAW / "alpha" / "a004.txt",
        RAW / "beta" / "b003.txt",
        RAW / "gamma" / "g003.txt",
    ],
    1: [
        RAW / "alpha" / "a002.txt",
        RAW / "beta" / "b001.txt",
        RAW / "gamma" / "g001.txt",
        RAW / "gamma" / "g004.txt",
    ],
    2: [
        RAW / "alpha" / "a003.txt",
        RAW / "beta" / "b002.txt",
        RAW / "gamma" / "g002.txt",
        RAW / "gamma" / "g005.txt",
    ],
}


def expected_row_for(path: Path, shard: int) -> tuple[str, str, str, str, str, str]:
    data = path.read_bytes()
    return (
        path.parent.name,
        str(shard),
        path.stem,
        path.name,
        str(len(data)),
        hashlib.sha256(data).hexdigest(),
    )


def expected_all_rows() -> list[tuple[str, str, str, str, str, str]]:
    rows = []
    for shard, paths in EXPECTED_SHARD_ASSIGNMENTS.items():
        for path in paths:
            rows.append(expected_row_for(path, shard))
    return sorted(rows, key=lambda r: (r[0], int(r[1]), r[2], r[3]))


def read_text_lines_strict(path: Path) -> list[str]:
    assert path.exists(), f"Required file is missing: {path}"
    assert path.is_file(), f"Required path exists but is not a file: {path}"
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"File is not valid UTF-8: {path}: {exc}")
    assert text.endswith("\n"), f"File must be newline-terminated: {path}"
    return text.splitlines()


def parse_tsv_rows(path: Path, *, expected_line_count: int | None = None) -> list[tuple[str, ...]]:
    lines = read_text_lines_strict(path)
    if expected_line_count is not None:
        assert len(lines) == expected_line_count, (
            f"{path} has wrong number of lines: expected {expected_line_count}, "
            f"found {len(lines)}. Lines: {lines!r}"
        )

    rows = []
    for line_number, line in enumerate(lines, start=1):
        fields = tuple(line.split("\t"))
        assert len(fields) == 6, (
            f"{path} line {line_number} must have exactly 6 tab-separated fields; "
            f"found {len(fields)} fields in {line!r}"
        )
        rows.append(fields)
    return rows


def test_raw_dataset_files_were_not_modified_or_added_or_removed():
    raw_files = sorted(p for p in RAW.rglob("*") if p.is_file())
    expected_files = sorted(EXPECTED_RAW_FILES)

    assert raw_files == expected_files, (
        "Raw dataset file set was changed. The task explicitly says not to modify raw data.\n"
        f"Expected: {[str(p) for p in expected_files]}\n"
        f"Found: {[str(p) for p in raw_files]}"
    )

    for path, expected_bytes in sorted(EXPECTED_RAW_FILES.items()):
        assert path.read_bytes() == expected_bytes, (
            f"Raw data file contents were modified: {path}"
        )


@pytest.mark.parametrize("shard", [0, 1, 2])
def test_each_shard_manifest_exists_with_exact_expected_rows(shard):
    shard_path = SHARDS / f"shard_{shard}.tsv"
    expected_rows = [expected_row_for(path, shard) for path in EXPECTED_SHARD_ASSIGNMENTS[shard]]

    actual_rows = parse_tsv_rows(shard_path, expected_line_count=4)

    assert actual_rows == expected_rows, (
        f"Shard manifest {shard_path} is incomplete or incorrect.\n"
        f"Expected rows:\n{expected_rows!r}\n"
        f"Actual rows:\n{actual_rows!r}"
    )


def test_shard_1_includes_gamma_g004_record_from_full_rerun():
    shard_1_path = Path("/home/user/research_cluster/datasets/manifests/shards/shard_1.tsv")
    rows = parse_tsv_rows(shard_1_path, expected_line_count=4)
    assert expected_row_for(RAW / "gamma" / "g004.txt", 1) in rows, (
        "shard_1.tsv is missing gamma/g004.txt. This indicates shard 1 was not "
        "successfully rerun with RESEARCH_SCAN_FULL=1 after detecting incomplete output."
    )


def test_final_manifest_exists_with_exact_header_and_all_expected_rows():
    lines = read_text_lines_strict(FINAL_MANIFEST)

    assert len(lines) == 13, (
        f"Final manifest must contain exactly 13 lines: 1 header plus 12 data rows. "
        f"Found {len(lines)} lines in {FINAL_MANIFEST}."
    )
    assert lines[0] == HEADER, (
        f"Final manifest header is wrong.\n"
        f"Expected: {HEADER!r}\n"
        f"Found: {lines[0]!r}"
    )

    actual_rows = []
    for line_number, line in enumerate(lines[1:], start=2):
        fields = tuple(line.split("\t"))
        assert len(fields) == 6, (
            f"Final manifest line {line_number} must have exactly 6 tab-separated fields; "
            f"found {len(fields)} fields in {line!r}"
        )
        actual_rows.append(fields)

    expected_rows = expected_all_rows()

    assert actual_rows == expected_rows, (
        "Final manifest data rows are missing, unsorted, or contain incorrect metadata.\n"
        f"Expected rows:\n{expected_rows!r}\n"
        f"Actual rows:\n{actual_rows!r}"
    )


def test_final_manifest_rows_have_valid_sizes_and_sha256_digests_matching_raw_files():
    lines = read_text_lines_strict(FINAL_MANIFEST)
    assert lines and lines[0] == HEADER, "Cannot validate final manifest rows because header is missing or incorrect."

    seen_raw_paths = set()
    for line_number, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        assert len(fields) == 6, (
            f"Final manifest line {line_number} must have exactly 6 fields; found {len(fields)}."
        )
        dataset, shard_text, record_id, filename, size_text, sha256_text = fields

        raw_path = RAW / dataset / filename
        assert raw_path in EXPECTED_RAW_FILES, (
            f"Final manifest line {line_number} references an unexpected raw file: {raw_path}"
        )
        assert raw_path.exists(), (
            f"Final manifest line {line_number} references a missing raw file: {raw_path}"
        )
        assert record_id == raw_path.stem, (
            f"Final manifest line {line_number} has record_id={record_id!r}, "
            f"but expected filename stem {raw_path.stem!r}."
        )

        try:
            shard = int(shard_text)
        except ValueError:
            pytest.fail(f"Final manifest line {line_number} has non-integer shard value: {shard_text!r}")

        assert raw_path in EXPECTED_SHARD_ASSIGNMENTS[shard], (
            f"Final manifest line {line_number} assigns {raw_path} to shard {shard}, "
            "which does not match the intended shard assignment."
        )

        data = raw_path.read_bytes()
        assert size_text == str(len(data)), (
            f"Final manifest line {line_number} has wrong size for {raw_path}: "
            f"expected {len(data)}, found {size_text!r}."
        )
        assert sha256_text == hashlib.sha256(data).hexdigest(), (
            f"Final manifest line {line_number} has wrong SHA-256 digest for {raw_path}. "
            "Digest must be computed from file contents, not filename."
        )

        seen_raw_paths.add(raw_path)

    assert seen_raw_paths == set(EXPECTED_RAW_FILES), (
        "Final manifest does not cover exactly all 12 expected raw files.\n"
        f"Missing: {[str(p) for p in sorted(set(EXPECTED_RAW_FILES) - seen_raw_paths)]}\n"
        f"Unexpected: {[str(p) for p in sorted(seen_raw_paths - set(EXPECTED_RAW_FILES))]}"
    )


def test_final_manifest_rows_are_sorted_by_dataset_numeric_shard_record_id_filename():
    lines = read_text_lines_strict(FINAL_MANIFEST)
    rows = [tuple(line.split("\t")) for line in lines[1:]]
    sorted_rows = sorted(rows, key=lambda r: (r[0], int(r[1]), r[2], r[3]))

    assert rows == sorted_rows, (
        "Final manifest rows are not sorted by dataset, numeric shard, record_id, filename."
    )


def test_verification_log_exists_with_exact_five_line_ok_format():
    raw = VERIFICATION_LOG.read_bytes() if VERIFICATION_LOG.exists() else None
    assert raw is not None, f"Required verification log is missing: {VERIFICATION_LOG}"
    assert VERIFICATION_LOG.is_file(), f"Verification log path exists but is not a file: {VERIFICATION_LOG}"

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"Verification log is not valid UTF-8: {VERIFICATION_LOG}: {exc}")

    assert text.endswith("\n"), (
        f"Verification log must be newline-terminated: {VERIFICATION_LOG}"
    )

    lines = text.splitlines()
    assert len(lines) == 5, (
        f"Verification log must contain exactly five lines; found {len(lines)} lines: {lines!r}"
    )

    assert lines[0] == "status=OK", (
        "verification.log must report status=OK only after a complete successful validation."
    )
    assert lines[1] == "raw_file_count=12", (
        f"verification.log has wrong raw file count line: {lines[1]!r}"
    )
    assert lines[2] == "manifest_row_count=12", (
        f"verification.log has wrong manifest row count line: {lines[2]!r}"
    )
    assert lines[3] == "shard_files=shard_0.tsv,shard_1.tsv,shard_2.tsv", (
        "verification.log shard_files line must list exactly "
        "shard_0.tsv,shard_1.tsv,shard_2.tsv in ascending shard order."
    )

    assert re.fullmatch(
        r"verified_at=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
        lines[4],
    ), (
        "verification.log verified_at line must be an ISO-8601 UTC timestamp like "
        "verified_at=2025-02-14T09:31:07Z."
    )

    timestamp_text = lines[4].split("=", 1)[1]
    try:
        parsed = _dt.datetime.strptime(timestamp_text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        pytest.fail(f"verified_at timestamp is not a valid UTC date/time: {timestamp_text!r}: {exc}")

    assert 2000 <= parsed.year <= 2100, (
        f"verified_at timestamp year is implausible: {timestamp_text!r}"
    )


def test_verification_log_claim_matches_actual_final_artifacts():
    log_lines = read_text_lines_strict(VERIFICATION_LOG)
    assert log_lines[0] == "status=OK", "verification.log does not report status=OK."

    manifest_lines = read_text_lines_strict(FINAL_MANIFEST)
    manifest_data_rows = manifest_lines[1:] if manifest_lines and manifest_lines[0] == HEADER else []
    raw_files = sorted(p for p in RAW.rglob("*") if p.is_file())

    assert log_lines[1] == f"raw_file_count={len(raw_files)}", (
        "verification.log raw_file_count does not match actual raw file count."
    )
    assert log_lines[2] == f"manifest_row_count={len(manifest_data_rows)}", (
        "verification.log manifest_row_count does not match actual final manifest row count."
    )

    shard_basenames = [f"shard_{i}.tsv" for i in range(3)]
    for basename in shard_basenames:
        assert (SHARDS / basename).exists(), (
            f"verification.log lists shard files, but required shard file is missing: {SHARDS / basename}"
        )
    assert log_lines[3] == "shard_files=" + ",".join(shard_basenames), (
        "verification.log shard_files line does not match the actual required shard set."
    )