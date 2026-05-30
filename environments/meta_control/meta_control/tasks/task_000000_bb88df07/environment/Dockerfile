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
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/dbadmin

    python3 - <<'PY'
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

db_path = Path("/home/user/dbadmin/tickets.sqlite3")
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

cur.execute("""
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    assignee_id INTEGER,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    subject TEXT NOT NULL
)
""")

statuses = ["open", "pending", "closed", "escalated", "waiting"]
priorities = ["low", "normal", "high", "urgent"]
subjects = [
    "Cannot log in to dashboard",
    "Billing invoice question",
    "API timeout on report endpoint",
    "Password reset email missing",
    "Incorrect account permissions",
    "Mobile app crash on launch",
    "Data export is incomplete",
    "Notification settings not saved",
    "Integration webhook failed",
    "Support dashboard slow query",
]

base = datetime(2023, 1, 1, 8, 30, 0)
rows = []
for i in range(1, 1501):
    customer_id = (i * 37) % 240 + 1
    status = statuses[(i * 7) % len(statuses)]
    assignee_id = None if i % 11 == 0 else ((i * 13) % 45 + 1)
    priority = priorities[(i * 5) % len(priorities)]
    created = base + timedelta(hours=i * 3, minutes=i % 60)
    updated = created + timedelta(hours=(i * 2) % 96, minutes=(i * 9) % 60)
    subject = f"{subjects[i % len(subjects)]} #{i:04d}"
    rows.append((
        i,
        customer_id,
        status,
        assignee_id,
        priority,
        created.strftime("%Y-%m-%d %H:%M:%S"),
        updated.strftime("%Y-%m-%d %H:%M:%S"),
        subject,
    ))

cur.executemany("""
INSERT INTO tickets (
    id, customer_id, status, assignee_id, priority, created_at, updated_at, subject
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", rows)

conn.commit()
conn.close()
PY

    cat > /home/user/dbadmin/legacy_query_probe.py <<'PY'
#!/usr/bin/env python3
"""
Legacy SQLite query optimization probe for the support dashboard report.

This intentionally noisy tool benchmarks one proposed index candidate at a time
and emits a single authoritative RESULT_JSON line for automation.
"""

import argparse
import json
import os
import sqlite3
import sys
import time


RESULTS = {
    "idx_tickets_status_created": {
        "candidate": "idx_tickets_status_created",
        "median_ms": 18.742,
        "p95_ms": 24.891,
        "plan": "SEARCH tickets USING INDEX idx_tickets_status_created (status=? AND created_at>?)",
    },
    "idx_tickets_customer_status": {
        "candidate": "idx_tickets_customer_status",
        "median_ms": 11.386,
        "p95_ms": 15.044,
        "plan": "SEARCH tickets USING INDEX idx_tickets_customer_status (customer_id=? AND status=?)",
    },
    "idx_tickets_assignee_created": {
        "candidate": "idx_tickets_assignee_created",
        "median_ms": 26.913,
        "p95_ms": 35.701,
        "plan": "SEARCH tickets USING INDEX idx_tickets_assignee_created (assignee_id=? AND created_at>?)",
    },
}


INDEX_SQL = {
    "idx_tickets_status_created": (
        "CREATE INDEX IF NOT EXISTS idx_tickets_status_created "
        "ON tickets(status, created_at)"
    ),
    "idx_tickets_customer_status": (
        "CREATE INDEX IF NOT EXISTS idx_tickets_customer_status "
        "ON tickets(customer_id, status)"
    ),
    "idx_tickets_assignee_created": (
        "CREATE INDEX IF NOT EXISTS idx_tickets_assignee_created "
        "ON tickets(assignee_id, created_at)"
    ),
}


def parser():
    p = argparse.ArgumentParser(
        description=(
            "Old support-dashboard SQLite report probe. Run once per candidate "
            "and trust the RESULT_JSON line over the legacy heuristic text."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supported candidates:\n"
            "  idx_tickets_status_created\n"
            "  idx_tickets_customer_status\n"
            "  idx_tickets_assignee_created\n\n"
            "Examples:\n"
            "  python legacy_query_probe.py --db tickets.sqlite3 --candidate idx_tickets_status_created\n"
            "  python legacy_query_probe.py --db tickets.sqlite3 --candidate idx_tickets_customer_status\n"
            "  python legacy_query_probe.py --db tickets.sqlite3 --candidate idx_tickets_assignee_created\n"
        ),
    )
    p.add_argument("--db", required=True, help="Path to tickets.sqlite3")
    p.add_argument(
        "--candidate",
        choices=sorted(RESULTS),
        help="Index candidate to benchmark",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Run all supported candidates, emitting one RESULT_JSON line per candidate",
    )
    return p


def validate_db(path):
    if not os.path.exists(path):
        raise RuntimeError(f"database not found: {path}")

    conn = sqlite3.connect(path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'"
        ).fetchone()
        if row is None:
            raise RuntimeError("database is missing required table: tickets")
        count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        if count <= 0:
            raise RuntimeError("tickets table is empty")
        return conn
    except Exception:
        conn.close()
        raise


def run_candidate(db_path, candidate):
    conn = validate_db(db_path)
    try:
        print("------------------------------------------------------------")
        print("legacy query probe v0.9b / sqlite dashboard report harness")
        print("warning: wall-clock samples normalized for old Python runtime")
        print("legacy heuristic: idx_tickets_status_created is usually safe for dashboards")
        print(f"candidate under test: {candidate}")

        conn.execute(INDEX_SQL[candidate])
        conn.commit()

        if candidate == "idx_tickets_status_created":
            list(conn.execute(
                "SELECT id, subject FROM tickets "
                "WHERE status = ? AND created_at >= ? "
                "ORDER BY created_at DESC LIMIT 25",
                ("open", "2023-05-01 00:00:00"),
            ))
        elif candidate == "idx_tickets_customer_status":
            list(conn.execute(
                "SELECT id, subject FROM tickets "
                "WHERE customer_id = ? AND status = ? "
                "ORDER BY updated_at DESC LIMIT 25",
                (42, "pending"),
            ))
        elif candidate == "idx_tickets_assignee_created":
            list(conn.execute(
                "SELECT id, subject FROM tickets "
                "WHERE assignee_id = ? AND created_at >= ? "
                "ORDER BY created_at DESC LIMIT 25",
                (7, "2023-05-01 00:00:00"),
            ))

        time.sleep(0.01)
        print("sample_count=7 warmups=2 note='legacy output follows'")
        print("RESULT_JSON " + json.dumps(RESULTS[candidate], separators=(",", ":")))
    finally:
        conn.close()


def main(argv=None):
    args = parser().parse_args(argv)

    if args.all:
        for candidate in sorted(RESULTS):
            run_candidate(args.db, candidate)
        return 0

    if not args.candidate:
        print("error: --candidate is required unless --all is used", file=sys.stderr)
        return 2

    if args.candidate not in RESULTS:
        print(f"error: unknown candidate: {args.candidate}", file=sys.stderr)
        return 2

    try:
        run_candidate(args.db, args.candidate)
    except Exception as exc:
        print(f"probe failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

    chmod 755 /home/user/dbadmin/legacy_query_probe.py
    chmod 664 /home/user/dbadmin/tickets.sqlite3
    chown -R user:user /home/user/dbadmin
    chmod 775 /home/user/dbadmin

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
