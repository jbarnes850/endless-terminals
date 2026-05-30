FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-cryptography \
        openssl \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/cert-audit/certs

    cat > /home/user/cert-audit/services.tsv <<'EOF'
service	expected_dns
orders	orders.svc.cluster.local
payments	payments.svc.cluster.local
inventory	inventory.svc.cluster.local
EOF

    cat > /tmp/generate_certs.py <<'PY'
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


outdir = Path("/home/user/cert-audit/certs")

cert_specs = {
    "orders": {
        "cn": "orders",
        "sans": ["orders.svc.cluster.local", "orders.internal"],
        "not_after": datetime(2030, 5, 10, 12, 0, 0, tzinfo=timezone.utc),
        "serial": 1001,
    },
    "payments": {
        "cn": "payments",
        "sans": ["billing.svc.cluster.local", "payments.internal"],
        "not_after": datetime(2028, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
        "serial": 1002,
    },
    "inventory": {
        "cn": "inventory",
        "sans": ["inventory.svc.cluster.local", "inventory.internal"],
        "not_after": datetime(2027, 1, 20, 12, 0, 0, tzinfo=timezone.utc),
        "serial": 1003,
    },
}

not_before = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

for service, spec in cert_specs.items():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, spec["cn"]),
    ])

    san = x509.SubjectAlternativeName([
        x509.DNSName(name) for name in spec["sans"]
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(spec["serial"])
        .not_valid_before(not_before)
        .not_valid_after(spec["not_after"])
        .add_extension(san, critical=False)
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(private_key=key, algorithm=hashes.SHA256())
    )

    pem_path = outdir / f"{service}.pem"
    pem_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
PY

    python3 /tmp/generate_certs.py
    rm -f /tmp/generate_certs.py

    chown -R user:user /home/user/cert-audit
    chmod 755 /home/user
    chmod 775 /home/user/cert-audit
    chmod 775 /home/user/cert-audit/certs
    chmod 664 /home/user/cert-audit/services.tsv
    chmod 664 /home/user/cert-audit/certs/*.pem

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
