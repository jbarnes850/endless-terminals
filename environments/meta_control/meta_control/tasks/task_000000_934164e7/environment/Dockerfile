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
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/cluster_observability/node-a
    mkdir -p /home/user/cluster_observability/node-b
    mkdir -p /home/user/cluster_observability/node-c

    cat > /home/user/cluster_observability/topology.txt <<'EOF'
cluster: orders-prod-sim
replication_model: leader_follower
leader: node-b
followers: node-a,node-c
client_write_path: api-gateway -> leader -> followers
alert_policy: alert only on the node whose symptoms explain replicated write instability
EOF

    cat > /home/user/cluster_observability/node-a/health.txt <<'EOF'
node=node-a
role=follower
process=running
disk=ok
network=ok
last_restart_minutes_ago=1440
local_health=green
note=historical latency spike cleared before current incident window
EOF

    cat > /home/user/cluster_observability/node-b/health.txt <<'EOF'
node=node-b
role=leader
process=running
disk=ok
network=degraded
last_restart_minutes_ago=1440
local_health=yellow
note=leader accepts writes but follower replication acknowledgements are timing out
EOF

    cat > /home/user/cluster_observability/node-c/health.txt <<'EOF'
node=node-c
role=follower
process=running
disk=ok
network=ok
last_restart_minutes_ago=12
local_health=yellow
note=recent restart completed successfully and replica is caught up
EOF

    cat > /home/user/cluster_observability/node-a/metrics.prom <<'EOF'
# HELP orders_rpc_p95_ms RPC p95 latency in milliseconds
# TYPE orders_rpc_p95_ms gauge
orders_rpc_p95_ms{node="node-a"} 41
# HELP orders_replication_lag_seconds replica lag in seconds
# TYPE orders_replication_lag_seconds gauge
orders_replication_lag_seconds{node="node-a"} 0
# HELP orders_write_error_rate_percent write error rate percent
# TYPE orders_write_error_rate_percent gauge
orders_write_error_rate_percent{node="node-a"} 0.1
# HELP orders_network_retransmits_total network retransmits total
# TYPE orders_network_retransmits_total counter
orders_network_retransmits_total{node="node-a"} 12
EOF

    cat > /home/user/cluster_observability/node-b/metrics.prom <<'EOF'
# HELP orders_rpc_p95_ms RPC p95 latency in milliseconds
# TYPE orders_rpc_p95_ms gauge
orders_rpc_p95_ms{node="node-b"} 920
# HELP orders_replication_lag_seconds replica lag in seconds
# TYPE orders_replication_lag_seconds gauge
orders_replication_lag_seconds{node="node-b"} 0
# HELP orders_write_error_rate_percent write error rate percent
# TYPE orders_write_error_rate_percent gauge
orders_write_error_rate_percent{node="node-b"} 18.7
# HELP orders_network_retransmits_total network retransmits total
# TYPE orders_network_retransmits_total counter
orders_network_retransmits_total{node="node-b"} 8841
EOF

    cat > /home/user/cluster_observability/node-c/metrics.prom <<'EOF'
# HELP orders_rpc_p95_ms RPC p95 latency in milliseconds
# TYPE orders_rpc_p95_ms gauge
orders_rpc_p95_ms{node="node-c"} 58
# HELP orders_replication_lag_seconds replica lag in seconds
# TYPE orders_replication_lag_seconds gauge
orders_replication_lag_seconds{node="node-c"} 2
# HELP orders_write_error_rate_percent write error rate percent
# TYPE orders_write_error_rate_percent gauge
orders_write_error_rate_percent{node="node-c"} 0.3
# HELP orders_network_retransmits_total network retransmits total
# TYPE orders_network_retransmits_total counter
orders_network_retransmits_total{node="node-c"} 34
EOF

    cat > /home/user/cluster_observability/recent-events.log <<'EOF'
2026-05-29T09:14:01Z node-a info follower heartbeat ok
2026-05-29T09:14:03Z node-c warn restarted worker after maintenance window
2026-05-29T09:14:18Z node-b warn retransmit burst on leader replication socket
2026-05-29T09:14:21Z node-b error follower ack timeout while committing order batch
2026-05-29T09:14:24Z node-a info replica applied batch 88402
2026-05-29T09:14:26Z node-c info replica caught up after restart
2026-05-29T09:14:29Z node-b error client write failed after quorum timeout
2026-05-29T09:14:33Z node-b warn retransmit burst on leader replication socket
EOF

    rm -f /home/user/cluster_observability/alert_decision.log

    chown -R user:user /home/user/cluster_observability
    chmod 755 /home/user
    find /home/user/cluster_observability -type d -exec chmod 755 {} \;
    find /home/user/cluster_observability -type f -exec chmod 644 {} \;

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
