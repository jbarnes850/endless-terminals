FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        ca-certificates
    python3 -m pip install --no-cache-dir --upgrade pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/config_manager/baseline
    mkdir -p /home/user/config_manager/current
    mkdir -p /home/user/config_manager/out
    mkdir -p /home/user/config_manager/tools

    cat > /home/user/config_manager/baseline/api.conf <<'EOF'
# API service baseline configuration

host = api.internal.local
port = 8080
timeout = 30
log_level = info
feature_payments = false
allowed_origins: https://app.example.com,https://admin.example.com
max_connections = 200

# deprecated but still present
legacy_mode = enabled
EOF

    cat > /home/user/config_manager/current/api.conf <<'EOF'
# API service current configuration

host = api.internal.local
port=8081
timeout = 45
log_level = info
feature_payments = true
allowed_origins: https://app.example.com,https://admin.example.com
max_connections = 200
rate_limit_per_minute = 1200
EOF

    cat > /home/user/config_manager/baseline/worker.conf <<'EOF'
# Worker baseline
queue = default
concurrency = 4
retry_limit = 3
dead_letter_queue = worker-dlq
metrics_enabled: false
image_tag = worker:1.7.2
EOF

    cat > /home/user/config_manager/current/worker.conf <<'EOF'
# Worker current
queue = default
concurrency = 6
retry_limit = 3
dead_letter_queue = worker-dlq-v2
metrics_enabled: true
image_tag = worker:1.8.0
prefetch_count = 25
EOF

    cat > /home/user/config_manager/baseline/db.conf <<'EOF'
# Database baseline

engine = postgres
host = db01.internal.local
port = 5432
pool_min = 5
pool_max = 30
sslmode: require
backup_window = 02:00-03:00
read_replica = db-read-01.internal.local
EOF

    cat > /home/user/config_manager/current/db.conf <<'EOF'
# Database current

engine = postgres
host = db02.internal.local
port = 5432
pool_min = 5
pool_max = 50
sslmode: verify-full
backup_window = 01:00-02:00
statement_timeout = 60s
EOF

    cat > /home/user/config_manager/out/change_report.tsv <<'EOF'
component	key	change_type	baseline_value	current_value
api	port	modified	8080	8081
EOF

    cat > /home/user/config_manager/tools/verify_report.py <<'PY'
#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path("/home/user/config_manager")
BASELINE = ROOT / "baseline"
CURRENT = ROOT / "current"
REPORT = ROOT / "out" / "change_report.tsv"
HEADER = "component\tkey\tchange_type\tbaseline_value\tcurrent_value"

def parse_config(path: Path):
    data = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        data[key.strip()] = value.strip()
    return data

def expected_rows():
    rows = []
    baseline_files = {p.name: p for p in BASELINE.glob("*.conf") if p.is_file()}
    current_files = {p.name: p for p in CURRENT.glob("*.conf") if p.is_file()}
    for name in sorted(set(baseline_files) & set(current_files)):
        component = Path(name).stem
        b = parse_config(baseline_files[name])
        c = parse_config(current_files[name])
        for key in sorted(set(b) | set(c)):
            if key in b and key not in c:
                rows.append((component, key, "removed", b[key], ""))
            elif key not in b and key in c:
                rows.append((component, key, "added", "", c[key]))
            elif b[key] != c[key]:
                rows.append((component, key, "modified", b[key], c[key]))
    return sorted(rows, key=lambda r: (r[0], r[1], r[2]))

def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)

def main():
    if not REPORT.exists():
        fail(f"missing report: {REPORT}")

    content = REPORT.read_bytes()
    if b"\r" in content:
        fail("report contains carriage returns")
    if content and not content.endswith(b"\n"):
        fail("report must end with a Unix newline")

    text = content.decode("utf-8")
    lines = text.splitlines()
    if not lines:
        fail("report is empty")
    if lines[0] != HEADER:
        fail("invalid header")

    actual_lines = lines[1:]
    actual = []
    seen = set()
    for idx, line in enumerate(actual_lines, start=2):
        parts = line.split("\t")
        if len(parts) != 5:
            fail(f"line {idx} has {len(parts)} fields, expected 5")
        row = tuple(parts)
        if row in seen:
            fail(f"duplicate row on line {idx}")
        seen.add(row)
        actual.append(row)

    if actual != sorted(actual, key=lambda r: (r[0], r[1], r[2])):
        fail("rows are not sorted by component, key, change_type")

    expected = expected_rows()
    if actual != expected:
        print("report rows do not match expected changes", file=sys.stderr)
        print(f"expected {len(expected)} rows, got {len(actual)} rows", file=sys.stderr)
        sys.exit(1)

    print(f"OK rows={len(actual)}")

if __name__ == "__main__":
    main()
PY

    chmod 755 /home/user/config_manager/tools/verify_report.py

    chown -R user:user /home/user/config_manager
    chmod 755 /home/user
    chmod -R u+rwX,go+rX /home/user/config_manager
    chmod 775 /home/user/config_manager /home/user/config_manager/baseline /home/user/config_manager/current /home/user/config_manager/out /home/user/config_manager/tools

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
