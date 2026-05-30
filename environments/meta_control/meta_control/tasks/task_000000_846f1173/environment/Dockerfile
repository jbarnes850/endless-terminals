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
        useradd -m -s /bin/bash -u 1000 user
    fi

    mkdir -p /home/user/rotation/current.secret.d
    mkdir -p /home/user/rotation/audit

    printf 'rotated-service-token:tb-simple-perm-pivot-2026\n' > /home/user/rotation/current.secret.d/token.txt

    chown -R user:user /home/user/rotation
    chown user:user /home/user

    chmod 0755 /home/user
    chmod 0755 /home/user/rotation
    chmod 0755 /home/user/rotation/audit
    chmod 0644 /home/user/rotation/current.secret.d/token.txt
    chmod 0600 /home/user/rotation/current.secret.d

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
