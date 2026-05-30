# test_final_state.py
import json
from pathlib import Path

ROOT = Path("/home/user/site-admin-release")

EXPECTED_PACKAGE_TEXT = """{
  "name": "site-admin-accounts",
  "version": "2.5.0",
  "description": "Administrative tools for website user account lifecycle management",
  "private": true,
  "scripts": {
    "test": "python3 tools/check_release.py"
  }
}
"""

EXPECTED_CHANGELOG_TEXT = """# Changelog

## [2.5.0] - 2026-05-29

### Added
- bulk-suspend: Add CSV-driven suspension workflow for dormant accounts
- roles: Preview permission changes before saving role edits

### Fixed
- email-normalization: Match user emails case-insensitively during lookup

### Security
- password-reset: Record admin identity when issuing reset links

### Changed
- runbook: Document locked-account escalation steps

## [2.4.9] - 2026-04-18

### Fixed
- sessions: Stop extending admin sessions after account suspension

### Security
- password-reset: Reduce reset token reuse window

## [2.4.8] - 2026-03-02

### Changed
- exports: Include account status in monthly compliance export
"""

EXPECTED_AUDIT_TEXT = """package_version=2.5.0
changelog_version=2.5.0
change_records=5
highest_bump=minor
verified=true
"""

EXPECTED_CHANGE_RECORDS = {
    ROOT / "changes" / "001-feature-bulk-suspend.txt": """type: feature
scope: bulk-suspend
summary: Add CSV-driven suspension workflow for dormant accounts
ticket: ADMIN-1842
""",
    ROOT / "changes" / "002-security-reset-audit.txt": """type: security
scope: password-reset
summary: Record admin identity when issuing reset links
ticket: ADMIN-1851
""",
    ROOT / "changes" / "003-fix-email-case.txt": """type: fix
scope: email-normalization
summary: Match user emails case-insensitively during lookup
ticket: ADMIN-1854
""",
    ROOT / "changes" / "004-chore-runbook.txt": """type: chore
scope: runbook
summary: Document locked-account escalation steps
ticket: OPS-911
""",
    ROOT / "changes" / "005-feature-role-preview.txt": """type: feature
scope: roles
summary: Preview permission changes before saving role edits
ticket: ADMIN-1860
""",
}


def read_utf8(path: Path) -> str:
    assert path.is_file(), f"Missing required file: {path}"
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"File is not valid UTF-8 text: {path}: {exc}") from exc


def assert_file_exact(path: Path, expected: str, description: str) -> None:
    actual = read_utf8(path)
    assert actual == expected, (
        f"{description} is not exactly correct: {path}\n"
        f"Expected exactly:\n{expected!r}\n"
        f"Actual:\n{actual!r}"
    )


def test_required_release_artifacts_exist():
    required_files = [
        ROOT / "package.json",
        ROOT / "CHANGELOG.md",
        ROOT / "release_audit.log",
    ]
    for path in required_files:
        assert path.is_file(), f"Missing required final artifact: {path}"


def test_package_json_has_exact_expected_final_state_and_valid_json():
    path = ROOT / "package.json"
    assert_file_exact(
        path,
        EXPECTED_PACKAGE_TEXT,
        "package.json final contents",
    )

    try:
        parsed = json.loads(read_utf8(path))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"package.json is not valid JSON after release update: {path}: {exc}") from exc

    assert parsed.get("version") == "2.5.0", (
        "package.json version is wrong. The change records require a minor bump "
        "from 2.4.9 to 2.5.0 because feature records are present and no record "
        f"is breaking; got {parsed.get('version')!r}."
    )

    assert parsed == {
        "name": "site-admin-accounts",
        "version": "2.5.0",
        "description": "Administrative tools for website user account lifecycle management",
        "private": True,
        "scripts": {
            "test": "python3 tools/check_release.py",
        },
    }, "package.json should only have the version field changed from the initial metadata."


def test_changelog_exact_final_contents():
    assert_file_exact(
        ROOT / "CHANGELOG.md",
        EXPECTED_CHANGELOG_TEXT,
        "CHANGELOG.md final contents",
    )


