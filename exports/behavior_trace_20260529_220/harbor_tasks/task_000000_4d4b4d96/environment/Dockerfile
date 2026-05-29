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

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/iot-edge

    cat > /home/user/iot-edge/device-policy.env <<'EOF'
DEVICE_ID=edge-sensor-a17
INTERFACE=wlan0
ALLOW_CIDR=10.42.8.0/24
ALLOW_TCP_PORT=1883
DEFAULT_INPUT_POLICY=drop
RULESET_NAME=mqtt-ingress-v4
EOF

    rm -f /home/user/iot-edge/firewall.apply.log

    chown -R user:user /home/user
    chmod 755 /home/user
    chmod 777 /home/user/iot-edge
    chmod 644 /home/user/iot-edge/device-policy.env

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
