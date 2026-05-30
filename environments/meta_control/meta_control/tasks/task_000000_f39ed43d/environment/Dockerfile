FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        findutils \
        coreutils \
        passwd \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/build_staging/legacy_artifacts
    mkdir -p /home/user/build_staging/release_artifacts
    mkdir -p /home/user/build_staging/tmp

    printf 'artifact api-server 1.4.2 linux amd64\n' > /home/user/build_staging/legacy_artifacts/api-server-1.4.2-linux-amd64.tar.gz
    printf 'artifact api-server 1.4.2 linux arm64\n' > /home/user/build_staging/legacy_artifacts/api-server-1.4.2-linux-arm64.tar.gz
    printf 'artifact worker 1.4.2 linux amd64\n' > /home/user/build_staging/legacy_artifacts/worker-1.4.2-linux-amd64.tar.gz
    printf 'artifact worker 1.4.2 linux arm64\n' > /home/user/build_staging/legacy_artifacts/worker-1.4.2-linux-arm64.tar.gz
    printf 'legacy checksum file - do not migrate\n' > /home/user/build_staging/legacy_artifacts/checksums.txt
    printf '# Build notes\nThese notes stay in the legacy directory.\n' > /home/user/build_staging/legacy_artifacts/build-notes.md

    chown -R user:user /home/user/build_staging
    chmod -R u+rwX,go+rX /home/user/build_staging
    chmod u+w /home/user/build_staging /home/user/build_staging/legacy_artifacts /home/user/build_staging/release_artifacts /home/user/build_staging/tmp

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
