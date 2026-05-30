# test_final_state.py
from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest


WORKSPACE = Path("/home/user/mlops_workspace")
EXPERIMENTS = Path("/home/user/mlops_workspace/experiments")
OLD_CACHE = Path("/home/user/mlops_workspace/.du_cache")
NEW_INDEX = Path("/home/user/mlops_workspace/.artifact_index")
INVENTORY = Path("/home/user/mlops_workspace/.artifact_index/inventory.tsv")
SUMMARY = Path("/home/user/mlops_workspace/.artifact_index/summary.json")
REPORT = Path("/home/user/mlops_workspace/reports/artifact_disk_report.tsv")
VERIFICATION_LOG = Path("/home/user/mlops_workspace/reports/verification.log")

EXPECTED_EXPERIMENT_FILES = {
    "exp_alpha": {
        "checkpoints/model_epoch_001.ckpt": 16384,
        "checkpoints/model_epoch_002.ckpt": 24576,
        "checkpoints/export.onnx": 32768,
        "metrics.json": 512,
        "validation.metrics.json": 768,
        "history.csv": 1024,
        "logs/train.log": 4096,
        "logs/notes.txt": 2048,
        "images/confusion_matrix.png": 8192,
    },
    "exp_beta": {
        "weights/final.pt": 65536,
        "weights/final_ema.pth": 65536,
        "weights/best.ckpt": 49152,
        "metrics.json": 2048,
        "fold_0.csv": 4096,
        "fold_1.csv": 4096,
        "logs/run.log": 8192,
        "logs/debug.txt": 1024,
        "artifacts/sample_predictions.parquet": 32768,
        "artifacts/plot.png": 6144,
    },
    "exp_gamma": {
        "models/last.onnx": 40960,
        "models/teacher.pt": 57344,
        "metrics.json": 1024,
        "reports/eval.csv": 3072,
        "logs/train.log": 2048,
        "logs/eval.log": 2048,
        "tensorboard/events.out.tfevents.local": 12288,
        "README.txt": 1536,
    },
    "exp_delta": {
        "snapshot.ckpt": 32768,
        "metrics.json": 2048,
        "metrics.extra.csv": 2048,
        "logs/train.log": 1024,
        "logs/stdout.txt": 1024,
        "exports/model.onnx": 32768,
        "exports/model_quant.onnx": 28672,
        "cache/intermediate.bin": 16384,
    },
    "exp_epsilon": {
        "trial_a/checkpoint.pth": 20480,
        "trial_a/metrics.json": 1024,
        "trial_a/log.txt": 2048,
        "trial_b/checkpoint.pth": 22528,
        "trial_b/metrics.json": 1024,
        "trial_b/log.txt": 2048,
        "ensemble.onnx": 36864,
        "summary.csv": 4096,
    },
}

EXPECTED_INVENTORY_TEXT = (
    "experiment_id\ttotal_bytes\tfile_count\tcheckpoint_count\tmetric_count\t"
    "log_count\tlargest_file_bytes\tlargest_file_relpath\n"
    "exp_beta\t238592\t10\t3\t3\t2\t65536\tweights/final.pt\n"
    "exp_gamma\t120320\t8\t2\t2\t3\t57344\tmodels/teacher.pt\n"
    "exp_delta\t116736\t8\t3\t2\t2\t32768\texports/model.onnx\n"
    "exp_alpha\t90368\t9\t3\t3\t2\t32768\tcheckpoints/export.onnx\n"
    "exp_epsilon\t90112\t8\t3\t3\t2\t36864\tensemble.onnx\n"
)

EXPECTED_REPORT_TEXT = (
    "rank\texperiment_id\ttotal_bytes\tfile_count\tcheckpoint_count\tmetric_count\t"
    "log_count\tlargest_file_relpath\n"
    "1\texp_beta\t238592\t10\t3\t3\t2\tweights/final.pt\n"
    "2\texp_gamma\t120320\t8\t2\t2\t3\tmodels/teacher.pt\n"
    "3\texp_delta\t116736\t8\t3\t2\t2\texports/model.onnx\n"
    "4\texp_alpha\t90368\t9\t3\t3\t2\tcheckpoints/export.onnx\n"
    "5\texp_epsilon\t90112\t8\t3\t3\t2\tensemble.onnx\n"
)

