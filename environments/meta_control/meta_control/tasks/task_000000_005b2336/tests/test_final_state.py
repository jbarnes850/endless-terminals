# test_final_state.py
import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path("/home/user/policy-pipeline")
CANONICAL_DIR = Path("/home/user/policy-pipeline/config/policy")
CANONICAL_PATH = Path("/home/user/policy-pipeline/config/policy/exceptions.json")
LEGACY_PATH = Path("/home/user/policy-pipeline/data/legacy_exceptions.json")
SCRIPT_PATH = Path("/home/user/policy-pipeline/bin/render_policy_report.py")
REPORT_PATH = Path("/home/user/policy-pipeline/output/policy_report.json")
LOG_PATH = Path("/home/user/policy-pipeline/output/migration_verification.log")

EXPECTED_SCHEMA_VERSION = "2024-ops-policy-v2"
EXPECTED_EXCEPTIONS = [
    {
        "control_id": "CIS-1.1.1",
        "service": "artifact-registry",
        "environment": "dev",
        "expires": "2026-01-15",
        "reason": "Temporary exception while container signing rollout completes",
    },
    {
        "control_id": "CIS-2.3.4",
        "service": "build-runner",
        "environment": "ci",
        "expires": "2025-12-31",
        "reason": "Pinned legacy runner requires scoped network egress during migration",
    },
    {
        "control_id": "ORG-SEC-7",
        "service": "secrets-sync",
        "environment": "staging",
        "expires": "2025-10-01",
        "reason": "Compensating monitoring enabled until vault namespace split is complete",
    },
]
EXPECTED_EXCEPTION_KEYS = {
    "control_id",
    "service",
    "environment",
    "expires",
    "reason",
}
EXPECTED_REPORT = {
    "pipeline": "policy-exception-render",
    "source": str(CANONICAL_PATH),
    "exception_count": 3,
    "exceptions_by_environment": {"ci": 1, "dev": 1, "staging": 1},
    "controls": ["CIS-1.1.1", "CIS-2.3.4", "ORG-SEC-7"],
    "expired_count": 0,
}
EXPECTED_LOG_TEXT = "\n".join(
    [
        "old_source_retired=true",
        "new_source_exists=true",
        "pipeline_source=/home/user/policy-pipeline/config/policy/exceptions.json",
        "report_path=/home/user/policy-pipeline/output/policy_report.json",
        "verified_from_new_source=true",
    ]
)


def _load_json_file(path: Path):
    assert path.exists(), f"Required JSON file is missing: {path}"
    assert path.is_file(), f"Required JSON path exists but is not a regular file: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"File is not valid JSON: {path}: {exc}")


def _canonicalize_exception(item):
    assert isinstance(item, dict), f"Exception record is not a JSON object: {item!r}"
    assert set(item.keys()) == EXPECTED_EXCEPTION_KEYS, (
        "Exception record keys were changed. Expected exactly "
        f"{sorted(EXPECTED_EXCEPTION_KEYS)}, got {sorted(item.keys())}: {item!r}"
    )
    return tuple((key, item[key]) for key in sorted(EXPECTED_EXCEPTION_KEYS))


def _assert_exceptions_equal_expected(actual):
    assert isinstance(actual, list), (
        f"'exceptions' must be a JSON array/list, got {type(actual).__name__}"
    )
    assert len(actual) == len(EXPECTED_EXCEPTIONS), (
        f"Expected {len(EXPECTED_EXCEPTIONS)} migrated exceptions, got {len(actual)}"
    )
    actual_set = {_canonicalize_exception(item) for item in actual}
    expected_set = {_canonicalize_exception(item) for item in EXPECTED_EXCEPTIONS}
    assert actual_set == expected_set, (
        "Migrated exceptions do not exactly match the original legacy records. "
        "All field names and values must be preserved with no missing or extra records."
    )


