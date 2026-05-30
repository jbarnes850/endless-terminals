# test_final_state.py

import os
import subprocess
from pathlib import Path

import pytest


PROJECT_DIR = Path("/home/user/projects/portfolio-site")

NEW_VENV = Path("/home/user/projects/portfolio-site/.venv")
NEW_PYTHON = Path("/home/user/projects/portfolio-site/.venv/bin/python")
NEW_PIP = Path("/home/user/projects/portfolio-site/.venv/bin/pip")
NEW_PYVENV_CFG = Path("/home/user/projects/portfolio-site/.venv/pyvenv.cfg")

OLD_VENV = Path("/home/user/projects/portfolio-site/venv")
OLD_PYTHON = Path("/home/user/projects/portfolio-site/venv/bin/python")
OLD_PIP = Path("/home/user/projects/portfolio-site/venv/bin/pip")
OLD_PYVENV_CFG = Path("/home/user/projects/portfolio-site/venv/pyvenv.cfg")

ENVRC = Path("/home/user/projects/portfolio-site/.envrc")
LOG = Path("/home/user/projects/portfolio-site/venv_migration_check.log")

EXPECTED_ENVRC = "source /home/user/projects/portfolio-site/.venv/bin/activate\n"

EXPECTED_LOG_PREFIX_LINES = [
    "PROJECT_DIR=/home/user/projects/portfolio-site",
    "ACTIVE_ENV=/home/user/projects/portfolio-site/.venv",
    "PYTHON_EXE=/home/user/projects/portfolio-site/.venv/bin/python",
    "PIP_EXE=/home/user/projects/portfolio-site/.venv/bin/pip",
]

ALLOWED_OLD_ENV_STATUS_LINES = {
    "OLD_ENV_STATUS=missing",
    "OLD_ENV_STATUS=renamed",
    "OLD_ENV_STATUS=inactive",
}


def assert_is_dir(path: Path, description: str) -> None:
    assert path.exists(), f"Missing required {description}: {path}"
    assert path.is_dir(), f"Expected {description} to be a directory, but it is not: {path}"


def assert_is_file(path: Path, description: str) -> None:
    assert path.exists(), f"Missing required {description}: {path}"
    assert path.is_file(), f"Expected {description} to be a regular file, but it is not: {path}"


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_project_directory_still_exists() -> None:
    assert_is_dir(PROJECT_DIR, "project directory")


def test_new_virtual_environment_exists_with_required_files() -> None:
    assert_is_dir(NEW_VENV, "new virtual environment directory")

    assert_is_file(NEW_PYTHON, "Python executable in new virtual environment")
    assert os.access(NEW_PYTHON, os.X_OK), (
        f"New virtual environment Python exists but is not executable: {NEW_PYTHON}"
    )

    assert_is_file(NEW_PIP, "pip executable in new virtual environment")
    assert os.access(NEW_PIP, os.X_OK), (
        f"New virtual environment pip exists but is not executable: {NEW_PIP}"
    )

    assert_is_file(NEW_PYVENV_CFG, "pyvenv.cfg in new virtual environment")


def test_new_virtual_environment_python_reports_new_prefix() -> None:
    assert_is_file(NEW_PYTHON, "Python executable in new virtual environment")

    result = run_command(
        [str(NEW_PYTHON), "-c", "import sys; print(sys.prefix)"]
    )

    assert result.returncode == 0, (
        f"Python from the new virtual environment did not run successfully: {NEW_PYTHON}\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert result.stdout == f"{NEW_VENV}\n", (
        "Python must be verified from the new virtual environment, not the old venv "
        "or the system interpreter.\n"
        f"Command: {NEW_PYTHON} -c 'import sys; print(sys.prefix)'\n"
        f"Expected stdout: {str(NEW_VENV)!r} followed by newline\n"
        f"Actual stdout:   {result.stdout!r}\n"
        f"stderr:          {result.stderr!r}"
    )


