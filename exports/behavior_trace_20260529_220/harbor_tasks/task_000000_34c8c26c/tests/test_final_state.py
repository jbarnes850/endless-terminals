# test_final_state.py
from pathlib import Path
import os
import stat

PROJECT = Path("/home/user/docs_project")
SOURCE_DIR = Path("/home/user/docs_project/source")
PUBLIC_DIR = Path("/home/user/docs_project/public")
CHECKS_DIR = Path("/home/user/docs_project/checks")

SOURCE_FILE = Path("/home/user/docs_project/source/getting-started.md")
LINK_PATH = Path("/home/user/docs_project/public/start-here.md")
REPORT_PATH = Path("/home/user/docs_project/checks/link-report.txt")

EXPECTED_TARGET = "/home/user/docs_project/source/getting-started.md"
EXPECTED_REPORT_WITH_NEWLINE = (
    b"link_path=/home/user/docs_project/public/start-here.md\n"
    b"is_symlink=yes\n"
    b"target=/home/user/docs_project/source/getting-started.md\n"
)
EXPECTED_REPORT_WITHOUT_NEWLINE = EXPECTED_REPORT_WITH_NEWLINE.rstrip(b"\n")

EXPECTED_SOURCE_CONTENT = (
    "# Getting Started\n"
    "\n"
    "Welcome to the Widget Docs.\n"
    "\n"
    "Follow the installation guide before running examples.\n"
)


def test_required_project_directories_still_exist():
    for path in (PROJECT, SOURCE_DIR, PUBLIC_DIR, CHECKS_DIR):
        assert path.exists(), f"Required directory is missing: {path}"
        assert path.is_dir(), f"Required path exists but is not a directory: {path}"


def test_canonical_source_file_still_exists_and_is_unchanged():
    assert SOURCE_FILE.exists(), f"Canonical source file is missing: {SOURCE_FILE}"
    assert SOURCE_FILE.is_file(), (
        f"Canonical source path exists but is not a regular file: {SOURCE_FILE}"
    )

    actual = SOURCE_FILE.read_text(encoding="utf-8")
    assert actual == EXPECTED_SOURCE_CONTENT, (
        "Canonical source file content was changed or corrupted.\n"
        f"Path: {SOURCE_FILE}\n"
        f"Expected: {EXPECTED_SOURCE_CONTENT!r}\n"
        f"Actual:   {actual!r}"
    )


def test_public_start_here_exists_and_is_real_symbolic_link():
    assert os.path.lexists(LINK_PATH), (
        f"Published documentation link is missing: {LINK_PATH}"
    )

    lstat_result = os.lstat(LINK_PATH)
    assert stat.S_ISLNK(lstat_result.st_mode), (
        f"{LINK_PATH} must be a real symbolic link. "
        "It is not acceptable for this path to be a copied regular file, "
        "directory, hard link, or any other file type."
    )


def test_public_start_here_symlink_target_is_exact_absolute_path():
    assert os.path.lexists(LINK_PATH), (
        f"Cannot inspect symlink target because link path is missing: {LINK_PATH}"
    )
    assert LINK_PATH.is_symlink(), (
        f"Cannot inspect required symlink target because path is not a symlink: {LINK_PATH}"
    )

    actual_target = os.readlink(LINK_PATH)
    assert actual_target == EXPECTED_TARGET, (
        "Symlink target is incorrect.\n"
        f"Path: {LINK_PATH}\n"
        f"Expected exact absolute target: {EXPECTED_TARGET!r}\n"
        f"Actual target from readlink: {actual_target!r}\n"
        "The target must be the absolute source path, not a relative path."
    )


def test_public_start_here_resolves_to_canonical_source_file():
    assert LINK_PATH.is_symlink(), (
        f"Cannot verify resolved link destination because path is not a symlink: {LINK_PATH}"
    )

    resolved_link = LINK_PATH.resolve(strict=True)
    resolved_source = SOURCE_FILE.resolve(strict=True)
    assert resolved_link == resolved_source, (
        "Symlink does not resolve to the canonical source file.\n"
        f"Link path: {LINK_PATH}\n"
        f"Resolved link destination: {resolved_link}\n"
        f"Expected canonical source: {resolved_source}"
    )


def test_report_exists_as_regular_file_not_symlink():
    assert REPORT_PATH.exists(), f"Verification report is missing: {REPORT_PATH}"

    lstat_result = os.lstat(REPORT_PATH)
    assert stat.S_ISREG(lstat_result.st_mode), (
        f"Verification report must be a regular file, not a symlink or other type: {REPORT_PATH}"
    )
    assert REPORT_PATH.is_file(), (
        f"Verification report path exists but is not a regular file: {REPORT_PATH}"
    )


def test_report_has_exact_required_three_line_content():
    assert REPORT_PATH.exists(), f"Verification report is missing: {REPORT_PATH}"

    actual = REPORT_PATH.read_bytes()
    acceptable = {EXPECTED_REPORT_WITH_NEWLINE, EXPECTED_REPORT_WITHOUT_NEWLINE}

    assert actual in acceptable, (
        "Verification report content is incorrect.\n"
        f"Path: {REPORT_PATH}\n"
        "Expected exactly these three lines, with at most one trailing newline after "
        "the third line and no extra blank lines or commentary:\n"
        f"{EXPECTED_REPORT_WITH_NEWLINE!r}\n"
        f"Actual bytes:\n{actual!r}"
    )


def test_report_claims_match_actual_filesystem_state():
    assert LINK_PATH.is_symlink(), (
        f"Report cannot be considered valid because required symlink is missing or not a symlink: {LINK_PATH}"
    )
    actual_target = os.readlink(LINK_PATH)
    assert actual_target == EXPECTED_TARGET, (
        f"Report cannot be considered valid because actual symlink target is {actual_target!r}, "
        f"not {EXPECTED_TARGET!r}."
    )

    actual_report = REPORT_PATH.read_bytes()
    assert actual_report in {EXPECTED_REPORT_WITH_NEWLINE, EXPECTED_REPORT_WITHOUT_NEWLINE}, (
        "Report does not exactly document the required final symlink state."
    )