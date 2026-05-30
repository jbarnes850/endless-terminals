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

    if ! id user >/dev/null 2>&1; then
        useradd -m -u 1000 -s /bin/bash user
    fi

    mkdir -p /home/user/observability/snapshots

    cat > /home/user/observability/snapshots/candidate-a.prom <<'EOF'
# HELP http_requests_total Total HTTP requests handled by api-gateway.
# TYPE http_requests_total counter
http_requests_total{service="api-gateway",code="200"} 11920
http_requests_total{service="api-gateway",code="500"} 23
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total{service="api-gateway"} 842.17
# HELP up Whether the last scrape of the target was successful.
# TYPE up gauge
up{job="api-gateway"} 1
# scrape_time_seconds 0.084
EOF

    cat > /home/user/observability/snapshots/candidate-b.prom <<'EOF'
# HELP http_requests_total Total HTTP requests handled by api-gateway.
# TYPE http_requests_total counter
http_requests_total{service="api-gateway",code="200"} 14
http_requests_total{service="api-gateway",code="500"} 0
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total{service="api-gateway"} 3.92
# HELP up Whether the last scrape of the target was successful.
# TYPE up gauge
up{job="api-gateway"} 1
# scrape_time_seconds 0.071
# note fresh pod after restart
EOF

    cat > /home/user/observability/snapshots/candidate-c.prom <<'EOF'
# HELP http_requests_total Total HTTP requests handled by api-gateway.
# TYPE http_requests_total counter
http_requests_total{service="api-gateway",code="200"} 11888
http_requests_total{service="api-gateway",code="500"} 25
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total{service="api-gateway"} 846.44
# HELP up Whether the last scrape of the target was successful.
# TYPE up gauge
up{job="api-gateway"} 1
# scrape_time_seconds 0.079
EOF

    cat > /home/user/observability/snapshots/candidate-d.prom <<'EOF'
# HELP http_requests_total Total HTTP requests handled by api-gateway.
# TYPE http_requests_total counter
http_requests_total{service="api-gateway",code="200"} 12001
http_requests_total{service="api-gateway",code="500"} 24
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total{service="api-gateway"} 848.03
# HELP up Whether the last scrape of the target was successful.
# TYPE up gauge
up{job="api-gateway"} 0
# scrape_time_seconds 5.000
EOF

    cat > /home/user/observability/snapshots/candidate-e.prom <<'EOF'
# HELP http_requests_total Total HTTP requests handled by api-gateway.
# TYPE http_requests_total counter
http_requests_total{service="api-gateway",code="200"} 87422
http_requests_total{service="api-gateway",code="500"} 611
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total{service="api-gateway"} 1219.64
# HELP up Whether the last scrape of the target was successful.
# TYPE up gauge
up{job="api-gateway"} 1
# scrape_time_seconds 0.093
# note canary load-test window
EOF

    cat > /home/user/observability/snapshots/candidate-f.prom <<'EOF'
# HELP http_requests_total Total HTTP requests handled by api-gateway.
# TYPE http_requests_total counter
http_requests_total{service="api-gateway",code="200"} 11937
http_requests_total{service="api-gateway",code="500"} 24
# HELP up Whether the last scrape of the target was successful.
# TYPE up gauge
up{job="api-gateway"} 1
# scrape_time_seconds 0.077
EOF

    cat > /home/user/observability/snapshots/candidate-g.prom <<'EOF'
# HELP http_requests_total Total HTTP requests handled by api-gateway.
# TYPE http_requests_total counter
http_requests_total{service="api-gateway",code="200"} 11891
http_requests_total{service="api-gateway",code="500"} 24
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total{service="api-gateway"} 845.20
# HELP up Whether the last scrape of the target was successful.
# TYPE up gauge
up{job="api-gateway"} 1
# ERROR exporter returned partial response
# scrape_time_seconds 0.081
EOF

    cat > /home/user/observability/snapshots/README.txt <<'EOF'
Candidate snapshots were copied from staging scrapes. Prefer evidence in the .prom files.
EOF

    chown -R user:user /home/user/observability
    chmod -R u+rwX,go+rX /home/user/observability
    chmod 775 /home/user/observability /home/user/observability/snapshots

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
