# test_final_state.py
from pathlib import Path
import re

ROOT = Path("/home/user/artifact_triage")
POLICY = Path("/home/user/artifact_triage/policy")
CANDIDATES = Path("/home/user/artifact_triage/candidates")
PROMOTION_DECISION = Path("/home/user/artifact_triage/promotion_decision.txt")
TRIAGE_PROGRESS = Path("/home/user/artifact_triage/triage_progress.log")

EXPECTED_PROMOTION_DECISION = (
    "selected_candidate=build-2024.11.08-a1\n"
    "artifact_id=rel-2024.11-a1\n"
    "commit=8f14e45fceea167a5a36dedd4bea2543\n"
    "component_count=4\n"
)

EXPECTED_TRIAGE_PROGRESS = (
    "candidate=build-2024.11.08-a1|status=SELECTED|reason=all policy checks passed\n"
    "candidate=build-2024.11.08-b2|status=REJECTED|reason=component mismatch\n"
    "candidate=build-2024.11.08-c3|status=REJECTED|reason=commit not allowed\n"
    "candidate=build-2024.11.08-d4|status=REJECTED|reason=missing checksum\n"
    "candidate=build-2024.11.08-e5|status=REJECTED|reason=wrong channel\n"
    "candidate=build-2024.11.08-f6|status=REJECTED|reason=unsigned manifest\n"
    "verification=promotion_decision_matches_selected_candidate\n"
)

EXPECTED_CANDIDATES = [
    "build-2024.11.08-a1",
    "build-2024.11.08-b2",
    "build-2024.11.08-c3",
    "build-2024.11.08-d4",
    "build-2024.11.08-e5",
    "build-2024.11.08-f6",
]

EXPECTED_COMPONENTS = {
    ("api-gateway", "2.8.1"),
    ("auth-service", "5.4.0"),
    ("billing-worker", "1.19.7"),
    ("web-console", "3.12.2"),
}

ALLOWED_COMMIT = "8f14e45fceea167a5a36dedd4bea2543"


def _read_text(path: Path) -> str:
    assert path.exists(), f"Required output file is missing: {path}"
    assert path.is_file(), f"Required output path is not a regular file: {path}"
    return path.read_text(encoding="utf-8")


def _parse_key_value_lines(text: str, path: Path) -> dict:
    result = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        assert "=" in line, f"{path} line {line_number} is not a key=value line: {line!r}"
        key, value = line.split("=", 1)
        assert key, f"{path} line {line_number} has an empty key"
        assert key not in result, f"{path} repeats key {key!r}"
        result[key] = value
    return result


def _parse_manifest(candidate_name: str) -> tuple[dict, set[tuple[str, str]]]:
    manifest_path = CANDIDATES / candidate_name / "manifest.txt"
    assert manifest_path.exists(), f"Selected candidate manifest is missing: {manifest_path}"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()

    fields = {}
    components = set()
    for line in lines:
        if line.startswith("component="):
            component_value = line[len("component="):]
            assert "\t" in component_value, (
                f"Manifest component line in {manifest_path} is not tab-delimited: {line!r}"
            )
            name, version = component_value.split("\t", 1)
            components.add((name, version))
        else:
            assert "=" in line, f"Manifest line in {manifest_path} is not key=value: {line!r}"
            key, value = line.split("=", 1)
            fields[key] = value
    return fields, components


def _checksum_filenames(candidate_name: str) -> set[str]:
    checksum_path = CANDIDATES / candidate_name / "checksums.sha256"
    assert checksum_path.exists(), f"Checksum file is missing: {checksum_path}"
    filenames = set()
    for line_number, line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = line.split()
        assert len(parts) >= 2, f"Malformed checksum line {line_number} in {checksum_path}: {line!r}"
        filenames.add(parts[-1])
    return filenames


def test_required_output_files_exist_and_are_exact():
    promotion_text = _read_text(PROMOTION_DECISION)
    triage_text = _read_text(TRIAGE_PROGRESS)

    assert promotion_text == EXPECTED_PROMOTION_DECISION, (
        f"{PROMOTION_DECISION} does not exactly match the required final contents.\n"
        f"Expected:\n{EXPECTED_PROMOTION_DECISION!r}\n"
        f"Actual:\n{promotion_text!r}"
    )
    assert triage_text == EXPECTED_TRIAGE_PROGRESS, (
        f"{TRIAGE_PROGRESS} does not exactly match the required final contents, including "
        f"candidate order, first-failure rejection reasons, and final verification line.\n"
        f"Expected:\n{EXPECTED_TRIAGE_PROGRESS!r}\n"
        f"Actual:\n{triage_text!r}"
    )


