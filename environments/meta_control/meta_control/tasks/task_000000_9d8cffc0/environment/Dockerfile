FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/rollout/incoming
    mkdir -p /home/user/rollout/config
    mkdir -p /home/user/rollout/bin
    mkdir -p /home/user/rollout/staging

    cat > /home/user/rollout/config/release.env <<'EOF'
RELEASE_ID=2025-02-17-a
PIPELINE_VERSION=3
EOF

    cat > /home/user/rollout/incoming/events.csv <<'EOF'
event_id,user_id,event_type,event_ts,amount
1001,u-17,purchase,2025-02-17T09:00:00Z,42.50
1002,u-18,,2025-02-17T09:01:15Z,0
1003,u-19,signup,2025-02-17T09:03:21Z,0
1004,u-20,purchase,2025-02-17T09:05:00Z,18.75
EOF

    cat > /home/user/rollout/bin/deploy_pipeline.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

ROLLOUT="/home/user/rollout"
EVENTS="${ROLLOUT}/incoming/events.csv"
RELEASE_ENV="${ROLLOUT}/config/release.env"
STAGING="${ROLLOUT}/staging"
NORMALIZED="${STAGING}/events.normalized.csv"
REJECTED="${STAGING}/events.rejected.csv"

mkdir -p "${STAGING}"

python3 - <<'PY'
import csv
import os
from decimal import Decimal, ROUND_HALF_UP

rollout = "/home/user/rollout"
events_path = os.path.join(rollout, "incoming", "events.csv")
release_env_path = os.path.join(rollout, "config", "release.env")
staging = os.path.join(rollout, "staging")
normalized_path = os.path.join(staging, "events.normalized.csv")
rejected_path = os.path.join(staging, "events.rejected.csv")

release_id = None
with open(release_env_path, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line.startswith("RELEASE_ID="):
            release_id = line.split("=", 1)[1]
            break

if not release_id:
    raise SystemExit("RELEASE_ID not found")

os.makedirs(staging, exist_ok=True)

with open(events_path, "r", encoding="utf-8", newline="") as src, \
     open(normalized_path, "w", encoding="utf-8", newline="") as norm_fh, \
     open(rejected_path, "w", encoding="utf-8", newline="") as rej_fh:

    reader = csv.DictReader(src)
    norm_writer = csv.writer(norm_fh, lineterminator="\n")
    rej_writer = csv.writer(rej_fh, lineterminator="\n")

    norm_writer.writerow(["release_id", "event_id", "user_id", "event_type", "event_ts", "amount_cents"])
    rej_writer.writerow(["event_id", "user_id", "event_type", "event_ts", "amount", "reject_reason"])

    for row in reader:
        event_type = (row.get("event_type") or "").strip()
        if not event_type:
            rej_writer.writerow([
                row.get("event_id", ""),
                row.get("user_id", ""),
                row.get("event_type", ""),
                row.get("event_ts", ""),
                row.get("amount", ""),
                "missing_event_type",
            ])
            continue

        amount = Decimal(row.get("amount", "0"))
        amount_cents = int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        norm_writer.writerow([
            release_id,
            row.get("event_id", ""),
            row.get("user_id", ""),
            event_type,
            row.get("event_ts", ""),
            str(amount_cents),
        ])
PY
EOF

    cat > /home/user/rollout/bin/check_rollout.py <<'EOF'
#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

rollout = Path("/home/user/rollout")
normalized_path = rollout / "staging" / "events.normalized.csv"
rejected_path = rollout / "staging" / "events.rejected.csv"

def fail(message: str) -> int:
    print(f"rollout check failed: {message}", file=sys.stderr)
    return 1

if not normalized_path.exists():
    sys.exit(fail(f"missing {normalized_path}"))

if not rejected_path.exists():
    sys.exit(fail(f"missing {rejected_path}"))

with normalized_path.open("r", encoding="utf-8", newline="") as fh:
    normalized_rows = list(csv.DictReader(fh))

with rejected_path.open("r", encoding="utf-8", newline="") as fh:
    rejected_rows = list(csv.DictReader(fh))

if len(normalized_rows) != 4:
    sys.exit(fail(f"expected 4 normalized data rows, found {len(normalized_rows)}"))

if len(rejected_rows) != 0:
    sys.exit(fail(f"expected 0 rejected data rows, found {len(rejected_rows)}"))

row_1002 = next((row for row in normalized_rows if row.get("event_id") == "1002"), None)
if row_1002 is None:
    sys.exit(fail("missing normalized row for event_id=1002"))

if row_1002.get("event_type") != "unknown":
    sys.exit(fail("event_id=1002 must have event_type=unknown"))

bad_release_rows = [
    row.get("event_id", "<unknown>")
    for row in normalized_rows
    if row.get("release_id") != "2025-02-17-a"
]
if bad_release_rows:
    sys.exit(fail(f"normalized rows with incorrect release_id: {', '.join(bad_release_rows)}"))

print("rollout check ok")
sys.exit(0)
EOF

    chmod 0755 /home/user/rollout/bin/deploy_pipeline.sh
    chmod 0755 /home/user/rollout/bin/check_rollout.py

    chown -R user:user /home/user/rollout
    chmod 0755 /home/user
    chmod -R u+rwX /home/user/rollout
    chmod 0755 /home/user/rollout/bin/deploy_pipeline.sh /home/user/rollout/bin/check_rollout.py

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
