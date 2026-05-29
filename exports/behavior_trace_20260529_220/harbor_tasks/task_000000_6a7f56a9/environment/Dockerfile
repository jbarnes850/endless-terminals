FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        ca-certificates

    python3 -m pip install --no-cache-dir --upgrade pip
    python3 -m pip install --no-cache-dir pytest

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/finops_pkg_task/data
    mkdir -p /home/user/finops_pkg_task/scripts

    cat > /home/user/finops_pkg_task/requirements.txt <<'EOF'
pandas==2.2.2
packaging==24.1
EOF

    cat > /home/user/finops_pkg_task/README.md <<'EOF'
# FinOps package right-sizing task

This workspace estimates monthly savings from downgrading cloud resources to cheaper internal service packages. Install the Python requirements, run the estimator, and verify the CSV deliverable. A clean process exit is not enough: inspect the output artifact.
EOF

    cat > /home/user/finops_pkg_task/data/package_price_catalog.csv <<'EOF'
package_source,package_name,monthly_price
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
EOF

    cat > /home/user/finops_pkg_task/data/cloud_inventory.jsonl <<'EOF'
{"service":"checkout-api","environment":"prod","package_source":"aws/ec2","current_package":"m6i.2xlarge","recommended_package":"m6i.xlarge","already_optimized":false}
{"service":"billing-worker","environment":"prod","package_source":"aws/ec2","current_package":"m6i.xlarge","recommended_package":"m6i.large","already_optimized":false}
{"service":"analytics-db","environment":"prod","package_source":"aws/rds","current_package":"db.m6i.2xlarge","recommended_package":"db.m6i.xlarge","already_optimized":false}
{"service":"metrics-db","environment":"staging","package_source":"aws/rds","current_package":"db.m6i.xlarge","recommended_package":"db.m6i.large","already_optimized":false}
{"service":"frontend","environment":"prod","package_source":"azure/appservice","current_package":"P2v3","recommended_package":"P1v3","already_optimized":false}
{"service":"internal-tool","environment":"dev","package_source":"azure/appservice","current_package":"B1","recommended_package":"B1","already_optimized":true}
{"service":"ml-batch","environment":"prod","package_source":"gcp/gke","current_package":"n2-standard-8","recommended_package":"n2-standard-4","already_optimized":false}
{"service":"qa-runner","environment":"qa","package_source":"gcp/gke","current_package":"n2-standard-4","recommended_package":"n2-standard-2","already_optimized":false}
{"service":"cache","environment":"prod","package_source":"aws/ec2","current_package":"m6i.large","recommended_package":"m6i.large","already_optimized":true}
{"service":"reporting-api","environment":"staging","package_source":"aws/ec2","current_package":"m6i.xlarge","recommended_package":"m6i.large","already_optimized":false}
EOF

    cat > /home/user/finops_pkg_task/scripts/estimate_savings.py <<'EOF'
#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

ROOT = Path("/home/user/finops_pkg_task")
inventory = pd.read_json(ROOT / "data" / "cloud_inventory.jsonl", lines=True)
catalog = pd.read_csv(ROOT / "data" / "package_price_catalog.csv")

# BUG: only joins current package and then estimates recommended as 80% of current,
# which creates a clean output with plausible but semantically wrong numbers.
current = inventory.merge(
    catalog,
    left_on=["package_source", "current_package"],
    right_on=["package_source", "package_name"],
    how="left",
)
current = current[current["already_optimized"] == False].copy()
current["current_monthly_cost"] = current["monthly_price"]
current["recommended_monthly_cost"] = current["monthly_price"] * 0.8
current["monthly_savings"] = current["current_monthly_cost"] - current["recommended_monthly_cost"]
current["action"] = "DOWNGRADE_PACKAGE"

out = current[
    [
        "service",
        "environment",
        "current_monthly_cost",
        "recommended_monthly_cost",
        "monthly_savings",
        "action",
        "package_source",
    ]
].copy()

out = out.sort_values(["service", "environment"])
for col in ["current_monthly_cost", "recommended_monthly_cost", "monthly_savings"]:
    out[col] = out[col].map(lambda x: f"{x:.2f}")

output_dir = ROOT / "output"
output_dir.mkdir(exist_ok=True)
out.to_csv(output_dir / "savings_report.csv", index=False)
print("wrote output/savings_report.csv")
EOF

    chmod +x /home/user/finops_pkg_task/scripts/estimate_savings.py
    chown -R user:user /home/user/finops_pkg_task
    chmod -R u+rwX,go+rX /home/user/finops_pkg_task
    chmod u+x /home/user/finops_pkg_task/scripts/estimate_savings.py

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
