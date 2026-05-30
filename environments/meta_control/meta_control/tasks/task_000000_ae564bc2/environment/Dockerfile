FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! getent passwd user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/cloud-migration/legacy

    cat > /home/user/cloud-migration/legacy/.env <<'EOF'
BILLING_API_ENDPOINT=https://billing.internal.example.com/v1
BILLING_REGION=us-east-2
FEATURE_FLAG_LEDGER_V2=false
EOF

    rm -rf /home/user/cloud-migration/current
    rm -f /home/user/cloud-migration/migration-check.log

    chown -R user:user /home/user/cloud-migration
    chmod 755 /home/user
    chmod 755 /home/user/cloud-migration
    chmod 755 /home/user/cloud-migration/legacy
    chmod 644 /home/user/cloud-migration/legacy/.env

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
