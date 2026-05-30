# test_final_state.py
import json
import stat
import subprocess
from pathlib import Path

import pytest


BASE_DIR = Path("/home/user/solver_case")
EVENTS_CSV = Path("/home/user/solver_case/events.csv")
SELECT_PATTERNS = Path("/home/user/solver_case/select_patterns.py")
CHECK_REPORT = Path("/home/user/solver_case/check_report.py")
OUTPUT_DIR = Path("/home/user/solver_case/output")
CANDIDATE_SUMMARY = Path("/home/user/solver_case/output/candidate_summary.txt")
FINAL_SOLUTION = Path("/home/user/solver_case/output/final_solution.json")
PATTERN_REPORT = Path("/home/user/solver_case/pattern_report.txt")
VERIFICATION_LOG = Path("/home/user/solver_case/verification.log")


EXPECTED_REPORT_TEXT = (
    "solver_status=OPTIMAL\n"
    "selected_count=3\n"
    "selected_patterns=P02,P03,P05\n"
    "covered_events=8\n"
    "total_score=39\n"
)

EXPECTED_VERIFICATION_LOG_TEXT = (
    "REPORT CHECK PASSED: optimal pattern report verified\n"
)

EXPECTED_FINAL_SOLUTION = {
    "solver_status": "OPTIMAL",
    "selected_patterns": ["P02", "P03", "P05"],
    "selected_count": 3,
    "covered_events": 8,
    "total_score": 39,
}

EXPECTED_FINAL_SOLUTION_TEXT = (
    "{\n"
    '  "solver_status": "OPTIMAL",\n'
    '  "selected_patterns": [\n'
    '    "P02",\n'
    '    "P03",\n'
    '    "P05"\n'
    "  ],\n"
    '  "selected_count": 3,\n'
    '  "covered_events": 8,\n'
    '  "total_score": 39\n'
    "}\n"
)

MISLEADING_CANDIDATE_SNIPPETS = [
    "candidate_status=generated",
    "candidate_patterns=P01,P03",
    "candidate_score=17",
    "note=not final optimization solution",
]


def _assert_regular_file(path: Path, description: str) -> None:
    assert path.exists(), f"Missing {description}: {path}"
    assert path.is_file(), f"{description} exists but is not a regular file: {path}"


def _assert_directory(path: Path, description: str) -> None:
    assert path.exists(), f"Missing {description}: {path}"
    assert path.is_dir(), f"{description} exists but is not a directory: {path}"


def _assert_user_executable(path: Path, description: str) -> None:
    mode = path.stat().st_mode
    assert mode & stat.S_IXUSR, f"{description} is not executable by its owner/user: {path}"


def test_required_base_files_and_output_directory_exist() -> None:
    _assert_directory(BASE_DIR, "solver case directory")
    _assert_regular_file(EVENTS_CSV, "input events CSV")
    _assert_regular_file(SELECT_PATTERNS, "solver utility")
    _assert_user_executable(SELECT_PATTERNS, "solver utility")
    _assert_regular_file(CHECK_REPORT, "report checker utility")
    _assert_user_executable(CHECK_REPORT, "report checker utility")
    _assert_directory(OUTPUT_DIR, "solver output directory")


def test_solver_was_run_and_final_solution_json_exists() -> None:
    _assert_regular_file(FINAL_SOLUTION, "final solver solution JSON")

    assert FINAL_SOLUTION.stat().st_size > 0, (
        f"{FINAL_SOLUTION} is empty; the solver's final optimization output "
        "must be present and populated."
    )

    assert CANDIDATE_SUMMARY.exists(), (
        f"{CANDIDATE_SUMMARY} is missing. The provided solver normally creates "
        "this misleading partial artifact before writing the final solution; "
        "its absence suggests the solver utility may not have been run."
    )


def test_candidate_summary_is_not_used_as_final_report_source() -> None:
    _assert_regular_file(CANDIDATE_SUMMARY, "candidate summary artifact")
    candidate_text = CANDIDATE_SUMMARY.read_text(encoding="utf-8")

    missing = [
        snippet for snippet in MISLEADING_CANDIDATE_SNIPPETS
        if snippet not in candidate_text
    ]
    assert not missing, (
        f"{CANDIDATE_SUMMARY} does not look like the expected misleading "
        "candidate artifact. Missing snippets: "
        + ", ".join(repr(item) for item in missing)
    )

    if PATTERN_REPORT.exists() and PATTERN_REPORT.is_file():
        report_text = PATTERN_REPORT.read_text(encoding="utf-8")
        assert "P01,P03" not in report_text, (
            f"{PATTERN_REPORT} appears to use the misleading candidate pattern "
            "set P01,P03 instead of the final optimization solution P02,P03,P05."
        )
        assert "candidate_" not in report_text, (
            f"{PATTERN_REPORT} contains candidate-summary fields. The report "
            "must be built from output/final_solution.json, not candidate_summary.txt."
        )