def _run_pipeline():
    assert SCRIPT_PATH.exists(), f"Pipeline script is missing: {SCRIPT_PATH}"
    assert SCRIPT_PATH.is_file(), f"Pipeline script path is not a regular file: {SCRIPT_PATH}"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    assert result.returncode == 0, (
        "Pipeline failed when run from repository root. "
        f"Command: {sys.executable} {SCRIPT_PATH}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result


def _looks_like_active_exception_json(value):
    records = None
    if isinstance(value, list):
        records = value
    elif isinstance(value, dict) and isinstance(value.get("exceptions"), list):
        records = value["exceptions"]

    if records is None:
        return False

    return any(
        isinstance(item, dict)
        and {"control_id", "service", "environment", "expires", "reason"}.issubset(item.keys())
        for item in records
    )


def test_canonical_policy_directory_and_json_file_exist_with_required_wrapper_schema():
    assert CANONICAL_DIR.exists(), f"Canonical policy directory is missing: {CANONICAL_DIR}"
    assert CANONICAL_DIR.is_dir(), (
        f"Canonical policy path exists but is not a directory: {CANONICAL_DIR}"
    )
    assert CANONICAL_PATH.exists(), f"Canonical exceptions file is missing: {CANONICAL_PATH}"
    assert CANONICAL_PATH.is_file(), (
        f"Canonical exceptions path exists but is not a regular file: {CANONICAL_PATH}"
    )

    data = _load_json_file(CANONICAL_PATH)
    assert isinstance(data, dict), (
        f"Canonical exceptions JSON must be a top-level object: {CANONICAL_PATH}"
    )
    assert set(data.keys()) == {"schema_version", "exceptions"}, (
        "Canonical exceptions JSON must have exactly the top-level keys "
        "'schema_version' and 'exceptions'; got "
        f"{sorted(data.keys())}"
    )
    assert data["schema_version"] == EXPECTED_SCHEMA_VERSION, (
        f"Canonical schema_version must be {EXPECTED_SCHEMA_VERSION!r}, "
        f"got {data['schema_version']!r}"
    )
    _assert_exceptions_equal_expected(data["exceptions"])


def test_render_policy_report_script_references_canonical_source_and_not_legacy_source():
    assert SCRIPT_PATH.exists(), f"Pipeline script is missing: {SCRIPT_PATH}"
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "config" in source and "policy" in source and "exceptions.json" in source, (
        "Pipeline script should reference the canonical policy file "
        f"{CANONICAL_PATH}, but the expected path components were not found in {SCRIPT_PATH}"
    )
    assert "legacy_exceptions.json" not in source, (
        f"Pipeline script must not reference the retired legacy filename {LEGACY_PATH}"
    )
    assert "/home/user/policy-pipeline/data/legacy_exceptions.json" not in source, (
        f"Pipeline script must not reference the retired legacy path {LEGACY_PATH}"
    )

    try:
        tree = ast.parse(source, filename=str(SCRIPT_PATH))
    except SyntaxError as exc:
        pytest.fail(f"Pipeline script is not valid Python: {SCRIPT_PATH}: {exc}")

    string_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    forbidden_literals = [
        literal
        for literal in string_literals
        if "legacy_exceptions.json" in literal
        or "/home/user/policy-pipeline/data/legacy_exceptions.json" in literal
    ]
    assert not forbidden_literals, (
        "Pipeline script still contains string literal(s) referencing the legacy source: "
        f"{forbidden_literals!r}"
    )


def test_pipeline_runs_without_active_legacy_source_and_generates_expected_report(tmp_path):
    backup_path = tmp_path / "legacy_exceptions.json.backup"
    legacy_existed = LEGACY_PATH.exists()

    if legacy_existed:
        assert LEGACY_PATH.is_file(), (
            f"Legacy path exists but is not a regular file, cannot validate retirement: {LEGACY_PATH}"
        )
        shutil.copy2(str(LEGACY_PATH), str(backup_path))
        LEGACY_PATH.unlink()

    try:
        _run_pipeline()
        report = _load_json_file(REPORT_PATH)
    finally:
        if legacy_existed and not LEGACY_PATH.exists():
            shutil.copy2(str(backup_path), str(LEGACY_PATH))

    assert report == EXPECTED_REPORT, (
        "Generated policy report does not match expected semantics from the new canonical "
        f"source {CANONICAL_PATH}. Actual report: {report!r}"
    )


def test_policy_report_exists_and_proves_it_used_the_new_canonical_source():
    assert REPORT_PATH.exists(), f"Policy report was not written: {REPORT_PATH}"
    assert REPORT_PATH.is_file(), f"Policy report path is not a regular file: {REPORT_PATH}"

    report = _load_json_file(REPORT_PATH)
    for key, expected_value in EXPECTED_REPORT.items():
        assert report.get(key) == expected_value, (
            f"Policy report field {key!r} is wrong. Expected {expected_value!r}, "
            f"got {report.get(key)!r}. Report must be generated from {CANONICAL_PATH}."
        )

    assert report.get("source") != str(LEGACY_PATH), (
        f"Policy report still says it used the retired legacy source: {LEGACY_PATH}"
    )


def test_legacy_source_is_retired_or_replaced_by_clear_non_json_notice():
    if not LEGACY_PATH.exists():
        return

    assert LEGACY_PATH.is_file(), (
        f"Retired legacy path exists but is not a regular notice file: {LEGACY_PATH}"
    )

    text = LEGACY_PATH.read_text(encoding="utf-8")
    assert str(CANONICAL_PATH) in text, (
        "Legacy path still exists, so it must clearly say the canonical source is "
        f"{CANONICAL_PATH}. Notice text did not include that exact absolute path."
    )

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return

    assert not _looks_like_active_exception_json(parsed), (
        f"Legacy path {LEGACY_PATH} still contains parseable active exception JSON. "
        "It must be removed or replaced with a human-readable retirement notice, "
        f"and the canonical source must be {CANONICAL_PATH}."
    )


def test_migration_verification_log_has_exact_required_five_lines():
    assert LOG_PATH.exists(), f"Migration verification log is missing: {LOG_PATH}"
    assert LOG_PATH.is_file(), (
        f"Migration verification log path exists but is not a regular file: {LOG_PATH}"
    )

    raw_text = LOG_PATH.read_text(encoding="utf-8")
    normalized = raw_text[:-1] if raw_text.endswith("\n") else raw_text

    assert normalized == EXPECTED_LOG_TEXT, (
        "Migration verification log contents are wrong. It must contain exactly the "
        "five required non-empty lines in order, with no extra fields or blank lines.\n"
        f"Expected:\n{EXPECTED_LOG_TEXT}\n"
        f"Actual:\n{raw_text}"
    )

    lines = normalized.split("\n")
    assert len(lines) == 5 and all(lines), (
        "Migration verification log must contain exactly five non-empty lines."
    )