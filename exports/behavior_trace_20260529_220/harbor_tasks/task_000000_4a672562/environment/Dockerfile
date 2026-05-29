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

    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -u 1000 -s /bin/bash user
    fi

    mkdir -p /home/user/workspace/policy-envcheck/config
    mkdir -p /home/user/workspace/policy-envcheck/policy

    cat > /home/user/workspace/policy-envcheck/config/.env.release <<'EOF'
# Release dotenv for payments-api
APP_ENV=production
export SERVICE_NAME=payments-api
API_URL=https://api.example.internal/v1
API_TOKEN=old-token
API_TOKEN="rotated-token-2024"
LOG_LEVEL=info
DEBUG=false
DB_HOST=db01.internal
DB_PORT=5432
DB_USER=payments_app
DB_PASSWORD='correct horse battery staple'
SENTRY_DSN=
FEATURE_FLAGS="cards,refunds,\nfraud"
ALLOWED_ORIGINS=https://app.example.com, https://admin.example.com # production origins
AWS_SECRET_ACCESS_KEY=should-not-ship
BAD-KEY=value
UNFINISHED_QUOTE="abc
TRAILING_SPACE = not-valid-key-because-space-before-equals
export CACHE_TTL=300
EMPTY_VALUE=
QUOTED_HASH="value # not comment"
SINGLE_HASH='literal # hash'
ESCAPED_VALUE="line1\nline2\tTabbed\\Backslash\"Quote"
EOF

    cat > /home/user/workspace/policy-envcheck/policy/required-env.txt <<'EOF'
# policy for release deployment
required:APP_ENV
required:SERVICE_NAME
required:API_URL
required:API_TOKEN
required:DB_HOST
required:DB_PORT
required:DB_USER
required:DB_PASSWORD
required:REDIS_URL
required:CACHE_TTL

forbidden:DEBUG
forbidden:AWS_SECRET_ACCESS_KEY
forbidden:LOCAL_ONLY_FLAG
EOF

    chown -R user:user /home/user
    chmod 755 /home/user
    chmod -R u+rwX,go+rX /home/user/workspace
    chmod u+w,go+w /home/user/workspace/policy-envcheck
    chmod u+w,go+w /home/user/workspace/policy-envcheck/config
    chmod u+w,go+w /home/user/workspace/policy-envcheck/policy

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
