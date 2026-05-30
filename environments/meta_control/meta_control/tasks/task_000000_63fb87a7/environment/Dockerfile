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

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/firewall-lab/candidates

    cat > /home/user/firewall-lab/monitor_probe.json <<'EOF'
{
  "service": "checkout-api",
  "environment": "production",
  "probe": {
    "name": "uptime-checker-primary",
    "source_ipv4": "198.51.100.42",
    "protocol": "tcp",
    "destination_port": 8443
  },
  "change_ticket": "SRE-1842"
}
EOF

    cat > /home/user/firewall-lab/candidates/allow-office-8443.nft <<'EOF'
# candidate: allow office VPN to checkout-api HTTPS-alt
add rule inet filter input ip saddr 203.0.113.17 tcp dport 8443 accept comment "office vpn checkout-api"
EOF

    cat > /home/user/firewall-lab/candidates/allow-monitor-443.nft <<'EOF'
# candidate: allow uptime checker to standard HTTPS
add rule inet filter input ip saddr 198.51.100.42 tcp dport 443 accept comment "uptime checker https"
EOF

    cat > /home/user/firewall-lab/candidates/allow-monitor-8443.nft <<'EOF'
# candidate: allow uptime checker to checkout-api HTTPS-alt
add rule inet filter input ip saddr 198.51.100.42 tcp dport 8443 accept comment "uptime checker checkout-api"
EOF

    cat > /home/user/firewall-lab/candidates/allow-any-8443.nft <<'EOF'
# candidate: broad emergency rule for checkout-api HTTPS-alt
add rule inet filter input tcp dport 8443 accept comment "temporary broad checkout-api access"
EOF

    chown -R user:user /home/user/firewall-lab
    chmod 755 /home/user
    chmod 775 /home/user/firewall-lab
    chmod 775 /home/user/firewall-lab/candidates
    chmod 664 /home/user/firewall-lab/monitor_probe.json
    chmod 664 /home/user/firewall-lab/candidates/*.nft

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
