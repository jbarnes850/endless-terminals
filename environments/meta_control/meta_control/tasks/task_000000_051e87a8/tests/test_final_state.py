# test_final_state.py
import subprocess
from pathlib import Path

import pytest

REPO = Path("/home/user/ml-data-repo")
MANIFEST = Path("/home/user/ml-data-repo/training_data_manifest.tsv")
VERIFY_LOG = Path("/home/user/ml-data-repo/training_data_manifest.verify.log")

EXPECTED_MANIFEST_LINES = [
    "git_path\trecord_count\tsplit",
    "data/raw/test/shard-000.jsonl\t1\ttest",
    "data/raw/test/shard-001.jsonl\t5\ttest",
    "data/raw/train/shard-000.jsonl\t3\ttrain",
    "data/raw/train/shard-001.jsonl\t2\ttrain",
    "data/raw/validation/shard-000.jsonl\t4\tvalidation",
]

EXPECTED_VERIFY_LOG_LINES = [
    "artifact=training_data_manifest.tsv",
    "tracked_jsonl_files=5",
    "manifest_rows=5",
    "all_rows_have_three_columns=yes",
    "status=verified",
]

EXPECTED_ELIGIBLE_PATHS = [
    "data/raw/test/shard-000.jsonl",
    "data/raw/test/shard-001.jsonl",
    "data/raw/train/shard-000.jsonl",
    "data/raw/train/shard-001.jsonl",
    "data/raw/validation/shard-000.jsonl",
]

EXPECTED_COUNTS = {
    "data/raw/test/shard-000.jsonl": 1,
    "data/raw/test/shard-001.jsonl": 5,
    "data/raw/train/shard-000.jsonl": 3,
    "data/raw/train/shard-001.jsonl": 2,
    "data/raw/validation/shard-000.jsonl": 4,
}

EXPECTED_SPLITS = {
    "data/raw/test/shard-000.jsonl": "test",
    "data/raw/test/shard-001.jsonl": "test",
    "data/raw/train/shard-000.jsonl": "train",
    "data/raw/train/shard-001.jsonl": "train",
    "data/raw/validation/shard-000.jsonl": "validation",
}

FORBIDDEN_PATHS = {
    "data/raw/train/debug-sample.jsonl",
    "data/raw/validation/local-copy.jsonl",
    "data/raw/train/.cache.jsonl",
    "data/raw/test/shard-999.tmp",
    "tmp/generated_manifest.tsv",
}


