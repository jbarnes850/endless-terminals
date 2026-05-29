# test_final_state.py
import json
import math
from pathlib import Path

import pytest


ROOT = Path("/home/user/finops-cloud-costs")

CONFIG = Path("/home/user/finops-cloud-costs/config/security-scan.toml")
CURRENT_INVENTORY = Path("/home/user/finops-cloud-costs/data/cloud_assets_current.json")
LEGACY_INVENTORY = Path("/home/user/finops-cloud-costs/data/cloud_assets_legacy.json")

CANONICAL_RESULT = Path("/home/user/finops-cloud-costs/state/security/current_findings.json")
ACTIVE_LEGACY_CSV = Path("/home/user/finops-cloud-costs/reports/security_findings.csv")
RETIRED_LEGACY_CSV = Path("/home/user/finops-cloud-costs/reports/security_findings.csv.retired")
FINAL_LOG = Path("/home/user/finops-cloud-costs/reports/security-scan-final.log")
LEGACY_STATE_JSON = Path("/home/user/finops-cloud-costs/state/legacy/current_findings.json")

EXPECTED_LOG_TEXT = (
    "scan_source=/home/user/finops-cloud-costs/data/cloud_assets_current.json\n"
    "canonical_result=/home/user/finops-cloud-costs/state/security/current_findings.json\n"
    "legacy_report=/home/user/finops-cloud-costs/reports/security_findings.csv.retired\n"
    "legacy_active_present=no\n"
    "finding_count=5\n"
    "critical_or_high_count=5\n"
    "verification=new-state"
)

ORIGINAL_LEGACY_CSV_TEXT = (
    "finding_id,resource_id,severity,issue,status\n"
    "LEGACY-000,s3-legacy-clean,INFO,no active security-cost finding,stale-pass\n"
)

REQUIRED_TOP_LEVEL_KEYS = {"scanner", "inventory", "generated_at", "findings"}
REQUIRED_FINDING_KEYS = {
    "finding_id",
    "resource_id",
    "service",
    "region",
    "severity",
    "monthly_cost_usd",
    "cost_owner",
    "issue",
    "recommendation",
}

EXPECTED_FINDINGS = [
    {
        "finding_id": "FSC-001",
        "resource_id": "ebs-ledger-cache-004",
        "service": "ebs",
        "region": "us-east-2",
        "severity": "HIGH",
        "monthly_cost_usd": 91.88,
        "cost_owner": "ledger-systems",
        "issue": "unencrypted_volume",
        "recommendation": (
            "Enable encryption at rest or migrate data to an encrypted volume before the next "
            "billing cycle."
        ),
    },
    {
        "finding_id": "FSC-002",
        "resource_id": "ec2-cost-etl-admin-017",
        "service": "ec2",
        "region": "us-west-2",
        "severity": "CRITICAL",
        "monthly_cost_usd": 612.30,
        "cost_owner": "finops-analytics",
        "issue": "open_admin_port",
        "recommendation": (
            "Restrict administrative ingress to approved corporate CIDR ranges or replace direct "
            "access with a managed session service."
        ),
    },
    {
        "finding_id": "FSC-003",
        "resource_id": "ec2-rightsize-api-009",
        "service": "ec2",
        "region": "eu-central-1",
        "severity": "HIGH",
        "monthly_cost_usd": 257.44,
        "cost_owner": "rightsizing-api",
        "issue": "unencrypted_volume",
        "recommendation": (
            "Enable encryption at rest or migrate data to an encrypted volume before the next "
            "billing cycle."
        ),
    },
    {
        "finding_id": "FSC-004",
        "resource_id": "s3-prod-invoices-001",
        "service": "s3",
        "region": "us-east-1",
        "severity": "CRITICAL",
        "monthly_cost_usd": 184.72,
        "cost_owner": "finance-platform",
        "issue": "public_storage",
        "recommendation": (
            "Disable public access blocks exceptions and validate bucket policy before committing "
            "additional storage spend."
        ),
    },
    {
        "finding_id": "FSC-005",
        "resource_id": "s3-archive-receipts-021",
        "service": "s3",
        "region": "us-west-1",
        "severity": "HIGH",
        "monthly_cost_usd": 34.11,
        "cost_owner": "tax-archive",
        "issue": "public_storage",
        "recommendation": (
            "Disable public access blocks exceptions and validate bucket policy before committing "
            "additional storage spend."
        ),
    },
]