EXPECTED_SUMMARY = {
    "schema_version": "artifact-index-v2",
    "source": "/home/user/mlops_workspace/experiments",
    "experiment_count": 5,
    "total_bytes": 656128,
    "total_files": 43,
    "largest_experiment": "exp_beta",
    "largest_experiment_bytes": 238592,
    "generated_by": "terminal-agent",
}

EXPECTED_VERIFICATION_LOG_TEXT = (
    "checked_old_path_retired=true\n"
    "checked_new_inventory_exists=true\n"
    "checked_summary_matches_inventory=true\n"
    "checked_report_matches_inventory=true\n"
    "new_inventory_path=/home/user/mlops_workspace/.artifact_index/inventory.tsv\n"
    "old_cache_path=/home/user/mlops_workspace/.du_cache\n"
)

EXPECTED_OLD_CACHE_FILENAMES = {"inventory.tsv", "summary.json", "README.txt"}


def read_text_normalized(path: Path) -> str:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Required path is not a regular file: {path}"
    assert not path.is_symlink(), f"Required file must not be a symlink: {path}"
    return path.read_text(encoding="utf-8").rstrip("\n") + "\n"


def parse_tsv(path: Path) -> list[list[str]]:
    text = read_text_normalized(path)
    return [line.split("\t") for line in text.rstrip("\n").split("\n")]


def test_workspace_and_experiment_source_still_exist() -> None:
    for path in (WORKSPACE, EXPERIMENTS):
        assert path.exists(), f"Missing required directory after task completion: {path}"
        assert path.is_dir(), f"Required path is not a directory after task completion: {path}"
        assert not path.is_symlink(), f"Required directory must not be a symlink: {path}"


