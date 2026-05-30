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

    mkdir -p /home/user/api-integration

    cat > /home/user/api-integration/.env <<'EOF'
# Shared defaults for partner API integration
API_BASE_URL=https://sandbox-api.example.test/v1
API_TOKEN="shared-token-should-not-win"
CLIENT_ID=integration-dev-client
REQUEST_TIMEOUT_MS=3000

# These are intentionally not part of request.env
LOG_LEVEL=debug
EMPTY_FROM_BASE=
DISABLED_FEATURE=false

# Default feature flags, overridden locally
FEATURE_FLAGS=accounts,balances

# malformed/ignored examples
BROKEN LINE WITHOUT EQUALS
# API_TOKEN=commented-out-token
EOF

    cat > /home/user/api-integration/.env.local <<'EOF'
# Local developer overrides
API_TOKEN='local-token_7yF.pilot-42'
REQUEST_TIMEOUT_MS=8500
FEATURE_FLAGS="accounts,balances,transfers"
API_BASE_URL=https://localhost:9443/mock-api/v1?tenant=dev&trace=true

# Should be ignored because final value is empty and not in required set anyway
LOCAL_EMPTY=

# Not required by the request runner
EXTRA_HEADER=X-Debug-Integration:true
EOF

    cat > /home/user/api-integration/generate_request_env.py <<'EOF'
#!/usr/bin/env python3
from pathlib import Path

# This helper intentionally exits cleanly while producing a subtly wrong artifact:
# it reads only .env, keeps lower-priority values, and does not validate the final contract.
root = Path("/home/user/api-integration")
outdir = root / "build"
outdir.mkdir(exist_ok=True)
required = ["API_BASE_URL", "API_TOKEN", "CLIENT_ID", "FEATURE_FLAGS", "REQUEST_TIMEOUT_MS"]

values = {}
for raw in (root / ".env").read_text().splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, val = line.split("=", 1)
    key = key.strip()
    val = val.strip()
    if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
        val = val[1:-1]
    if key in required and val:
        values[key] = val

with (outdir / "request.env").open("w") as f:
    for key in required:
        if key in values:
            f.write(f"{key}={values[key]}\n")

print("request.env generated")
EOF

    chmod 777 /home/user
    chmod 777 /home/user/api-integration
    chmod 666 /home/user/api-integration/.env
    chmod 666 /home/user/api-integration/.env.local
    chmod 777 /home/user/api-integration/generate_request_env.py

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
