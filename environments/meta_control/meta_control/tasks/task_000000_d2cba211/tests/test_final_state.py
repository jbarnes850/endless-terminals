# test_final_state.py
from pathlib import Path
import os


HOME = Path("/home/user")
INPUT_FILE = Path("/home/user/mobile-pipeline.ini")
BUILD_DIR = Path("/home/user/build")
SUMMARY_FILE = Path("/home/user/build/release-summary.tsv")

EXPECTED_INI = """# Mobile release pipeline configuration
# Generated from the shared CI template.

[pipeline]
owner = mobile-build
active_profile = beta
default_track = internal

[profile.alpha]
applicationId = com.example.wallet.alpha
versionName = 3.8.0-alpha.4
versionCode = 38004
track = internal

; The beta profile is the one currently promoted by CI.
[profile.beta]
applicationId = com.example.wallet
versionName = 3.8.0
versionCode = 38017
track = production

[profile.qa]
applicationId = com.example.wallet.qa
versionName = 3.8.0-qa.2
versionCode = 38012
track = beta

[signing]
keystore_alias = ci-release
v1_enabled = true
v2_enabled = true
"""

EXPECTED_HEADER = "profile\tapplicationId\tversionName\tversionCode\ttrack"
EXPECTED_DATA = "beta\tcom.example.wallet\t3.8.0\t38017\tproduction"
EXPECTED_SUMMARY = EXPECTED_HEADER + "\n" + EXPECTED_DATA + "\n"


def test_input_ini_still_exists_and_matches_truth():
    assert INPUT_FILE.exists(), f"Required input INI file is missing: {INPUT_FILE}"
    assert INPUT_FILE.is_file(), f"Required input path exists but is not a regular file: {INPUT_FILE}"
    assert os.access(INPUT_FILE, os.R_OK), f"Required input INI file is not readable: {INPUT_FILE}"

    actual = INPUT_FILE.read_text(encoding="utf-8")
    assert actual == EXPECTED_INI, (
        f"Input INI file was changed or does not match the expected truth data: {INPUT_FILE}. "
        "The release summary must be generated from active_profile=beta and [profile.beta]."
    )


def test_build_directory_exists_and_is_directory():
    assert BUILD_DIR.exists(), (
        f"Build directory was not created: {BUILD_DIR}. "
        "Create /home/user/build before writing the release summary."
    )
    assert BUILD_DIR.is_dir(), (
        f"Build output path exists but is not a directory: {BUILD_DIR}"
    )


def test_release_summary_file_exists_and_is_regular_file():
    assert SUMMARY_FILE.exists(), (
        f"Release summary file is missing: {SUMMARY_FILE}"
    )
    assert SUMMARY_FILE.is_file(), (
        f"Release summary path exists but is not a regular file: {SUMMARY_FILE}"
    )


def test_release_summary_exact_bytes_and_final_newline():
    actual_bytes = SUMMARY_FILE.read_bytes()
    expected_bytes = EXPECTED_SUMMARY.encode("utf-8")

    assert actual_bytes == expected_bytes, (
        f"Release summary contents are not exactly correct: {SUMMARY_FILE}\n"
        "Expected exact UTF-8 bytes including tabs and final newline:\n"
        f"{expected_bytes!r}\n"
        "Actual bytes:\n"
        f"{actual_bytes!r}"
    )


def test_release_summary_has_exactly_two_lines():
    text = SUMMARY_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert len(lines) == 2, (
        f"Release summary must contain exactly two lines, but found {len(lines)} line(s): "
        f"{SUMMARY_FILE}. Actual split lines: {lines!r}"
    )


def test_release_summary_header_line_is_exact():
    lines = SUMMARY_FILE.read_text(encoding="utf-8").splitlines()

    assert lines, f"Release summary is empty: {SUMMARY_FILE}"
    assert lines[0] == EXPECTED_HEADER, (
        "Header line is incorrect. It must be exactly tab-separated with columns in this order:\n"
        f"{EXPECTED_HEADER!r}\n"
        f"Actual header:\n{lines[0]!r}"
    )


def test_release_summary_data_line_is_exact_beta_profile_only():
    lines = SUMMARY_FILE.read_text(encoding="utf-8").splitlines()

    assert len(lines) >= 2, (
        f"Release summary is missing the data line for active profile beta: {SUMMARY_FILE}"
    )
    assert lines[1] == EXPECTED_DATA, (
        "Data line is incorrect. It must use values from [profile.beta], the active profile, "
        "not [profile.alpha] or any other section.\n"
        f"Expected:\n{EXPECTED_DATA!r}\n"
        f"Actual:\n{lines[1]!r}"
    )


def test_release_summary_uses_real_tabs_no_extra_columns_or_spaces():
    text = SUMMARY_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert "\\t" not in text, (
        "Release summary contains literal backslash-t characters instead of real tab separators."
    )

    assert len(lines) == 2, (
        f"Cannot validate columns because summary should have exactly two lines, found {len(lines)}."
    )

    for line_number, line in enumerate(lines, start=1):
        assert not line.startswith(" "), (
            f"Line {line_number} has leading space, which is not allowed: {line!r}"
        )
        assert not line.endswith(" "), (
            f"Line {line_number} has trailing space, which is not allowed: {line!r}"
        )

        columns = line.split("\t")
        assert len(columns) == 5, (
            f"Line {line_number} must have exactly 5 tab-separated columns, "
            f"but found {len(columns)} columns: {columns!r}"
        )

        for column_number, value in enumerate(columns, start=1):
            assert value == value.strip(), (
                f"Line {line_number}, column {column_number} contains surrounding whitespace: {value!r}"
            )


def test_release_summary_did_not_use_alpha_or_qa_profile_values():
    text = SUMMARY_FILE.read_text(encoding="utf-8")

    forbidden_values = [
        "alpha",
        "com.example.wallet.alpha",
        "3.8.0-alpha.4",
        "38004",
        "internal",
        "qa",
        "com.example.wallet.qa",
        "3.8.0-qa.2",
        "38012",
    ]

    present = [value for value in forbidden_values if value in text]
    assert not present, (
        "Release summary appears to include values from a non-active profile. "
        "Only [profile.beta] values are allowed. Unexpected value(s): "
        + ", ".join(repr(value) for value in present)
    )