def test_final_solution_json_has_exact_expected_contents_and_format() -> None:
    _assert_regular_file(FINAL_SOLUTION, "final solver solution JSON")

    raw = FINAL_SOLUTION.read_text(encoding="utf-8")
    assert raw == EXPECTED_FINAL_SOLUTION_TEXT, (
        f"{FINAL_SOLUTION} does not exactly match the expected pretty-printed "
        "final optimization solution JSON."
    )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"{FINAL_SOLUTION} is not valid JSON: {exc}")

    assert parsed == EXPECTED_FINAL_SOLUTION, (
        f"{FINAL_SOLUTION} contains valid JSON but not the expected final "
        f"optimization result. Expected {EXPECTED_FINAL_SOLUTION!r}, got {parsed!r}."
    )


def test_pattern_report_exists_and_has_exact_required_contents() -> None:
    _assert_regular_file(PATTERN_REPORT, "final analyst report")

    actual = PATTERN_REPORT.read_text(encoding="utf-8")
    assert actual == EXPECTED_REPORT_TEXT, (
        f"{PATTERN_REPORT} has incorrect contents. It must contain exactly five "
        "non-empty lines in the required order, with a single trailing newline:\n"
        f"{EXPECTED_REPORT_TEXT!r}\n"
        f"Actual contents were:\n{actual!r}"
    )

    lines = actual.splitlines()
    assert len(lines) == 5, (
        f"{PATTERN_REPORT} must contain exactly 5 non-empty report lines; "
        f"found {len(lines)} lines."
    )
    assert all(line.strip() == line and line for line in lines), (
        f"{PATTERN_REPORT} must not contain blank lines or leading/trailing spaces."
    )


def test_pattern_report_matches_final_solution_json_values() -> None:
    _assert_regular_file(FINAL_SOLUTION, "final solver solution JSON")
    _assert_regular_file(PATTERN_REPORT, "final analyst report")

    solution = json.loads(FINAL_SOLUTION.read_text(encoding="utf-8"))
    report_lines = PATTERN_REPORT.read_text(encoding="utf-8").splitlines()

    expected_from_solution = [
        f"solver_status={solution['solver_status']}",
        f"selected_count={solution['selected_count']}",
        "selected_patterns=" + ",".join(solution["selected_patterns"]),
        f"covered_events={solution['covered_events']}",
        f"total_score={solution['total_score']}",
    ]

    assert report_lines == expected_from_solution, (
        f"{PATTERN_REPORT} does not faithfully reflect the values in "
        f"{FINAL_SOLUTION}. Expected lines derived from final solution: "
        f"{expected_from_solution!r}; got {report_lines!r}."
    )

    assert solution["selected_patterns"] == sorted(solution["selected_patterns"]), (
        f"{FINAL_SOLUTION} selected_patterns must be in ascending order."
    )


def test_verification_log_contains_exact_checker_success_message() -> None:
    _assert_regular_file(VERIFICATION_LOG, "checker verification log")

    actual = VERIFICATION_LOG.read_text(encoding="utf-8")
    assert actual == EXPECTED_VERIFICATION_LOG_TEXT, (
        f"{VERIFICATION_LOG} must contain exactly the checker success message "
        "written verbatim, including its trailing newline. "
        f"Expected {EXPECTED_VERIFICATION_LOG_TEXT!r}, got {actual!r}."
    )


def test_checker_currently_passes_against_final_report() -> None:
    _assert_regular_file(CHECK_REPORT, "report checker utility")
    _assert_user_executable(CHECK_REPORT, "report checker utility")
    _assert_regular_file(PATTERN_REPORT, "final analyst report")

    result = subprocess.run(
        [str(CHECK_REPORT)],
        cwd=str(BASE_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, (
        f"Running {CHECK_REPORT} against {PATTERN_REPORT} did not succeed. "
        f"Exit code: {result.returncode}. "
        f"stdout: {result.stdout!r}. stderr: {result.stderr!r}."
    )
    assert result.stdout == EXPECTED_VERIFICATION_LOG_TEXT, (
        f"{CHECK_REPORT} stdout is not the expected success message. "
        f"Expected {EXPECTED_VERIFICATION_LOG_TEXT!r}, got {result.stdout!r}."
    )
    assert result.stderr == "", (
        f"{CHECK_REPORT} should not write stderr on success, but wrote: "
        f"{result.stderr!r}"
    )


def test_deliverable_paths_are_absolute_and_under_expected_directory() -> None:
    for path in [
        OUTPUT_DIR,
        CANDIDATE_SUMMARY,
        FINAL_SOLUTION,
        PATTERN_REPORT,
        VERIFICATION_LOG,
    ]:
        assert path.is_absolute(), f"Tested deliverable path is not absolute: {path}"
        assert str(path).startswith("/home/user/solver_case/"), (
            f"Deliverable path is outside /home/user/solver_case: {path}"
        )