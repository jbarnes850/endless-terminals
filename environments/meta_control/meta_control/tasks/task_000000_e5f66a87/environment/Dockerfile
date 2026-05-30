FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        python3-pytest \
        ca-certificates

    # Ensure pytest is available for the verifier.
    python3 -m pip install --no-cache-dir --upgrade pip pytest

    # Create the non-root user expected by the task/tests.
    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    PROJECT_DIR=/home/user/projects/portfolio-site
    OLD_VENV="${PROJECT_DIR}/venv"
    NEW_VENV="${PROJECT_DIR}/.venv"

    # Create the project directory and intentionally stale old virtualenv.
    mkdir -p "${PROJECT_DIR}"

    # Ensure the new virtual environment path does not exist initially.
    rm -rf "${NEW_VENV}"

    # Recreate the old venv from scratch so it is a real, working venv.
    rm -rf "${OLD_VENV}"
    python3 -m venv "${OLD_VENV}"

    # Add the stale marker file.
    printf 'this is the retired venv and must not be used as final truth\n' > "${OLD_VENV}/STILL_OLD_ENV.txt"

    # Initial .envrc points to the stale location.
    printf 'source /home/user/projects/portfolio-site/venv/bin/activate\n' > "${PROJECT_DIR}/.envrc"

    # Optional misleading stale verification log.
    cat > "${PROJECT_DIR}/venv_migration_check.log" <<'EOF'
PROJECT_DIR=/home/user/projects/portfolio-site
ACTIVE_ENV=/home/user/projects/portfolio-site/venv
PYTHON_EXE=/home/user/projects/portfolio-site/venv/bin/python
PIP_EXE=/home/user/projects/portfolio-site/venv/bin/pip
OLD_ENV_STATUS=active
EOF

    # Make the entire project tree owned and writable by the non-root user.
    chown -R user:user /home/user/projects
    chmod -R u+rwX /home/user/projects

    # Ensure home ownership is correct.
    chown -R user:user /home/user

    # Clean apt caches.
    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
