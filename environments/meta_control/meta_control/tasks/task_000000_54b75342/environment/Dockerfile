FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        passwd
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! getent group user >/dev/null 2>&1; then
        groupadd -g 1000 user
    fi

    if ! getent passwd user >/dev/null 2>&1; then
        useradd -m -u 1000 -g user -s /bin/bash user
    else
        mkdir -p /home/user
        chown user:user /home/user
    fi

    mkdir -p /home/user/hardening-lab/accounts
    mkdir -p /home/user/hardening-lab/audit

    printf 'appsvc:x:1501:1501:Application Service Account:/srv/appsvc:/usr/sbin/nologin\n' > /home/user/hardening-lab/accounts/appsvc.passwd
    printf 'appsvc:!:19876:0:99999:7:::\n' > /home/user/hardening-lab/accounts/appsvc.shadow

    rm -f /home/user/hardening-lab/audit/permission-check.log

    chown -R user:user /home/user/hardening-lab

    chmod 0755 /home/user
    chmod 0755 /home/user/hardening-lab
    chmod 0755 /home/user/hardening-lab/accounts
    chmod 0755 /home/user/hardening-lab/audit
    chmod 0666 /home/user/hardening-lab/accounts/appsvc.passwd
    chmod 0644 /home/user/hardening-lab/accounts/appsvc.shadow

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
