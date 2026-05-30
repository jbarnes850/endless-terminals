# test_final_state.py
from pathlib import Path
import filecmp

import pytest


ROOT = Path("/home/user/mlops_runs")
CANDIDATES = Path("/home/user/mlops_runs/candidates")
REGISTRY_MODEL_DIR = Path("/home/user/mlops_runs/registry/churn_model")

SELECTED_RUN = "run_2024_06_18_gamma"
ELIMINATED_RUNS = [
    "run_2024_06_17_alpha",
    "run_2024_06_17_beta",
    "run_2024_06_18_delta",
]

EXPECTED_REGISTRY_FILES = sorted(
    [
        "model.pkl",
        "metrics.json",
        "schema.json",
        "promotion_audit.log",
    ]
)

EXPECTED_ARTIFACT_CONTENTS = {
    "model.pkl": "MODEL_BINARY_PLACEHOLDER_GAMMA_DEPLOYABLE\n",
    "metrics.json": '{"run_id":"run_2024_06_18_gamma","accuracy":0.927,"auc":0.916,"f1":0.821}\n',
    "schema.json": '{"features":["age","tenure_months","monthly_charges","support_tickets"],"target":"churned","version":"1.1"}\n',
}

EXPECTED_AUDIT_LOG = (
    "selected_run=run_2024_06_18_gamma\n"
    "eliminated=run_2024_06_17_alpha,run_2024_06_17_beta,run_2024_06_18_delta\n"
    "copied_files=model.pkl,metrics.json,schema.json\n"
    "verification=complete\n"
)


def assert_directory(path: Path) -> None:
    assert path.exists(), f"Required directory is missing: {path}"
    assert path.is_dir(), f"Required path exists but is not a directory: {path}"


def assert_regular_file(path: Path) -> None:
    assert path.exists(), f"Required file is missing: {path}"
    assert path.is_file(), f"Required path exists but is not a regular file: {path}"


def test_registry_model_directory_exists():
    assert_directory(REGISTRY_MODEL_DIR)


def test_registry_contains_exactly_expected_files_and_no_directories():
    assert_directory(REGISTRY_MODEL_DIR)

    entries = sorted(child.name for child in REGISTRY_MODEL_DIR.iterdir())
    assert entries == EXPECTED_REGISTRY_FILES, (
        f"Registry directory has the wrong contents: {REGISTRY_MODEL_DIR}\n"
        f"Expected exactly these entries and no others: {EXPECTED_REGISTRY_FILES}\n"
        f"Found: {entries}"
    )

    non_files = sorted(
        child.name for child in REGISTRY_MODEL_DIR.iterdir() if not child.is_file()
    )
    assert non_files == [], (
        f"Registry directory must contain only regular files, but found non-file entries "
        f"in {REGISTRY_MODEL_DIR}: {non_files}"
    )


@pytest.mark.parametrize("filename", ["model.pkl", "metrics.json", "schema.json"])
def test_promoted_artifacts_exist_as_regular_files(filename):
    artifact_path = REGISTRY_MODEL_DIR / filename
    assert_regular_file(artifact_path)


@pytest.mark.parametrize("filename, expected_content", EXPECTED_ARTIFACT_CONTENTS.items())
def test_promoted_artifact_contents_are_exact_gamma_contents(filename, expected_content):
    registry_artifact = REGISTRY_MODEL_DIR / filename
    selected_candidate_artifact = CANDIDATES / SELECTED_RUN / filename

    assert_regular_file(registry_artifact)
    assert_regular_file(selected_candidate_artifact)

    actual_content = registry_artifact.read_text(encoding="utf-8")
    assert actual_content == expected_content, (
        f"Promoted artifact has incorrect contents: {registry_artifact}\n"
        f"It should have been copied from selected run {SELECTED_RUN}.\n"
        f"Expected content: {expected_content!r}\n"
        f"Found content: {actual_content!r}"
    )

    assert filecmp.cmp(
        str(registry_artifact),
        str(selected_candidate_artifact),
        shallow=False,
    ), (
        f"Promoted artifact is not byte-for-byte identical to the selected candidate file.\n"
        f"Registry file: {registry_artifact}\n"
        f"Expected source file: {selected_candidate_artifact}"
    )


def test_no_status_file_was_copied_to_registry():
    forbidden_path = REGISTRY_MODEL_DIR / "status.txt"
    assert not forbidden_path.exists(), (
        f"status.txt must not be copied into the registry, but it exists at: {forbidden_path}"
    )


