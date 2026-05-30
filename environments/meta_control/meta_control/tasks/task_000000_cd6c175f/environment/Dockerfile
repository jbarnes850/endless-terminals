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

    mkdir -p /home/user/cm-dns/legacy
    mkdir -p /home/user/cm-dns/current

    cat > /home/user/cm-dns/legacy/hosts.static <<'EOF'
# managed by old config-manager v1
10.44.8.21 api.internal.test api
10.44.8.22 cache.internal.test cache
10.44.8.20 app.internal.test app
10.44.8.25 db.internal.test db
EOF

    cat > /home/user/cm-dns/current/dns-overrides.zone <<'EOF'
# managed by config-manager v2
# TODO: migrate active host records from ../legacy/hosts.static
stale.internal.test A 192.0.2.99
EOF

    chmod -R a+rwX /home/user/cm-dns
    chmod a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
