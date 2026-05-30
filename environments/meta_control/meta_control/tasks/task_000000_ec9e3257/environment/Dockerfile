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
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/artifact_triage/policy
    mkdir -p /home/user/artifact_triage/candidates/build-2024.11.08-a1
    mkdir -p /home/user/artifact_triage/candidates/build-2024.11.08-b2
    mkdir -p /home/user/artifact_triage/candidates/build-2024.11.08-c3
    mkdir -p /home/user/artifact_triage/candidates/build-2024.11.08-d4
    mkdir -p /home/user/artifact_triage/candidates/build-2024.11.08-e5
    mkdir -p /home/user/artifact_triage/candidates/build-2024.11.08-f6

    cat > /home/user/artifact_triage/policy/release_policy.txt <<'EOF'
release_train=2024.11
allowed_channel=stable
allowed_commit=8f14e45fceea167a5a36dedd4bea2543
required_schema_version=3
require_signed=yes
require_qa_status=pass
EOF

    cat > /home/user/artifact_triage/policy/expected_components.tsv <<'EOF'
api-gateway	2.8.1
auth-service	5.4.0
billing-worker	1.19.7
web-console	3.12.2
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-a1/manifest.txt <<'EOF'
artifact_id=rel-2024.11-a1
channel=stable
signed=yes
qa_status=pass
schema_version=3
commit=8f14e45fceea167a5a36dedd4bea2543
component=api-gateway	2.8.1
component=auth-service	5.4.0
component=billing-worker	1.19.7
component=web-console	3.12.2
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-b2/manifest.txt <<'EOF'
artifact_id=rel-2024.11-b2
channel=stable
signed=yes
qa_status=pass
schema_version=3
commit=8f14e45fceea167a5a36dedd4bea2543
component=api-gateway	2.8.1
component=auth-service	5.4.0
component=billing-worker	1.19.8
component=web-console	3.12.2
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-c3/manifest.txt <<'EOF'
artifact_id=rel-2024.11-c3
channel=stable
signed=yes
qa_status=pass
schema_version=3
commit=0cc175b9c0f1b6a831c399e269772661
component=api-gateway	2.8.1
component=auth-service	5.4.0
component=billing-worker	1.19.7
component=web-console	3.12.2
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-d4/manifest.txt <<'EOF'
artifact_id=rel-2024.11-d4
channel=stable
signed=yes
qa_status=pass
schema_version=3
commit=8f14e45fceea167a5a36dedd4bea2543
component=api-gateway	2.8.1
component=auth-service	5.4.0
component=billing-worker	1.19.7
component=web-console	3.12.2
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-e5/manifest.txt <<'EOF'
artifact_id=rel-2024.11-e5
channel=beta
signed=yes
qa_status=pass
schema_version=3
commit=8f14e45fceea167a5a36dedd4bea2543
component=api-gateway	2.8.1
component=auth-service	5.4.0
component=billing-worker	1.19.7
component=web-console	3.12.2
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-f6/manifest.txt <<'EOF'
artifact_id=rel-2024.11-f6
channel=stable
signed=no
qa_status=pass
schema_version=3
commit=8f14e45fceea167a5a36dedd4bea2543
component=api-gateway	2.8.1
component=auth-service	5.4.0
component=billing-worker	1.19.7
component=web-console	3.12.2
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-a1/checksums.sha256 <<'EOF'
1111111111111111111111111111111111111111111111111111111111111111  api-gateway-2.8.1.tar.gz
2222222222222222222222222222222222222222222222222222222222222222  auth-service-5.4.0.tar.gz
3333333333333333333333333333333333333333333333333333333333333333  billing-worker-1.19.7.tar.gz
4444444444444444444444444444444444444444444444444444444444444444  web-console-3.12.2.tar.gz
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-b2/checksums.sha256 <<'EOF'
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  api-gateway-2.8.1.tar.gz
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb  auth-service-5.4.0.tar.gz
cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc  billing-worker-1.19.8.tar.gz
dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd  web-console-3.12.2.tar.gz
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-c3/checksums.sha256 <<'EOF'
eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee  api-gateway-2.8.1.tar.gz
ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff  auth-service-5.4.0.tar.gz
1212121212121212121212121212121212121212121212121212121212121212  billing-worker-1.19.7.tar.gz
3434343434343434343434343434343434343434343434343434343434343434  web-console-3.12.2.tar.gz
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-d4/checksums.sha256 <<'EOF'
5555555555555555555555555555555555555555555555555555555555555555  api-gateway-2.8.1.tar.gz
6666666666666666666666666666666666666666666666666666666666666666  auth-service-5.4.0.tar.gz
7777777777777777777777777777777777777777777777777777777777777777  billing-worker-1.19.7.tar.gz
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-e5/checksums.sha256 <<'EOF'
8888888888888888888888888888888888888888888888888888888888888888  api-gateway-2.8.1.tar.gz
9999999999999999999999999999999999999999999999999999999999999999  auth-service-5.4.0.tar.gz
abababababababababababababababababababababababababababababababab  billing-worker-1.19.7.tar.gz
bcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbc  web-console-3.12.2.tar.gz
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-f6/checksums.sha256 <<'EOF'
cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd  api-gateway-2.8.1.tar.gz
dededededededededededededededededededededededededededededededede  auth-service-5.4.0.tar.gz
efefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefef  billing-worker-1.19.7.tar.gz
fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa  web-console-3.12.2.tar.gz
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-a1/build.log <<'EOF'
2024-11-08T10:14:01Z INFO starting release build
2024-11-08T10:16:22Z INFO tests completed
2024-11-08T10:18:45Z INFO packaging completed successfully
2024-11-08T10:18:49Z INFO uploaded artifacts to staging
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-b2/build.log <<'EOF'
2024-11-08T10:21:01Z INFO starting release build
2024-11-08T10:23:17Z INFO tests completed
2024-11-08T10:25:03Z INFO packaging completed successfully
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-c3/build.log <<'EOF'
2024-11-08T10:31:09Z INFO starting release build
2024-11-08T10:35:44Z INFO tests completed
2024-11-08T10:38:11Z INFO packaging completed successfully
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-d4/build.log <<'EOF'
2024-11-08T10:41:02Z INFO starting release build
2024-11-08T10:44:29Z INFO tests completed
2024-11-08T10:47:53Z INFO packaging completed successfully
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-e5/build.log <<'EOF'
2024-11-08T10:51:07Z INFO starting release build
2024-11-08T10:54:26Z INFO tests completed
2024-11-08T10:57:39Z INFO packaging completed successfully
EOF

    cat > /home/user/artifact_triage/candidates/build-2024.11.08-f6/build.log <<'EOF'
2024-11-08T11:01:07Z INFO starting release build
2024-11-08T11:04:26Z INFO tests completed
2024-11-08T11:07:39Z INFO packaging completed successfully
EOF

    chown -R user:user /home/user/artifact_triage
    chmod -R u+rwX,go+rX /home/user/artifact_triage
    find /home/user/artifact_triage -type d -exec chmod 755 {} \;
    find /home/user/artifact_triage -type f -exec chmod 644 {} \;

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
