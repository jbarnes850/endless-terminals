FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        ca-certificates \
        sudo

    python3 -m pip install --no-cache-dir --upgrade pip
    python3 -m pip install --no-cache-dir pytest

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -u 1000 -s /bin/bash user
    fi

    mkdir -p /home/user/deploy-rollout

    cat > /home/user/deploy-rollout/requirements.txt <<'EOF'
requests==2.31.0
EOF

    cat > /home/user/deploy-rollout/rollout_probe.py <<'EOF'
import hashlib
import json
import platform
import requests
import sys

payload = {
    "component": "rollout-probe",
    "runtime_major": sys.version_info.major,
    "runtime_minor": sys.version_info.minor,
    "requests": requests.__version__,
    "platform": platform.system().lower(),
}

encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
digest = hashlib.sha256(encoded).hexdigest()[:12]
print(f"probe-ok requests={requests.__version__} digest={digest}")
EOF

    rm -rf /home/user/deploy-rollout/.venv
    rm -f /home/user/deploy-rollout/deployment_evidence.log

    chown -R user:user /home/user
    chmod 755 /home/user
    chmod 755 /home/user/deploy-rollout
    chmod 644 /home/user/deploy-rollout/requirements.txt
    chmod 644 /home/user/deploy-rollout/rollout_probe.py

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
