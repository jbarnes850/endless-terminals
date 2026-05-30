FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        coreutils \
        passwd

    python3 -m pip install --no-cache-dir pytest

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/analyst_workspace/raw
    mkdir -p /home/user/analyst_workspace/processed
    mkdir -p /home/user/analyst_workspace/archive

    cat > /home/user/analyst_workspace/raw/customer_export_legacy.csv <<'EOF'
region,customer_id,last_name,email,signup_date,plan
EMEA,C-1007,Nguyen,linh.nguyen@example.net,2023-08-14,pro
NA,C-1012,Patel,arjun.patel@example.net,2022-11-03,basic
APAC,C-1020,Okafor,mina.okafor@example.net,2024-01-27,enterprise
LATAM,C-1033,Silva,renata.silva@example.net,2023-05-09,pro
EOF

    rm -f /home/user/analyst_workspace/processed/customer_contact_canonical.csv
    rm -f /home/user/analyst_workspace/processed/customer_contact_canonical.verify.log
    rm -f /home/user/analyst_workspace/archive/customer_export_legacy.csv.retired

    chown -R user:user /home/user/analyst_workspace
    chmod 755 /home/user
    chmod 755 /home/user/analyst_workspace
    chmod 755 /home/user/analyst_workspace/raw
    chmod 755 /home/user/analyst_workspace/processed
    chmod 755 /home/user/analyst_workspace/archive
    chmod 644 /home/user/analyst_workspace/raw/customer_export_legacy.csv

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
