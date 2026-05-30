FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        passwd \
        ca-certificates
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/release-prep

    cat > /home/user/release-prep/deploy.env <<'EOF'
# Draft deployment environment for release manager
APP_NAME=inventory-api
DEPLOY_ENV=staging
RELEASE_CHANNEL=beta
REGION=us-west-1
CANARY_PERCENT=5
FEATURE_FLAGS=audit_logging,metrics_v2
DEBUG_MODE=false
EOF

    rm -f /home/user/release-prep/release_ledger.log

    chown -R user:user /home/user
    chmod 755 /home/user
    chmod 755 /home/user/release-prep
    chmod 644 /home/user/release-prep/deploy.env

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
