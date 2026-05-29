# test_final_state.py
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path("/home/user/devops-log-lab")
ENV_DIR = Path("/home/user/devops-log-lab/env-candidates")
LOG_DIR = Path("/home/user/devops-log-lab/logs")
DIAG_DIR = Path("/home/user/devops-log-lab/diagnostics")
MATRIX_PATH = Path("/home/user/devops-log-lab/diagnostics/hypothesis_matrix.tsv")
FINAL_LOG_PATH = Path("/home/user/devops-log-lab/diagnostics/final_verification.log")
SELECTED_ENV_COPY = Path("/home/user/devops-log-lab/diagnostics/selected.env")

EXPECTED_CANDIDATES = ["dev-a.env", "dev-b.env", "dev-c.env", "dev-d.env"]
EXPECTED_HEADER = ["candidate", "status", "evidence", "next_action"]
EXPECTED_HEALTH_JSON_TEXT = (
    '{"status":"ok","profile":"development","cache":"memory",'
    '"database":"sqlite","stream":"enabled","port":8127}'
)
EXPECTED_HEALTH_JSON = {
    "status": "ok",
    "profile": "development",
    "cache": "memory",
    "database": "sqlite",
    "stream": "enabled",
    "port": 8127,
}
EXPECTED_SELECTED_ENV_TEXT = "\n".join(
    [
        "APP_PROFILE=development",
        "APP_PORT=8127",
        "CACHE_BACKEND=memory",
        "DATABASE_URL=sqlite:///tmp/devops_log_lab.sqlite3",
        "FEATURE_FLAG_STREAM=enabled",
    ]
)


def _read_text(path: Path) -> str:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Required path is not a regular file: {path}"
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"{path} must be valid UTF-8, but could not be decoded: {exc}")


def _parse_matrix() -> list[dict[str, str]]:
    text = _read_text(MATRIX_PATH)
    assert text.strip(), f"{MATRIX_PATH} is empty"

    lines = text.splitlines()
    reader = csv.reader(lines, delimiter="\t")
    rows = list(reader)

    assert rows, f"{MATRIX_PATH} has no rows"
    assert rows[0] == EXPECTED_HEADER, (
        f"{MATRIX_PATH} header must be exactly "
        f"{'	'.join(EXPECTED_HEADER)!r}, got {rows[0]!r}"
    )

    data_rows = rows[1:]
    assert len(data_rows) == len(EXPECTED_CANDIDATES), (
        f"{MATRIX_PATH} must contain exactly one data row per candidate "
        f"{EXPECTED_CANDIDATES}, but has {len(data_rows)} data rows"
    )

    parsed = []
    for line_number, row in enumerate(data_rows, start=2):
        assert len(row) == 4, (
            f"{MATRIX_PATH} line {line_number} must have exactly four "
            f"tab-separated fields, got {len(row)} fields: {row!r}"
        )
        parsed.append(dict(zip(EXPECTED_HEADER, row)))

    return parsed


def _parse_final_verification() -> dict[str, str]:
    text = _read_text(FINAL_LOG_PATH)
    raw_lines = text.splitlines()

    assert len(raw_lines) == 6, (
        f"{FINAL_LOG_PATH} must have exactly six lines and no extras, "
        f"but has {len(raw_lines)} lines: {raw_lines!r}"
    )

    assert all(line.strip() for line in raw_lines), (
        f"{FINAL_LOG_PATH} must contain exactly six non-empty lines; "
        f"found: {raw_lines!r}"
    )

    expected_keys = [
        "selected_candidate",
        "app_module",
        "configured_port",
        "readiness_result",
        "health_json",
        "stop_reason",
    ]

    parsed = {}
    for index, (line, expected_key) in enumerate(zip(raw_lines, expected_keys), start=1):
        prefix = expected_key + "="
        assert line.startswith(prefix), (
            f"{FINAL_LOG_PATH} line {index} must start with {prefix!r}, "
            f"got {line!r}"
        )
        value = line[len(prefix):]
        assert value, f"{FINAL_LOG_PATH} line {index} has an empty value for {expected_key!r}"
        parsed[expected_key] = value

    return parsed


