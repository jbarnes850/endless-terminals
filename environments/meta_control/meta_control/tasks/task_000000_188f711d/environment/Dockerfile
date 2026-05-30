FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        sqlite3 \
        ca-certificates \
        bash

    python3 -m pip install --no-cache-dir pytest

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/tickets/TK-2048

    python3 <<'PY'
import sqlite3
from pathlib import Path

db_path = Path("/home/user/tickets/TK-2048/asset_cache.db")
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
CREATE TABLE assets (
    asset_id INTEGER PRIMARY KEY,
    hostname TEXT NOT NULL,
    owner TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT NOT NULL,
    last_seen TEXT NOT NULL
)
""")

rows = []
asset_id = 1

# Add the required target row exactly once.
rows.append((
    asset_id,
    "ws-finance-042",
    "finance-support",
    "floor-3-west",
    "active",
    "2024-05-17T09:35:00Z",
))
asset_id += 1

owners = [
    "engineering", "finance", "hr", "sales", "ops", "security",
    "legal", "support", "analytics", "platform"
]
locations = [
    "floor-1-east", "floor-1-west", "floor-2-east", "floor-2-west",
    "floor-3-east", "floor-3-west", "floor-4-east", "floor-4-west"
]
statuses = ["active", "inactive", "maintenance", "retired"]

# Many workstation hostnames, including multiple ws-* values.
for i in range(1, 4501):
    hostname = f"ws-{i:05d}"
    # Avoid accidentally duplicating the target hostname.
    if hostname == "ws-finance-042":
        hostname = f"ws-alt-{i:05d}"
    rows.append((
        asset_id,
        hostname,
        owners[i % len(owners)],
        locations[i % len(locations)],
        statuses[i % len(statuses)],
        f"2024-05-{(i % 28) + 1:02d}T{(i % 24):02d}:{(i * 7) % 60:02d}:00Z",
    ))
    asset_id += 1

# Add server/network/printer assets to exceed 8000 rows.
for i in range(1, 4201):
    prefix = ["srv", "net", "prt", "cam"][i % 4]
    hostname = f"{prefix}-{i:05d}"
    rows.append((
        asset_id,
        hostname,
        owners[(i + 3) % len(owners)],
        locations[(i + 5) % len(locations)],
        statuses[(i + 1) % len(statuses)],
        f"2024-04-{(i % 30) + 1:02d}T{(i * 3) % 24:02d}:{(i * 11) % 60:02d}:00Z",
    ))
    asset_id += 1

cur.executemany(
    """
    INSERT INTO assets(asset_id, hostname, owner, location, status, last_seen)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    rows,
)

conn.commit()

# Ensure there are no user-created indexes.
cur.execute("PRAGMA integrity_check")
assert cur.fetchone()[0] == "ok"
cur.execute("PRAGMA index_list(assets)")
indexes = cur.fetchall()
assert not [row for row in indexes if not row[1].startswith("sqlite_autoindex_")]

conn.close()
PY

    cat > /home/user/tickets/TK-2048/check_lookup.sh <<'SH'
#!/usr/bin/env bash
set -u

DB="/home/user/tickets/TK-2048/asset_cache.db"

python3 - "$DB" <<'PY'
import sqlite3
import sys

db_path = sys.argv[1]

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT asset_id, owner, location, status
        FROM assets
        WHERE hostname='ws-finance-042'
        """
    ).fetchone()

    if row is None:
        print("lookup=ws-finance-042 result=missing plan=unknown")
        sys.exit(2)

    _asset_id, owner, location, status = row
    if owner != "finance-support" or location != "floor-3-west" or status != "active":
        print("lookup=ws-finance-042 result=wrong plan=unknown")
        sys.exit(3)

    plan_rows = cur.execute(
        """
        EXPLAIN QUERY PLAN
        SELECT asset_id, owner, location, status
        FROM assets
        WHERE hostname='ws-finance-042'
        """
    ).fetchall()

    plan_text = " ".join(str(item) for plan_row in plan_rows for item in plan_row).upper()

    # Treat a SEARCH using an index as optimized. Without a hostname index,
    # SQLite reports a table scan for this lookup.
    if "USING INDEX" in plan_text or "USING COVERING INDEX" in plan_text:
        print("lookup=ws-finance-042 result=ok plan=index")
        sys.exit(0)

    print("lookup=ws-finance-042 result=ok plan=scan")
    sys.exit(1)

except sqlite3.Error:
    print("lookup=ws-finance-042 result=db-error plan=unknown")
    sys.exit(4)
finally:
    try:
        conn.close()
    except Exception:
        pass
PY
SH

    chmod 755 /home/user/tickets/TK-2048/check_lookup.sh
    chown -R user:user /home/user/tickets
    chmod 755 /home/user
    chmod 755 /home/user/tickets
    chmod 775 /home/user/tickets/TK-2048
    chmod 664 /home/user/tickets/TK-2048/asset_cache.db

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
