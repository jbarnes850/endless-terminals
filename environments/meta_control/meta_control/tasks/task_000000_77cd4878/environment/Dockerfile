FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        bash \
        coreutils \
        grep

    python3 -m pip install --no-cache-dir pytest

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    BASE="/home/user/backup-restore-firewall"
    RESTORED_DIR="${BASE}/restored"
    ACTIVE_DIR="${BASE}/active"
    BIN_DIR="${BASE}/bin"
    VERIFY_DIR="${BASE}/verify"

    mkdir -p "${RESTORED_DIR}" "${ACTIVE_DIR}" "${BIN_DIR}" "${VERIFY_DIR}"

    cat > "${RESTORED_DIR}/iptables-restore.rules" <<'EOF'
# restored iptables backup from nightly restore test
-A INPUT -p tcp --dport 28731 -s 10.42.18.0/24 -j ACCEPT
COMMIT
EOF

    cat > "${ACTIVE_DIR}/firewall.policy" <<'EOF'
# active simulated firewall policy
ALLOW tcp 22 from 10.42.0.0/16
ALLOW tcp 873 from 10.42.18.0/24
DENY all
EOF

    cat > "${BIN_DIR}/check-firewall" <<'EOF'
#!/usr/bin/env bash
set -u

ACTIVE_POLICY="/home/user/backup-restore-firewall/active/firewall.policy"
STALE_POLICY="/home/user/backup-restore-firewall/restored/iptables-restore.rules"
REQUIRED_RULE="ALLOW tcp 28731 from 10.42.18.0/24"

if [ -e "$STALE_POLICY" ]; then
    printf 'FAIL stale restored policy still present\n'
    exit 2
fi

if [ ! -f "$ACTIVE_POLICY" ]; then
    printf 'FAIL active firewall missing backup restore listener\n'
    exit 1
fi

if grep -Fxq "$REQUIRED_RULE" "$ACTIVE_POLICY"; then
    printf 'PASS active firewall allows backup restore listener\n'
    exit 0
fi

printf 'FAIL active firewall missing backup restore listener\n'
exit 1
EOF

    chmod 0755 "${BIN_DIR}/check-firewall"
    chmod 0644 "${RESTORED_DIR}/iptables-restore.rules"
    chmod 0644 "${ACTIVE_DIR}/firewall.policy"

    chown -R user:user "${BASE}"
    chmod 0755 "${BASE}" "${RESTORED_DIR}" "${ACTIVE_DIR}" "${BIN_DIR}" "${VERIFY_DIR}"

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
