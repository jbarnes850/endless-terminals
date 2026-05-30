# test_final_state.py
from __future__ import annotations

import csv
import importlib.metadata
import json
import re
import site
import sys
from decimal import Decimal
from pathlib import Path

import pytest


ROOT = Path("/home/user/finops_pkg_task")
DATA_DIR = Path("/home/user/finops_pkg_task/data")
OUTPUT_DIR = Path("/home/user/finops_pkg_task/output")
REPORT_PATH = Path("/home/user/finops_pkg_task/output/savings_report.csv")
VERIFICATION_LOG_PATH = Path("/home/user/finops_pkg_task/output/verification.log")
INVENTORY_PATH = Path("/home/user/finops_pkg_task/data/cloud_inventory.jsonl")
CATALOG_PATH = Path("/home/user/finops_pkg_task/data/package_price_catalog.csv")
REQUIREMENTS_PATH = Path("/home/user/finops_pkg_task/requirements.txt")

EXPECTED_HEADER = [
    "service",
    "environment",
    "current_monthly_cost",
    "recommended_monthly_cost",
    "monthly_savings",
    "action",
    "package_source",
]

EXPECTED_REPORT_TEXT = """service,environment,current_monthly_cost,recommended_monthly_cost,monthly_savings,action,package_source
analytics-db,prod,455.00,235.00,220.00,DOWNGRADE_PACKAGE,aws/rds
checkout-api,prod,280.00,150.00,130.00,DOWNGRADE_PACKAGE,aws/ec2
metrics-db,staging,235.00,128.00,107.00,DOWNGRADE_PACKAGE,aws/rds
ml-batch,prod,194.00,102.00,92.00,DOWNGRADE_PACKAGE,gcp/gke
frontend,prod,146.00,73.00,73.00,DOWNGRADE_PACKAGE,azure/appservice
billing-worker,prod,150.00,82.00,68.00,DOWNGRADE_PACKAGE,aws/ec2
reporting-api,staging,150.00,82.00,68.00,DOWNGRADE_PACKAGE,aws/ec2
qa-runner,qa,102.00,56.00,46.00,DOWNGRADE_PACKAGE,gcp/gke
"""

EXPECTED_VERIFICATION_LOG_TEXT = """CHECKPOINT package_install: PASS
CHECKPOINT command_completed: PASS
CHECKPOINT artifact_exists: PASS
CHECKPOINT artifact_valid: PASS
CHECKPOINT semantic_correctness: PASS
"""

INITIAL_CATALOG_TEXT = """package_source,package_name,monthly_price
aws/ec2,m6i.2xlarge,280.00
aws/ec2,m6i.xlarge,150.00
aws/ec2,m6i.large,82.00
aws/rds,db.m6i.2xlarge,455.00
aws/rds,db.m6i.xlarge,235.00
aws/rds,db.m6i.large,128.00
gcp/gke,n2-standard-8,194.00
gcp/gke,n2-standard-4,102.00
gcp/gke,n2-standard-2,56.00
azure/appservice,P2v3,146.00
azure/appservice,P1v3,73.00
azure/appservice,B1,13.00
"""

INITIAL_INVENTORY_TEXT = """{"service":"checkout-api","environment":"prod","package_source":"aws/ec2","current_package":"m6i.2xlarge","recommended_package":"m6i.xlarge","already_optimized":false}
{"service":"billing-worker","environment":"prod","package_source":"aws/ec2","current_package":"m6i.xlarge","recommended_package":"m6i.large","already_optimized":false}
{"service":"analytics-db","environment":"prod","package_source":"aws/rds","current_package":"db.m6i.2xlarge","recommended_package":"db.m6i.xlarge","already_optimized":false}
{"service":"metrics-db","environment":"staging","package_source":"aws/rds","current_package":"db.m6i.xlarge","recommended_package":"db.m6i.large","already_optimized":false}
{"service":"frontend","environment":"prod","package_source":"azure/appservice","current_package":"P2v3","recommended_package":"P1v3","already_optimized":false}
{"service":"internal-tool","environment":"dev","package_source":"azure/appservice","current_package":"B1","recommended_package":"B1","already_optimized":true}
{"service":"ml-batch","environment":"prod","package_source":"gcp/gke","current_package":"n2-standard-8","recommended_package":"n2-standard-4","already_optimized":false}
{"service":"qa-runner","environment":"qa","package_source":"gcp/gke","current_package":"n2-standard-4","recommended_package":"n2-standard-2","already_optimized":false}
{"service":"cache","environment":"prod","package_source":"aws/ec2","current_package":"m6i.large","recommended_package":"m6i.large","already_optimized":true}
{"service":"reporting-api","environment":"staging","package_source":"aws/ec2","current_package":"m6i.xlarge","recommended_package":"m6i.large","already_optimized":false}
"""


def _read_text(path: Path) -> str:
    assert path.exists(), f"Missing required path: {path}"
    assert path.is_file(), f"Required path is not a regular file: {path}"
    return path.read_text()


