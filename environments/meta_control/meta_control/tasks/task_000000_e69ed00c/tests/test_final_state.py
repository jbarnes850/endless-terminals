# test_final_state.py
import os
import subprocess
from pathlib import Path

import pytest


BASE = Path("/home/user/dbadmin_link_lab")
ACTIVE = Path("/home/user/dbadmin_link_lab/active")
HELPER = Path("/home/user/dbadmin_link_lab/bin/check_active_links.py")
REPORT = Path("/home/user/dbadmin_link_lab/active/link_verification_report.txt")

EXPECTED_LINKS = {
    Path("/home/user/dbadmin_link_lab/active/current_schema.sql"): {
        "target_text": "../workloads/checkout/sql/schema.sql",
        "resolved": Path("/home/user/dbadmin_link_lab/workloads/checkout/sql/schema.sql"),
    },
    Path("/home/user/dbadmin_link_lab/active/current_stats.json"): {
        "target_text": "../workloads/checkout/stats/pg_stats_snapshot.json",
        "resolved": Path("/home/user/dbadmin_link_lab/workloads/checkout/stats/pg_stats_snapshot.json"),
    },
    Path("/home/user/dbadmin_link_lab/active/current_queries.sql"): {
        "target_text": "../workloads/checkout/sql/candidate_queries.sql",
        "resolved": Path("/home/user/dbadmin_link_lab/workloads/checkout/sql/candidate_queries.sql"),
    },
    Path("/home/user/dbadmin_link_lab/active/tuning_notes.md"): {
        "target_text": "../shared/dba_tuning_notes.md",
        "resolved": Path("/home/user/dbadmin_link_lab/shared/dba_tuning_notes.md"),
    },
}

EXPECTED_REPORT_TEXT = """link_verification_report
current_schema.sql -> ../workloads/checkout/sql/schema.sql
current_stats.json -> ../workloads/checkout/stats/pg_stats_snapshot.json
current_queries.sql -> ../workloads/checkout/sql/candidate_queries.sql
tuning_notes.md -> ../shared/dba_tuning_notes.md
check_active_links.py: PASS
verified: yes
"""

EXPECTED_SOURCE_CONTENTS = {
    Path("/home/user/dbadmin_link_lab/workloads/checkout/sql/schema.sql"): """-- workload: checkout
CREATE TABLE checkout_orders (
    order_id bigint PRIMARY KEY,
    customer_id bigint NOT NULL,
    created_at timestamp NOT NULL,
    status text NOT NULL
);

CREATE INDEX checkout_orders_customer_created_idx
    ON checkout_orders (customer_id, created_at DESC);
""",
    Path("/home/user/dbadmin_link_lab/workloads/checkout/stats/pg_stats_snapshot.json"): """{
  "workload": "checkout",
  "captured_at": "2024-05-17T10:15:00Z",
  "tables": {
    "checkout_orders": {
      "rows": 1842500,
      "dead_tuple_percent": 2.7
    }
  }
}
""",
    Path("/home/user/dbadmin_link_lab/workloads/checkout/sql/candidate_queries.sql"): """-- checkout candidate queries
EXPLAIN (ANALYZE, BUFFERS)
SELECT order_id, created_at, status
FROM checkout_orders
WHERE customer_id = $1
ORDER BY created_at DESC
LIMIT 20;
""",
    Path("/home/user/dbadmin_link_lab/shared/dba_tuning_notes.md"): """# DBA Tuning Notes

- Prefer workload-specific schema, stats, and candidate query files.
- Keep active pointers as relative symbolic links.
- Re-run the active link checker after every rotation.
""",
}


def test_required_base_active_and_helper_paths_exist():
    assert BASE.exists(), f"Missing lab base directory: {BASE}"
    assert BASE.is_dir(), f"Lab base path is not a directory: {BASE}"

    assert ACTIVE.exists(), f"Missing active directory: {ACTIVE}"
    assert ACTIVE.is_dir(), f"Active path is not a directory: {ACTIVE}"

    assert HELPER.exists(), f"Missing verification helper: {HELPER}"
    assert HELPER.is_file(), f"Verification helper is not a regular file: {HELPER}"