def test_promotion_decision_has_exact_four_lines_no_extra_content():
    text = _read_text(PROMOTION_DECISION)
    lines = text.splitlines()

    assert text.endswith("\n"), f"{PROMOTION_DECISION} must end after the fourth line with a newline"
    assert len(lines) == 4, (
        f"{PROMOTION_DECISION} must contain exactly four lines and no extra content; "
        f"found {len(lines)} lines: {lines!r}"
    )
    assert all(line.strip() == line and line for line in lines), (
        f"{PROMOTION_DECISION} must not contain blank lines or leading/trailing spaces: {lines!r}"
    )

    expected_keys = ["selected_candidate", "artifact_id", "commit", "component_count"]
    actual_keys = [line.split("=", 1)[0] if "=" in line else line for line in lines]
    assert actual_keys == expected_keys, (
        f"{PROMOTION_DECISION} keys must be exactly {expected_keys} in order; found {actual_keys}"
    )


def test_triage_progress_has_exact_candidate_lines_sorted_and_verification_line():
    text = _read_text(TRIAGE_PROGRESS)
    lines = text.splitlines()

    assert text.endswith("\n"), f"{TRIAGE_PROGRESS} must end after the verification line with a newline"
    assert len(lines) == 7, (
        f"{TRIAGE_PROGRESS} must contain exactly six candidate lines plus one verification line; "
        f"found {len(lines)} lines: {lines!r}"
    )
    assert all(line.strip() == line and line for line in lines), (
        f"{TRIAGE_PROGRESS} must not contain blank lines or leading/trailing spaces: {lines!r}"
    )
    assert lines[-1] == "verification=promotion_decision_matches_selected_candidate", (
        f"The final line of {TRIAGE_PROGRESS} is wrong: {lines[-1]!r}"
    )

    candidate_pattern = re.compile(
        r"^candidate=([^|]+)\|status=(SELECTED|REJECTED)\|reason=(.+)$"
    )
    parsed_names = []
    selected_names = []

    for index, line in enumerate(lines[:-1], start=1):
        match = candidate_pattern.fullmatch(line)
        assert match, (
            f"{TRIAGE_PROGRESS} line {index} does not use the exact required "
            f"pipe-delimited candidate format: {line!r}"
        )
        name, status, reason = match.groups()
        parsed_names.append(name)
        if status == "SELECTED":
            selected_names.append(name)
            assert reason == "all policy checks passed", (
                f"Selected candidate {name} must use reason='all policy checks passed', "
                f"but used {reason!r}"
            )

    assert parsed_names == sorted(parsed_names), (
        f"Candidate lines in {TRIAGE_PROGRESS} must be sorted lexicographically by candidate name; "
        f"found order {parsed_names}"
    )
    assert parsed_names == EXPECTED_CANDIDATES, (
        f"{TRIAGE_PROGRESS} must contain exactly the expected candidate directories and no extras; "
        f"expected {EXPECTED_CANDIDATES}, found {parsed_names}"
    )
    assert selected_names == ["build-2024.11.08-a1"], (
        f"Exactly build-2024.11.08-a1 must be selected; selected candidates found: {selected_names}"
    )


