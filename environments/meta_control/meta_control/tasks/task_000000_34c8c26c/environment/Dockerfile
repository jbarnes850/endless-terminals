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

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/docs_project/source
    mkdir -p /home/user/docs_project/public
    mkdir -p /home/user/docs_project/checks

    cat > /home/user/docs_project/source/getting-started.md <<'EOF'
# Getting Started

Welcome to the Widget Docs.

Follow the installation guide before running examples.
EOF

    rm -f /home/user/docs_project/public/start-here.md
    rm -f /home/user/docs_project/checks/link-report.txt

    chown -R user:user /home/user/docs_project
    chmod 755 /home/user
    chmod 755 /home/user/docs_project
    chmod 755 /home/user/docs_project/source
    chmod 755 /home/user/docs_project/public
    chmod 755 /home/user/docs_project/checks
    chmod 644 /home/user/docs_project/source/getting-started.md

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
