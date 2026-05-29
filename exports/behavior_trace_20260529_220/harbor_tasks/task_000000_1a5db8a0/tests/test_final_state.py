# test_final_state.py
import os
import re
import stat
import subprocess
from pathlib import Path


BASE = Path("/home/user/policy-docs-lab")
POLICIES = Path("/home/user/policy-docs-lab/policies")
DOCS = Path("/home/user/policy-docs-lab/docs")
TOOLS = Path("/home/user/policy-docs-lab/tools")

MARKDOWN_PATH = Path("/home/user/policy-docs-lab/docs/policy-lint-summary.md")
LOG_PATH = Path("/home/user/policy-docs-lab/docs/policy-lint-summary.log")
LINTER_PATH = Path("/home/user/policy-docs-lab/tools/markdown_policy_lint.py")

EXPECTED_MARKDOWN = """# Policy Lint Summary

This document summarizes the policy-as-code controls currently enforced in this repository.

## Controls

| Policy File | Control ID | Severity | Enforcement | Summary |
| --- | --- | --- | --- | --- |
| container_registry.yaml | REG-104 | high | deny | Require container images to come from approved registries. |
| iam_mfa.yaml | IAM-201 | critical | deny | Require multi-factor authentication for privileged IAM users. |
| tls_minimum.yaml | TLS-122 | high | warn | Enforce TLS 1.2 or newer for public endpoints. |

## Verification

Generated documentation was checked with the repository Markdown policy linter.
"""

EXPECTED_POLICY_FILES = {
    Path("/home/user/policy-docs-lab/policies/container_registry.yaml"),
    Path("/home/user/policy-docs-lab/policies/iam_mfa.yaml"),
    Path("/home/user/policy-docs-lab/policies/tls_minimum.yaml"),
}

EXPECTED_DOC_FILES = {
    MARKDOWN_PATH,
    LOG_PATH,
}