def _parse_env_file(path: Path) -> dict[str, str]:
    text = _read_text(path)
    values = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        assert "=" in line, f"{path} line {line_number} is not KEY=VALUE: {raw_line!r}"
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_required_diagnostics_files_exist_and_are_utf8_regular_files():
    assert DIAG_DIR.exists(), f"Missing diagnostics directory: {DIAG_DIR}"
    assert DIAG_DIR.is_dir(), f"Diagnostics path is not a directory: {DIAG_DIR}"

    for path in [MATRIX_PATH, FINAL_LOG_PATH]:
        assert path.exists(), f"Missing required diagnostics output file: {path}"
        assert path.is_file(), f"Required diagnostics output is not a regular file: {path}"
        _read_text(path)


def test_hypothesis_matrix_has_exact_header_rows_order_and_statuses():
    rows = _parse_matrix()

    actual_candidates = [row["candidate"] for row in rows]
    assert actual_candidates == EXPECTED_CANDIDATES, (
        f"{MATRIX_PATH} rows must be sorted lexicographically by candidate filename "
        f"and exactly {EXPECTED_CANDIDATES}, but got {actual_candidates}"
    )

    statuses = {row["candidate"]: row["status"] for row in rows}
    expected_statuses = {
        "dev-a.env": "ELIMINATED",
        "dev-b.env": "SELECTED",
        "dev-c.env": "ELIMINATED",
        "dev-d.env": "ELIMINATED",
    }
    assert statuses == expected_statuses, (
        f"{MATRIX_PATH} must mark only dev-b.env SELECTED and all other "
        f"candidates ELIMINATED, but got {statuses}"
    )

    selected = [row for row in rows if row["status"] == "SELECTED"]
    assert len(selected) == 1, (
        f"{MATRIX_PATH} must contain exactly one SELECTED row, got {len(selected)}: {selected!r}"
    )
    assert selected[0]["candidate"] == "dev-b.env", (
        f"The selected candidate must be dev-b.env, got {selected[0]['candidate']!r}"
    )

    invalid_status_rows = [
        row for row in rows if row["status"] not in {"ELIMINATED", "SELECTED"}
    ]
    assert not invalid_status_rows, (
        f"Every matrix status must be exactly ELIMINATED or SELECTED; "
        f"invalid rows: {invalid_status_rows!r}"
    )


def test_hypothesis_matrix_next_actions_are_correct_for_selected_and_eliminated():
    rows = _parse_matrix()

    for row in rows:
        candidate = row["candidate"]
        next_action = row["next_action"]
        assert next_action.strip(), f"{candidate} next_action must not be empty"

        if candidate == "dev-b.env":
            assert next_action.startswith("use_for_dev:"), (
                f"dev-b.env next_action must start with 'use_for_dev:', "
                f"got {next_action!r}"
            )
        else:
            assert next_action.startswith("do_not_use:"), (
                f"{candidate} is eliminated, so next_action must start with "
                f"'do_not_use:', got {next_action!r}"
            )


def test_hypothesis_matrix_contains_candidate_specific_decisive_evidence():
    rows = _parse_matrix()
    by_candidate = {row["candidate"]: row for row in rows}

    for candidate, row in by_candidate.items():
        evidence = row["evidence"]
        assert evidence.strip(), f"{candidate} evidence field must not be empty"
        assert "\n" not in evidence and "\r" not in evidence, (
            f"{candidate} evidence must be compact single-field TSV text, got {evidence!r}"
        )
        assert "archive-prod-incident.log" not in evidence, (
            f"{candidate} evidence must not cite archive-prod-incident.log, "
            "which is an unrelated archived production incident"
        )

    dev_a_evidence = by_candidate["dev-a.env"]["evidence"].lower()
    assert (
        "startup-dev-a.log" in dev_a_evidence
        or "redis" in dev_a_evidence
        or ("cache" in dev_a_evidence and "unavailable" in dev_a_evidence)
    ), (
        "dev-a.env evidence must cite startup-dev-a.log or mention the decisive "
        f"redis/cache-unavailable readiness failure, got {by_candidate['dev-a.env']['evidence']!r}"
    )

    dev_b_evidence = by_candidate["dev-b.env"]["evidence"]
    dev_b_evidence_lower = dev_b_evidence.lower()
    assert (
        "startup-dev-b.log" in dev_b_evidence_lower
        or "readiness pass" in dev_b_evidence_lower
        or EXPECTED_HEALTH_JSON_TEXT in dev_b_evidence
    ), (
        "dev-b.env evidence must cite startup-dev-b.log, readiness PASS, or the "
        f"correct health JSON, got {dev_b_evidence!r}"
    )

    dev_c_evidence = by_candidate["dev-c.env"]["evidence"].lower()
    assert (
        "startup-dev-c.log" in dev_c_evidence
        or "9001" in dev_c_evidence and "8127" in dev_c_evidence
        or "wrong port" in dev_c_evidence
    ), (
        "dev-c.env evidence must cite startup-dev-c.log or mention the decisive "
        f"wrong-port 9001 vs 8127 failure, got {by_candidate['dev-c.env']['evidence']!r}"
    )

    dev_d_evidence = by_candidate["dev-d.env"]["evidence"].lower()
    assert (
        "startup-dev-d.log" in dev_d_evidence
        or "postgres" in dev_d_evidence
        or "postgresql" in dev_d_evidence
    ), (
        "dev-d.env evidence must cite startup-dev-d.log or mention the decisive "
        f"postgres/postgresql unavailable failure, got {by_candidate['dev-d.env']['evidence']!r}"
    )

    evidence_values = [row["evidence"].strip() for row in rows]
    assert len(set(evidence_values)) == len(evidence_values), (
        "Evidence rows must contain distinct candidate-specific reasons; "
        f"got repeated evidence values: {evidence_values!r}"
    )


