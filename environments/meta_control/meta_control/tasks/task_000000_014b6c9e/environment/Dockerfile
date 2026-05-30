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

    mkdir -p /home/user/site-admin/incoming/accounts
    mkdir -p /home/user/site-admin/public/users

    printf '%s\n' '{"username":"samuel.lee","full_name":"Samuel Lee","status":"stale","role":"editor"}' > /home/user/site-admin/incoming/accounts/samuel.lee.json
    printf '%s\n' '{"username":"maya.chen","full_name":"Maya Chen","status":"active","role":"publisher"}' > /home/user/site-admin/incoming/accounts/maya.chen.json
    printf '%s\n' 'Drop staged account JSON exports here before publication.' > /home/user/site-admin/incoming/accounts/README.txt

    rm -rf /home/user/site-admin/public/users/archived
    rm -f /home/user/site-admin/public/users/maya.chen.json
    rm -f /home/user/site-admin/account_migration_check.txt

    chown -R user:user /home/user/site-admin
    chmod -R u+rwX,go+rX /home/user/site-admin
    chmod -R u+w /home/user/site-admin

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
