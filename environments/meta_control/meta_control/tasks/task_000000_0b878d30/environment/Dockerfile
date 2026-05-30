FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    ROOT=/home/user/finops-cloud-costs

    mkdir -p "$ROOT/bin" \
             "$ROOT/config" \
             "$ROOT/data" \
             "$ROOT/reports" \
             "$ROOT/state/legacy"

    cat > "$ROOT/config/security-scan.toml" <<'EOF'
[scanner]
name = "finops-security-cost-scan"
version = "1.8.2"

[input]
inventory = "/home/user/finops-cloud-costs/data/cloud_assets_current.json"

[output]
state_dir = "/home/user/finops-cloud-costs/state/security"
current_findings = "current_findings.json"

[rules]
flag_public_storage = true
flag_unencrypted_volumes = true
flag_open_admin_ports = true
minimum_monthly_cost_usd = 50
EOF

    cat > "$ROOT/data/cloud_assets_current.json" <<'EOF'
{
  "inventory_id": "finops-prod-q3-current",
  "generated_at": "2025-02-18T09:15:00Z",
  "assets": [
    {
      "resource_id": "s3-prod-invoices-001",
      "service": "s3",
      "region": "us-east-1",
      "monthly_cost_usd": 184.72,
      "cost_owner": "finance-platform",
      "public_access": true,
      "encrypted": true,
      "open_ports": []
    },
    {
      "resource_id": "ec2-cost-etl-admin-017",
      "service": "ec2",
      "region": "us-west-2",
      "monthly_cost_usd": 612.30,
      "cost_owner": "finops-analytics",
      "public_access": false,
      "encrypted": true,
      "open_ports": [22, 443]
    },
    {
      "resource_id": "ebs-ledger-cache-004",
      "service": "ebs",
      "region": "us-east-2",
      "monthly_cost_usd": 91.88,
      "cost_owner": "ledger-systems",
      "public_access": false,
      "encrypted": false,
      "open_ports": []
    },
    {
      "resource_id": "rds-cost-dashboard-002",
      "service": "rds",
      "region": "us-east-1",
      "monthly_cost_usd": 438.19,
      "cost_owner": "finops-dashboard",
      "public_access": false,
      "encrypted": true,
      "open_ports": [5432]
    },
    {
      "resource_id": "s3-archive-receipts-021",
      "service": "s3",
      "region": "us-west-1",
      "monthly_cost_usd": 34.11,
      "cost_owner": "tax-archive",
      "public_access": true,
      "encrypted": false,
      "open_ports": []
    },
    {
      "resource_id": "ec2-rightsize-api-009",
      "service": "ec2",
      "region": "eu-central-1",
      "monthly_cost_usd": 257.44,
      "cost_owner": "rightsizing-api",
      "public_access": false,
      "encrypted": false,
      "open_ports": [8080]
    }
  ]
}
EOF

    cat > "$ROOT/data/cloud_assets_legacy.json" <<'EOF'
{
  "inventory_id": "finops-prod-q2-legacy",
  "generated_at": "2024-11-30T16:00:00Z",
  "assets": [
    {
      "resource_id": "s3-legacy-clean",
      "service": "s3",
      "region": "us-east-1",
      "monthly_cost_usd": 22.10,
      "cost_owner": "legacy",
      "public_access": false,
      "encrypted": true,
      "open_ports": []
    }
  ]
}
EOF

    cat > "$ROOT/reports/security_findings.csv" <<'EOF'
finding_id,resource_id,severity,issue,status
LEGACY-000,s3-legacy-clean,INFO,no active security-cost finding,stale-pass
EOF

    cat > "$ROOT/state/legacy/current_findings.json" <<'EOF'
{
  "scanner": "finops-security-cost-scan",
  "inventory": "/home/user/finops-cloud-costs/data/cloud_assets_legacy.json",
  "generated_at": "2024-11-30T16:05:00Z",
  "findings": []
}
EOF

    cat > "$ROOT/bin/finops_security_scan.py" <<'EOF'
