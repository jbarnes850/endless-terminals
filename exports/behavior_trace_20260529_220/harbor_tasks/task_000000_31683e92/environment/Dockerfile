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
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    ROOT=/home/user/devops-log-lab
    mkdir -p "$ROOT/service" "$ROOT/env-candidates" "$ROOT/logs"

    : > "$ROOT/service/__init__.py"

    cat > "$ROOT/service/app.py" <<'PY'
"""Minimal local development service used for diagnostics.

The module can be imported as ``service.app`` from the repository root.  It
uses only Python's standard library and reads its configuration from
environment variables:

- APP_PROFILE
- APP_PORT
- CACHE_BACKEND
- DATABASE_URL
- FEATURE_FLAG_STREAM

For the intended local development configuration, the readiness/health JSON is
exactly:
{"status":"ok","profile":"development","cache":"memory","database":"sqlite","stream":"enabled","port":8127}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


EXPECTED_PROFILE = "development"
EXPECTED_PORT = 8127
EXPECTED_CACHE = "memory"
EXPECTED_DATABASE_URL = "sqlite:///tmp/devops_log_lab.sqlite3"
EXPECTED_STREAM = "enabled"


def _configured_port() -> int:
    raw = os.environ.get("APP_PORT", "")
    try:
        return int(raw)
    except ValueError:
        return -1


def _database_kind(database_url: str) -> str:
    if database_url.startswith("sqlite:"):
        return "sqlite"
    if database_url.startswith("postgresql:") or database_url.startswith("postgres:"):
        return "postgresql"
    if "://" in database_url:
        return database_url.split("://", 1)[0]
    return "unknown"


def current_config() -> dict[str, Any]:
    """Return the current environment-derived service configuration."""
    return {
        "profile": os.environ.get("APP_PROFILE", ""),
        "port": _configured_port(),
        "cache": os.environ.get("CACHE_BACKEND", ""),
        "database_url": os.environ.get("DATABASE_URL", ""),
        "database": _database_kind(os.environ.get("DATABASE_URL", "")),
        "stream": os.environ.get("FEATURE_FLAG_STREAM", ""),
    }


def readiness() -> dict[str, Any]:
    """Return a compact readiness result for the current configuration.

    The selected local development configuration returns the exact JSON object
    expected by the diagnostics task.  Other plausible configurations return a
    structured failure object with a decisive symptom.
    """
    cfg = current_config()

    if cfg["cache"] == "redis":
        return {
            "status": "fail",
            "reason": "cache backend redis unavailable on localhost:6379",
            "profile": cfg["profile"],
            "cache": cfg["cache"],
            "database": cfg["database"],
            "stream": cfg["stream"],
            "port": cfg["port"],
        }

    if cfg["database"] == "postgresql":
        return {
            "status": "fail",
            "reason": "database backend postgresql not available in local dev container",
            "profile": cfg["profile"],
            "cache": cfg["cache"],
            "database": cfg["database"],
            "stream": cfg["stream"],
            "port": cfg["port"],
        }

    if cfg["port"] != EXPECTED_PORT:
        return {
            "status": "fail",
            "reason": f"expected dev port {EXPECTED_PORT} but candidate configured {cfg['port']}",
            "profile": cfg["profile"],
            "cache": cfg["cache"],
            "database": cfg["database"],
            "stream": cfg["stream"],
            "port": cfg["port"],
        }

    if (
        cfg["profile"] == EXPECTED_PROFILE
        and cfg["port"] == EXPECTED_PORT
        and cfg["cache"] == EXPECTED_CACHE
        and cfg["database_url"] == EXPECTED_DATABASE_URL
        and cfg["stream"] == EXPECTED_STREAM
    ):
        return {
            "status": "ok",
            "profile": "development",
            "cache": "memory",
            "database": "sqlite",
            "stream": "enabled",
            "port": 8127,
        }

    return {
        "status": "fail",
        "reason": "configuration does not match local development readiness requirements",
        "profile": cfg["profile"],
        "cache": cfg["cache"],
        "database": cfg["database"],
        "stream": cfg["stream"],
        "port": cfg["port"],
    }


def health() -> dict[str, Any]:
    """Alias for the intended readiness/health mechanism."""
    return readiness()


def ready() -> dict[str, Any]:
    return readiness()


def healthcheck() -> dict[str, Any]:
    return readiness()


def get_health() -> dict[str, Any]:
    return readiness()


def get_readiness() -> dict[str, Any]:
    return readiness()


def build_health() -> dict[str, Any]:
    return readiness()


def current_health() -> dict[str, Any]:
    return readiness()


def health_json() -> str:
    return json.dumps(readiness(), separators=(",", ":"))


def run_readiness_check() -> dict[str, Any]:
    result = readiness()
    print(json.dumps(result, separators=(",", ":")))
    return result


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        path = urlparse(self.path).path
        if path not in {"/health", "/ready", "/readiness", "/"}:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found\n")
            return

        payload = readiness()
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        status = 200 if payload.get("status") == "ok" else 503

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("service.app:", fmt % args, file=sys.stderr)


def serve() -> None:
    port = _configured_port()
    if port <= 0:
        raise SystemExit("APP_PORT must be an integer port")
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    print(f"service.app listening on 127.0.0.1:{port}", flush=True)
    server.serve_forever()


def main() -> dict[str, Any] | None:
    parser = argparse.ArgumentParser(description="Local diagnostics service")
    parser.add_argument(
        "--check",
        action="store_true",
        help="print readiness JSON and exit with 0 only when ready",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="serve readiness JSON over localhost HTTP",
    )
    args = parser.parse_args()

    if args.serve:
        serve()
        return None

    result = readiness()
    print(json.dumps(result, separators=(",", ":")))
    if args.check and result.get("status") != "ok":
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    main()
PY

    cat > "$ROOT/env-candidates/dev-a.env" <<'EOF'
APP_PROFILE=development
APP_PORT=8127
CACHE_BACKEND=redis
DATABASE_URL=sqlite:///tmp/devops_log_lab.sqlite3
FEATURE_FLAG_STREAM=enabled
EOF

    cat > "$ROOT/env-candidates/dev-b.env" <<'EOF'
APP_PROFILE=development
APP_PORT=8127
CACHE_BACKEND=memory
DATABASE_URL=sqlite:///tmp/devops_log_lab.sqlite3
FEATURE_FLAG_STREAM=enabled
EOF

    cat > "$ROOT/env-candidates/dev-c.env" <<'EOF'
APP_PROFILE=development
APP_PORT=9001
CACHE_BACKEND=memory
DATABASE_URL=sqlite:///tmp/devops_log_lab.sqlite3
FEATURE_FLAG_STREAM=enabled
EOF

    cat > "$ROOT/env-candidates/dev-d.env" <<'EOF'
APP_PROFILE=development
APP_PORT=8127
CACHE_BACKEND=memory
DATABASE_URL=postgresql://localhost/devops_log_lab
FEATURE_FLAG_STREAM=enabled
EOF

    cat > "$ROOT/logs/startup-dev-a.log" <<'EOF'
candidate=dev-a.env
config parse OK
import service.app OK
readiness FAIL cache backend redis unavailable on localhost:6379
EOF

    cat > "$ROOT/logs/startup-dev-b.log" <<'EOF'
candidate=dev-b.env
config parse OK
import service.app OK
readiness PASS
health {"status":"ok","profile":"development","cache":"memory","database":"sqlite","stream":"enabled","port":8127}
EOF

    cat > "$ROOT/logs/startup-dev-c.log" <<'EOF'
candidate=dev-c.env
config parse OK
import service.app OK
server listening on 9001
readiness FAIL expected dev port 8127 but candidate configured 9001
EOF

    cat > "$ROOT/logs/startup-dev-d.log" <<'EOF'
candidate=dev-d.env
config parse OK
import service.app OK
readiness FAIL database backend postgresql not available in local dev container
EOF

    cat > "$ROOT/logs/archive-prod-incident.log" <<'EOF'
profile=production
FATAL payment gateway token missing
bind 0.0.0.0:443 permission denied
EOF

    cat > "$ROOT/README.md" <<'EOF'
# DevOps Log Lab

This local diagnostics workspace contains mutually exclusive development
environment candidates under `env-candidates/`.

Startup evidence is under `logs/`. Some logs are active candidate startup logs,
while old archive logs may be unrelated and should not be treated as decisive
candidate evidence. In particular, archived production incidents are not local
development candidate runs.

Use `service.app` from the repository root with a selected candidate environment
to validate the service readiness JSON.
EOF

    chown -R user:user /home/user/devops-log-lab
    chmod -R u+rwX,go+rX /home/user/devops-log-lab
    find /home/user/devops-log-lab -type d -exec chmod 755 {} \;
    find /home/user/devops-log-lab -type f -exec chmod 644 {} \;

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
