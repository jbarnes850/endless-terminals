FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    BASE=/home/user/cloud-migration
    SERVICES="${BASE}/services"

    mkdir -p "${SERVICES}"

    mkdir -p "${SERVICES}/auth-gateway/configs" \
             "${SERVICES}/auth-gateway/data/shard-a"
    cat > "${SERVICES}/auth-gateway/service.yaml" <<'EOF'
name: auth-gateway
environment: prod
platform: vm
owner: identity
EOF
    cat > "${SERVICES}/auth-gateway/Dockerfile" <<'EOF'
FROM alpine:3.18
CMD ["sh"]
EOF
    cat > "${SERVICES}/auth-gateway/configs/prod.env" <<'EOF'
SERVICE_PORT=8080
REGION=us-east-1
EOF
    cat > "${SERVICES}/auth-gateway/data/shard-a/READY" <<'EOF'
ready
EOF

    mkdir -p "${SERVICES}/billing-api/configs" \
             "${SERVICES}/billing-api/data/primary"
    cat > "${SERVICES}/billing-api/service.yaml" <<'EOF'
name: billing-api
environment: prod
platform: k8s
owner: finance
EOF
    cat > "${SERVICES}/billing-api/Dockerfile" <<'EOF'
FROM python:3.11-slim
CMD ["python", "-m", "billing"]
EOF
    cat > "${SERVICES}/billing-api/configs/staging.env" <<'EOF'
SERVICE_PORT=9090
REGION=us-west-2
EOF
    cat > "${SERVICES}/billing-api/data/primary/READY" <<'EOF'
ready
EOF

    mkdir -p "${SERVICES}/catalog-worker/configs" \
             "${SERVICES}/catalog-worker/ops" \
             "${SERVICES}/catalog-worker/data/live"
    cat > "${SERVICES}/catalog-worker/service.yaml" <<'EOF'
name: catalog-worker
environment: prod
platform: k8s
owner: catalog
EOF
    cat > "${SERVICES}/catalog-worker/Dockerfile" <<'EOF'
FROM node:20-alpine
CMD ["node", "worker.js"]
EOF
    cat > "${SERVICES}/catalog-worker/configs/prod.env" <<'EOF'
SERVICE_PORT=7070
REGION=eu-central-1
EOF
    cat > "${SERVICES}/catalog-worker/ops/BLOCK_MIGRATION" <<'EOF'
awaiting dependency approval
EOF
    cat > "${SERVICES}/catalog-worker/data/live/READY" <<'EOF'
ready
EOF

    mkdir -p "${SERVICES}/invoice-router/configs" \
             "${SERVICES}/invoice-router/data/cutover-batch"
    cat > "${SERVICES}/invoice-router/service.yaml" <<'EOF'
name: invoice-router
environment: prod
platform: k8s
owner: finance-platform
EOF
    cat > "${SERVICES}/invoice-router/Dockerfile" <<'EOF'
FROM golang:1.22-alpine
CMD ["/usr/local/bin/invoice-router"]
EOF
    cat > "${SERVICES}/invoice-router/configs/prod.env" <<'EOF'
SERVICE_PORT=8443
REGION=us-east-2
EOF
    cat > "${SERVICES}/invoice-router/data/cutover-batch/READY" <<'EOF'
ready
EOF

    mkdir -p "${SERVICES}/metrics-sidecar/configs" \
             "${SERVICES}/metrics-sidecar/data/window-a"
    cat > "${SERVICES}/metrics-sidecar/service.yaml" <<'EOF'
name: metrics-sidecar
environment: staging
platform: k8s
owner: observability
EOF
    cat > "${SERVICES}/metrics-sidecar/Dockerfile" <<'EOF'
FROM alpine:3.19
CMD ["sleep", "3600"]
EOF
    cat > "${SERVICES}/metrics-sidecar/configs/prod.env" <<'EOF'
SERVICE_PORT=9100
REGION=us-east-1
EOF
    cat > "${SERVICES}/metrics-sidecar/data/window-a/READY" <<'EOF'
ready
EOF

    mkdir -p "${SERVICES}/orders-api/configs" \
             "${SERVICES}/orders-api/data/blue" \
             "${SERVICES}/orders-api/data/green"
    cat > "${SERVICES}/orders-api/service.yaml" <<'EOF'
name: orders-api
environment: prod
platform: k8s
owner: commerce
EOF
    cat > "${SERVICES}/orders-api/Dockerfile" <<'EOF'
FROM eclipse-temurin:21-jre
CMD ["java", "-jar", "orders.jar"]
EOF
    cat > "${SERVICES}/orders-api/configs/prod.env" <<'EOF'
SERVICE_PORT=8081
REGION=us-west-1
EOF
    cat > "${SERVICES}/orders-api/data/blue/READY" <<'EOF'
ready
EOF
    cat > "${SERVICES}/orders-api/data/green/READY" <<'EOF'
ready
EOF

    mkdir -p "${SERVICES}/search-indexer/configs" \
             "${SERVICES}/search-indexer/runtime" \
             "${SERVICES}/search-indexer/data/segment-1"
    cat > "${SERVICES}/search-indexer/service.yaml" <<'EOF'
name: search-indexer
environment: prod
platform: k8s
owner: search
EOF
    cat > "${SERVICES}/search-indexer/Dockerfile" <<'EOF'
FROM rust:1.76
CMD ["search-indexer"]
EOF
    cat > "${SERVICES}/search-indexer/configs/prod.env" <<'EOF'
SERVICE_PORT=6060
REGION=us-east-1
EOF
    cat > "${SERVICES}/search-indexer/runtime/legacy.lock" <<'EOF'
legacy runtime still attached
EOF
    cat > "${SERVICES}/search-indexer/data/segment-1/READY" <<'EOF'
ready
EOF

    rm -f "${BASE}/selected-service.txt" "${BASE}/migration_audit.log"

    chown -R user:user /home/user
    chmod -R u+rwX,go+rX /home/user
    chmod u+w "${BASE}" "${SERVICES}"

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
