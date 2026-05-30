# test_final_state.py

from pathlib import Path
import csv
import io

import pytest


RAW_LEGACY_FILE = Path("/home/user/analyst_workspace/raw/customer_export_legacy.csv")
CANONICAL_FILE = Path("/home/user/analyst_workspace/processed/customer_contact_canonical.csv")
VERIFY_LOG = Path("/home/user/analyst_workspace/processed/customer_contact_canonical.verify.log")
RETIRED_LEGACY_FILE = Path("/home/user/analyst_workspace/archive/customer_export_legacy.csv.retired")

EXPECTED_CANONICAL_CONTENT = (
    "customer_id,email,signup_date,region\n"
    "C-1007,linh.nguyen@example.net,2023-08-14,EMEA\n"
    "C-1012,arjun.patel@example.net,2022-11-03,NA\n"
    "C-1020,mina.okafor@example.net,2024-01-27,APAC\n"
    "C-1033,renata.silva@example.net,2023-05-09,LATAM\n"
)

EXPECTED_RETIRED_LEGACY_CONTENT = (
    "region,customer_id,last_name,email,signup_date,plan\n"
    "EMEA,C-1007,Nguyen,linh.nguyen@example.net,2023-08-14,pro\n"
    "NA,C-1012,Patel,arjun.patel@example.net,2022-11-03,basic\n"
    "APAC,C-1020,Okafor,mina.okafor@example.net,2024-01-27,enterprise\n"
    "LATAM,C-1033,Silva,renata.silva@example.net,2023-05-09,pro\n"
)