#!/usr/bin/env python3
"""
Local FinOps security cost scanner.

Reads a TOML configuration file, loads the configured cloud inventory, applies
security-oriented cost rules, and writes the configured current_findings JSON
artifact under the configured state directory.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_CONFIG = "/home/user/finops-cloud-costs/config/security-scan.toml"


PUBLIC_STORAGE_RECOMMENDATION = (
    "Disable public access blocks exceptions and validate bucket policy before "
    "committing additional storage spend."
)
UNENCRYPTED_VOLUME_RECOMMENDATION = (
    "Enable encryption at rest or migrate data to an encrypted volume before "
    "the next billing cycle."
)
OPEN_ADMIN_PORT_RECOMMENDATION = (
    "Restrict administrative ingress to approved corporate CIDR ranges or "
    "replace direct access with a managed session service."
)


def parse_scalar(value):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def load_toml_config(path):
    """Parse the small TOML configuration used by this scanner."""
    config = {}
    section = None
    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                config.setdefault(section, {})
                continue
            if "=" in line and section:
                key, value = line.split("=", 1)
                config[section][key.strip()] = parse_scalar(value)
    return config


def base_finding(asset, issue, severity, recommendation):
    return {
        "resource_id": asset["resource_id"],
        "service": asset["service"],
        "region": asset["region"],
        "severity": severity,
        "monthly_cost_usd": asset["monthly_cost_usd"],
        "cost_owner": asset["cost_owner"],
        "issue": issue,
        "recommendation": recommendation,
    }


def build_findings(inventory, rules):
    findings = []
    min_cost = float(rules.get("minimum_monthly_cost_usd", 0))
    admin_ports = {22, 3389}

    for asset in inventory.get("assets", []):
        service = asset.get("service")
        monthly_cost = float(asset.get("monthly_cost_usd", 0))

        if (
            rules.get("flag_public_storage", False)
            and service == "s3"
            and asset.get("public_access") is True
        ):
            findings.append(
                base_finding(
                    asset,
                    "public_storage",
                    "CRITICAL" if monthly_cost >= min_cost else "HIGH",
                    PUBLIC_STORAGE_RECOMMENDATION,
                )
            )

        if (
            rules.get("flag_unencrypted_volumes", False)
            and asset.get("encrypted") is False
            and monthly_cost >= min_cost
        ):
            findings.append(
                base_finding(
                    asset,
                    "unencrypted_volume",
                    "HIGH",
                    UNENCRYPTED_VOLUME_RECOMMENDATION,
                )
            )

        if (
            rules.get("flag_open_admin_ports", False)
            and any(port in admin_ports for port in asset.get("open_ports", []))
        ):
            findings.append(
                base_finding(
                    asset,
                    "open_admin_port",
                    "CRITICAL",
                    OPEN_ADMIN_PORT_RECOMMENDATION,
                )
            )

    findings.sort(key=lambda item: (item["resource_id"], item["issue"]))

    for index, finding in enumerate(findings, start=1):
        finding["finding_id"] = f"FSC-{index:03d}"

    ordered = []
    for finding in findings:
        ordered.append(
            {
                "finding_id": finding["finding_id"],
                "resource_id": finding["resource_id"],
                "service": finding["service"],
                "region": finding["region"],
                "severity": finding["severity"],
                "monthly_cost_usd": finding["monthly_cost_usd"],
                "cost_owner": finding["cost_owner"],
                "issue": finding["issue"],
                "recommendation": finding["recommendation"],
            }
        )
    return ordered


def run_scan(config_path):
    config = load_toml_config(config_path)

    scanner_name = config["scanner"]["name"]
    inventory_path = config["input"]["inventory"]
    state_dir = config["output"]["state_dir"]
    current_findings_name = config["output"]["current_findings"]

    with open(inventory_path, "r", encoding="utf-8") as fh:
        inventory = json.load(fh)

    result = {
        "scanner": scanner_name,
        "inventory": inventory_path,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "findings": build_findings(inventory, config.get("rules", {})),
    }

    Path(state_dir).mkdir(parents=True, exist_ok=True)
    output_path = os.path.join(state_dir, current_findings_name)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")

    print(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Run the FinOps security cost scan.")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Path to security-scan TOML configuration.",
    )
    args = parser.parse_args()
    run_scan(args.config)


if __name__ == "__main__":
    main()
EOF

    chmod 755 "$ROOT/bin/finops_security_scan.py"
    chown -R user:user /home/user
    chmod -R u+rwX,go+rX "$ROOT"
    chmod -R u+w "$ROOT"

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
