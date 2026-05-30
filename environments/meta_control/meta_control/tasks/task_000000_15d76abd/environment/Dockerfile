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

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/netdebug

    cat > /home/user/netdebug/probes.jsonl <<'EOF'
{"source":"api-1","target":"auth.internal","port":443,"protocol":"tcp","status":"ok","error":"","rtt_ms":12.4}
{"source":"api-1","target":"db-primary.internal","port":5432,"protocol":"tcp","status":"fail","error":"connection timed out","rtt_ms":null}
{"source":"api-2","target":"auth.internal","port":443,"protocol":"tcp","status":"ok","error":"","rtt_ms":11.9}
{"source":"api-2","target":"cache.internal","port":6379,"protocol":"tcp","status":"fail","error":"no route to host","rtt_ms":null}
{"source":"api-3","target":"db-primary.internal","port":5432,"protocol":"tcp","status":"ok","error":"","rtt_ms":16.8}
{"source":"worker-1","target":"queue.internal","port":5672,"protocol":"tcp","status":"fail","error":"connection refused","rtt_ms":null}
{"source":"api-1","target":"cache.internal","port":6379,"protocol":"tcp","status":"ok","error":"","rtt_ms":4.1}
{"source":"worker-2","target":"queue.internal","port":5672,"protocol":"tcp","status":"ok","error":"","rtt_ms":8.5}
{"source":"api-3","target":"auth.internal","port":443,"protocol":"tcp","status":"fail","error":"tls handshake timeout","rtt_ms":null}
{"source":"worker-1","target":"db-primary.internal","port":5432,"protocol":"tcp","status":"fail","error":"connection timed out","rtt_ms":null}
EOF

    cat > /home/user/netdebug/build_report.py <<'EOF'
#!/usr/bin/env python3
import json
from pathlib import Path

base = Path("/home/user/netdebug")
input_path = base / "probes.jsonl"
output_path = base / "connectivity_report.txt"

# BUGGY HELPER: exits successfully but writes an incomplete report.
# It only records one failure per target, which loses source-specific failures.
seen_targets = set()
rows = []
with input_path.open() as f:
    for line in f:
        rec = json.loads(line)
        if rec.get("status") == "fail" and rec.get("target") not in seen_targets:
            seen_targets.add(rec.get("target"))
            rows.append((rec["source"], rec["target"], rec["port"], rec["error"]))

rows.sort(key=lambda r: (r[0], r[1], r[2]))

with output_path.open("w") as out:
    out.write("CONNECTIVITY FAILURE REPORT\n")
    out.write("source,target,port,error\n")
    for source, target, port, error in rows:
        out.write(f"{source},{target},{port},{error}\n")
    out.write(f"TOTAL_FAILURES={len(rows)}\n")
    out.write("VERIFIED=yes\n")

print(f"wrote {output_path}")
EOF

    chmod 755 /home/user
    chmod 755 /home/user/netdebug
    chmod 644 /home/user/netdebug/probes.jsonl
    chmod 755 /home/user/netdebug/build_report.py
    chown -R user:user /home/user/netdebug /home/user

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