def test_new_virtual_environment_python_executable_identity_is_new_path() -> None:
    assert_is_file(NEW_PYTHON, "Python executable in new virtual environment")

    result = run_command(
        [str(NEW_PYTHON), "-c", "import sys; print(sys.executable)"]
    )

    assert result.returncode == 0, (
        f"Could not inspect sys.executable using new venv Python: {NEW_PYTHON}\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )

    assert result.stdout.strip() == str(NEW_PYTHON), (
        "The Python executable being verified must be inside the new .venv.\n"
        f"Expected sys.executable: {NEW_PYTHON}\n"
        f"Actual sys.executable:   {result.stdout.strip()!r}"
    )


def test_new_virtual_environment_pip_works_via_python_module() -> None:
    assert_is_file(NEW_PYTHON, "Python executable in new virtual environment")

    result = run_command(
        [str(NEW_PYTHON), "-m", "pip", "--version"]
    )

    assert result.returncode == 0, (
        f"pip is not working from the new virtual environment via "
        f"{NEW_PYTHON} -m pip --version\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert str(NEW_VENV) in result.stdout, (
        "pip --version should report that pip is installed in the new .venv, "
        "not in the old venv or system Python.\n"
        f"Expected stdout to mention: {NEW_VENV}\n"
        f"Actual stdout: {result.stdout!r}"
    )
    assert str(OLD_VENV) not in result.stdout, (
        "pip --version output still mentions the retired old venv, which means "
        "verification may be using stale state.\n"
        f"Old venv path: {OLD_VENV}\n"
        f"Actual stdout: {result.stdout!r}"
    )


def test_new_virtual_environment_pip_executable_runs() -> None:
    assert_is_file(NEW_PIP, "pip executable in new virtual environment")

    result = run_command([str(NEW_PIP), "--version"])

    assert result.returncode == 0, (
        f"The pip executable inside the new virtual environment does not run: {NEW_PIP}\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert str(NEW_VENV) in result.stdout, (
        "The pip executable must belong to the new .venv.\n"
        f"Expected stdout to mention: {NEW_VENV}\n"
        f"Actual stdout: {result.stdout!r}"
    )


def test_envrc_points_exactly_to_new_virtual_environment() -> None:
    assert_is_file(ENVRC, ".envrc pointer file")

    actual = ENVRC.read_text()

    assert actual == EXPECTED_ENVRC, (
        f".envrc must contain exactly one line pointing to the new virtual environment.\n"
        f"Path:     {ENVRC}\n"
        f"Expected: {EXPECTED_ENVRC!r}\n"
        f"Actual:   {actual!r}"
    )
    assert "/home/user/projects/portfolio-site/venv" not in actual, (
        ".envrc still references the retired old virtual environment path.\n"
        f"Actual .envrc contents: {actual!r}"
    )


def test_old_virtual_environment_path_is_retired_and_not_active() -> None:
    if not OLD_VENV.exists():
        return

    assert OLD_VENV.is_dir(), (
        f"The retired old venv path exists but is not a directory: {OLD_VENV}"
    )

    old_python_exists = OLD_PYTHON.exists()
    old_pyvenv_cfg_exists = OLD_PYVENV_CFG.exists()

    assert not (old_python_exists and old_pyvenv_cfg_exists), (
        "The old virtual environment path still appears to be an active Python venv. "
        "It must be removed, renamed, or made inactive. An active venv at the old "
        "path is defined by both of these still existing:\n"
        f"- {OLD_PYTHON}: exists={old_python_exists}\n"
        f"- {OLD_PYVENV_CFG}: exists={old_pyvenv_cfg_exists}"
    )


def test_old_virtual_environment_is_not_the_only_working_environment() -> None:
    assert_is_file(NEW_PYTHON, "Python executable in new virtual environment")
    assert str(NEW_PYTHON).startswith(str(NEW_VENV)), (
        f"New Python path is not inside new venv: {NEW_PYTHON}"
    )

    assert str(NEW_PIP).startswith(str(NEW_VENV)), (
        f"New pip path is not inside new venv: {NEW_PIP}"
    )


def test_verification_log_exists_and_has_exact_five_non_empty_key_value_lines() -> None:
    assert_is_file(LOG, "verification log")

    content = LOG.read_text()
    raw_lines = content.splitlines()

    assert content.endswith("\n"), (
        f"Verification log must end with a newline: {LOG}"
    )

    assert all(line.strip() for line in raw_lines), (
        "Verification log must contain exactly 5 non-empty lines and no blank lines.\n"
        f"Actual lines: {raw_lines!r}"
    )

    assert len(raw_lines) == 5, (
        f"Verification log must contain exactly 5 non-empty lines.\n"
        f"Expected 5 lines, got {len(raw_lines)}.\n"
        f"Actual content: {content!r}"
    )

    for index, line in enumerate(raw_lines, start=1):
        assert "=" in line, (
            f"Verification log line {index} must use KEY=VALUE format, "
            f"but no '=' was found: {line!r}"
        )
        key, value = line.split("=", 1)
        assert key, (
            f"Verification log line {index} has an empty key: {line!r}"
        )
        assert value, (
            f"Verification log line {index} has an empty value: {line!r}"
        )


def test_verification_log_has_required_exact_values_and_key_order() -> None:
    assert_is_file(LOG, "verification log")

    lines = LOG.read_text().splitlines()

    assert len(lines) == 5, (
        f"Verification log must contain exactly 5 lines before checking values; got {len(lines)}"
    )

    expected_keys = [
        "PROJECT_DIR",
        "ACTIVE_ENV",
        "PYTHON_EXE",
        "PIP_EXE",
        "OLD_ENV_STATUS",
    ]
    actual_keys = [line.split("=", 1)[0] for line in lines]

    assert actual_keys == expected_keys, (
        "Verification log keys are not in the required exact order.\n"
        f"Expected keys: {expected_keys!r}\n"
        f"Actual keys:   {actual_keys!r}\n"
        f"Actual lines:  {lines!r}"
    )

    assert lines[:4] == EXPECTED_LOG_PREFIX_LINES, (
        "Verification log must point to the project and the new .venv paths exactly.\n"
        f"Expected first four lines: {EXPECTED_LOG_PREFIX_LINES!r}\n"
        f"Actual first four lines:   {lines[:4]!r}"
    )

    assert lines[4] in ALLOWED_OLD_ENV_STATUS_LINES, (
        "Verification log OLD_ENV_STATUS must show the old environment was retired.\n"
        f"Allowed values: {sorted(ALLOWED_OLD_ENV_STATUS_LINES)!r}\n"
        f"Actual line:    {lines[4]!r}"
    )


def test_verification_log_does_not_reference_old_python_or_old_pip() -> None:
    assert_is_file(LOG, "verification log")

    content = LOG.read_text()

    forbidden_paths = [
        "/home/user/projects/portfolio-site/venv/bin/python",
        "/home/user/projects/portfolio-site/venv/bin/pip",
    ]

    for forbidden in forbidden_paths:
        assert forbidden not in content, (
            "Verification log still mentions a stale executable from the retired old venv.\n"
            f"Forbidden path: {forbidden}\n"
            f"Actual log:     {content!r}"
        )

    assert "OLD_ENV_STATUS=active" not in content, (
        "Verification log still reports OLD_ENV_STATUS=active; the old venv must be retired.\n"
        f"Actual log: {content!r}"
    )


def test_verification_log_paths_match_existing_new_environment_executables() -> None:
    assert_is_file(LOG, "verification log")

    values = {}
    for line in LOG.read_text().splitlines():
        key, value = line.split("=", 1)
        values[key] = value

    assert Path(values["PYTHON_EXE"]) == NEW_PYTHON, (
        f"PYTHON_EXE in log must be exactly {NEW_PYTHON}, got {values['PYTHON_EXE']!r}"
    )
    assert Path(values["PIP_EXE"]) == NEW_PIP, (
        f"PIP_EXE in log must be exactly {NEW_PIP}, got {values['PIP_EXE']!r}"
    )

    assert_is_file(Path(values["PYTHON_EXE"]), "logged Python executable")
    assert_is_file(Path(values["PIP_EXE"]), "logged pip executable")

    assert os.access(values["PYTHON_EXE"], os.X_OK), (
        f"Logged PYTHON_EXE is not executable: {values['PYTHON_EXE']}"
    )
    assert os.access(values["PIP_EXE"], os.X_OK), (
        f"Logged PIP_EXE is not executable: {values['PIP_EXE']}"
    )


def test_logged_old_env_status_matches_final_old_path_state() -> None:
    assert_is_file(LOG, "verification log")

    lines = LOG.read_text().splitlines()
    status_line = lines[4]
    status = status_line.split("=", 1)[1]

    if status == "missing":
        assert not OLD_VENV.exists(), (
            "Verification log says OLD_ENV_STATUS=missing, but the old venv path still exists.\n"
            f"Existing path: {OLD_VENV}"
        )
    elif status == "inactive":
        assert OLD_VENV.exists(), (
            "Verification log says OLD_ENV_STATUS=inactive, but the old venv path is missing. "
            "Use OLD_ENV_STATUS=missing when the path is absent."
        )
        assert not (OLD_PYTHON.exists() and OLD_PYVENV_CFG.exists()), (
            "Verification log says OLD_ENV_STATUS=inactive, but the old venv still has both "
            "bin/python and pyvenv.cfg and therefore still appears active.\n"
            f"{OLD_PYTHON}: exists={OLD_PYTHON.exists()}\n"
            f"{OLD_PYVENV_CFG}: exists={OLD_PYVENV_CFG.exists()}"
        )
    elif status == "renamed":
        assert not OLD_VENV.exists(), (
            "Verification log says OLD_ENV_STATUS=renamed, so the original old venv path "
            f"must no longer exist: {OLD_VENV}"
        )
    else:
        pytest.fail(
            f"Unexpected OLD_ENV_STATUS value in verification log: {status!r}"
        )