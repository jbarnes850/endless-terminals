# test_final_state.py
import os
import re
import subprocess
from pathlib import Path

import pytest


BASE_DIR = Path("/home/user/deploy-rollout")
REQUIREMENTS = Path("/home/user/deploy-rollout/requirements.txt")
PROBE = Path("/home/user/deploy-rollout/rollout_probe.py")
VENV = Path("/home/user/deploy-rollout/.venv")
VENV_CFG = Path("/home/user/deploy-rollout/.venv/pyvenv.cfg")
VENV_BIN = Path("/home/user/deploy-rollout/.venv/bin")
VENV_PYTHON = Path("/home/user/deploy-rollout/.venv/bin/python")
VENV_PIP = Path("/home/user/deploy-rollout/.venv/bin/pip")
EVIDENCE = Path("/home/user/deploy-rollout/deployment_evidence.log")

EXPECTED_REQUIREMENTS = "requests==2.31.0\n"
EXPECTED_REQUESTS_VERSION = "2.31.0"
EXPECTED_PROBE_RE = re.compile(r"^probe-ok requests=2\.31\.0 digest=[0-9a-f]{12}$")
PYTHON_EVIDENCE_RE = re.compile(
    r"^python_executable=(/home/user/deploy-rollout/\.venv/.+python[0-9.]*)$"
)
PIP_EVIDENCE_RE = re.compile(
    r"^pip_executable=(/home/user/deploy-rollout/\.venv/.+pip[0-9.]*)$"
)


