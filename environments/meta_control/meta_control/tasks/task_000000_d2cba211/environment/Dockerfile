FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        ca-certificates

    rm -rf /var/lib/apt/lists/*

    mkdir -p /home/user

    cat > /home/user/mobile-pipeline.ini <<'EOF'
# Mobile release pipeline configuration
# Generated from the shared CI template.

[pipeline]
owner = mobile-build
active_profile = beta
default_track = internal

[profile.alpha]
applicationId = com.example.wallet.alpha
versionName = 3.8.0-alpha.4
versionCode = 38004
track = internal

; The beta profile is the one currently promoted by CI.
[profile.beta]
applicationId = com.example.wallet
versionName = 3.8.0
versionCode = 38017
track = production

[profile.qa]
applicationId = com.example.wallet.qa
versionName = 3.8.0-qa.2
versionCode = 38012
track = beta

[signing]
keystore_alias = ci-release
v1_enabled = true
v2_enabled = true
EOF

    chmod 777 /home/user
    chmod 644 /home/user/mobile-pipeline.ini

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