@pytest.mark.parametrize("path, expectation", EXPECTED_LINKS.items())
def test_active_entries_are_relative_symlinks_with_exact_target_text(path, expectation):
    assert path.is_symlink(), (
        f"{path} must be a symbolic link in the final state. "
        "It is missing or is still a regular file/directory."
    )

    actual_target = os.readlink(path)
    expected_target = expectation["target_text"]

    assert actual_target == expected_target, (
        f"{path} has the wrong symlink target text. "
        f"Expected exactly {expected_target!r}, but found {actual_target!r}."
    )

    assert not os.path.isabs(actual_target), (
        f"{path} must use a relative symlink target, but found absolute target "
        f"{actual_target!r}."
    )


@pytest.mark.parametrize("path, expectation", EXPECTED_LINKS.items())
def test_active_symlinks_resolve_to_intended_checkout_or_shared_sources(path, expectation):
    assert path.is_symlink(), f"{path} must be a symlink before target resolution can be checked."

    target_text = os.readlink(path)
    resolved = (path.parent / target_text).resolve()
    expected_resolved = expectation["resolved"].resolve()

    assert resolved == expected_resolved, (
        f"{path} resolves to the wrong file. "
        f"Target text is {target_text!r}; resolved to {resolved}, "
        f"but expected {expected_resolved}."
    )

    assert resolved.exists(), (
        f"{path} resolves to {resolved}, but that target file does not exist."
    )
    assert resolved.is_file(), (
        f"{path} resolves to {resolved}, but that target is not a regular file."
    )


@pytest.mark.parametrize("source_path, expected_content", EXPECTED_SOURCE_CONTENTS.items())
def test_expected_source_files_still_exist_with_original_contents(source_path, expected_content):
    assert source_path.exists(), f"Required source file is missing: {source_path}"
    assert source_path.is_file(), f"Required source path is not a regular file: {source_path}"
    actual_content = source_path.read_text()
    assert actual_content == expected_content, (
        f"Source file {source_path} does not contain the expected original content. "
        "The active symlinks should point to these source files, not replace or alter them."
    )


def test_verification_helper_succeeds_in_final_state():
    assert HELPER.exists(), f"Cannot run missing verification helper: {HELPER}"
    assert HELPER.is_file(), f"Verification helper is not a regular file: {HELPER}"

    result = subprocess.run(
        [str(HELPER)],
        cwd=str(BASE),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )

    assert result.returncode == 0, (
        f"Verification helper {HELPER} failed with exit code {result.returncode}.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_link_verification_report_exists_as_regular_file_not_symlink():
    assert REPORT.exists(), f"Missing final report file: {REPORT}"
    assert not REPORT.is_symlink(), f"Final report must be a regular file, not a symlink: {REPORT}"
    assert REPORT.is_file(), f"Final report path is not a regular file: {REPORT}"


def test_link_verification_report_matches_exact_required_contents():
    assert REPORT.exists(), f"Missing final report file: {REPORT}"

    actual_bytes = REPORT.read_bytes()
    expected_bytes = EXPECTED_REPORT_TEXT.encode()

    assert actual_bytes == expected_bytes, (
        f"Final report {REPORT} does not match the required byte-for-byte contents.\n"
        f"Expected:\n{EXPECTED_REPORT_TEXT!r}\n"
        f"Actual:\n{actual_bytes.decode(errors='replace')!r}"
    )


def test_link_verification_report_has_exactly_seven_lines_and_no_extra_blank_lines():
    assert REPORT.exists(), f"Missing final report file: {REPORT}"

    actual_text = REPORT.read_text()
    lines = actual_text.splitlines()

    assert len(lines) == 7, (
        f"Final report {REPORT} must contain exactly 7 lines, but contains "
        f"{len(lines)} lines: {lines!r}"
    )

    assert lines == EXPECTED_REPORT_TEXT.splitlines(), (
        f"Final report {REPORT} has incorrect line contents or order. "
        f"Expected lines {EXPECTED_REPORT_TEXT.splitlines()!r}, but found {lines!r}."
    )

    assert all(line != "" for line in lines), (
        f"Final report {REPORT} must not contain extra blank lines, but found lines {lines!r}."
    )

    assert actual_text.endswith("\n"), (
        f"Final report {REPORT} should end with a single trailing newline."
    )
    assert not actual_text.endswith("\n\n"), (
        f"Final report {REPORT} must not contain an extra blank line at the end."
    )