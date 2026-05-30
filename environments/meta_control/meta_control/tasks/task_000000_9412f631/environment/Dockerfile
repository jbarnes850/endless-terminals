FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-yaml \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest PyYAML

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/alerting-lab/input
    mkdir -p /home/user/alerting-lab/tools
    mkdir -p /home/user/alerting-lab/output

    cat > /home/user/alerting-lab/input/services.csv <<'EOF'
service_name,team,environment,severity,window,enabled,priority
checkout-api,payments,prod,critical,5m,true,P0
catalog-worker,retail,prod,warning,10m,true,P2
fraud-scanner,risk,prod,critical,3m,false,P0
email-dispatcher,growth,staging,warning,15m,true,P3
inventory-sync,supply,prod,critical,7m,true,P1
EOF

    cat > /home/user/alerting-lab/tools/generate_alerts.py <<'EOF'
#!/usr/bin/env python3
import csv
import os
import yaml

BASE = "/home/user/alerting-lab"
INPUT = os.path.join(BASE, "input", "services.csv")
OUTPUT = os.path.join(BASE, "output", "service_alerts.yml")

def build_rule(row):
    service = row["service_name"]
    env = row["environment"]
    team = row["team"]
    window = row["window"]
    return {
        "alert": f"ServiceDown_{service}",
        "expr": f'up{{job="{service}"}} == 0',
        "for": window,
        "labels": {
            "severity": row["severity"],
            "team": team,
            "environment": env,
        },
        "annotations": {
            "summary": f"{service} is down",
            "description": f"Service {service} in {env} has been down for {window}. Notify {team}.",
        },
    }

def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    rules = []
    with open(INPUT, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("enabled", "").lower() != "true":
                continue
            if row.get("priority") not in ("P0", "P1"):
                continue
            rules.append(build_rule(row))

    doc = {
        "groups": [
            {
                "name": "generated-service-alerts",
                "rules": rules,
            }
        ]
    }

    with open(OUTPUT, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)

    print(f"Wrote {len(rules)} alert rules to {OUTPUT}")

if __name__ == "__main__":
    main()
EOF

    chmod 755 /home/user/alerting-lab/tools/generate_alerts.py
    chmod 644 /home/user/alerting-lab/input/services.csv

    chown -R user:user /home/user/alerting-lab
    chmod 755 /home/user
    chmod 755 /home/user/alerting-lab
    chmod 755 /home/user/alerting-lab/input
    chmod 755 /home/user/alerting-lab/tools
    chmod 755 /home/user/alerting-lab/output

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
