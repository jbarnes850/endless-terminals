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

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/policy-pipeline/bin
    mkdir -p /home/user/policy-pipeline/data
    mkdir -p /home/user/policy-pipeline/output

    cat > /home/user/policy-pipeline/data/legacy_exceptions.json <<'EOF'
[
  {
    "control_id": "CIS-1.1.1",
    "service": "artifact-registry",
    "environment": "dev",
    "expires": "2026-01-15",
    "reason": "Temporary exception while container signing rollout completes"
  },
  {
    "control_id": "CIS-2.3.4",
    "service": "build-runner",
    "environment": "ci",
    "expires": "2025-12-31",
    "reason": "Pinned legacy runner requires scoped network egress during migration"
  },
  {
    "control_id": "ORG-SEC-7",
    "service": "secrets-sync",
    "environment": "staging",
    "expires": "2025-10-01",
    "reason": "Compensating monitoring enabled until vault namespace split is complete"
  }
]
EOF

    cat > /home/user/policy-pipeline/bin/render_policy_report.py <<'EOF'
#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS_PATH = ROOT / "data" / "legacy_exceptions.json"
REPORT_PATH = ROOT / "output" / "policy_report.json"

def load_exceptions():
    with EXCEPTIONS_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def main():
    exceptions = load_exceptions()
    report = {
        "pipeline": "policy-exception-render",
        "source": str(EXCEPTIONS_PATH),
        "exception_count": len(exceptions),
        "exceptions_by_environment": {},
        "controls": sorted(item["control_id"] for item in exceptions),
        "expired_count": 0
    }
    for item in exceptions:
        env = item["environment"]
        report["exceptions_by_environment"][env] = report["exceptions_by_environment"].get(env, 0) + 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")

if __name__ == "__main__":
    main()
EOF

    chmod 755 /home/user/policy-pipeline/bin/render_policy_report.py
    chmod 664 /home/user/policy-pipeline/data/legacy_exceptions.json

    chown -R user:user /home/user/policy-pipeline
    chmod -R u+rwX,g+rwX /home/user/policy-pipeline

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