def test_selected_candidate_decision_matches_manifest_policy_components_and_checksums():
    decision = _parse_key_value_lines(_read_text(PROMOTION_DECISION), PROMOTION_DECISION)

    selected = decision.get("selected_candidate")
    assert selected == "build-2024.11.08-a1", (
        f"Wrong selected candidate in {PROMOTION_DECISION}: expected build-2024.11.08-a1, "
        f"found {selected!r}"
    )

    selected_dir = CANDIDATES / selected
    assert selected_dir.exists(), f"Selected candidate directory does not exist: {selected_dir}"
    assert selected_dir.is_dir(), f"Selected candidate path is not a directory: {selected_dir}"

    fields, components = _parse_manifest(selected)

    assert decision.get("artifact_id") == fields.get("artifact_id") == "rel-2024.11-a1", (
        f"artifact_id in {PROMOTION_DECISION} must match selected manifest artifact_id "
        f"rel-2024.11-a1; decision={decision.get('artifact_id')!r}, "
        f"manifest={fields.get('artifact_id')!r}"
    )
    assert decision.get("commit") == fields.get("commit") == ALLOWED_COMMIT, (
        f"commit in {PROMOTION_DECISION} must match selected manifest and allowed policy commit "
        f"{ALLOWED_COMMIT}; decision={decision.get('commit')!r}, manifest={fields.get('commit')!r}"
    )
    assert decision.get("component_count") == "4", (
        f"component_count in {PROMOTION_DECISION} must be 4; found {decision.get('component_count')!r}"
    )

    assert fields.get("channel") == "stable", f"Selected manifest still has wrong channel: {fields.get('channel')!r}"
    assert fields.get("signed") == "yes", f"Selected manifest is not signed: {fields.get('signed')!r}"
    assert fields.get("qa_status") == "pass", f"Selected manifest QA status is not pass: {fields.get('qa_status')!r}"
    assert fields.get("schema_version") == "3", (
        f"Selected manifest schema_version is not 3: {fields.get('schema_version')!r}"
    )
    assert components == EXPECTED_COMPONENTS, (
        f"Selected manifest components do not match policy expected components; "
        f"expected {sorted(EXPECTED_COMPONENTS)}, found {sorted(components)}"
    )

    checksum_names = _checksum_filenames(selected)
    expected_artifact_names = {f"{name}-{version}.tar.gz" for name, version in components}
    missing = expected_artifact_names - checksum_names
    assert not missing, (
        f"Selected candidate {selected} is missing checksum entries for component artifacts: "
        f"{sorted(missing)}"
    )

    build_log_path = CANDIDATES / selected / "build.log"
    build_log = build_log_path.read_text(encoding="utf-8")
    lowered = build_log.lower()
    forbidden_terms = ["error", "fatal", "panic", "traceback"]
    present_forbidden = [term for term in forbidden_terms if term in lowered]
    assert not present_forbidden, (
        f"Selected candidate build log {build_log_path} contains forbidden failure terms: "
        f"{present_forbidden}"
    )
    assert any("packaging completed successfully" in line.lower() for line in build_log.splitlines()), (
        f"Selected candidate build log {build_log_path} lacks packaging completion success line"
    )


def test_policy_files_still_support_the_recorded_decision():
    release_policy_path = POLICY / "release_policy.txt"
    expected_components_path = POLICY / "expected_components.tsv"

    assert release_policy_path.exists(), f"Policy file is missing: {release_policy_path}"
    assert expected_components_path.exists(), f"Expected components file is missing: {expected_components_path}"

    policy = _parse_key_value_lines(release_policy_path.read_text(encoding="utf-8"), release_policy_path)
    assert policy.get("allowed_commit") == ALLOWED_COMMIT, (
        f"{release_policy_path} allowed_commit should be {ALLOWED_COMMIT}, "
        f"found {policy.get('allowed_commit')!r}"
    )
    assert policy.get("allowed_channel") == "stable", (
        f"{release_policy_path} allowed_channel should be stable, found {policy.get('allowed_channel')!r}"
    )
    assert policy.get("required_schema_version") == "3", (
        f"{release_policy_path} required_schema_version should be 3, "
        f"found {policy.get('required_schema_version')!r}"
    )
    assert policy.get("require_signed") == "yes", (
        f"{release_policy_path} require_signed should be yes, found {policy.get('require_signed')!r}"
    )
    assert policy.get("require_qa_status") == "pass", (
        f"{release_policy_path} require_qa_status should be pass, "
        f"found {policy.get('require_qa_status')!r}"
    )

    actual_components = set()
    for line_number, line in enumerate(expected_components_path.read_text(encoding="utf-8").splitlines(), start=1):
        assert "\t" in line, (
            f"{expected_components_path} line {line_number} must be tab-delimited name/version: {line!r}"
        )
        name, version = line.split("\t", 1)
        actual_components.add((name, version))

    assert actual_components == EXPECTED_COMPONENTS, (
        f"{expected_components_path} no longer contains the expected component set; "
        f"expected {sorted(EXPECTED_COMPONENTS)}, found {sorted(actual_components)}"
    )


def test_no_extra_top_level_deliverables_were_created():
    allowed_top_level_names = {
        "policy",
        "candidates",
        "promotion_decision.txt",
        "triage_progress.log",
    }
    assert ROOT.exists(), f"Required task root is missing: {ROOT}"
    actual_top_level_names = {path.name for path in ROOT.iterdir()}
    unexpected = sorted(actual_top_level_names - allowed_top_level_names)
    assert not unexpected, (
        f"Unexpected extra top-level deliverables exist under {ROOT}: {unexpected}. "
        f"The task requires only promotion_decision.txt and triage_progress.log."
    )