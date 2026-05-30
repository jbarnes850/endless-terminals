FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        sqlite3 \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest

    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/releases

    rm -f /home/user/releases/releases_legacy.sqlite \
          /home/user/releases/releases_active.sqlite \
          /home/user/releases/releases_legacy.sqlite-journal \
          /home/user/releases/releases_active.sqlite-journal \
          /home/user/releases/deployment_verification.log

    sqlite3 /home/user/releases/releases_legacy.sqlite <<'SQL'
CREATE TABLE deployment_manifest (
    service TEXT,
    version TEXT,
    environment TEXT,
    approved INTEGER
);
INSERT INTO deployment_manifest (service, version, environment, approved) VALUES
    ('api-gateway', '2026.05.22', 'production', 1),
    ('billing-worker', '2026.05.22', 'production', 1),
    ('reporting-ui', '2026.05.22', 'staging', 0);
PRAGMA integrity_check;
SQL

    sqlite3 /home/user/releases/releases_active.sqlite <<'SQL'
CREATE TABLE deployment_manifest (
    service TEXT,
    version TEXT,
    environment TEXT,
    approved INTEGER
);
INSERT INTO deployment_manifest (service, version, environment, approved) VALUES
    ('api-gateway', '2026.05.15', 'production', 1),
    ('billing-worker', '2026.05.15', 'staging', 0);
PRAGMA integrity_check;
SQL

    chown -R user:user /home/user/releases
    chmod 0777 /home/user/releases
    chmod 0666 /home/user/releases/releases_legacy.sqlite /home/user/releases/releases_active.sqlite

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