EXPECTED_VERIFY_LOG_CONTENT = (
    "canonical_path=/home/user/analyst_workspace/processed/customer_contact_canonical.csv\n"
    "canonical_rows=5\n"
    "legacy_path_retired=yes\n"
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        pytest.fail(f"Expected file is missing: {path}")


def test_original_raw_legacy_path_has_been_retired_and_no_longer_exists():
    assert not RAW_LEGACY_FILE.exists(), (
        "The original legacy CSV path still exists, but it must be retired by moving it away.\n"
        f"Stale path that must be absent: {RAW_LEGACY_FILE}"
    )


def test_canonical_csv_exists_at_exact_processed_path():
    assert CANONICAL_FILE.exists(), (
        "Canonical processed CSV was not created at the required absolute path.\n"
        f"Expected path: {CANONICAL_FILE}"
    )
    assert CANONICAL_FILE.is_file(), (
        "Canonical processed CSV path exists but is not a regular file.\n"
        f"Path: {CANONICAL_FILE}"
    )


def test_canonical_csv_has_exact_expected_contents():
    actual = _read_text(CANONICAL_FILE)
    assert actual == EXPECTED_CANONICAL_CONTENT, (
        "Canonical CSV contents are not exactly correct. It must contain only the four required "
        "columns in the order customer_id,email,signup_date,region, preserve all rows, and have "
        "no extra spaces, quotes, columns, or blank lines.\n"
        f"Path checked: {CANONICAL_FILE}"
    )


def test_canonical_csv_is_valid_four_column_csv_with_expected_rows():
    actual = _read_text(CANONICAL_FILE)

    assert actual.endswith("\n"), (
        "Canonical CSV should end with exactly the expected final newline and no missing trailing newline.\n"
        f"Path checked: {CANONICAL_FILE}"
    )

    lines = actual.splitlines()
    assert len(lines) == 5, (
        "Canonical CSV must have exactly 5 lines including the header.\n"
        f"Actual line count: {len(lines)}\n"
        f"Path checked: {CANONICAL_FILE}"
    )

    rows = list(csv.reader(io.StringIO(actual), strict=True))
    expected_rows = [
        ["customer_id", "email", "signup_date", "region"],
        ["C-1007", "linh.nguyen@example.net", "2023-08-14", "EMEA"],
        ["C-1012", "arjun.patel@example.net", "2022-11-03", "NA"],
        ["C-1020", "mina.okafor@example.net", "2024-01-27", "APAC"],
        ["C-1033", "renata.silva@example.net", "2023-05-09", "LATAM"],
    ]

    assert rows == expected_rows, (
        "Canonical CSV parsed rows are incorrect. The file must be derived from the legacy CSV "
        "using columns customer_id, email, signup_date, region in that exact order.\n"
        f"Path checked: {CANONICAL_FILE}"
    )

    bad_widths = [(index + 1, len(row), row) for index, row in enumerate(rows) if len(row) != 4]
    assert not bad_widths, (
        "Canonical CSV must contain exactly 4 comma-separated columns on every row.\n"
        f"Rows with wrong column counts: {bad_widths}\n"
        f"Path checked: {CANONICAL_FILE}"
    )


def test_retired_legacy_file_exists_at_exact_archive_path():
    assert RETIRED_LEGACY_FILE.exists(), (
        "Retired legacy CSV is missing from the required archive path. The legacy file should "
        "have been moved, not merely copied or left in raw.\n"
        f"Expected retired path: {RETIRED_LEGACY_FILE}"
    )
    assert RETIRED_LEGACY_FILE.is_file(), (
        "Retired legacy CSV path exists but is not a regular file.\n"
        f"Path: {RETIRED_LEGACY_FILE}"
    )


def test_retired_legacy_file_preserves_original_contents_exactly():
    actual = _read_text(RETIRED_LEGACY_FILE)
    assert actual == EXPECTED_RETIRED_LEGACY_CONTENT, (
        "Retired legacy CSV contents do not exactly match the original six-column legacy export. "
        "The archive copy must preserve the original file exactly.\n"
        f"Path checked: {RETIRED_LEGACY_FILE}"
    )


def test_verification_log_exists_at_exact_processed_path():
    assert VERIFY_LOG.exists(), (
        "Verification log was not created at the required processed path.\n"
        f"Expected path: {VERIFY_LOG}"
    )
    assert VERIFY_LOG.is_file(), (
        "Verification log path exists but is not a regular file.\n"
        f"Path: {VERIFY_LOG}"
    )


def test_verification_log_has_exact_expected_contents():
    actual = _read_text(VERIFY_LOG)
    assert actual == EXPECTED_VERIFY_LOG_CONTENT, (
        "Verification log contents are not exactly correct. It must contain exactly the required "
        "three lines with canonical_rows=5 and legacy_path_retired=yes.\n"
        f"Path checked: {VERIFY_LOG}"
    )


def test_verification_log_values_match_final_filesystem_state():
    actual = _read_text(VERIFY_LOG)
    lines = actual.splitlines()

    assert lines == [
        "canonical_path=/home/user/analyst_workspace/processed/customer_contact_canonical.csv",
        "canonical_rows=5",
        "legacy_path_retired=yes",
    ], (
        "Verification log must contain exactly three lines in the required order and with values "
        "computed from the final filesystem state.\n"
        f"Actual lines: {lines!r}\n"
        f"Path checked: {VERIFY_LOG}"
    )

    canonical_line_count = len(_read_text(CANONICAL_FILE).splitlines())
    assert canonical_line_count == 5, (
        "The verification log reports canonical_rows=5, but the canonical CSV does not actually "
        "have exactly 5 lines.\n"
        f"Actual canonical line count: {canonical_line_count}\n"
        f"Canonical path checked: {CANONICAL_FILE}"
    )

    retired_state_is_yes = (not RAW_LEGACY_FILE.exists()) and RETIRED_LEGACY_FILE.exists()
    assert retired_state_is_yes, (
        "The verification log must report legacy_path_retired=yes only when the raw legacy path "
        "is gone and the retired archive file exists. The final filesystem state does not satisfy this.\n"
        f"Raw legacy path exists: {RAW_LEGACY_FILE.exists()} ({RAW_LEGACY_FILE})\n"
        f"Retired legacy path exists: {RETIRED_LEGACY_FILE.exists()} ({RETIRED_LEGACY_FILE})"
    )