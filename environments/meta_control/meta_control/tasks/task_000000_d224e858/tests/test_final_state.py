# test_final_state.py
import json
import os
import pathlib
import subprocess

PROJECT_DIR = pathlib.Path("/home/user/ops-pip-debug")
REQUIREMENTS = pathlib.Path("/home/user/ops-pip-debug/requirements.txt")
SERVICE_LOG = pathlib.Path("/home/user/ops-pip-debug/logs/service.log")
ANALYZER = pathlib.Path("/home/user/ops-pip-debug/analyze_logs.py")
SUMMARY_JSON = pathlib.Path("/home/user/ops-pip-debug/logs/summary.json")
REPORT = pathlib.Path("/home/user/ops-pip-debug/env_repair_report.txt")

EXPECTED_REQUIREMENTS = """requests==2.31.0
urllib3==1.26.18
python-dateutil==2.8.2
"""

EXPECTED_SERVICE_LOG = """2024-05-12T08:15:01Z INFO api-gateway boot sequence started
2024-05-12T08:15:03Z INFO api-gateway listening on 0.0.0.0:8080
2024-05-12T08:16:10Z WARNING auth-cache refresh took 1840ms
2024-05-12T08:17:44Z ERROR upstream inventory timeout after 3000ms
2024-05-12T08:18:01Z INFO retry scheduled for inventory request
2024-05-12T08:19:22Z WARNING payment queue depth above threshold
2024-05-12T08:21:09Z ERROR checkout request failed with HTTP 502
2024-05-12T08:22:11Z INFO api-gateway health check passed
"""

EXPECTED_ANALYZER = '''#!/usr/bin/env python3
import json
import pathlib
import sys

try:
    import requests
    import urllib3
except Exception as exc:
    print(f"IMPORT_ERROR: {exc}", file=sys.stderr)
    sys.exit(2)

EXPECTED_REQUESTS = "2.31.0"
EXPECTED_URLLIB3_PREFIX = "1.26."

if requests.__version__ != EXPECTED_REQUESTS:
    print(
        f"ENV_ERROR: requests version {requests.__version__} does not match required {EXPECTED_REQUESTS}",
        file=sys.stderr,
    )
    sys.exit(3)

if not urllib3.__version__.startswith(EXPECTED_URLLIB3_PREFIX):
    print(
        f"ENV_ERROR: urllib3 version {urllib3.__version__} is incompatible; expected prefix {EXPECTED_URLLIB3_PREFIX}",
        file=sys.stderr,
    )
    sys.exit(4)

log_path = pathlib.Path("/home/user/ops-pip-debug/logs/service.log")
summary_path = pathlib.Path("/home/user/ops-pip-debug/logs/summary.json")

lines = [line.rstrip("\\n") for line in log_path.read_text().splitlines()]
errors = [line for line in lines if " ERROR " in line]
warnings = [line for line in lines if " WARNING " in line]

summary = {
    "status": "degraded",
    "total_lines": len(lines),
    "error_count": len(errors),
    "warning_count": len(warnings),
    "requests_version": requests.__version__,
    "urllib3_version": urllib3.__version__,
}

summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\\n")
print(f"WROTE {summary_path}")
'''

EXPECTED_SUMMARY = {
    "error_count": 2,
    "requests_version": "2.31.0",
    "status": "degraded",
    "total_lines": 8,
    "urllib3_version": "1.26.18",
    "warning_count": 2,
}