def test_changelog_top_release_section_is_semantically_correct():
    changelog = read_utf8(ROOT / "CHANGELOG.md")
    lines = changelog.splitlines()

    assert lines[:3] == ["# Changelog", "", "## [2.5.0] - 2026-05-29"], (
        "The first changelog section must appear directly below '# Changelog' "
        "and must be exactly '## [2.5.0] - 2026-05-29'."
    )

    previous_header = "\n## [2.4.9] - 2026-04-18"
    assert previous_header in changelog, "Existing 2.4.9 changelog section is missing."
    new_section = changelog.split(previous_header, 1)[0]

    expected_new_section = """# Changelog

## [2.5.0] - 2026-05-29

### Added
- bulk-suspend: Add CSV-driven suspension workflow for dormant accounts
- roles: Preview permission changes before saving role edits

### Fixed
- email-normalization: Match user emails case-insensitively during lookup

### Security
- password-reset: Record admin identity when issuing reset links

### Changed
- runbook: Document locked-account escalation steps
"""
    assert new_section == expected_new_section, (
        "The new top changelog section has incorrect version, date, category order, "
        "blank lines, bullet text, or alphabetic ordering."
    )

    category_lines = [line for line in new_section.splitlines() if line.startswith("### ")]
    assert category_lines == ["### Added", "### Fixed", "### Security", "### Changed"], (
        "The new changelog section must contain exactly these category headings in order: "
        "Added, Fixed, Security, Changed. "
        f"Got: {category_lines!r}"
    )

    assert "## [2.4.10] - 2026-05-29" not in changelog, (
        "Found invalid patch-bump release 2.4.10 in CHANGELOG.md. "
        "The correct feature-driven minor release is 2.5.0."
    )


def test_existing_changelog_sections_preserved_below_new_release():
    changelog = read_utf8(ROOT / "CHANGELOG.md")
    marker = "## [2.4.9] - 2026-04-18"
    assert marker in changelog, "The previous 2.4.9 changelog section must remain below the new release."

    preserved_tail = changelog[changelog.index(marker):]
    expected_tail = """## [2.4.9] - 2026-04-18

### Fixed
- sessions: Stop extending admin sessions after account suspension

### Security
- password-reset: Reduce reset token reuse window

## [2.4.8] - 2026-03-02

### Changed
- exports: Include account status in monthly compliance export
"""
    assert preserved_tail == expected_tail, (
        "Older changelog content below the new 2.5.0 section was not preserved exactly."
    )


def test_release_audit_log_exact_final_contents_and_format():
    path = ROOT / "release_audit.log"
    actual = read_utf8(path)
    assert actual == EXPECTED_AUDIT_TEXT, (
        "release_audit.log is incorrect. It must contain exactly five newline-terminated "
        "key/value lines reflecting the verified final release 2.5.0.\n"
        f"Expected exactly:\n{EXPECTED_AUDIT_TEXT!r}\n"
        f"Actual:\n{actual!r}"
    )

    lines = actual.splitlines()
    assert len(lines) == 5, f"release_audit.log must contain exactly five lines, got {len(lines)}."
    for line in lines:
        assert "=" in line, f"Audit log line is not in key=value format: {line!r}"
        key, value = line.split("=", 1)
        assert key, f"Audit log line has an empty key: {line!r}"
        assert value, f"Audit log line has an empty value: {line!r}"

    assert actual.endswith("\n"), "release_audit.log must be newline-terminated."


def test_all_original_change_records_still_exist_and_are_unchanged():
    for path, expected in EXPECTED_CHANGE_RECORDS.items():
        assert_file_exact(path, expected, "change-record file")

    actual_txt_files = sorted((ROOT / "changes").glob("*.txt"))
    expected_txt_files = sorted(EXPECTED_CHANGE_RECORDS)
    assert actual_txt_files == expected_txt_files, (
        "The changes directory must still contain exactly the five original staged "
        "change-record .txt files; do not delete or rename them.\n"
        f"Expected: {expected_txt_files}\n"
        f"Actual: {actual_txt_files}"
    )


def test_final_release_metadata_is_consistent_across_artifacts():
    package = json.loads(read_utf8(ROOT / "package.json"))
    changelog = read_utf8(ROOT / "CHANGELOG.md")
    audit = read_utf8(ROOT / "release_audit.log")

    assert package["version"] == "2.5.0", "package.json must describe release 2.5.0."
    assert changelog.startswith("# Changelog\n\n## [2.5.0] - 2026-05-29\n"), (
        "CHANGELOG.md must have release 2.5.0 as the top section."
    )
    assert "package_version=2.5.0\n" in audit, "Audit log package_version must be 2.5.0."
    assert "changelog_version=2.5.0\n" in audit, "Audit log changelog_version must be 2.5.0."
    assert "change_records=5\n" in audit, "Audit log must report all five change records were processed."
    assert "highest_bump=minor\n" in audit, (
        "Audit log must report highest_bump=minor because feature records require "
        "a minor bump and no change record is breaking."
    )
    assert audit.endswith("verified=true\n"), "Audit log must end with verified=true after final verification."