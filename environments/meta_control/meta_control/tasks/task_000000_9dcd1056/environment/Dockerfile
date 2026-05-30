FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        ca-certificates
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/netops/sites/edge-a/state
    mkdir -p /home/user/netops/inventory/previous/edge-a

    cat > /home/user/netops/sites/edge-a/state/devices.csv <<'EOF'
device,mgmt_ip,role,status,last_checked
edge-a-fw01,10.42.10.1,firewall,reachable,2025-02-14T09:15:00Z
edge-a-sw02,10.42.10.12,switch,unreachable,2025-02-14T09:16:30Z
edge-a-rtr01,10.42.10.254,router,reachable,2025-02-14T09:17:45Z
EOF

    cat > /home/user/netops/sites/edge-a/state/endpoint.conf <<'EOF'
site=edge-a
source=legacy
inventory_dir=/home/user/netops/sites/edge-a/state
devices_file=/home/user/netops/sites/edge-a/state/devices.csv
EOF

    cat > /home/user/netops/sites/edge-a/state/migration_verify.log <<'EOF'
CHECKPOINT old_state_scanned
CHECKPOINT canonical_created
CHECKPOINT data_preserved
CHECKPOINT old_path_retired
CHECKPOINT endpoint_rotated
CANONICAL_DEVICE_COUNT=3
CANONICAL_DEVICE_LIST=edge-a-fw01|edge-a-rtr01|edge-a-sw02
EOF

    cat > /home/user/netops/inventory/previous/edge-a/devices.csv <<'EOF'
device,mgmt_ip,role,status,last_checked
edge-a-fw01,10.42.10.1,firewall,reachable,2025-02-13T09:15:00Z
edge-a-rtr01,10.42.10.254,router,reachable,2025-02-13T09:17:45Z
EOF

    rm -rf /home/user/netops/inventory/current

    chown -R user:user /home/user
    chmod -R a+rwX /home/user/netops
    chmod a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
