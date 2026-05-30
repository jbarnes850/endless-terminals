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

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/monitoring-migration/migrations

    cat > /home/user/monitoring-migration/migrations/002_add_alert_metadata.sql <<'EOF'
BEGIN TRANSACTION;

ALTER TABLE alerts ADD COLUMN notification_channel TEXT NOT NULL DEFAULT 'pagerduty';
ALTER TABLE alerts ADD COLUMN runbook_url TEXT NOT NULL DEFAULT 'https://runbooks.internal/alerts/default';

CREATE TABLE IF NOT EXISTS alert_metadata (
    alert_id INTEGER PRIMARY KEY,
    owner_team TEXT NOT NULL,
    escalation_minutes INTEGER NOT NULL CHECK(escalation_minutes > 0),
    FOREIGN KEY(alert_id) REFERENCES alerts(id)
);

INSERT INTO alert_metadata (alert_id, owner_team, escalation_minutes) VALUES
(1, 'platform-monitoring', 5),
(2, 'storage-monitoring', 30),
(3, 'api-monitoring', 10),
(4, 'platform-monitoring', 60);

INSERT INTO migration_history (version, applied_at)
VALUES ('002_add_alert_metadata', '2025-02-14T10:00:00Z');

COMMIT;
EOF

    python3 - <<'PY'
import sqlite3
from pathlib import Path

db_path = Path("/home/user/monitoring-migration/alerts.db")
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(db_path)
try:
    conn.executescript("""
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    severity TEXT NOT NULL,
    metric TEXT NOT NULL,
    threshold REAL NOT NULL,
    enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
);

CREATE TABLE migration_history (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

INSERT INTO alerts (id, name, severity, metric, threshold, enabled) VALUES
(1, 'High CPU saturation', 'critical', 'cpu_usage_percent', 95.0, 1),
(2, 'Disk space warning', 'warning', 'disk_used_percent', 85.0, 1),
(3, 'API latency critical', 'critical', 'api_latency_ms', 1200.0, 1),
(4, 'Memory pressure', 'warning', 'memory_used_percent', 90.0, 0);
""")
    conn.commit()
finally:
    conn.close()
PY

    cat > /home/user/monitoring-migration/validate_alerts.py <<'PY'
#!/usr/bin/env python3
import json
import sqlite3
import sys


def table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def column_names(conn, table):
    try:
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    except sqlite3.Error:
        return []


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_alerts.py /path/to/alerts.db", file=sys.stderr)
        return 2

    db_path = sys.argv[1]

    migration_applied = False
    schema_ok = False
    row_count_ok = False
    critical_alerts_ok = False

    try:
        conn = sqlite3.connect(db_path)
        try:
            history_rows = conn.execute(
                "SELECT version FROM migration_history WHERE version='002_add_alert_metadata'"
            ).fetchall()
            total_history = conn.execute(
                "SELECT COUNT(*) FROM migration_history"
            ).fetchone()[0]
            migration_applied = (len(history_rows) == 1 and total_history == 1)

            alerts_cols = column_names(conn, "alerts")
            schema_ok = (
                "notification_channel" in alerts_cols
                and "runbook_url" in alerts_cols
                and table_exists(conn, "alert_metadata")
            )

            row_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            row_count_ok = (row_count == 4)

            if schema_ok:
                critical_rows = conn.execute(
                    """
                    SELECT a.id, a.notification_channel, a.runbook_url, m.alert_id
                    FROM alerts a
                    LEFT JOIN alert_metadata m ON m.alert_id = a.id
                    WHERE a.severity='critical' AND a.enabled=1
                    ORDER BY a.id
                    """
                ).fetchall()
                critical_alerts_ok = (
                    len(critical_rows) == 2
                    and all(row[3] is not None for row in critical_rows)
                    and all(row[1] == "pagerduty" for row in critical_rows)
                    and all(isinstance(row[2], str) and row[2] != "" for row in critical_rows)
                )
        finally:
            conn.close()
    except sqlite3.Error:
        migration_applied = False
        schema_ok = False
        row_count_ok = False
        critical_alerts_ok = False

    all_ok = migration_applied and schema_ok and row_count_ok and critical_alerts_ok

    result = {
        "migration_applied": migration_applied,
        "schema_ok": schema_ok,
        "row_count_ok": row_count_ok,
        "critical_alerts_ok": critical_alerts_ok,
        "validation_status": "pass" if all_ok else "fail",
        "checklist": {
            "migration": "ok" if migration_applied else "fail",
            "schema": "ok" if schema_ok else "fail",
            "row_count": "ok" if row_count_ok else "fail",
            "critical_alerts": "ok" if critical_alerts_ok else "fail",
        },
    }

    print(json.dumps(result, separators=(", ", ": ")))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
PY

    chmod 755 /home/user/monitoring-migration/validate_alerts.py
    chmod 644 /home/user/monitoring-migration/migrations/002_add_alert_metadata.sql
    chmod 664 /home/user/monitoring-migration/alerts.db
    chown -R user:user /home/user/monitoring-migration

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