def load_json(path: Path):
    assert path.exists(), f"Required JSON file is missing: {path}"
    assert path.is_file(), f"Required JSON path is not a file: {path}"
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        pytest.fail(f"File is not valid JSON: {path}: {exc}")


@pytest.fixture(scope="module")
def canonical_json():
    return load_json(CANONICAL_RESULT)


def normalize_finding_for_comparison(finding):
    normalized = {}
    for key in REQUIRED_FINDING_KEYS:
        assert key in finding, f"Canonical finding is missing required key {key!r}: {finding!r}"
        normalized[key] = finding[key]

    try:
        normalized["monthly_cost_usd"] = float(normalized["monthly_cost_usd"])
    except (TypeError, ValueError):
        pytest.fail(
            "Finding monthly_cost_usd must be numeric or numeric-like for "
            f"{finding.get('finding_id', '<missing finding_id>')}: "
            f"{finding.get('monthly_cost_usd')!r}"
        )

    return normalized


def assert_findings_equal(actual_findings, expected_findings):
    assert len(actual_findings) == len(expected_findings), (
        f"Canonical result should contain exactly {len(expected_findings)} findings, "
        f"but contains {len(actual_findings)}. Actual findings: {actual_findings!r}"
    )

    actual_by_id = {}
    for finding in actual_findings:
        normalized = normalize_finding_for_comparison(finding)
        finding_id = normalized["finding_id"]
        assert finding_id not in actual_by_id, (
            f"Duplicate finding_id found in canonical JSON: {finding_id}"
        )
        actual_by_id[finding_id] = normalized

    expected_by_id = {finding["finding_id"]: finding for finding in expected_findings}
    assert set(actual_by_id) == set(expected_by_id), (
        "Canonical finding IDs are incorrect. "
        f"Expected {sorted(expected_by_id)}, got {sorted(actual_by_id)}"
    )

    for finding_id, expected in expected_by_id.items():
        actual = actual_by_id[finding_id]
        for key, expected_value in expected.items():
            actual_value = actual[key]
            if key == "monthly_cost_usd":
                assert math.isclose(float(actual_value), float(expected_value), rel_tol=0, abs_tol=0.001), (
                    f"Finding {finding_id} has wrong monthly_cost_usd: "
                    f"expected {expected_value}, got {actual_value}"
                )
            else:
                assert actual_value == expected_value, (
                    f"Finding {finding_id} has wrong {key}: "
                    f"expected {expected_value!r}, got {actual_value!r}"
                )


def test_canonical_current_finding_artifact_exists_under_configured_state_directory():
    assert CANONICAL_RESULT.exists(), (
        "Canonical current finding artifact was not created at the configured state path: "
        f"{CANONICAL_RESULT}"
    )
    assert CANONICAL_RESULT.is_file(), (
        f"Canonical current finding artifact exists but is not a regular file: {CANONICAL_RESULT}"
    )


def test_canonical_json_has_required_top_level_shape_and_uses_current_inventory(canonical_json):
    assert isinstance(canonical_json, dict), (
        f"Canonical JSON must be a top-level object: {CANONICAL_RESULT}"
    )

    missing = REQUIRED_TOP_LEVEL_KEYS - set(canonical_json)
    assert not missing, (
        f"Canonical JSON is missing required top-level keys {sorted(missing)}: {CANONICAL_RESULT}"
    )

    assert canonical_json["scanner"] == "finops-security-cost-scan", (
        "Canonical JSON has the wrong scanner value; it should be produced by the configured "
        "finops security scanner."
    )
    assert canonical_json["inventory"] == str(CURRENT_INVENTORY), (
        "Canonical JSON was not generated from the configured current inventory. "
        f"Expected inventory {CURRENT_INVENTORY}, got {canonical_json.get('inventory')!r}"
    )
    assert canonical_json["inventory"] != str(LEGACY_INVENTORY), (
        "Canonical JSON incorrectly points to the retired legacy inventory."
    )
    assert isinstance(canonical_json["generated_at"], str) and canonical_json["generated_at"], (
        "Canonical JSON generated_at must be a non-empty string."
    )
    assert isinstance(canonical_json["findings"], list), (
        "Canonical JSON top-level 'findings' value must be an array."
    )


