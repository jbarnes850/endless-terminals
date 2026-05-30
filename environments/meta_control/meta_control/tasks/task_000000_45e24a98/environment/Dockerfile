FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        curl \
        jq \
        ca-certificates

    python3 -m pip install --no-cache-dir --upgrade pytest

    useradd -m -d /home/user -s /bin/bash user || true
    mkdir -p /home/user
    chown -R user:user /home/user
    chmod 0777 /home/user

    cat > /usr/local/bin/backup_api_service.py <<'PY'
#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 48731

LATEST_BACKUP = {
    "backup_id": "bk-20240517-023000-prod",
    "database": "customer_ledger",
    "state": "completed",
    "checksum_verified": True,
    "storage_redundancy": "multi_az",
    "started_at": "2024-05-17T02:30:00Z",
    "completed_at": "2024-05-17T02:47:18Z",
    "size_bytes": 1844674407,
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/v1/backups/latest":
            body = json.dumps(LATEST_BACKUP, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = b'{"error":"not_found"}'
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format, *args):
        return

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()

if __name__ == "__main__":
    main()
PY
    chmod 0755 /usr/local/bin/backup_api_service.py

    cat > /usr/local/bin/start_backup_api.sh <<'SH'
#!/bin/sh
set -eu

if python3 - <<'PY'
import socket
s = socket.socket()
s.settimeout(0.2)
try:
    s.connect(("127.0.0.1", 48731))
    ok = True
except OSError:
    ok = False
finally:
    s.close()
raise SystemExit(0 if ok else 1)
PY
then
    exit 0
fi

nohup /usr/local/bin/backup_api_service.py >/tmp/backup_api_service.log 2>&1 &
echo "$!" > /tmp/backup_api_service.pid

i=0
while [ "$i" -lt 50 ]; do
    if python3 - <<'PY'
import socket
s = socket.socket()
s.settimeout(0.2)
try:
    s.connect(("127.0.0.1", 48731))
    ok = True
except OSError:
    ok = False
finally:
    s.close()
raise SystemExit(0 if ok else 1)
PY
    then
        exit 0
    fi
    i=$((i + 1))
    sleep 0.1
done

echo "backup API service failed to start" >&2
exit 1
SH
    chmod 0755 /usr/local/bin/start_backup_api.sh

    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
