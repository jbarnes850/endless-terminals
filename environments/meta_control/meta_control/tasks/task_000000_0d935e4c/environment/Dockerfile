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

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -u 1000 -s /bin/bash user
    fi

    mkdir -p /home/user/cert-rollout/legacy
    mkdir -p /home/user/cert-rollout/deploy

    cat > /home/user/cert-rollout/legacy/live-api.pem <<'EOF'
# active certificate metadata
# common_name=api.staging.internal
# serial=7B:91:03:DE:44:18
# not_after=2026-08-17T23:59:59Z
-----BEGIN CERTIFICATE-----
MIIBPLACEHOLDERSTAGINGCERTDATA
-----END CERTIFICATE-----
EOF

    rm -f /home/user/cert-rollout/deploy/current-cert.env
    rm -f /home/user/cert-rollout/deploy/rollout-verification.log

    chown -R user:user /home/user/cert-rollout
    chmod 755 /home/user
    chmod 755 /home/user/cert-rollout
    chmod 755 /home/user/cert-rollout/legacy
    chmod 755 /home/user/cert-rollout/deploy
    chmod 644 /home/user/cert-rollout/legacy/live-api.pem

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