def _read_report_rows() -> list[dict[str, str]]:
    assert REPORT_PATH.exists(), f"Final report is missing: {REPORT_PATH}"
    assert REPORT_PATH.is_file(), f"Final report path is not a file: {REPORT_PATH}"
    assert REPORT_PATH.stat().st_size > 0, f"Final report exists but is empty: {REPORT_PATH}"

    with REPORT_PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == EXPECTED_HEADER, (
            f"{REPORT_PATH} has the wrong CSV header.\n"
            f"Expected exactly: {EXPECTED_HEADER!r}\n"
            f"Actual: {reader.fieldnames!r}"
        )
        rows = list(reader)

    assert all(row is not None for row in rows), f"{REPORT_PATH} contains malformed CSV rows"
    return rows


def _load_catalog_prices() -> dict[tuple[str, str], Decimal]:
    with CATALOG_PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["package_source", "package_name", "monthly_price"], (
            f"Input catalog header was modified or is invalid: {CATALOG_PATH}"
        )
        return {
            (row["package_source"], row["package_name"]): Decimal(row["monthly_price"])
            for row in reader
        }


def _load_inventory() -> list[dict[str, object]]:
    with INVENTORY_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _expected_rows_from_inputs() -> list[dict[str, str]]:
    prices = _load_catalog_prices()
    expected: list[dict[str, str]] = []

    for item in _load_inventory():
        if item["already_optimized"] is True:
            continue

        source = str(item["package_source"])
        current_package = str(item["current_package"])
        recommended_package = str(item["recommended_package"])

        current = prices[(source, current_package)]
        recommended = prices[(source, recommended_package)]
        savings = current - recommended

        if savings <= Decimal("0.00"):
            continue

        expected.append(
            {
                "service": str(item["service"]),
                "environment": str(item["environment"]),
                "current_monthly_cost": f"{current:.2f}",
                "recommended_monthly_cost": f"{recommended:.2f}",
                "monthly_savings": f"{savings:.2f}",
                "action": "DOWNGRADE_PACKAGE",
                "package_source": source,
            }
        )

    expected.sort(
        key=lambda row: (
            -Decimal(row["monthly_savings"]),
            row["service"],
            row["environment"],
        )
    )
    return expected


def test_input_data_files_were_not_modified():
    assert _read_text(CATALOG_PATH) == INITIAL_CATALOG_TEXT, (
        f"The task explicitly forbids modifying input data, but {CATALOG_PATH} "
        "does not match its original expected contents."
    )
    assert _read_text(INVENTORY_PATH) == INITIAL_INVENTORY_TEXT, (
        f"The task explicitly forbids modifying input data, but {INVENTORY_PATH} "
        "does not match its original expected contents."
    )


def test_requirements_still_request_expected_dependencies():
    assert _read_text(REQUIREMENTS_PATH) == "pandas==2.2.2\npackaging==24.1\n", (
        f"{REQUIREMENTS_PATH} should still contain the required dependency pins."
    )


def test_required_dependencies_are_installed_at_expected_versions_and_not_only_declared():
    installed = {}
    for package_name in ("pandas", "packaging"):
        try:
            installed[package_name] = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            pytest.fail(
                f"Required dependency {package_name!r} is not installed in the Python "
                "environment running the workflow/tests."
            )

    assert installed["pandas"] == "2.2.2", (
        "pandas must be installed at exactly version 2.2.2; "
        f"found {installed['pandas']!r}."
    )
    assert installed["packaging"] == "24.1", (
        "packaging must be installed at exactly version 24.1; "
        f"found {installed['packaging']!r}."
    )

    user_site = Path(site.getusersitepackages()).resolve()
    workspace = ROOT.resolve()

    for package_name in ("pandas", "packaging"):
        dist = importlib.metadata.distribution(package_name)
        dist_location = Path(str(dist.locate_file(""))).resolve()
        assert not str(dist_location).startswith(("/usr/lib", "/usr/local/lib")), (
            f"{package_name!r} appears to be installed in a system/root location "
            f"({dist_location}), not a non-root user/workspace environment."
        )
        assert (
            str(dist_location).startswith(str(user_site))
            or str(dist_location).startswith(str(workspace))
            or dist_location in [Path(p).resolve() for p in sys.path if p]
        ), (
            f"{package_name!r} is installed at {dist_location}, which does not look "
            "like an importable user-site or workspace-local environment."
        )


def test_output_directory_and_final_report_exist_and_are_nonempty():
    assert OUTPUT_DIR.exists(), f"Output directory was not created: {OUTPUT_DIR}"
    assert OUTPUT_DIR.is_dir(), f"Output path is not a directory: {OUTPUT_DIR}"
    assert REPORT_PATH.exists(), f"Required final CSV was not created: {REPORT_PATH}"
    assert REPORT_PATH.is_file(), f"Required final CSV path is not a file: {REPORT_PATH}"
    assert REPORT_PATH.stat().st_size > 0, f"Required final CSV is empty: {REPORT_PATH}"