def _run_command(args, *, timeout=30):
    return subprocess.run(
        [str(arg) for arg in args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _assert_executable_file(path: Path, description: str):
    assert path.is_absolute(), f"{description} must be an absolute path, got: {path}"
    assert path.exists(), f"{description} does not exist: {path}"
    assert path.is_file() or path.is_symlink(), f"{description} is not a file/symlink: {path}"
    assert os.access(path, os.X_OK), f"{description} is not executable by current user: {path}"


def _assert_path_under_venv(path: Path, description: str):
    assert path.is_absolute(), f"{description} must be absolute, got: {path}"
    try:
        path.relative_to(VENV)
    except ValueError:
        pytest.fail(f"{description} must be inside {VENV}, got: {path}")


@pytest.fixture(scope="session")
def venv_requests_version():
    assert VENV_PYTHON.exists(), (
        f"Cannot verify dependencies because virtualenv Python is missing: {VENV_PYTHON}"
    )
    result = _run_command(
        [VENV_PYTHON, "-c", "import requests; print(requests.__version__)"]
    )
    assert result.returncode == 0, (
        "The virtual environment Python cannot import requests successfully.\n"
        f"Command: {VENV_PYTHON} -c 'import requests; print(requests.__version__)'\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    version = result.stdout.strip()
    assert version == EXPECTED_REQUESTS_VERSION, (
        f"requests must be installed in the virtual environment as version "
        f"{EXPECTED_REQUESTS_VERSION}, but {VENV_PYTHON} reported {version!r}.\n"
        f"stderr: {result.stderr!r}"
    )
    return version


@pytest.fixture(scope="session")
def expected_probe_output(venv_requests_version):
    result = _run_command([VENV_PYTHON, PROBE])
    assert result.returncode == 0, (
        "The rollout probe must run successfully using the virtualenv Python.\n"
        f"Command: {VENV_PYTHON} {PROBE}\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )

    stdout_lines = result.stdout.splitlines()
    assert len(stdout_lines) == 1, (
        "The rollout probe must print exactly one output line when run with the "
        f"virtualenv Python, but printed {len(stdout_lines)} line(s): {stdout_lines!r}"
    )

    line = stdout_lines[0]
    assert EXPECTED_PROBE_RE.fullmatch(line), (
        "The rollout probe output has the wrong format or requests version. "
        f"Expected regex {EXPECTED_PROBE_RE.pattern!r}, got {line!r}."
    )
    return line


def test_required_input_files_still_exist_with_expected_requirements():
    assert BASE_DIR.exists(), f"Required working directory is missing: {BASE_DIR}"
    assert BASE_DIR.is_dir(), f"Required working path is not a directory: {BASE_DIR}"

    assert REQUIREMENTS.exists(), f"Required dependency file is missing: {REQUIREMENTS}"
    assert REQUIREMENTS.is_file(), f"Requirements path is not a file: {REQUIREMENTS}"
    actual_requirements = REQUIREMENTS.read_text(encoding="utf-8")
    assert actual_requirements == EXPECTED_REQUIREMENTS, (
        f"{REQUIREMENTS} must still contain exactly {EXPECTED_REQUIREMENTS!r}, "
        f"but contained {actual_requirements!r}"
    )

    assert PROBE.exists(), f"Required probe file is missing: {PROBE}"
    assert PROBE.is_file(), f"Probe path is not a file: {PROBE}"
    assert os.access(PROBE, os.R_OK), f"Probe file must be readable: {PROBE}"


def test_virtual_environment_exists_with_venv_layout():
    assert VENV.exists(), f"Virtual environment directory was not created: {VENV}"
    assert VENV.is_dir(), f"Virtual environment path exists but is not a directory: {VENV}"

    assert VENV_CFG.exists(), f"venv metadata file is missing: {VENV_CFG}"
    assert VENV_CFG.is_file(), f"venv metadata path is not a file: {VENV_CFG}"

    assert VENV_BIN.exists(), f"venv bin directory is missing: {VENV_BIN}"
    assert VENV_BIN.is_dir(), f"venv bin path is not a directory: {VENV_BIN}"

    _assert_executable_file(VENV_PYTHON, "Expected virtualenv Python")
    _assert_executable_file(VENV_PIP, "Expected virtualenv pip")

    cfg_text = VENV_CFG.read_text(encoding="utf-8", errors="replace")
    assert "home =" in cfg_text, (
        f"{VENV_CFG} does not look like a Python venv pyvenv.cfg file; "
        "expected it to contain a 'home =' entry."
    )


def test_requests_installed_in_virtual_environment(venv_requests_version):
    assert venv_requests_version == EXPECTED_REQUESTS_VERSION


def test_rollout_probe_runs_successfully_with_virtualenv_python(expected_probe_output):
    assert EXPECTED_PROBE_RE.fullmatch(expected_probe_output), (
        f"Unexpected probe output from {VENV_PYTHON}: {expected_probe_output!r}"
    )


def test_deployment_evidence_file_exists_and_has_exact_line_count():
    assert EVIDENCE.exists(), f"Deployment evidence file is missing: {EVIDENCE}"
    assert EVIDENCE.is_file(), f"Deployment evidence path exists but is not a file: {EVIDENCE}"

    raw = EVIDENCE.read_text(encoding="utf-8")
    lines = raw.splitlines()

    assert len(lines) == 8, (
        f"{EVIDENCE} must contain exactly 8 lines with no blank or extra lines, "
        f"but contained {len(lines)} line(s): {lines!r}"
    )
    assert all(line != "" for line in lines), (
        f"{EVIDENCE} must not contain blank lines, but contained: {lines!r}"
    )

    if raw:
        assert raw.endswith("\n") or raw == "\n".join(lines), (
            f"{EVIDENCE} must be parseable as exactly 8 text lines without trailing "
            "extra content."
        )


def test_deployment_evidence_exact_semantics_and_order(
    venv_requests_version, expected_probe_output
):
    assert EVIDENCE.exists(), f"Deployment evidence file is missing: {EVIDENCE}"
    lines = EVIDENCE.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 8, (
        f"{EVIDENCE} must contain exactly 8 lines, but contained {len(lines)}: {lines!r}"
    )

    expected_fixed = {
        0: "status=ready",
        1: "venv_path=/home/user/deploy-rollout/.venv",
        4: f"requests_version={EXPECTED_REQUESTS_VERSION}",
        5: f"probe_result={expected_probe_output}",
        6: "site_scope=venv",
        7: (
            "deployment_note=dependencies installed and probe executed with "
            "isolated interpreter"
        ),
    }

    for index, expected in expected_fixed.items():
        assert lines[index] == expected, (
            f"Line {index + 1} of {EVIDENCE} is wrong.\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {lines[index]!r}"
        )

    python_match = PYTHON_EVIDENCE_RE.fullmatch(lines[2])
    assert python_match, (
        "Line 3 must be an absolute python_executable path inside the virtualenv, "
        "with field name exactly 'python_executable'. "
        f"Expected like 'python_executable={VENV_PYTHON}', got {lines[2]!r}."
    )
    evidence_python = Path(python_match.group(1))
    _assert_path_under_venv(evidence_python, "Evidence python_executable")
    _assert_executable_file(evidence_python, "Evidence python_executable")

    pip_match = PIP_EVIDENCE_RE.fullmatch(lines[3])
    assert pip_match, (
        "Line 4 must be an absolute pip_executable path inside the virtualenv, "
        "with field name exactly 'pip_executable'. "
        f"Expected like 'pip_executable={VENV_PIP}', got {lines[3]!r}."
    )
    evidence_pip = Path(pip_match.group(1))
    _assert_path_under_venv(evidence_pip, "Evidence pip_executable")
    _assert_executable_file(evidence_pip, "Evidence pip_executable")

    version_result = _run_command(
        [evidence_python, "-c", "import requests; print(requests.__version__)"]
    )
    assert version_result.returncode == 0, (
        "The python_executable recorded in the evidence file cannot import requests.\n"
        f"Recorded executable: {evidence_python}\n"
        f"stdout: {version_result.stdout!r}\n"
        f"stderr: {version_result.stderr!r}"
    )
    assert version_result.stdout.strip() == venv_requests_version == EXPECTED_REQUESTS_VERSION, (
        "The python_executable recorded in the evidence file does not report the "
        f"required requests version {EXPECTED_REQUESTS_VERSION}.\n"
        f"Recorded executable: {evidence_python}\n"
        f"stdout: {version_result.stdout!r}\n"
        f"stderr: {version_result.stderr!r}"
    )

    probe_result = _run_command([evidence_python, PROBE])
    assert probe_result.returncode == 0, (
        "The python_executable recorded in the evidence file cannot run the probe.\n"
        f"Recorded executable: {evidence_python}\n"
        f"stdout: {probe_result.stdout!r}\n"
        f"stderr: {probe_result.stderr!r}"
    )
    assert probe_result.stdout.splitlines() == [expected_probe_output], (
        "The probe_result in the evidence file must match the actual single-line "
        "output from running rollout_probe.py with the recorded virtualenv Python.\n"
        f"Expected line: {expected_probe_output!r}\n"
        f"Actual probe stdout from recorded executable: {probe_result.stdout!r}"
    )


def test_evidence_contains_no_extra_commentary_or_unknown_fields():
    assert EVIDENCE.exists(), f"Deployment evidence file is missing: {EVIDENCE}"
    lines = EVIDENCE.read_text(encoding="utf-8").splitlines()

    expected_field_names = [
        "status",
        "venv_path",
        "python_executable",
        "pip_executable",
        "requests_version",
        "probe_result",
        "site_scope",
        "deployment_note",
    ]

    actual_field_names = []
    for line_number, line in enumerate(lines, start=1):
        assert "=" in line, (
            f"Line {line_number} of {EVIDENCE} is not a key=value field: {line!r}"
        )
        key, value = line.split("=", 1)
        assert key, f"Line {line_number} of {EVIDENCE} has an empty field name: {line!r}"
        assert value, f"Line {line_number} of {EVIDENCE} has an empty value: {line!r}"
        actual_field_names.append(key)

    assert actual_field_names == expected_field_names, (
        f"{EVIDENCE} must contain exactly these fields in order: "
        f"{expected_field_names!r}, but contained {actual_field_names!r}"
    )