def test_final_verification_log_has_exact_required_values_and_json():
    parsed = _parse_final_verification()

    expected_exact = {
        "selected_candidate": "dev-b.env",
        "app_module": "service.app",
        "configured_port": "8127",
        "readiness_result": "PASS",
        "health_json": EXPECTED_HEALTH_JSON_TEXT,
    }

    for key, expected_value in expected_exact.items():
        assert parsed[key] == expected_value, (
            f"{FINAL_LOG_PATH} must contain {key}={expected_value}, "
            f"but got {key}={parsed[key]!r}"
        )

    try:
        observed_health = json.loads(parsed["health_json"])
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"{FINAL_LOG_PATH} health_json must be a single-line parseable JSON object, "
            f"but json.loads failed: {exc}"
        )

    assert isinstance(observed_health, dict), (
        f"health_json must parse to a JSON object, got {type(observed_health).__name__}"
    )
    assert observed_health == EXPECTED_HEALTH_JSON, (
        f"health_json must equal {EXPECTED_HEALTH_JSON}, got {observed_health}"
    )

    stop_reason = parsed["stop_reason"].lower()
    assert "verification succeeded" in stop_reason, (
        f"stop_reason must state that verification succeeded, got {parsed['stop_reason']!r}"
    )
    assert "eliminated candidate" in stop_reason or "eliminated candidates" in stop_reason, (
        f"stop_reason must state that eliminated candidates were not pursued further, "
        f"got {parsed['stop_reason']!r}"
    )


def test_final_verification_and_matrix_are_internally_consistent():
    rows = _parse_matrix()
    final = _parse_final_verification()

    selected_rows = [row for row in rows if row["status"] == "SELECTED"]
    assert len(selected_rows) == 1, "Matrix must have exactly one selected row"

    matrix_selected = selected_rows[0]["candidate"]
    assert final["selected_candidate"] == matrix_selected, (
        f"selected_candidate in {FINAL_LOG_PATH} ({final['selected_candidate']!r}) "
        f"must match SELECTED candidate in {MATRIX_PATH} ({matrix_selected!r})"
    )

    assert final["selected_candidate"] == "dev-b.env", (
        f"The final selected candidate must be dev-b.env, got {final['selected_candidate']!r}"
    )
    assert final["app_module"] == "service.app", (
        f"The app_module must be service.app, got {final['app_module']!r}"
    )
    assert final["configured_port"] == "8127", (
        f"The configured_port must be 8127, got {final['configured_port']!r}"
    )


def test_selected_environment_is_applied_or_accurately_recorded():
    final = _parse_final_verification()

    if SELECTED_ENV_COPY.exists():
        assert SELECTED_ENV_COPY.is_file(), (
            f"If present, selected env copy must be a regular file: {SELECTED_ENV_COPY}"
        )
        selected_copy_text = _read_text(SELECTED_ENV_COPY).strip()
        expected_text = EXPECTED_SELECTED_ENV_TEXT.strip()
        assert selected_copy_text == expected_text, (
            f"{SELECTED_ENV_COPY} must be an exact copy of dev-b.env contents. "
            f"Expected {expected_text!r}, got {selected_copy_text!r}"
        )
    else:
        assert final["selected_candidate"] == "dev-b.env", (
            "If diagnostics/selected.env is not present, final_verification.log must "
            "accurately record dev-b.env as the selected candidate"
        )
        assert final["app_module"] == "service.app", (
            "If diagnostics/selected.env is not present, final_verification.log must "
            "accurately record service.app as the module used"
        )

    dev_b_values = _parse_env_file(Path("/home/user/devops-log-lab/env-candidates/dev-b.env"))
    assert dev_b_values == {
        "APP_PROFILE": "development",
        "APP_PORT": "8127",
        "CACHE_BACKEND": "memory",
        "DATABASE_URL": "sqlite:///tmp/devops_log_lab.sqlite3",
        "FEATURE_FLAG_STREAM": "enabled",
    }, (
        "The selected source env-candidate dev-b.env must remain intact and runnable"
    )


