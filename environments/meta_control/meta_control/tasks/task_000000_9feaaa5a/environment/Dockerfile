FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pytest \
        iputils-ping \
        ca-certificates \
        netbase

    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/edge_diagnostics/reports

    cat > /home/user/edge_diagnostics/device_inventory.txt <<'EOF'
# Edge IoT rollout inventory for lab pod B
# Format: device_name endpoint

gateway-alpha 127.0.0.1
sensor-temp-01 localhost
camera-yard-03 192.0.2.77

# Spare node currently offline
meter-east-09 198.51.100.42
EOF

    chown -R user:user /home/user/edge_diagnostics
    chmod 755 /home/user
    chmod 755 /home/user/edge_diagnostics
    chmod 755 /home/user/edge_diagnostics/reports
    chmod 644 /home/user/edge_diagnostics/device_inventory.txt

    if ! grep -Eq '^[[:space:]]*127\.0\.0\.1[[:space:]].*\blocalhost\b' /etc/hosts; then
        printf '127.0.0.1 localhost\n' >> /etc/hosts
    fi

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
