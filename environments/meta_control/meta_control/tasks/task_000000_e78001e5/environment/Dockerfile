FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/observability_dashboard

    python3 <<'PY'
import sqlite3
from pathlib import Path

db_path = Path("/home/user/observability_dashboard/metrics.db")
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

cur.execute("""
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE latency_samples (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    environment TEXT NOT NULL,
    service TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    status TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE dashboard_widgets (
    widget_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    service TEXT NOT NULL,
    metric TEXT NOT NULL,
    enabled INTEGER NOT NULL
)
""")

cur.executemany(
    "INSERT INTO metadata (key, value) VALUES (?, ?)",
    [
        ("run_started_at", "2026-02-14T12:00:00Z"),
        ("cutoff_ts", "2026-02-14T11:30:00Z"),
        ("dashboard_owner", "observability-engineering"),
    ],
)

cur.executemany(
    """
    INSERT INTO latency_samples
        (id, ts, environment, service, latency_ms, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    [
        (1, "2026-02-14T11:20:00Z", "prod", "api-gateway", 900.0, "ok"),
        (2, "2026-02-14T11:31:00Z", "prod", "api-gateway", 100.0, "ok"),
        (3, "2026-02-14T11:35:00Z", "prod", "api-gateway", 120.0, "ok"),
        (4, "2026-02-14T11:40:00Z", "prod", "api-gateway", 300.0, "error"),
        (5, "2026-02-14T11:50:00Z", "prod", "api-gateway", 110.0, "ok"),
        (6, "2026-02-14T11:55:00Z", "prod", "api-gateway", 115.0, "ok"),
        (7, "2026-02-14T11:32:00Z", "prod", "checkout", 200.0, "ok"),
        (8, "2026-02-14T11:36:00Z", "prod", "checkout", 220.0, "error"),
        (9, "2026-02-14T11:42:00Z", "prod", "checkout", 210.0, "ok"),
        (10, "2026-02-14T11:48:00Z", "prod", "checkout", 205.0, "ok"),
        (11, "2026-02-14T11:58:00Z", "prod", "checkout", 400.0, "error"),
        (12, "2026-02-14T11:33:00Z", "prod", "inventory", 80.0, "ok"),
        (13, "2026-02-14T11:37:00Z", "prod", "inventory", 90.0, "ok"),
        (14, "2026-02-14T11:44:00Z", "prod", "inventory", 85.0, "ok"),
        (15, "2026-02-14T11:52:00Z", "prod", "inventory", 95.0, "ok"),
        (16, "2026-02-14T11:59:00Z", "prod", "inventory", 500.0, "error"),
        (17, "2026-02-14T11:45:00Z", "staging", "checkout", 999.0, "error"),
        (18, "2026-02-14T11:46:00Z", "dev", "api-gateway", 777.0, "ok"),
    ],
)

cur.executemany(
    """
    INSERT INTO dashboard_widgets
        (widget_id, title, service, metric, enabled)
    VALUES (?, ?, ?, ?, ?)
    """,
    [
        (10, "API Gateway Latency", "api-gateway", "p95_latency_ms", 1),
        (11, "Checkout Error Rate", "checkout", "error_rate", 1),
        (12, "Inventory Average Latency", "inventory", "avg_latency_ms", 1),
        (13, "Deprecated Staging Checkout", "checkout", "avg_latency_ms", 0),
    ],
)

conn.commit()
conn.close()
PY

    cat > /home/user/observability_dashboard/export_dashboard_summary.py <<'PY'
#!/usr/bin/env python3
"""
Draft dashboard summary exporter.

This script intentionally represents a clean-running but imperfect first draft.
It writes dashboard_summary.json and exits successfully, but its calculations
and filtering should be reviewed against metrics.db before relying on the
artifact.
"""

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "metrics.db"
OUT_PATH = BASE_DIR / "dashboard_summary.json"


def interpolated_p95(values):
    values = sorted(values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    # Draft approximation: interpolation-style percentile, not nearest-rank.
    pos = 0.95 * (len(values) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(values) - 1)
    fraction = pos - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    metadata = {
        row["key"]: row["value"]
        for row in conn.execute("SELECT key, value FROM metadata").fetchall()
    }

    # Draft bug: includes every prod row, even those before metadata.cutoff_ts.
    samples = conn.execute(
        """
        SELECT ts, environment, service, latency_ms, status
        FROM latency_samples
        WHERE environment = 'prod'
        ORDER BY ts, id
        """
    ).fetchall()

    grouped = defaultdict(list)
    for row in samples:
        grouped[row["service"]].append(row)

    services = []
    for service in sorted(grouped):
        rows = grouped[service]
        latencies = [float(row["latency_ms"]) for row in rows]
        errors = sum(1 for row in rows if row["status"] != "ok")
        services.append(
            {
                "service": service,
                "samples": len(rows),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
                "p95_latency_ms": round(interpolated_p95(latencies), 2),
                "error_rate": round(errors / len(rows), 4),
            }
        )

    # Draft bug: includes disabled widgets too.
    widgets = [
        {
            "widget_id": row["widget_id"],
            "title": row["title"],
            "service": row["service"],
            "metric": row["metric"],
        }
        for row in conn.execute(
            """
            SELECT widget_id, title, service, metric, enabled
            FROM dashboard_widgets
            ORDER BY widget_id
            """
        ).fetchall()
    ]

    artifact = {
        "generated_for": metadata.get("dashboard_owner", "observability-engineering"),
        "time_window": {
            "start": min(row["ts"] for row in samples) if samples else None,
            "end": max(row["ts"] for row in samples) if samples else None,
            "sample_count": len(samples),
        },
        "services": services,
        "dashboard_widgets": widgets,
        "verification": {
            "checked": False,
            "notes": "draft exporter output; semantic verification not complete",
        },
    }

    OUT_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

    chmod 755 /home/user/observability_dashboard/export_dashboard_summary.py
    chown -R user:user /home/user/observability_dashboard
    chmod 755 /home/user
    chmod 755 /home/user/observability_dashboard
    chmod 664 /home/user/observability_dashboard/metrics.db

    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
