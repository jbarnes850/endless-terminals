FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        jq \
        gawk \
        sed \
        python3 \
        python3-pip \
        python3-pytest \
        netcat-openbsd \
        procps

    python3 -m pip install --no-cache-dir --upgrade pip
    python3 -m pip install --no-cache-dir pytest

    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/sre-uptime-check
    chown -R user:user /home/user
    chmod 755 /home/user
    chmod 777 /home/user/sre-uptime-check

    cat > /usr/local/bin/catalog_api_server.py <<'PY'
#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = 8097


HEALTH = {
    "status": "healthy",
    "component": "catalog-api",
    "checks": {"database": "pass", "cache": "pass"},
}

READY = {
    "status": "not_ready",
    "component": "catalog-api",
    "reason": "search-index-lag",
    "checks": {"database": "pass", "cache": "pass", "search_index": "fail"},
}

VERSION = {
    "name": "catalog-api",
    "version": "2.7.4",
    "git_sha": "9f4c1b8",
    "build_time": "2025-02-14T11:06:22Z",
}

METRICS = (
    "# HELP uptime_seconds Process uptime in seconds\n"
    "# TYPE uptime_seconds gauge\n"
    "uptime_seconds 86442\n"
    "# HELP request_success_total Total successful API requests\n"
    "# TYPE request_success_total counter\n"
    "request_success_total 128903\n"
    "# HELP request_error_total Total failed API requests\n"
    "# TYPE request_error_total counter\n"
    "request_error_total 7\n"
)

INCIDENTS = [
    {
        "id": "INC-1042",
        "severity": "minor",
        "summary": "search index lag above threshold",
        "opened_at": "2025-02-14T10:58:03Z",
        "resolved": False,
    }
]


class Handler(BaseHTTPRequestHandler):
    server_version = "CatalogAPITest/1.0"

    def log_message(self, fmt, *args):
        return

    def _send_json(self, status_code, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status_code, text):
        body = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, HEALTH)
        elif self.path == "/ready":
            self._send_json(503, READY)
        elif self.path == "/version":
            self._send_json(200, VERSION)
        elif self.path == "/metrics":
            self._send_text(200, METRICS)
        elif self.path == "/incidents/recent":
            self._send_json(200, INCIDENTS)
        else:
            self._send_json(404, {"error": "not found"})


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
PY

    chmod 755 /usr/local/bin/catalog_api_server.py

    cat > /usr/local/bin/start_catalog_api_if_needed.sh <<'SH'
#!/bin/sh
set -eu

if nc -z 127.0.0.1 8097 >/dev/null 2>&1; then
    exit 0
fi

/usr/local/bin/catalog_api_server.py >/tmp/catalog_api_server.log 2>&1 &

i=0
while [ "$i" -lt 50 ]; do
    if nc -z 127.0.0.1 8097 >/dev/null 2>&1; then
        exit 0
    fi
    i=$((i + 1))
    sleep 0.1
done

echo "catalog API server did not start on 127.0.0.1:8097" >&2
exit 1
SH

    chmod 755 /usr/local/bin/start_catalog_api_if_needed.sh

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