def test_report_matches_exact_required_csv_contents_and_order():
    actual = _read_text(REPORT_PATH)
    assert actual == EXPECTED_REPORT_TEXT, (
        f"{REPORT_PATH} does not match the exact required final report contents, "
        "including row order sorted by descending numeric monthly_savings, then "
        "service, then environment.\n"
        f"Expected:\n{EXPECTED_REPORT_TEXT!r}\n"
        f"Actual:\n{actual!r}"
    )


def test_report_has_exact_header_row_count_and_no_blank_or_extra_rows():
    text = _read_text(REPORT_PATH)
    assert "\r" not in text, f"{REPORT_PATH} should use normal '\\n' line endings only."
    assert text.endswith("\n"), f"{REPORT_PATH} should end with a trailing newline."
    assert "\n\n" not in text, f"{REPORT_PATH} contains blank lines."

    rows = _read_report_rows()
    assert len(rows) == 8, (
        f"{REPORT_PATH} should contain exactly 8 optimizable resource rows; "
        f"found {len(rows)}."
    )

    for index, row in enumerate(rows, start=2):
        assert set(row) == set(EXPECTED_HEADER), (
            f"CSV row {index} has unexpected columns. "
            f"Expected exactly {EXPECTED_HEADER!r}; got {list(row)!r}."
        )
        assert all(value is not None and value != "" for value in row.values()), (
            f"CSV row {index} contains an empty field: {row!r}"
        )


def test_report_field_formats_actions_and_money_arithmetic_are_valid():
    rows = _read_report_rows()
    money_pattern = re.compile(r"^[0-9]+\.[0-9]{2}$")

    for index, row in enumerate(rows, start=2):
        assert row["action"] == "DOWNGRADE_PACKAGE", (
            f"CSV row {index} has wrong action {row['action']!r}; "
            "expected exactly 'DOWNGRADE_PACKAGE'."
        )

        for field in (
            "current_monthly_cost",
            "recommended_monthly_cost",
            "monthly_savings",
        ):
            assert money_pattern.fullmatch(row[field]), (
                f"CSV row {index} field {field!r} must be formatted as dollars "
                f"with exactly two decimal places and no currency symbol; got "
                f"{row[field]!r}."
            )

        current = Decimal(row["current_monthly_cost"])
        recommended = Decimal(row["recommended_monthly_cost"])
        savings = Decimal(row["monthly_savings"])

        assert current > recommended, (
            f"CSV row {index} should only include positive savings opportunities, "
            f"but current={current} and recommended={recommended}: {row!r}"
        )
        assert current - recommended == savings, (
            f"CSV row {index} has inconsistent savings arithmetic: expected "
            f"{current} - {recommended} = {current - recommended:.2f}, "
            f"but monthly_savings is {savings:.2f}."
        )


def test_report_semantically_matches_inventory_and_catalog_computation():
    expected = _expected_rows_from_inputs()
    actual = _read_report_rows()

    assert actual == expected, (
        "Final report does not match the optimization opportunities computed from "
        "cloud_inventory.jsonl and package_price_catalog.csv. The report must "
        "exclude already_optimized resources, look up recommended package prices "
        "using package_source plus recommended_package, include only positive "
        "savings, and sort by descending numeric savings then service and "
        "environment.\n"
        f"Expected rows:\n{expected!r}\n"
        f"Actual rows:\n{actual!r}"
    )


def test_no_already_optimized_resources_or_non_saving_resources_are_in_report():
    actual_keys = {
        (row["service"], row["environment"], row["package_source"])
        for row in _read_report_rows()
    }

    forbidden = {
        ("internal-tool", "dev", "azure/appservice"),
        ("cache", "prod", "aws/ec2"),
    }
    assert actual_keys.isdisjoint(forbidden), (
        "Report includes resources marked already_optimized, which must be excluded. "
        f"Forbidden rows present: {actual_keys & forbidden}"
    )


def test_verification_log_exists_and_has_exact_five_pass_checkpoints():
    assert VERIFICATION_LOG_PATH.exists(), (
        f"Required verification log was not created: {VERIFICATION_LOG_PATH}"
    )
    assert VERIFICATION_LOG_PATH.is_file(), (
        f"Verification log path is not a file: {VERIFICATION_LOG_PATH}"
    )

    actual = _read_text(VERIFICATION_LOG_PATH)
    assert actual == EXPECTED_VERIFICATION_LOG_TEXT, (
        f"{VERIFICATION_LOG_PATH} must contain exactly the five required PASS "
        "checkpoint lines and no FAIL, missing, reordered, or extra lines.\n"
        f"Expected:\n{EXPECTED_VERIFICATION_LOG_TEXT!r}\n"
        f"Actual:\n{actual!r}"
    )