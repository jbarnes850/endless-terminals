FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        bash \
        coreutils

    python3 -m pip install --no-cache-dir pytest

    rm -rf /var/lib/apt/lists/*

    # Create the non-root user expected by the task/tests.
    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    # Create required directory tree.
    mkdir -p /home/user/finops/cloud-costs/raw
    mkdir -p /home/user/finops/cloud-costs/audit
    mkdir -p /home/user/finops/cloud-costs/tmp

    # Create initial raw CSV files with exact contents.
    cat > /home/user/finops/cloud-costs/raw/aws_costs_january.csv <<'EOF'
account_id,service,region,usage_hours,cost_usd
1001,EC2,us-east-1,120,34.56
1001,S3,us-east-1,720,12.40
1002,RDS,us-west-2,240,88.10
EOF

    cat > /home/user/finops/cloud-costs/raw/azure_costs_january.csv <<'EOF'
subscription_id,service,region,usage_hours,cost_usd
sub-fin-01,Virtual Machines,eastus,96,41.25
sub-fin-01,Blob Storage,eastus,720,9.80
sub-eng-02,SQL Database,westus2,180,73.42
EOF

    cat > /home/user/finops/cloud-costs/raw/gcp_costs_january.csv <<'EOF'
project_id,service,region,usage_hours,cost_usd
proj-analytics,Compute Engine,us-central1,110,29.77
proj-analytics,Cloud Storage,us-central1,720,8.65
proj-ml,Cloud SQL,us-east1,200,66.31
EOF

    cat > /home/user/finops/cloud-costs/raw/README.txt <<'EOF'
Raw January cloud cost exports for FinOps optimization review.
Only CSV files in this directory are part of the checksum manifest.
EOF

    # Create tmp file that must not be included by the agent.
    cat > /home/user/finops/cloud-costs/tmp/aws_costs_january_copy.csv <<'EOF'
account_id,service,region,usage_hours,cost_usd
1001,EC2,us-east-1,120,34.56
1001,S3,us-east-1,720,12.40
1002,RDS,us-west-2,240,88.10
EOF

    # Create misleading helper script with exact contents.
    cat > /home/user/finops/cloud-costs/make_manifest.sh <<'EOF'
#!/usr/bin/env bash
set -e
mkdir -p /home/user/finops/cloud-costs/audit
md5sum /home/user/finops/cloud-costs/raw/* > /home/user/finops/cloud-costs/audit/cloud_cost_checksums.sha256
echo "manifest written"
EOF

    chmod 0755 /home/user/finops/cloud-costs/make_manifest.sh

    # Ensure the agent user owns and can write all task files/directories.
    chown -R user:user /home/user/finops
    chmod -R u+rwX /home/user/finops

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