def run_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_text_exact(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_lines_exact(path: Path):
    return read_text_exact(path).splitlines()


def non_empty_line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def parse_manifest_rows():
    lines = read_lines_exact(MANIFEST)
    rows = []
    for line_number, line in enumerate(lines[1:], start=2):
        columns = line.split("\t")
        assert len(columns) == 3, (
            f"Manifest row {line_number} must have exactly three tab-separated columns, "
            f"but got {len(columns)} columns: {line!r}"
        )
        git_path, record_count, split = columns
        rows.append(
            {
                "line_number": line_number,
                "git_path": git_path,
                "record_count": record_count,
                "split": split,
            }
        )
    return rows


def test_manifest_file_exists_at_required_absolute_path():
    assert MANIFEST.exists(), (
        "Missing required manifest file at absolute path "
        "/home/user/ml-data-repo/training_data_manifest.tsv"
    )
    assert MANIFEST.is_file(), (
        "Required manifest path exists but is not a regular file: "
        "/home/user/ml-data-repo/training_data_manifest.tsv"
    )


def test_manifest_content_matches_required_final_artifact_exactly():
    assert MANIFEST.exists(), (
        "Cannot inspect manifest because it is missing at "
        "/home/user/ml-data-repo/training_data_manifest.tsv"
    )

    actual_text = read_text_exact(MANIFEST)
    expected_text = "\n".join(EXPECTED_MANIFEST_LINES) + "\n"

    assert actual_text == expected_text, (
        "Manifest content is not exactly the required final content. "
        "It must contain only the header and the five eligible Git-tracked JSONL shards, "
        "sorted by git_path, with tab separators and correct non-empty record counts.\n"
        f"Expected:\n{expected_text!r}\n"
        f"Got:\n{actual_text!r}"
    )


def test_manifest_header_line_count_and_column_format_are_correct():
    lines = read_lines_exact(MANIFEST)

    assert lines, "Manifest is empty; it must start with header 'git_path\\trecord_count\\tsplit'"
    assert lines[0] == "git_path\trecord_count\tsplit", (
        f"Manifest header is wrong. Expected exactly "
        f"'git_path\\trecord_count\\tsplit', got {lines[0]!r}"
    )
    assert len(lines) == 6, (
        f"Manifest must have exactly 6 lines: one header plus five eligible shard rows. "
        f"Got {len(lines)} lines."
    )

    for line_number, line in enumerate(lines, start=1):
        columns = line.split("\t")
        assert len(columns) == 3, (
            f"Manifest line {line_number} must have exactly three tab-separated columns, "
            f"but got {len(columns)} columns: {line!r}"
        )


def test_manifest_rows_are_exactly_git_tracked_eligible_jsonl_paths():
    result = run_git("ls-files")
    assert result.returncode == 0, (
        "Could not query Git tracked files with 'git ls-files' in "
        f"/home/user/ml-data-repo: {result.stderr}"
    )
    tracked = set(result.stdout.splitlines())

    expected_from_git = sorted(
        path for path in tracked
        if path.startswith("data/raw/") and path.endswith(".jsonl")
    )
    assert expected_from_git == EXPECTED_ELIGIBLE_PATHS, (
        "The current Git-tracked eligible shard set does not match the expected task truth. "
        f"Expected {EXPECTED_ELIGIBLE_PATHS!r}, got {expected_from_git!r}"
    )

    rows = parse_manifest_rows()
    manifest_paths = [row["git_path"] for row in rows]

    assert manifest_paths == EXPECTED_ELIGIBLE_PATHS, (
        "Manifest includes the wrong shard paths. It must include exactly the eligible "
        "Git-tracked JSONL files under data/raw/ and exclude untracked, ignored, temporary, "
        f"and out-of-scope files. Expected {EXPECTED_ELIGIBLE_PATHS!r}, got {manifest_paths!r}"
    )

    unexpected_forbidden = sorted(FORBIDDEN_PATHS.intersection(manifest_paths))
    assert not unexpected_forbidden, (
        "Manifest incorrectly includes files that must be excluded because they are untracked, "
        "ignored, temporary, or outside the eligible shard set: "
        + ", ".join(unexpected_forbidden)
    )

    untracked_or_unlisted = sorted(path for path in manifest_paths if path not in tracked)
    assert not untracked_or_unlisted, (
        "Manifest contains paths that are not tracked by Git in the current checkout: "
        + ", ".join(untracked_or_unlisted)
    )


def test_manifest_rows_are_sorted_lexicographically_by_git_path():
    rows = parse_manifest_rows()
    manifest_paths = [row["git_path"] for row in rows]

    assert manifest_paths == sorted(manifest_paths), (
        "Manifest rows are not sorted lexicographically by git_path. "
        f"Got order {manifest_paths!r}; expected {sorted(manifest_paths)!r}"
    )


def test_manifest_record_counts_and_split_names_are_semantically_correct():
    rows = parse_manifest_rows()

    for row in rows:
        git_path = row["git_path"]
        full_path = Path("/home/user/ml-data-repo") / git_path

        assert git_path in EXPECTED_COUNTS, (
            f"Unexpected manifest path {git_path!r}; only tracked eligible JSONL shards "
            "under data/raw/ may appear."
        )

        assert full_path.exists(), (
            f"Manifest references {git_path!r}, but the corresponding absolute path "
            f"{full_path} does not exist."
        )
        assert full_path.is_file(), (
            f"Manifest references {git_path!r}, but the corresponding absolute path "
            f"{full_path} is not a regular file."
        )

        assert row["record_count"].isdigit(), (
            f"record_count for {git_path!r} must be a decimal integer, "
            f"got {row['record_count']!r}"
        )
        actual_count_from_file = non_empty_line_count(full_path)
        expected_count = EXPECTED_COUNTS[git_path]

        assert int(row["record_count"]) == expected_count, (
            f"record_count for {git_path!r} is wrong. Expected {expected_count} "
            f"non-empty lines, got manifest value {row['record_count']!r}."
        )
        assert actual_count_from_file == expected_count, (
            f"The source shard {full_path} no longer has the expected non-empty line count. "
            f"Expected {expected_count}, got {actual_count_from_file}."
        )

        expected_split = EXPECTED_SPLITS[git_path]
        assert row["split"] == expected_split, (
            f"split for {git_path!r} is wrong. Expected immediate directory name "
            f"under data/raw/ to be {expected_split!r}, got {row['split']!r}."
        )


def test_verification_log_exists_at_required_absolute_path():
    assert VERIFY_LOG.exists(), (
        "Missing required verification log at absolute path "
        "/home/user/ml-data-repo/training_data_manifest.verify.log"
    )
    assert VERIFY_LOG.is_file(), (
        "Required verification log path exists but is not a regular file: "
        "/home/user/ml-data-repo/training_data_manifest.verify.log"
    )


def test_verification_log_content_matches_required_five_lines_exactly():
    assert VERIFY_LOG.exists(), (
        "Cannot inspect verification log because it is missing at "
        "/home/user/ml-data-repo/training_data_manifest.verify.log"
    )

    actual_text = read_text_exact(VERIFY_LOG)
    expected_text = "\n".join(EXPECTED_VERIFY_LOG_LINES) + "\n"

    assert actual_text == expected_text, (
        "Verification log content is not exactly correct. It must contain exactly the five "
        "required lines, in order, with both counts equal to the number of eligible tracked "
        "JSONL shard files and no extra commentary.\n"
        f"Expected:\n{expected_text!r}\n"
        f"Got:\n{actual_text!r}"
    )


def test_manifest_and_verification_log_counts_agree():
    rows = parse_manifest_rows()
    manifest_row_count = len(rows)

    log_lines = read_lines_exact(VERIFY_LOG)
    assert len(log_lines) == 5, (
        f"Verification log must contain exactly five lines, got {len(log_lines)} lines."
    )

    tracked_line = log_lines[1]
    manifest_line = log_lines[2]

    assert tracked_line == f"tracked_jsonl_files={len(EXPECTED_ELIGIBLE_PATHS)}", (
        "Verification log tracked_jsonl_files line is wrong. "
        f"Expected 'tracked_jsonl_files={len(EXPECTED_ELIGIBLE_PATHS)}', got {tracked_line!r}"
    )
    assert manifest_line == f"manifest_rows={manifest_row_count}", (
        "Verification log manifest_rows line does not match the actual number of manifest "
        f"data rows. Expected 'manifest_rows={manifest_row_count}', got {manifest_line!r}"
    )
    assert manifest_row_count == len(EXPECTED_ELIGIBLE_PATHS), (
        f"Manifest should have {len(EXPECTED_ELIGIBLE_PATHS)} data rows, got {manifest_row_count}."
    )