def test_promoted_artifacts_do_not_match_known_wrong_candidate_contents():
    wrong_contents_by_file = {
        "model.pkl": {
            "alpha failed model": "MODEL_BINARY_PLACEHOLDER_ALPHA_FAILED\n",
            "beta missing schema model": "MODEL_BINARY_PLACEHOLDER_BETA_MISSING_SCHEMA\n",
        },
        "metrics.json": {
            "alpha failed metrics": '{"run_id":"run_2024_06_17_alpha","accuracy":0.901,"auc":0.884,"f1":0.798}\n',
            "beta missing schema metrics": '{"run_id":"run_2024_06_17_beta","accuracy":0.919,"auc":0.907,"f1":0.812}\n',
        },
        "schema.json": {
            "alpha failed schema": '{"features":["age","tenure_months","monthly_charges"],"target":"churned","version":"1.0-alpha"}\n',
            "delta running schema": '{"features":["age","tenure_months","monthly_charges","support_tickets"],"target":"churned","version":"1.1-delta"}\n',
        },
    }

    for filename, wrong_contents in wrong_contents_by_file.items():
        registry_artifact = REGISTRY_MODEL_DIR / filename
        assert_regular_file(registry_artifact)
        actual_content = registry_artifact.read_text(encoding="utf-8")

        for wrong_source, wrong_content in wrong_contents.items():
            assert actual_content != wrong_content, (
                f"{registry_artifact} appears to have been copied from the wrong candidate "
                f"({wrong_source}) instead of {SELECTED_RUN}."
            )


def test_promotion_audit_log_exists_and_is_exact():
    audit_path = REGISTRY_MODEL_DIR / "promotion_audit.log"
    assert_regular_file(audit_path)

    actual_log = audit_path.read_text(encoding="utf-8")
    assert actual_log == EXPECTED_AUDIT_LOG, (
        f"promotion_audit.log has incorrect contents: {audit_path}\n"
        "It must contain exactly four lines in the required order, with the selected run, "
        "alphabetically sorted eliminated run basenames, copied files, and verification line.\n"
        f"Expected: {EXPECTED_AUDIT_LOG!r}\n"
        f"Found: {actual_log!r}"
    )


def test_promotion_audit_log_has_exactly_four_lines_with_final_newline():
    audit_path = REGISTRY_MODEL_DIR / "promotion_audit.log"
    assert_regular_file(audit_path)

    actual_log = audit_path.read_text(encoding="utf-8")
    lines = actual_log.splitlines()

    assert actual_log.endswith("\n"), (
        f"promotion_audit.log must end with a final newline: {audit_path}"
    )
    assert lines == [
        "selected_run=run_2024_06_18_gamma",
        "eliminated=run_2024_06_17_alpha,run_2024_06_17_beta,run_2024_06_18_delta",
        "copied_files=model.pkl,metrics.json,schema.json",
        "verification=complete",
    ], (
        f"promotion_audit.log must contain exactly the required four non-blank lines.\n"
        f"Found lines: {lines}"
    )


def test_candidate_directories_still_show_gamma_is_only_valid_completed_run():
    assert_directory(CANDIDATES)

    expected_candidate_dirs = sorted([SELECTED_RUN] + ELIMINATED_RUNS)
    actual_candidate_dirs = sorted(
        child.name for child in CANDIDATES.iterdir() if child.is_dir()
    )
    assert actual_candidate_dirs == expected_candidate_dirs, (
        f"Candidate directory set should remain intact under {CANDIDATES}.\n"
        f"Expected candidate directories: {expected_candidate_dirs}\n"
        f"Found: {actual_candidate_dirs}"
    )

    valid_runs = []
    for run_name in expected_candidate_dirs:
        run_dir = CANDIDATES / run_name
        status_path = run_dir / "status.txt"
        assert_regular_file(status_path)

        status = status_path.read_text(encoding="utf-8").strip()
        has_required_artifacts = all(
            (run_dir / filename).is_file()
            for filename in ["metrics.json", "model.pkl", "schema.json"]
        )

        if status == "COMPLETED" and has_required_artifacts:
            valid_runs.append(run_name)

    assert valid_runs == [SELECTED_RUN], (
        "The final registry promotion should be based on the only valid completed run: "
        f"{SELECTED_RUN}.\n"
        "A valid run must have status COMPLETED and files metrics.json, model.pkl, and schema.json.\n"
        f"Found valid runs: {valid_runs}"
    )


def test_eliminated_runs_named_in_audit_log_are_all_non_selected_candidates_sorted():
    audit_path = REGISTRY_MODEL_DIR / "promotion_audit.log"
    assert_regular_file(audit_path)

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4, (
        f"promotion_audit.log must have exactly four lines before validating eliminated runs: {audit_path}"
    )

    eliminated_line = lines[1]
    expected_line = "eliminated=" + ",".join(sorted(ELIMINATED_RUNS))
    assert eliminated_line == expected_line, (
        "The eliminated line must list every non-selected candidate basename, sorted "
        "alphabetically, comma-separated, with no spaces.\n"
        f"Expected: {expected_line!r}\n"
        f"Found: {eliminated_line!r}"
    )

    assert " " not in eliminated_line, (
        f"The eliminated line must not contain spaces: {eliminated_line!r}"
    )
    assert SELECTED_RUN not in eliminated_line.split("=", 1)[1].split(","), (
        f"The selected run must not be listed as eliminated in {audit_path}"
    )