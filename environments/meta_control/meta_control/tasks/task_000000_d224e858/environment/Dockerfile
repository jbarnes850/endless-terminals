FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        python3-setuptools \
        python3-wheel \
        ca-certificates

    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    python3 -m pip install --no-cache-dir --upgrade pip
    python3 -m pip install --no-cache-dir \
        pytest \
        requests==2.31.0 \
        urllib3==2.2.0 \
        python-dateutil==2.8.2

    mkdir -p /home/user/ops-pip-debug/logs
    mkdir -p /home/user/ops-pip-debug/vendor_trap/urllib3

    cat > /home/user/ops-pip-debug/requirements.txt <<'EOF'
requests==2.31.0
urllib3==1.26.18
python-dateutil==2.8.2
EOF

    cat > /home/user/ops-pip-debug/logs/service.log <<'EOF'
2024-05-12T08:15:01Z INFO api-gateway boot sequence started
2024-05-12T08:15:03Z INFO api-gateway listening on 0.0.0.0:8080
2024-05-12T08:16:10Z WARNING auth-cache refresh took 1840ms
2024-05-12T08:17:44Z ERROR upstream inventory timeout after 3000ms
2024-05-12T08:18:01Z INFO retry scheduled for inventory request
2024-05-12T08:19:22Z WARNING payment queue depth above threshold
2024-05-12T08:21:09Z ERROR checkout request failed with HTTP 502
2024-05-12T08:22:11Z INFO api-gateway health check passed
EOF

    cat > /home/user/ops-pip-debug/analyze_logs.py <<'EOF'
#!/usr/bin/env python3
import json
import pathlib
import sys

try:
    import requests
    import urllib3
except Exception as exc:
    print(f"IMPORT_ERROR: {exc}", file=sys.stderr)
    sys.exit(2)

EXPECTED_REQUESTS = "2.31.0"
EXPECTED_URLLIB3_PREFIX = "1.26."

if requests.__version__ != EXPECTED_REQUESTS:
    print(
        f"ENV_ERROR: requests version {requests.__version__} does not match required {EXPECTED_REQUESTS}",
        file=sys.stderr,
    )
    sys.exit(3)

if not urllib3.__version__.startswith(EXPECTED_URLLIB3_PREFIX):
    print(
        f"ENV_ERROR: urllib3 version {urllib3.__version__} is incompatible; expected prefix {EXPECTED_URLLIB3_PREFIX}",
        file=sys.stderr,
    )
    sys.exit(4)

log_path = pathlib.Path("/home/user/ops-pip-debug/logs/service.log")
summary_path = pathlib.Path("/home/user/ops-pip-debug/logs/summary.json")

lines = [line.rstrip("\n") for line in log_path.read_text().splitlines()]
errors = [line for line in lines if " ERROR " in line]
warnings = [line for line in lines if " WARNING " in line]

summary = {
    "status": "degraded",
    "total_lines": len(lines),
    "error_count": len(errors),
    "warning_count": len(warnings),
    "requests_version": requests.__version__,
    "urllib3_version": urllib3.__version__,
}

summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(f"WROTE {summary_path}")
EOF

    cat > /home/user/ops-pip-debug/vendor_trap/urllib3/__init__.py <<'EOF'
__version__ = "2.2.0"
EOF

    chmod +x /home/user/ops-pip-debug/analyze_logs.py

    python3 -m venv /home/user/ops-pip-debug/.venv
    /home/user/ops-pip-debug/.venv/bin/python -m pip install --no-cache-dir --upgrade pip
    /home/user/ops-pip-debug/.venv/bin/python -m pip install --no-cache-dir \
        requests==2.31.0 \
        urllib3==2.2.0 \
        python-dateutil==2.8.2

    rm -f /home/user/ops-pip-debug/logs/summary.json
    rm -f /home/user/ops-pip-debug/env_repair_report.txt

    chown -R user:user /home/user/ops-pip-debug
    chmod -R u+rwX,go+rX /home/user/ops-pip-debug
    chmod -R u+w /home/user/ops-pip-debug/.venv

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
