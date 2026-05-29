# test_final_state.py
from pathlib import Path
import os

WORKSPACE = Path("/home/user/workspace/policy-envcheck")
AUDIT_DIR = Path("/home/user/workspace/policy-envcheck/audit")
REPORT_FILE = Path("/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt")
ENV_FILE = Path("/home/user/workspace/policy-envcheck/config/.env.release")
POLICY_FILE = Path("/home/user/workspace/policy-envcheck/policy/required-env.txt")

EXPECTED_REPORT = """DOTENV POLICY REPORT
workspace=/home/user/workspace/policy-envcheck
env_file=/home/user/workspace/policy-envcheck/config/.env.release
policy_file=/home/user/workspace/policy-envcheck/policy/required-env.txt
status=FAIL
missing_required_count=1
forbidden_present_count=2
duplicate_key_count=1
parse_error_count=3
[missing_required]
REDIS_URL
[forbidden_present]
AWS_SECRET_ACCESS_KEY
DEBUG
[duplicate_keys]
API_TOKEN=2
[parse_errors]
line 17: BAD-KEY=value
line 18: UNFINISHED_QUOTE="abc
line 19: TRAILING_SPACE = not-valid-key-because-space-before-equals
[effective_values_sha256]
ALLOWED_ORIGINS=6dddb702c9f2cc3eb6b42cb9f6467b30bbd54b34e89da867ff86d8c3ff903fad
APP_ENV=ab8e18ef4d96e5697ac8ac41d0275c43e506f3f85329e32e05085d4d18cb6296
API_TOKEN=090bfe1078c334bc392e40bc8b878e56bbf751a69f2641d93900a0393487c893
API_URL=fe010740eb06f5d8dbe343941ee73034dc8f5341a8c0815a4ec15cde58fa7e7f
AWS_SECRET_ACCESS_KEY=64dd9bfde5a38c7939964a0483a489f4ba5e3b7c628a249cfa7ca45a6c732699
CACHE_TTL=983bd614bb5afece5ab3b60250459f96b5c6a85c3c064011d46f897b26e3f64f
DB_HOST=2269b93a5c90ec3d09ba8759507405cc7173b1a426472d81f29bd86fd4a8e8f3
DB_PASSWORD=34c1b87fc0389e3f0efc534a0187f22b77462aed5f2be6d50fcb6ebdf8f7fd35
DB_PORT=91a73fd806ab2c097c981f4e6dcf5030a11d10f7b92d42f9cdcc0049e8d0a75d
DB_USER=02e39c817f0df168d326cc8dc74b715bd7843b37d9aa4f148231c4d1de2ebc3e
DEBUG=fcbcf165908dd18a9b8568cdc0d01f179653bed5c0aef603b4d25c1251b6d49a
EMPTY_VALUE=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
ESCAPED_VALUE=8f1697d4ebf89cb99ac35350b1de86a479a2b3b6b791f0367436a4445fb80a8d
FEATURE_FLAGS=fac32a98c5af8a23d3152b62d7480dfe98e14ca66c4827439620058b222dbe92
LOG_LEVEL=a4b750cb1fb9b98fb0d8dfd13e349f0c2be16f8d2b6c4a8fa7d4661d0e7d8d4c
QUOTED_HASH=ba5e8049d4142b420fd252c8b0c09da4e1634ea0610aba0b1949255579af7449
SENTRY_DSN=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
SERVICE_NAME=3a5f742447db68b30f112ed469861f8ba57e8ecbcd100acb7290524ab8119f65
SINGLE_HASH=4e525f4141e2b66ebeea51aa8c0b0fe1280220bc52eb9b0157ed7e40a9e5b535
"""

EXPECTED_LINES = EXPECTED_REPORT.splitlines()


def read_report_text() -> str:
    assert REPORT_FILE.exists(), (
        "Compliance report was not created at the required absolute path: "
        "/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt"
    )
    assert REPORT_FILE.is_file(), (
        "Required report path exists but is not a regular file: "
        "/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt"
    )
    try:
        return REPORT_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(
            "Compliance report is not valid plain UTF-8 text: "
            "/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt"
        ) from exc


def test_audit_directory_exists_at_required_absolute_path():
    assert AUDIT_DIR.exists(), (
        "Audit output directory is missing; create it at: "
        "/home/user/workspace/policy-envcheck/audit"
    )
    assert AUDIT_DIR.is_dir(), (
        "Audit output path exists but is not a directory: "
        "/home/user/workspace/policy-envcheck/audit"
    )


def test_exactly_one_report_file_exists_in_audit_directory():
    assert AUDIT_DIR.exists() and AUDIT_DIR.is_dir(), (
        "Cannot inspect audit directory because it is missing or not a directory: "
        "/home/user/workspace/policy-envcheck/audit"
    )

    entries = sorted(AUDIT_DIR.iterdir(), key=lambda path: path.name)
    unexpected_entries = [str(path) for path in entries if path != REPORT_FILE]
    assert not unexpected_entries, (
        "Audit directory must contain no extra files or directories besides "
        "/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt; "
        f"unexpected entries found: {unexpected_entries}"
    )

    assert entries == [REPORT_FILE], (
        "Audit directory must contain exactly one report file named "
        "dotenv-policy-report.txt"
    )


