FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        tar \
        gzip \
        zip \
        unzip \
        ca-certificates \
        coreutils \
        findutils

    python3 -m pip install --no-cache-dir --upgrade pip
    python3 -m pip install --no-cache-dir pytest

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/ml_data_prep/raw
    mkdir -p /home/user/ml_data_prep/work
    mkdir -p /home/user/ml_data_prep/deliverables

    rm -f /home/user/ml_data_prep/deliverables/training_data_ready.zip
    rm -f /home/user/ml_data_prep/deliverables/verification.log

    TMP_SRC="$(mktemp -d)"
    mkdir -p "${TMP_SRC}/batch_export/images"
    mkdir -p "${TMP_SRC}/batch_export/labels"
    mkdir -p "${TMP_SRC}/batch_export/tmp"

    cat > "${TMP_SRC}/batch_export/images/img_001.txt" <<'EOF'
pixel_summary=cat_sample_001
width=224
height=224
split=train
EOF

    cat > "${TMP_SRC}/batch_export/images/img_002.txt" <<'EOF'
pixel_summary=dog_sample_002
width=224
height=224
split=train
EOF

    cat > "${TMP_SRC}/batch_export/labels/labels.csv" <<'EOF'
filename,label
img_001.txt,cat
img_002.txt,dog
EOF

    cat > "${TMP_SRC}/batch_export/README.md" <<'EOF'
Internal export from annotation tool. Do not include in training bundle.
EOF

    cat > "${TMP_SRC}/batch_export/tmp/cache_note.txt" <<'EOF'
temporary cache artifact; exclude from final deliverable
EOF

    tar -C "${TMP_SRC}" -czf /home/user/ml_data_prep/raw/image_labels_batch.tar.gz batch_export

    rm -rf "${TMP_SRC}"

    chown -R user:user /home/user
    chmod 755 /home/user
    chmod -R u+rwX,go+rX /home/user/ml_data_prep

    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
