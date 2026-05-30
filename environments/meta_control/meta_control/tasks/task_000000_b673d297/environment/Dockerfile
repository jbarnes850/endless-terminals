FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pytest \
        passwd \
        locales \
        ca-certificates

    rm -rf /var/lib/apt/lists/*

    if ! getent group user >/dev/null 2>&1; then
        groupadd -g 1000 user
    fi

    if ! getent passwd user >/dev/null 2>&1; then
        useradd -m -u 1000 -g user -s /bin/bash user
    else
        usermod -d /home/user -s /bin/bash user
        mkdir -p /home/user
    fi

    chown -R user:user /home/user
    chmod 0755 /home/user

    locale-gen en_US.UTF-8 || true

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