def test_report_file_exists_is_regular_and_readable_utf8():
    assert REPORT_FILE.exists(), (
        "Missing required compliance report: "
        "/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt"
    )
    assert REPORT_FILE.is_file(), (
        "Required compliance report path is not a regular file: "
        "/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt"
    )
    assert os.access(REPORT_FILE, os.R_OK), (
        "Required compliance report is not readable: "
        "/home/user/workspace/policy-envcheck/audit/dotenv-policy-report.txt"
    )
    read_report_text()


def test_report_has_exact_expected_content_and_trailing_newline():
    actual = read_report_text()
    assert actual == EXPECTED_REPORT, (
        "Compliance report content is not exactly correct. It must match the "
        "required labels, ordering, counts, section entries, SHA-256 hashes, and "
        "single final trailing newline with no extra commentary or timestamps."
    )


def test_report_line_count_labels_and_order_are_exact():
    actual_lines = read_report_text().splitlines()

    assert len(actual_lines) == len(EXPECTED_LINES), (
        f"Report has the wrong number of lines: expected {len(EXPECTED_LINES)}, "
        f"got {len(actual_lines)}. Do not add or omit lines."
    )

    for index, (actual, expected) in enumerate(zip(actual_lines, EXPECTED_LINES), start=1):
        assert actual == expected, (
            f"Report line {index} is incorrect: expected {expected!r}, got {actual!r}"
        )


def test_report_header_metadata_and_counts_are_exact():
    actual_lines = read_report_text().splitlines()
    expected_prefix = [
        "DOTENV POLICY REPORT",
        "workspace=/home/user/workspace/policy-envcheck",
        "env_file=/home/user/workspace/policy-envcheck/config/.env.release",
        "policy_file=/home/user/workspace/policy-envcheck/policy/required-env.txt",
        "status=FAIL",
        "missing_required_count=1",
        "forbidden_present_count=2",
        "duplicate_key_count=1",
        "parse_error_count=3",
    ]

    assert actual_lines[:9] == expected_prefix, (
        "Report header/metadata/count lines are wrong. The first nine lines must "
        "use the exact required labels and expected computed values."
    )


def test_report_sections_are_in_exact_required_order():
    actual_lines = read_report_text().splitlines()
    actual_headers = [line for line in actual_lines if line.startswith("[") and line.endswith("]")]
    expected_headers = [
        "[missing_required]",
        "[forbidden_present]",
        "[duplicate_keys]",
        "[parse_errors]",
        "[effective_values_sha256]",
    ]

    assert actual_headers == expected_headers, (
        "Report section headers are missing, extra, misspelled, or out of order: "
        f"expected {expected_headers}, got {actual_headers}"
    )


def test_violation_sections_contain_expected_entries_only():
    actual_lines = read_report_text().splitlines()

    def section_lines(header: str, next_header: str) -> list[str]:
        start = actual_lines.index(header) + 1
        end = actual_lines.index(next_header)
        return actual_lines[start:end]

    assert section_lines("[missing_required]", "[forbidden_present]") == ["REDIS_URL"], (
        "Missing-required section must contain only REDIS_URL in lexicographic order."
    )
    assert section_lines("[forbidden_present]", "[duplicate_keys]") == [
        "AWS_SECRET_ACCESS_KEY",
        "DEBUG",
    ], (
        "Forbidden-present section must contain AWS_SECRET_ACCESS_KEY and DEBUG "
        "in lexicographic order."
    )
    assert section_lines("[duplicate_keys]", "[parse_errors]") == ["API_TOKEN=2"], (
        "Duplicate-keys section must contain exactly API_TOKEN=2."
    )
    assert section_lines("[parse_errors]", "[effective_values_sha256]") == [
        "line 17: BAD-KEY=value",
        'line 18: UNFINISHED_QUOTE="abc',
        "line 19: TRAILING_SPACE = not-valid-key-because-space-before-equals",
    ], (
        "Parse-errors section must list the three expected parse errors in "
        "ascending line-number order with original line text."
    )


def test_effective_values_sha256_section_is_exact_and_sorted():
    actual_lines = read_report_text().splitlines()
    start = actual_lines.index("[effective_values_sha256]") + 1
    actual_hash_lines = actual_lines[start:]
    expected_hash_lines = EXPECTED_LINES[EXPECTED_LINES.index("[effective_values_sha256]") + 1 :]

    assert actual_hash_lines == expected_hash_lines, (
        "Effective value SHA-256 section is wrong. It must contain every valid "
        "parsed key exactly once in lexicographic key order, hashing only the "
        "final effective value with decoded double-quoted escapes."
    )

    actual_keys = [line.split("=", 1)[0] for line in actual_hash_lines]
    assert actual_keys == sorted(actual_keys), (
        "Effective value SHA-256 entries are not in lexicographic key order."
    )
    assert len(actual_keys) == len(set(actual_keys)), (
        "Effective value SHA-256 section contains duplicate key entries."
    )


def test_input_files_still_exist_after_report_generation():
    assert ENV_FILE.exists() and ENV_FILE.is_file(), (
        "Dotenv input file should still exist as a regular file: "
        "/home/user/workspace/policy-envcheck/config/.env.release"
    )
    assert POLICY_FILE.exists() and POLICY_FILE.is_file(), (
        "Policy input file should still exist as a regular file: "
        "/home/user/workspace/policy-envcheck/policy/required-env.txt"
    )