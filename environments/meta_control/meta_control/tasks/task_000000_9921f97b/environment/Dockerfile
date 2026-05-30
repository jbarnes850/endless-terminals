FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/mlops_runs/candidates/run_2024_06_17_alpha
    mkdir -p /home/user/mlops_runs/candidates/run_2024_06_17_beta
    mkdir -p /home/user/mlops_runs/candidates/run_2024_06_18_gamma
    mkdir -p /home/user/mlops_runs/candidates/run_2024_06_18_delta
    mkdir -p /home/user/mlops_runs/registry

    cat > /home/user/mlops_runs/candidates/run_2024_06_17_alpha/status.txt <<'EOF'
FAILED
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_17_alpha/metrics.json <<'EOF'
{"run_id":"run_2024_06_17_alpha","accuracy":0.901,"auc":0.884,"f1":0.798}
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_17_alpha/model.pkl <<'EOF'
MODEL_BINARY_PLACEHOLDER_ALPHA_FAILED
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_17_alpha/schema.json <<'EOF'
{"features":["age","tenure_months","monthly_charges"],"target":"churned","version":"1.0-alpha"}
EOF

    cat > /home/user/mlops_runs/candidates/run_2024_06_17_beta/status.txt <<'EOF'
COMPLETED
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_17_beta/metrics.json <<'EOF'
{"run_id":"run_2024_06_17_beta","accuracy":0.919,"auc":0.907,"f1":0.812}
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_17_beta/model.pkl <<'EOF'
MODEL_BINARY_PLACEHOLDER_BETA_MISSING_SCHEMA
EOF

    cat > /home/user/mlops_runs/candidates/run_2024_06_18_gamma/status.txt <<'EOF'
COMPLETED
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_18_gamma/metrics.json <<'EOF'
{"run_id":"run_2024_06_18_gamma","accuracy":0.927,"auc":0.916,"f1":0.821}
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_18_gamma/model.pkl <<'EOF'
MODEL_BINARY_PLACEHOLDER_GAMMA_DEPLOYABLE
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_18_gamma/schema.json <<'EOF'
{"features":["age","tenure_months","monthly_charges","support_tickets"],"target":"churned","version":"1.1"}
EOF

    cat > /home/user/mlops_runs/candidates/run_2024_06_18_delta/status.txt <<'EOF'
RUNNING
EOF
    cat > /home/user/mlops_runs/candidates/run_2024_06_18_delta/schema.json <<'EOF'
{"features":["age","tenure_months","monthly_charges","support_tickets"],"target":"churned","version":"1.1-delta"}
EOF

    chown -R user:user /home/user
    chmod -R u+rwX,go+rX /home/user/mlops_runs
    chmod -R u+w /home/user/mlops_runs

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