def read_text_or_fail(path: pathlib.Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        raise AssertionError(f"Required file is missing: {path}")


def parse_report():
    assert REPORT.exists(), f"Final repair report is missing: {REPORT}"
    assert REPORT.is_file(), f"Repair report path exists but is not a regular file: {REPORT}"

    raw = read_text_or_fail(REPORT)
    assert raw, f"Repair report is empty: {REPORT}"
    assert raw.endswith("\n"), f"Repair report must end with a single trailing newline: {REPORT}"
    assert not raw.endswith("\n\n"), f"Repair report must not contain extra blank lines at the end: {REPORT}"

    lines = raw.splitlines()
    assert len(lines) == 5, (
        f"{REPORT} must contain exactly five lines, but found {len(lines)} lines: {lines!r}"
    )

    for index, line in enumerate(lines, start=1):
        assert line == line.strip(), (
            f"Line {index} of {REPORT} has leading or trailing whitespace: {line!r}"
        )
        assert line, f"Line {index} of {REPORT} is blank; no blank lines are allowed"

    expected_prefixes = [
        "ENV_REPAIR_STATUS=",
        "PYTHON_EXECUTABLE=",
        "REQUESTS_VERSION=",
        "URLLIB3_VERSION=",
        "SUMMARY_JSON=",
    ]
    for index, (line, prefix) in enumerate(zip(lines, expected_prefixes), start=1):
        assert line.startswith(prefix), (
            f"Line {index} of {REPORT} must start with {prefix!r}, got {line!r}"
        )

    values = {}
    for line in lines:
        key, value = line.split("=", 1)
        values[key] = value

    return lines, values


def test_original_project_inputs_and_analyzer_were_not_rewritten_to_fake_success():
    assert PROJECT_DIR.exists(), f"Project directory is missing: {PROJECT_DIR}"
    assert PROJECT_DIR.is_dir(), f"Project path is not a directory: {PROJECT_DIR}"

    assert REQUIREMENTS.exists(), f"Requirements file is missing: {REQUIREMENTS}"
    assert REQUIREMENTS.is_file(), f"Requirements path is not a file: {REQUIREMENTS}"
    assert read_text_or_fail(REQUIREMENTS) == EXPECTED_REQUIREMENTS, (
        f"{REQUIREMENTS} was changed. The task is to repair the Python environment, "
        "not rewrite the requirements file."
    )

    assert SERVICE_LOG.exists(), f"Service log is missing: {SERVICE_LOG}"
    assert SERVICE_LOG.is_file(), f"Service log path is not a file: {SERVICE_LOG}"
    assert read_text_or_fail(SERVICE_LOG) == EXPECTED_SERVICE_LOG, (
        f"{SERVICE_LOG} was changed. The summary must be produced from the original log."
    )

    assert ANALYZER.exists(), f"Analyzer script is missing: {ANALYZER}"
    assert ANALYZER.is_file(), f"Analyzer path is not a file: {ANALYZER}"
    assert read_text_or_fail(ANALYZER) == EXPECTED_ANALYZER, (
        f"{ANALYZER} was changed. The required fix is the importable Python environment, "
        "not bypassing the version checks or hand-writing a different analyzer."
    )


def test_env_repair_report_has_exact_required_five_line_format_and_values():
    lines, values = parse_report()

    assert lines[0] == "ENV_REPAIR_STATUS=success", (
        f"Line 1 of {REPORT} must be exactly ENV_REPAIR_STATUS=success"
    )
    assert lines[2] == "REQUESTS_VERSION=2.31.0", (
        f"Line 3 of {REPORT} must be exactly REQUESTS_VERSION=2.31.0"
    )
    assert lines[3] == "URLLIB3_VERSION=1.26.18", (
        f"Line 4 of {REPORT} must be exactly URLLIB3_VERSION=1.26.18"
    )
    assert lines[4] == f"SUMMARY_JSON={SUMMARY_JSON}", (
        f"Line 5 of {REPORT} must be exactly SUMMARY_JSON={SUMMARY_JSON}"
    )

    python_executable = pathlib.Path(values["PYTHON_EXECUTABLE"])
    assert python_executable.is_absolute(), (
        f"PYTHON_EXECUTABLE in {REPORT} must be an absolute path, got: {python_executable}"
    )
    assert python_executable.exists(), (
        f"PYTHON_EXECUTABLE in {REPORT} does not exist: {python_executable}"
    )
    assert python_executable.is_file(), (
        f"PYTHON_EXECUTABLE in {REPORT} is not a regular file: {python_executable}"
    )
    assert os.access(python_executable, os.X_OK), (
        f"PYTHON_EXECUTABLE in {REPORT} is not executable: {python_executable}"
    )


def test_reported_python_imports_exact_required_package_versions():
    _, values = parse_report()
    python_executable = values["PYTHON_EXECUTABLE"]

    probe = (
        "import json, sys\n"
        "import requests, urllib3\n"
        "print(json.dumps({"
        "'executable': sys.executable, "
        "'requests': requests.__version__, "
        "'urllib3': urllib3.__version__"
        "}, sort_keys=True))\n"
    )
    result = subprocess.run(
        [python_executable, "-c", probe],
        cwd=str(PROJECT_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"Reported PYTHON_EXECUTABLE could not import requests and urllib3 cleanly.\n"
        f"python: {python_executable}\n"
        f"return code: {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    try:
        observed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Could not parse import-version probe output from {python_executable} as JSON: {exc}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    assert observed["requests"] == "2.31.0", (
        f"{python_executable} imports requests {observed['requests']!r}, "
        "but the repaired environment must import requests '2.31.0'."
    )
    assert observed["urllib3"] == "1.26.18", (
        f"{python_executable} imports urllib3 {observed['urllib3']!r}, "
        "but the repaired environment must import urllib3 '1.26.18'."
    )

    assert values["REQUESTS_VERSION"] == observed["requests"], (
        f"REQUESTS_VERSION in {REPORT} does not match what the reported Python imports: "
        f"report={values['REQUESTS_VERSION']!r}, actual={observed['requests']!r}"
    )
    assert values["URLLIB3_VERSION"] == observed["urllib3"], (
        f"URLLIB3_VERSION in {REPORT} does not match what the reported Python imports: "
        f"report={values['URLLIB3_VERSION']!r}, actual={observed['urllib3']!r}"
    )


def test_analyzer_runs_successfully_with_reported_python_from_project_directory():
    _, values = parse_report()
    python_executable = values["PYTHON_EXECUTABLE"]

    result = subprocess.run(
        [python_executable, str(ANALYZER)],
        cwd=str(PROJECT_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"Analyzer does not run successfully with the reported PYTHON_EXECUTABLE.\n"
        f"python: {python_executable}\n"
        f"cwd: {PROJECT_DIR}\n"
        f"return code: {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert f"WROTE {SUMMARY_JSON}" in result.stdout, (
        f"Analyzer should report that it wrote {SUMMARY_JSON}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_summary_json_exists_is_parseable_and_has_exact_expected_semantic_content():
    assert SUMMARY_JSON.exists(), f"Analyzer summary JSON is missing: {SUMMARY_JSON}"
    assert SUMMARY_JSON.is_file(), f"Summary JSON path exists but is not a regular file: {SUMMARY_JSON}"

    raw = read_text_or_fail(SUMMARY_JSON)
    assert raw.strip(), f"Summary JSON is empty: {SUMMARY_JSON}"

    try:
        summary = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"{SUMMARY_JSON} is not valid JSON: {exc}\nContents:\n{raw}"
        )

    assert summary == EXPECTED_SUMMARY, (
        f"{SUMMARY_JSON} does not contain the expected analyzer result.\n"
        f"Expected: {EXPECTED_SUMMARY!r}\n"
        f"Actual:   {summary!r}"
    )


def test_report_summary_path_points_to_generated_summary_json():
    _, values = parse_report()

    assert values["SUMMARY_JSON"] == str(SUMMARY_JSON), (
        f"SUMMARY_JSON in {REPORT} must point to the required generated file "
        f"{SUMMARY_JSON}, got {values['SUMMARY_JSON']!r}"
    )
    assert pathlib.Path(values["SUMMARY_JSON"]).exists(), (
        f"SUMMARY_JSON path named in {REPORT} does not exist: {values['SUMMARY_JSON']}"
    )