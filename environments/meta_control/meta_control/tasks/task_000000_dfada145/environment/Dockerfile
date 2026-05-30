FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        ca-certificates
    python3 -m pip install --no-cache-dir --upgrade pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/net-triage/input

    cat > /home/user/net-triage/input/ping-results.csv <<'EOF'
hostname,ip_address,vlan,status,last_seen,notes
core-rtr-01,10.40.0.1,10,UP,2026-02-18T09:01:00Z,baseline gateway reachable
dist-sw-02,10.40.2.12,20,DOWN,2026-02-18T08:44:12Z,no arp response
cam-lobby-01,10.40.7.44,70,UP,2026-02-18T09:00:19Z,previously DOWN during maintenance window
ap-east-03,10.40.3.33,30,DEGRADED,2026-02-18T08:59:02Z,packet loss but not DOWN
printer-hr-02,10.40.5.22,50,DOWN,2026-02-18T08:41:55Z,icmp timeout
badge-reader-7,10.40.5.87,50,UNKNOWN,2026-02-18T08:35:10Z,status page says DOWN? needs manual check
lab-sensor-14,10.40.9.14,90,DOWN,2026-02-18T08:38:44Z,switchport err-disabled
voip-conf-2,10.40.4.62,40,UP,2026-02-18T09:02:11Z,contains text DOWN in ticket title
camera-dock-09,10.40.7.109,70,DOWN,2026-02-18T08:39:31Z,no dhcp renewal
nas-backup-01,10.40.6.10,60,UP,2026-02-18T09:04:18Z,healthy
EOF

    cat > /home/user/net-triage/input/interface-notes.txt <<'EOF'
Switch interface notes from access layer:
Gi1/0/12 dist-sw-02 VLAN20 link DOWN
Gi1/0/22 printer-hr-02 VLAN50 link DOWN
Gi1/0/44 cam-lobby-01 VLAN70 historical DOWN cleared
Gi1/0/87 badge-reader-7 VLAN50 admin state DOWN but ping status UNKNOWN
Gi1/0/14 lab-sensor-14 VLAN90 link DOWN
Gi1/0/109 camera-dock-09 VLAN70 link DOWN
Gi1/0/62 voip-conf-2 VLAN40 ticket text contains DOWN but interface is up
EOF

    cat > /home/user/net-triage/input/README.txt <<'EOF'
Connectivity triage inputs.
Use ping-results.csv as the source of truth for host status.
interface-notes.txt is advisory only and includes historical or administrative DOWN text.
EOF

    chown -R user:user /home/user
    chmod 0755 /home/user
    chmod 0775 /home/user/net-triage
    chmod 0775 /home/user/net-triage/input
    chmod 0664 /home/user/net-triage/input/ping-results.csv
    chmod 0664 /home/user/net-triage/input/interface-notes.txt
    chmod 0664 /home/user/net-triage/input/README.txt

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