def test_experiment_artifact_tree_was_not_modified() -> None:
    actual_experiment_dirs = {
        child.name
        for child in EXPERIMENTS.iterdir()
        if child.is_dir() and not child.is_symlink()
    }
    assert actual_experiment_dirs == set(EXPECTED_EXPERIMENT_FILES), (
        f"Experiment directories under {EXPERIMENTS} changed: expected "
        f"{sorted(EXPECTED_EXPERIMENT_FILES)}, got {sorted(actual_experiment_dirs)}"
    )

    for experiment_id, expected_files in EXPECTED_EXPERIMENT_FILES.items():
        experiment_dir = EXPERIMENTS / experiment_id
        actual_files = {
            str(path.relative_to(experiment_dir)): path.stat().st_size
            for path in experiment_dir.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        assert actual_files == expected_files, (
            f"Experiment files/sizes for {experiment_dir} changed or are incomplete: "
            f"expected {expected_files}, got {actual_files}"
        )

    symlinks = [path for path in EXPERIMENTS.rglob("*") if path.is_symlink()]
    assert not symlinks, (
        "Experiment tree should not contain symlinks after task completion, found: "
        + ", ".join(str(path) for path in symlinks)
    )


def test_new_artifact_index_directory_and_required_files_exist() -> None:
    assert NEW_INDEX.exists(), f"Missing new authoritative state directory: {NEW_INDEX}"
    assert NEW_INDEX.is_dir(), f"New authoritative state path is not a directory: {NEW_INDEX}"
    assert not NEW_INDEX.is_symlink(), f"New authoritative state directory must not be a symlink: {NEW_INDEX}"

    for path in (INVENTORY, SUMMARY):
        assert path.exists(), f"Missing required authoritative file: {path}"
        assert path.is_file(), f"Required authoritative path is not a regular file: {path}"
        assert not path.is_symlink(), f"Authoritative file must not be a symlink: {path}"


def test_inventory_tsv_matches_expected_authoritative_state_exactly() -> None:
    actual = read_text_normalized(INVENTORY)
    assert actual == EXPECTED_INVENTORY_TEXT, (
        f"Authoritative inventory at {INVENTORY} is incorrect. It must be generated "
        "from the live experiment tree with exact byte counts, sorted by total_bytes "
        "descending then experiment_id ascending."
    )


def test_inventory_tsv_format_is_strict_and_numeric_fields_are_decimal_integers() -> None:
    rows = parse_tsv(INVENTORY)
    expected_header = [
        "experiment_id",
        "total_bytes",
        "file_count",
        "checkpoint_count",
        "metric_count",
        "log_count",
        "largest_file_bytes",
        "largest_file_relpath",
    ]
    assert rows[0] == expected_header, f"Inventory header is wrong in {INVENTORY}: {rows[0]}"
    assert len(rows) == 6, f"Inventory should contain one header plus 5 experiment rows, got {len(rows)} rows"

    previous_total = None
    seen_ids = []
    for row in rows[1:]:
        assert len(row) == 8, f"Inventory row has wrong number of tab-separated columns: {row}"
        experiment_id = row[0]
        seen_ids.append(experiment_id)
        for value in row[1:7]:
            assert value.isdecimal(), f"Inventory numeric value is not a plain decimal integer: {value!r}"
        total = int(row[1])
        if previous_total is not None:
            assert previous_total >= total, (
                f"Inventory rows are not sorted by total_bytes descending: {previous_total} before {total}"
            )
        previous_total = total

    assert seen_ids == ["exp_beta", "exp_gamma", "exp_delta", "exp_alpha", "exp_epsilon"], (
        f"Inventory experiment order is incorrect: {seen_ids}"
    )


def test_summary_json_matches_expected_logical_state_exactly() -> None:
    try:
        data = json.loads(read_text_normalized(SUMMARY))
    except json.JSONDecodeError as exc:
        pytest.fail(f"Summary file is not valid JSON at {SUMMARY}: {exc}")

    assert set(data) == set(EXPECTED_SUMMARY), (
        f"Summary JSON must contain exactly keys {sorted(EXPECTED_SUMMARY)}, got {sorted(data)}"
    )
    assert data == EXPECTED_SUMMARY, (
        f"Summary JSON values are wrong at {SUMMARY}: expected {EXPECTED_SUMMARY}, got {data}"
    )


def test_summary_values_are_consistent_with_authoritative_inventory() -> None:
    rows = parse_tsv(INVENTORY)[1:]
    total_bytes = sum(int(row[1]) for row in rows)
    total_files = sum(int(row[2]) for row in rows)
    summary = json.loads(read_text_normalized(SUMMARY))

    assert summary["experiment_count"] == len(rows), (
        "summary.json experiment_count does not match inventory row count"
    )
    assert summary["total_bytes"] == total_bytes, (
        "summary.json total_bytes does not match sum of inventory total_bytes"
    )
    assert summary["total_files"] == total_files, (
        "summary.json total_files does not match sum of inventory file_count"
    )
    assert summary["largest_experiment"] == rows[0][0], (
        "summary.json largest_experiment does not match first inventory row"
    )
    assert summary["largest_experiment_bytes"] == int(rows[0][1]), (
        "summary.json largest_experiment_bytes does not match first inventory row total_bytes"
    )


def test_old_cache_path_is_retired_and_not_active() -> None:
    assert not OLD_CACHE.is_dir(), (
        f"Old cache path is still an active directory: {OLD_CACHE}. It must be retired "
        "so tools cannot read it as the source of truth."
    )
    assert not (OLD_CACHE / "inventory.tsv").exists(), (
        f"Old active inventory still exists at {OLD_CACHE / 'inventory.tsv'}"
    )


def test_old_cache_contents_were_preserved_readably_somewhere_under_workspace() -> None:
    found_in_directory = False
    for child in WORKSPACE.iterdir():
        if child == OLD_CACHE:
            continue
        if child.is_dir() and not child.is_symlink():
            child_files = {path.name for path in child.iterdir() if path.is_file()}
            if EXPECTED_OLD_CACHE_FILENAMES.issubset(child_files) and (
                "du_cache" in child.name or "retired" in child.name or "archive" in child.name
            ):
                found_in_directory = True
                break

    found_in_tar = False
    for path in WORKSPACE.rglob("*"):
        if path.is_file() and path.suffix in {".tar", ".gz", ".tgz"}:
            try:
                if tarfile.is_tarfile(path):
                    with tarfile.open(path) as archive:
                        member_basenames = {Path(member.name).name for member in archive.getmembers()}
                    if EXPECTED_OLD_CACHE_FILENAMES.issubset(member_basenames):
                        found_in_tar = True
                        break
            except (tarfile.TarError, OSError):
                continue

    assert found_in_directory or found_in_tar, (
        "The old .du_cache contents were not found preserved in a readable retired "
        "directory or tar archive under /home/user/mlops_workspace. Expected preserved "
        "filenames: inventory.tsv, summary.json, README.txt."
    )


def test_final_report_matches_expected_inventory_derived_text_exactly() -> None:
    actual = read_text_normalized(REPORT)
    assert actual == EXPECTED_REPORT_TEXT, (
        f"Final report at {REPORT} is incorrect. It must be derived from the new "
        f"authoritative inventory at {INVENTORY}, in the same sorted order, without "
        "largest_file_bytes."
    )


def test_report_is_consistent_with_authoritative_inventory_not_old_cache() -> None:
    inventory_rows = parse_tsv(INVENTORY)[1:]
    report_rows = parse_tsv(REPORT)[1:]

    assert len(report_rows) == len(inventory_rows), (
        "Report row count does not match authoritative inventory row count"
    )

    for index, (inventory_row, report_row) in enumerate(zip(inventory_rows, report_rows), start=1):
        expected_report_row = [
            str(index),
            inventory_row[0],
            inventory_row[1],
            inventory_row[2],
            inventory_row[3],
            inventory_row[4],
            inventory_row[5],
            inventory_row[7],
        ]
        assert report_row == expected_report_row, (
            f"Report row {index} does not match authoritative inventory row: "
            f"expected {expected_report_row}, got {report_row}"
        )


def test_verification_log_matches_expected_final_checks_exactly() -> None:
    actual = read_text_normalized(VERIFICATION_LOG)
    assert actual == EXPECTED_VERIFICATION_LOG_TEXT, (
        f"Verification log at {VERIFICATION_LOG} is incorrect. It must contain exactly "
        "the six required lines with all four checked_* booleans set to lowercase true."
    )


def test_verification_log_claims_are_true_in_current_filesystem_state() -> None:
    lines = read_text_normalized(VERIFICATION_LOG).rstrip("\n").split("\n")
    values = dict(line.split("=", 1) for line in lines)

    assert values["checked_old_path_retired"] == "true", "verification.log did not mark old path retired"
    assert values["checked_new_inventory_exists"] == "true", "verification.log did not mark new inventory present"
    assert values["checked_summary_matches_inventory"] == "true", (
        "verification.log did not mark summary/inventory consistency checked"
    )
    assert values["checked_report_matches_inventory"] == "true", (
        "verification.log did not mark report/inventory consistency checked"
    )
    assert values["new_inventory_path"] == str(INVENTORY), "verification.log has wrong new inventory path"
    assert values["old_cache_path"] == str(OLD_CACHE), "verification.log has wrong old cache path"

    assert not OLD_CACHE.is_dir(), (
        "verification.log claims old path is retired, but .du_cache is still a directory"
    )
    assert INVENTORY.exists() and INVENTORY.is_file(), (
        "verification.log claims new inventory exists, but it is missing or not a regular file"
    )
    assert read_text_normalized(INVENTORY) == EXPECTED_INVENTORY_TEXT, (
        "verification.log claims checks passed, but authoritative inventory content is wrong"
    )
    assert json.loads(read_text_normalized(SUMMARY)) == EXPECTED_SUMMARY, (
        "verification.log claims summary matches inventory, but summary content is wrong"
    )
    assert read_text_normalized(REPORT) == EXPECTED_REPORT_TEXT, (
        "verification.log claims report matches inventory, but report content is wrong"
    )