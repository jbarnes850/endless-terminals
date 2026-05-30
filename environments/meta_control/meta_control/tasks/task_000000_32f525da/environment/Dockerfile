FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
        ca-certificates \
        python3 \
        python3-pip \
        patch

    python3 -m pip install --no-cache-dir pytest

    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/credential-rotation/config
    mkdir -p /home/user/credential-rotation/patches

    cat > /home/user/credential-rotation/config/service.env <<'EOF'
# service.env - production payment gateway integration
SERVICE_NAME=payments-api
SERVICE_PORT=8443
API_BASE_URL=https://payments.example.internal/v1
API_CLIENT_ID=payroll-sync-prod
API_CLIENT_SECRET=old_secret_7f9c1a2b
TOKEN_ISSUER=https://issuer.example.internal
TOKEN_AUDIENCE=payments-api
CREDENTIAL_VERSION=2024-03
ROTATION_REQUIRED=true
EOF

    cat > /home/user/credential-rotation/patches/rotate-api-credentials.patch <<'EOF'
--- config/service.env
+++ config/service.env
@@ -3,8 +3,8 @@
 SERVICE_PORT=8443
 API_BASE_URL=https://payments.example.internal/v1
 API_CLIENT_ID=payroll-sync-prod
-API_CLIENT_SECRET=old_secret_7f9c1a2b
+API_CLIENT_SECRET=rotated_secret_91db6e44
 TOKEN_ISSUER=https://issuer.example.internal
 TOKEN_AUDIENCE=payments-api
-CREDENTIAL_VERSION=2024-03
-ROTATION_REQUIRED=true
+CREDENTIAL_VERSION=2024-09
+ROTATION_REQUIRED=false
EOF

    rm -f /home/user/credential-rotation/config/service.env.pre-rotation
    rm -f /home/user/credential-rotation/rotation_verification.log
    find /home/user/credential-rotation -name '*.rej' -type f -delete

    chown -R user:user /home/user/credential-rotation
    chmod -R u+rwX,go+rX /home/user/credential-rotation
    chmod 755 /home/user
    chmod 755 /home/user/credential-rotation
    chmod 755 /home/user/credential-rotation/config
    chmod 755 /home/user/credential-rotation/patches
    chmod 644 /home/user/credential-rotation/config/service.env
    chmod 644 /home/user/credential-rotation/patches/rotate-api-credentials.patch

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