def test_selected_service_validation_can_be_rerun_from_repository_root():
    env_values = _parse_env_file(Path("/home/user/devops-log-lab/env-candidates/dev-b.env"))
    env = os.environ.copy()
    env.update(env_values)
    env["PYTHONPATH"] = str(ROOT)

    probe_code = r'''
import importlib
import json
import sys

module = importlib.import_module("service.app")
expected = {
    "status": "ok",
    "profile": "development",
    "cache": "memory",
    "database": "sqlite",
    "stream": "enabled",
    "port": 8127,
}

candidate_callables = [
    "health",
    "readiness",
    "ready",
    "healthcheck",
    "get_health",
    "get_readiness",
    "build_health",
    "current_health",
]

result = None
for name in candidate_callables:
    func = getattr(module, name, None)
    if callable(func):
        try:
            value = func()
        except TypeError:
            continue
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        if isinstance(value, dict):
            result = value
            break

if result is None:
    for attr in ["HEALTH_JSON", "EXPECTED_HEALTH_JSON", "health_json"]:
        value = getattr(module, attr, None)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        if isinstance(value, dict):
            result = value
            break

if result is None:
    for name in ["main", "run_readiness_check", "readiness_check"]:
        func = getattr(module, name, None)
        if callable(func):
            try:
                value = func()
            except TypeError:
                continue
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            if isinstance(value, dict):
                result = value
                break

if result != expected:
    print(json.dumps({"observed": result, "expected": expected}, sort_keys=True), file=sys.stderr)
    raise SystemExit(2)

print(json.dumps(result, separators=(",", ":")))
'''

    completed = subprocess.run(
        [sys.executable, "-c", probe_code],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )

    assert completed.returncode == 0, (
        "Rerunning service.app validation from repository root with dev-b.env "
        f"must succeed. stdout={completed.stdout!r} stderr={completed.stderr!r}"
    )

    output_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    assert output_lines, (
        "Rerun validation produced no health JSON output from service.app"
    )

    assert output_lines[-1] == EXPECTED_HEALTH_JSON_TEXT, (
        "Rerun validation must produce the exact compact health JSON. "
        f"Expected {EXPECTED_HEALTH_JSON_TEXT!r}, got {output_lines[-1]!r}. "
        f"Full stdout={completed.stdout!r}, stderr={completed.stderr!r}"
    )


def test_diagnostics_do_not_treat_archived_production_log_as_active_evidence():
    matrix_text = _read_text(MATRIX_PATH)
    final_text = _read_text(FINAL_LOG_PATH)
    combined = matrix_text + "\n" + final_text

    forbidden_terms = [
        "archive-prod-incident.log",
        "payment gateway token missing",
        "0.0.0.0:443",
        "permission denied",
        "profile=production",
    ]

    for term in forbidden_terms:
        assert term not in combined, (
            f"Final diagnostics must not use archived production incident evidence "
            f"as decisive candidate evidence; found forbidden term {term!r}"
        )


def test_virtualenvs_and_diagnostic_outputs_stay_within_repository_if_present():
    assert ROOT.exists() and ROOT.is_dir(), f"Repository root is missing: {ROOT}"

    suspicious_absolute_paths = []
    for path in DIAG_DIR.rglob("*"):
        resolved = path.resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            suspicious_absolute_paths.append(str(resolved))

    assert not suspicious_absolute_paths, (
        "Diagnostics artifacts must remain under /home/user/devops-log-lab; "
        f"found paths resolving outside the repository: {suspicious_absolute_paths}"
    )

    for candidate in ROOT.rglob("*"):
        if candidate.name in {"bin", "pyvenv.cfg"}:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                pytest.fail(
                    f"Detected a possible virtualenv artifact outside repository root: {resolved}"
                )