FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        sqlite3 \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest

    # Create the non-root user expected by the task environment.
    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    # Create required task directory tree.
    mkdir -p /home/user/pentest/legacy
    mkdir -p /home/user/pentest/current

    # Ensure no student-created output artifacts exist initially.
    rm -f /home/user/pentest/current/vulnscan.sqlite
    rm -f /home/user/pentest/current/migration_report.txt
    rm -f /home/user/pentest/legacy/vulnscan_old.sqlite.retired
    rm -f /home/user/pentest/legacy/vulnscan_old.sqlite

    # Create the legacy SQLite database with the exact expected schema and rows.
    sqlite3 /home/user/pentest/legacy/vulnscan_old.sqlite <<'SQL'
CREATE TABLE findings (
  id INTEGER PRIMARY KEY,
  host TEXT NOT NULL,
  port INTEGER NOT NULL,
  service TEXT NOT NULL,
  severity TEXT NOT NULL,
  cve TEXT NOT NULL,
  status TEXT NOT NULL
);

INSERT INTO findings (id, host, port, service, severity, cve, status) VALUES
  (101, '10.10.14.21', 22, 'ssh', 'medium', 'CVE-2023-38408', 'open'),
  (102, '10.10.14.21', 80, 'http', 'critical', 'CVE-2021-41773', 'open'),
  (103, '10.10.14.22', 443, 'https', 'high', 'CVE-2022-1388', 'closed'),
  (104, '10.10.14.23', 445, 'smb', 'critical', 'CVE-2020-0796', 'open'),
  (105, '10.10.14.24', 3306, 'mysql', 'high', 'CVE-2012-2122', 'false_positive'),
  (106, '10.10.14.25', 8080, 'http-proxy', 'low', 'CVE-2019-0220', 'open');
SQL

    # Set ownership and permissions so the non-root agent can complete the task.
    chown -R user:user /home/user
    chmod 755 /home/user
    chmod -R u+rwX,go+rX /home/user/pentest
    chmod 775 /home/user/pentest
    chmod 775 /home/user/pentest/legacy
    chmod 775 /home/user/pentest/current
    chmod 664 /home/user/pentest/legacy/vulnscan_old.sqlite

    # Clean package manager cache.
    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
