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
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    BASE=/home/user/dbadmin_link_lab

    mkdir -p \
        "$BASE/bin" \
        "$BASE/workloads/checkout/sql" \
        "$BASE/workloads/checkout/stats" \
        "$BASE/workloads/inventory/sql" \
        "$BASE/workloads/inventory/stats" \
        "$BASE/shared" \
        "$BASE/active"

    cat > "$BASE/workloads/checkout/sql/schema.sql" <<'EOF'
-- workload: checkout
CREATE TABLE checkout_orders (
    order_id bigint PRIMARY KEY,
    customer_id bigint NOT NULL,
    created_at timestamp NOT NULL,
    status text NOT NULL
);

CREATE INDEX checkout_orders_customer_created_idx
    ON checkout_orders (customer_id, created_at DESC);
EOF

    cat > "$BASE/workloads/checkout/stats/pg_stats_snapshot.json" <<'EOF'
{
  "workload": "checkout",
  "captured_at": "2024-05-17T10:15:00Z",
  "tables": {
    "checkout_orders": {
      "rows": 1842500,
      "dead_tuple_percent": 2.7
    }
  }
}
EOF

    cat > "$BASE/workloads/checkout/sql/candidate_queries.sql" <<'EOF'
-- checkout candidate queries
EXPLAIN (ANALYZE, BUFFERS)
SELECT order_id, created_at, status
FROM checkout_orders
WHERE customer_id = $1
ORDER BY created_at DESC
LIMIT 20;
EOF

    cat > "$BASE/workloads/inventory/sql/schema.sql" <<'EOF'
-- workload: inventory
CREATE TABLE inventory_items (
    sku text PRIMARY KEY,
    warehouse_id integer NOT NULL,
    quantity integer NOT NULL
);
EOF

    cat > "$BASE/workloads/inventory/stats/pg_stats_snapshot.json" <<'EOF'
{
  "workload": "inventory",
  "captured_at": "2024-05-17T11:00:00Z",
  "tables": {
    "inventory_items": {
      "rows": 91240,
      "dead_tuple_percent": 0.6
    }
  }
}
EOF

    cat > "$BASE/workloads/inventory/sql/candidate_queries.sql" <<'EOF'
-- inventory candidate queries
EXPLAIN (ANALYZE, BUFFERS)
SELECT sku, quantity
FROM inventory_items
WHERE warehouse_id = $1
ORDER BY sku;
EOF

    cat > "$BASE/shared/dba_tuning_notes.md" <<'EOF'
# DBA Tuning Notes

- Prefer workload-specific schema, stats, and candidate query files.
- Keep active pointers as relative symbolic links.
- Re-run the active link checker after every rotation.
EOF

    cat > "$BASE/bin/check_active_links.py" <<'EOF'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

base = Path("/home/user/dbadmin_link_lab")
active = base / "active"

expected = {
    "current_schema.sql": base / "workloads/checkout/sql/schema.sql",
    "current_stats.json": base / "workloads/checkout/stats/pg_stats_snapshot.json",
    "current_queries.sql": base / "workloads/checkout/sql/candidate_queries.sql",
    "tuning_notes.md": base / "shared/dba_tuning_notes.md",
}

errors = []
for name, expected_abs in expected.items():
    p = active / name
    if not p.exists() and not p.is_symlink():
        errors.append(f"{name}: missing")
        continue
    if not p.is_symlink():
        errors.append(f"{name}: not a symlink")
        continue
    target_text = os.readlink(p)
    if os.path.isabs(target_text):
        errors.append(f"{name}: target is absolute")
        continue
    resolved = (p.parent / target_text).resolve()
    if resolved != expected_abs.resolve():
        errors.append(f"{name}: wrong target {target_text}")

if errors:
    for err in errors:
        print(err)
    sys.exit(1)

# Deliberately sparse success feedback to train against premature stopping.
sys.exit(0)
EOF
    chmod 755 "$BASE/bin/check_active_links.py"

    cp "$BASE/workloads/inventory/sql/schema.sql" "$BASE/active/current_schema.sql"

    ln -s "/home/user/dbadmin_link_lab/workloads/inventory/stats/pg_stats_snapshot.json" \
        "$BASE/active/current_stats.json"

    ln -s "../workloads/checkout/sql/candidate_queries.sql" \
        "$BASE/active/current_queries.sql"

    ln -s "../shared/old_tuning_notes.md" \
        "$BASE/active/tuning_notes.md"

    rm -f "$BASE/active/link_verification_report.txt"

    chown -R user:user /home/user
    chmod -R u+rwX /home/user/dbadmin_link_lab

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
