FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -euo pipefail

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        tar \
        gzip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/iot_gateway_deploy/device_config/network
    mkdir -p /home/user/iot_gateway_deploy/device_config/services
    mkdir -p /home/user/iot_gateway_deploy/device_config/certs
    mkdir -p /home/user/iot_gateway_deploy/out
    mkdir -p /home/user/iot_gateway_deploy/scripts

    cat > /home/user/iot_gateway_deploy/device_config/config.yaml <<'EOF'
device_id: edge-gw-014
site: pump-station-west
sample_interval_seconds: 30
uplink: mqtt
log_level: info
EOF

    cat > /home/user/iot_gateway_deploy/device_config/network/interfaces.conf <<'EOF'
[eth0]
mode=dhcp
metric=100

[wlan0]
mode=disabled
EOF

    cat > /home/user/iot_gateway_deploy/device_config/services/mqtt.env <<'EOF'
MQTT_HOST=broker.internal
MQTT_PORT=1883
MQTT_CLIENT_ID=edge-gw-014
MQTT_TLS=false
EOF

    cat > /home/user/iot_gateway_deploy/device_config/services/sensor-sampler.env <<'EOF'
SENSOR_BUS=i2c-1
SENSOR_PROFILE=vibration-basic
SAMPLER_BATCH_SIZE=20
EOF

    cat > /home/user/iot_gateway_deploy/device_config/certs/device.crt <<'EOF'
-----BEGIN CERTIFICATE-----
MIIBszCCAVmgAwIBAgIUEDGEGW014CERTFORTRAININGONLYwCgYIKoZIzj0EAwIw
EzERMA8GA1UEAwwIZWRnZS1ndzAeFw0yNDAxMDEwMDAwMDBaFw0yNzAxMDEwMDAw
MDBaMBMxETAPBgNVBAMMCGVkZ2UtZ3cwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNC
AATRAININGCERTDATAEDGEGW014ONLY0000000000000000000000000000000000
-----END CERTIFICATE-----
EOF

    cat > /home/user/iot_gateway_deploy/device_config/certs/device.key <<'EOF'
-----BEGIN PRIVATE KEY-----
TRAINING-ONLY-NOT-A-REAL-PRIVATE-KEY-EDGE-GW-014
-----END PRIVATE KEY-----
EOF

    cat > /home/user/iot_gateway_deploy/device_config/manifest.txt <<'EOF'
config.yaml
network/interfaces.conf
services/mqtt.env
services/sensor-sampler.env
certs/device.crt
certs/device.key
EOF

    cat > /home/user/iot_gateway_deploy/scripts/make_backup.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /home/user/iot_gateway_deploy/out
tar -czf /home/user/iot_gateway_deploy/out/gateway-edge-backup.tar.gz -C /home/user/iot_gateway_deploy device_config
printf '%s\n' \
  'archive=/home/user/iot_gateway_deploy/out/gateway-edge-backup.tar.gz' \
  'exists=yes' \
  'format=gzip-compressed-tar' \
  'root_prefix=device_config' \
  'file_count=7' \
  'status=created' \
  > /home/user/iot_gateway_deploy/out/backup_verification.log
EOF

    chmod 755 /home/user
    chmod -R u+rwX,go+rX /home/user/iot_gateway_deploy
    chmod 755 /home/user/iot_gateway_deploy/scripts/make_backup.sh
    chown -R user:user /home/user/iot_gateway_deploy

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
