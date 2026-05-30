FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        procps \
        ca-certificates

    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/backup_audit/manifests

    cat > /home/user/backup_audit/backup-integrity-worker <<'EOF'
#!/bin/sh
# Long-running placeholder used for process-management inspection tasks.
# Arguments are intentionally meaningful and should appear in ps output.
while :; do
  sleep 300
done
EOF

    chmod 755 /home/user/backup_audit/backup-integrity-worker

    touch /home/user/backup_audit/manifests/vault-prod-west-2024Q4.sha256
    touch /home/user/backup_audit/manifests/vault-prod-east-2024Q4.sha256
    touch /home/user/backup_audit/manifests/vault-prod-west-2024Q3.sha256

    chown -R user:user /home/user/backup_audit
    chmod 755 /home/user
    chmod 777 /home/user/backup_audit
    chmod 755 /home/user/backup_audit/manifests
    chmod 644 /home/user/backup_audit/manifests/*.sha256

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