def read_text_exact(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_regular_file(path: Path) -> None:
    assert path.is_absolute(), f"Test path must be absolute: {path}"
    assert path.exists(), f"Expected file is missing: {path}"
    assert path.is_file(), f"Expected a regular file, but found a different filesystem object: {path}"


def test_required_repository_directories_still_exist():
    for directory in (BASE, POLICIES, DOCS, TOOLS):
        assert directory.is_absolute(), f"Test path must be absolute: {directory}"
        assert directory.exists(), f"Required directory is missing: {directory}"
        assert directory.is_dir(), f"Required path exists but is not a directory: {directory}"


def test_policy_directory_contains_exactly_expected_policy_files():
    assert POLICIES.exists(), f"Policy directory is missing: {POLICIES}"
    actual_files = {path for path in POLICIES.iterdir() if path.is_file()}
    assert actual_files == EXPECTED_POLICY_FILES, (
        "Policy directory does not contain exactly the expected policy files. "
        f"Expected: {sorted(str(path) for path in EXPECTED_POLICY_FILES)}; "
        f"Actual: {sorted(str(path) for path in actual_files)}"
    )


def test_docs_directory_contains_exactly_required_deliverables():
    assert DOCS.exists(), f"Docs directory is missing: {DOCS}"
    actual_files = {path for path in DOCS.iterdir() if path.is_file()}
    assert actual_files == EXPECTED_DOC_FILES, (
        "Docs directory must contain exactly the required Markdown summary and verification log, "
        "with no extra documentation deliverables. "
        f"Expected: {sorted(str(path) for path in EXPECTED_DOC_FILES)}; "
        f"Actual: {sorted(str(path) for path in actual_files)}"
    )


def test_markdown_summary_exists_with_exact_expected_content():
    assert_regular_file(MARKDOWN_PATH)
    actual = read_text_exact(MARKDOWN_PATH)
    assert actual == EXPECTED_MARKDOWN, (
        "Markdown summary content is not exactly correct. It must use the required structure, "
        "include only active spec.control metadata, sort rows by policy filename, and end with "
        "exactly one trailing newline."
    )


def test_markdown_summary_has_single_trailing_newline_and_no_extra_blank_line():
    assert_regular_file(MARKDOWN_PATH)
    data = MARKDOWN_PATH.read_bytes()
    assert data.endswith(b"\n"), (
        f"Markdown summary must end with a trailing newline: {MARKDOWN_PATH}"
    )
    assert not data.endswith(b"\n\n"), (
        f"Markdown summary must end with exactly one trailing newline, not an extra blank line: {MARKDOWN_PATH}"
    )
    assert data == EXPECTED_MARKDOWN.encode("utf-8"), (
        "Markdown summary bytes differ from the expected final document."
    )


def test_markdown_table_uses_authoritative_active_control_values_only():
    assert_regular_file(MARKDOWN_PATH)
    text = read_text_exact(MARKDOWN_PATH)

    expected_rows = [
        "| container_registry.yaml | REG-104 | high | deny | Require container images to come from approved registries. |",
        "| iam_mfa.yaml | IAM-201 | critical | deny | Require multi-factor authentication for privileged IAM users. |",
        "| tls_minimum.yaml | TLS-122 | high | warn | Enforce TLS 1.2 or newer for public endpoints. |",
    ]
    for row in expected_rows:
        assert row in text, f"Missing expected active-control table row: {row}"

    forbidden_non_authoritative_values = [
        "REG-000",
        "Example registry rule only.",
        "IAM-OLD",
        "IAM-010",
        "Demonstration fixture; not an active control.",
        "TLS-099",
        "Legacy TLS check retained for migration notes.",
    ]
    for forbidden in forbidden_non_authoritative_values:
        assert forbidden not in text, (
            "Markdown summary includes a non-authoritative example, label, comment, "
            f"legacy, or fixture value that should not be used: {forbidden!r}"
        )


def test_repository_markdown_linter_exists_and_is_executable():
    assert_regular_file(LINTER_PATH)
    mode = LINTER_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, (
        f"Repository Markdown policy linter is not executable by its owner: {LINTER_PATH}"
    )
    assert os.access(LINTER_PATH, os.X_OK), (
        f"Repository Markdown policy linter is not executable by the current user: {LINTER_PATH}"
    )


def test_repository_markdown_linter_passes_on_final_summary():
    assert_regular_file(MARKDOWN_PATH)
    assert_regular_file(LINTER_PATH)

    result = subprocess.run(
        [str(LINTER_PATH), str(MARKDOWN_PATH)],
        cwd=str(BASE),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        "Repository Markdown policy linter did not pass on the final summary. "
        f"Command: {LINTER_PATH} {MARKDOWN_PATH}\n"
        f"Exit code: {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        "Repository Markdown policy linter should print PASS on success. "
        f"Actual stdout: {result.stdout!r}"
    )


def test_verification_log_exists_with_exact_two_line_shape_and_pass_result():
    assert_regular_file(LOG_PATH)
    content = read_text_exact(LOG_PATH)

    assert content.endswith("\n"), (
        f"Verification log must end with a trailing newline: {LOG_PATH}"
    )
    assert not content.endswith("\n\n"), (
        f"Verification log must end with exactly one trailing newline, not an extra blank line: {LOG_PATH}"
    )

    lines = content.splitlines()
    assert len(lines) == 2, (
        "Verification log must contain exactly two lines: lint_command=... and lint_result=PASS. "
        f"Actual lines: {lines!r}"
    )

    assert lines[0].startswith("lint_command="), (
        "Verification log line 1 must start with 'lint_command='."
    )
    assert lines[1] == "lint_result=PASS", (
        "Verification log line 2 must be exactly 'lint_result=PASS'."
    )


def test_verification_log_command_invokes_repository_linter_against_final_markdown():
    assert_regular_file(LOG_PATH)
    lines = read_text_exact(LOG_PATH).splitlines()
    assert len(lines) == 2, (
        "Cannot validate lint command because verification log does not contain exactly two lines."
    )

    command = lines[0][len("lint_command="):].strip()
    assert command, "Verification log lint_command value must not be empty."

    normalized = re.sub(r"\s+", " ", command)
    assert str(LINTER_PATH) in normalized, (
        "Verification log lint_command must invoke the repository Markdown policy checker. "
        f"Expected command to include: {LINTER_PATH}; actual command: {command!r}"
    )
    assert str(MARKDOWN_PATH) in normalized, (
        "Verification log lint_command must run the checker against the final Markdown file. "
        f"Expected command to include: {MARKDOWN_PATH}; actual command: {command!r}"
    )

    acceptable_patterns = [
        rf"^{re.escape(str(LINTER_PATH))}\s+{re.escape(str(MARKDOWN_PATH))}$",
        rf"^python3\s+{re.escape(str(LINTER_PATH))}\s+{re.escape(str(MARKDOWN_PATH))}$",
        rf"^/usr/bin/env\s+python3\s+{re.escape(str(LINTER_PATH))}\s+{re.escape(str(MARKDOWN_PATH))}$",
    ]
    assert any(re.fullmatch(pattern, normalized) for pattern in acceptable_patterns), (
        "Verification log lint_command must be a direct invocation of the repository linter "
        "against the final Markdown file. Acceptable forms include "
        f"'{LINTER_PATH} {MARKDOWN_PATH}' or "
        f"'python3 {LINTER_PATH} {MARKDOWN_PATH}'. "
        f"Actual command: {command!r}"
    )