def test_canonical_json_contains_exact_expected_current_findings(canonical_json):
    assert_findings_equal(canonical_json["findings"], EXPECTED_FINDINGS)

    resource_issue_pairs = {
        (finding["resource_id"], finding["issue"]) for finding in canonical_json["findings"]
    }
    assert ("rds-cost-dashboard-002", "open_admin_port") not in resource_issue_pairs, (
        "Port 5432 on rds-cost-dashboard-002 must not be treated as an admin-port finding."
    )
    assert ("s3-legacy-clean", "no active security-cost finding") not in resource_issue_pairs, (
        "Legacy CSV report data leaked into the canonical JSON findings."
    )


def test_legacy_csv_is_retired_and_no_active_legacy_report_remains():
    assert not ACTIVE_LEGACY_CSV.exists(), (
        "The active legacy CSV report must be gone so it cannot be mistaken for the source of "
        f"truth: {ACTIVE_LEGACY_CSV}"
    )
    assert RETIRED_LEGACY_CSV.exists(), (
        "The stale legacy CSV report must be retained for audit by renaming it to: "
        f"{RETIRED_LEGACY_CSV}"
    )
    assert RETIRED_LEGACY_CSV.is_file(), (
        f"The retired legacy CSV path exists but is not a regular file: {RETIRED_LEGACY_CSV}"
    )

    retired_text = RETIRED_LEGACY_CSV.read_text(encoding="utf-8")
    assert "LEGACY-000" in retired_text and "s3-legacy-clean" in retired_text, (
        "The retired CSV does not appear to preserve the original legacy report data for audit."
    )
    assert retired_text.startswith("finding_id,resource_id,severity,issue,status\n"), (
        "The retired CSV should preserve the original CSV header."
    )


def test_verification_log_exists_and_matches_exact_required_new_state_contents(canonical_json):
    assert FINAL_LOG.exists(), f"Final verification log is missing: {FINAL_LOG}"
    assert FINAL_LOG.is_file(), f"Final verification log exists but is not a file: {FINAL_LOG}"

    actual_text = FINAL_LOG.read_text(encoding="utf-8")
    assert actual_text == EXPECTED_LOG_TEXT, (
        "Final verification log does not exactly match the required seven lines proving "
        "verification was based on the new canonical JSON state.\n"
        f"Expected:\n{EXPECTED_LOG_TEXT!r}\n"
        f"Actual:\n{actual_text!r}"
    )

    lines = actual_text.splitlines()
    assert len(lines) == 7, (
        f"Verification log must contain exactly seven lines with no extra blank lines; got {len(lines)}."
    )

    finding_count = len(canonical_json["findings"])
    high_or_critical_count = sum(
        1 for finding in canonical_json["findings"] if finding.get("severity") in {"CRITICAL", "HIGH"}
    )
    assert lines[4] == f"finding_count={finding_count}", (
        "Verification log finding_count must be computed from canonical JSON findings."
    )
    assert lines[5] == f"critical_or_high_count={high_or_critical_count}", (
        "Verification log critical_or_high_count must be computed from canonical JSON findings."
    )
    assert lines[6] == "verification=new-state", (
        "Verification log must explicitly prove the new state was verified."
    )


def test_final_counts_are_from_canonical_json_not_legacy_or_retired_report(canonical_json):
    findings = canonical_json["findings"]
    assert len(findings) == 5, (
        "Canonical JSON must contain five current findings; a zero-count legacy state was likely "
        "used if this fails."
    )
    assert sum(1 for finding in findings if finding.get("severity") in {"CRITICAL", "HIGH"}) == 5, (
        "All five canonical findings must be CRITICAL or HIGH."
    )

    if LEGACY_STATE_JSON.exists():
        legacy_json = load_json(LEGACY_STATE_JSON)
        assert legacy_json.get("inventory") == str(LEGACY_INVENTORY), (
            "Legacy state file should remain clearly tied to the legacy inventory if present."
        )
        assert legacy_json.get("findings") == [], (
            "Legacy state should not be used or modified to masquerade as the current scan result."
        )

    retired_text = RETIRED_LEGACY_CSV.read_text(encoding="utf-8")
    assert "stale-pass" in retired_text, (
        "Retired report should remain an audit artifact, not be rewritten as the current result."
    )