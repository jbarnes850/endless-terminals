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

    ROOT=/home/user/alert_env_audit
    mkdir -p "$ROOT/env" "$ROOT/config" "$ROOT/scripts" "$ROOT/out"

    cat > "$ROOT/env/.env.base" <<'EOF'
# Base defaults for alerting
SERVICE_NAME=checkout-api
ENVIRONMENT=development
LOG_LEVEL=info
METRICS_BACKEND=prometheus
ALERT_WARNING_THRESHOLD=0.70
ALERT_CRITICAL_THRESHOLD=0.90
ALERT_LATENCY_MS=450
ALERT_CHANNELS=email, slack-dev
ALERT_OWNER=platform-default
ESCALATION_MINUTES=45
PAGER_ROTATION=none
EOF

    cat > "$ROOT/env/.env.shared" <<'EOF'
# Shared monitoring values
ENVIRONMENT=staging
LOG_LEVEL=debug
ALERT_CHANNELS=email, slack-observability
ALERT_OWNER=observability-team
ESCALATION_MINUTES=30
PAGER_ROTATION=primary-sre
EOF

    cat > "$ROOT/env/.env.production" <<'EOF'
# Production overrides
ENVIRONMENT=production
LOG_LEVEL=warn
METRICS_BACKEND=managed-prometheus
ALERT_WARNING_THRESHOLD=0.82
ALERT_CRITICAL_THRESHOLD=0.95
ALERT_LATENCY_MS=375
ALERT_CHANNELS=pagerduty, slack-prod, email
ESCALATION_MINUTES=15
PAGER_ROTATION=checkout-prod
EOF

    cat > "$ROOT/env/.env.local" <<'EOF'
# Temporary local override for current incident drill
LOG_LEVEL=error
ALERT_CRITICAL_THRESHOLD=0.97
ALERT_CHANNELS=pagerduty, slack-checkout, email
ALERT_OWNER=checkout-oncall
ESCALATION_MINUTES=10
EOF

    cat > "$ROOT/config/alert_rules.csv" <<'EOF'
name,metric,threshold_source,severity,enabled
High error ratio,http_error_ratio,critical,critical,true
Warning error ratio,http_error_ratio,warning,warning,true
Checkout latency p95,http_request_duration_p95_ms,latency_ms,warning,true
Synthetic canary failures,synthetic_canary_failures,critical,critical,false
Queue saturation,checkout_queue_saturation,warning,warning, TRUE 
EOF

    cat > "$ROOT/scripts/build_alert_matrix.py" <<'EOF'
#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path("/home/user/alert_env_audit")
OUT = ROOT / "out" / "alert_matrix.json"

def read_env_first_wins(paths):
    env = {}
    for path in paths:
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            # BUG: first value wins instead of dotenv-style later override
            env.setdefault(k.strip(), v.strip())
    return env

def main():
    paths = [
        ROOT / "env" / ".env.base",
        ROOT / "env" / ".env.shared",
        ROOT / "env" / ".env.production",
        ROOT / "env" / ".env.local",
    ]
    env = read_env_first_wins(paths)
    alerts = []
    disabled = 0
    with (ROOT / "config" / "alert_rules.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            # BUG: only lowercase true is enabled; spaced TRUE is dropped
            if row["enabled"].strip() != "true":
                disabled += 1
                continue
            source = row["threshold_source"].strip()
            threshold_key = {
                "warning": "ALERT_WARNING_THRESHOLD",
                "critical": "ALERT_CRITICAL_THRESHOLD",
                "latency_ms": "ALERT_LATENCY_MS",
            }[source]
            alerts.append({
                "name": row["name"].strip(),
                "metric": row["metric"].strip(),
                "threshold": float(env[threshold_key]),
                "severity": row["severity"].strip(),
                # BUG: leaves channels as a string
                "channels": env["ALERT_CHANNELS"],
                "owner": env["ALERT_OWNER"],
                "escalation_minutes": int(env["ESCALATION_MINUTES"]),
                "pager_rotation": env["PAGER_ROTATION"],
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "service": env["SERVICE_NAME"],
        "generated_from": [str(p) for p in paths],
        "effective_environment": env,
        "alerts": alerts,
        "summary": {
            "enabled_alert_count": len(alerts),
            "disabled_rule_count": disabled,
            "critical_alert_count": sum(1 for a in alerts if a["severity"] == "critical"),
            "warning_alert_count": sum(1 for a in alerts if a["severity"] == "warning"),
            "channels_count": len(env["ALERT_CHANNELS"].split(",")),
            "uses_local_override": False,
        }
    }, indent=2) + "\n")

if __name__ == "__main__":
    main()
EOF

    chmod 755 "$ROOT/scripts/build_alert_matrix.py"
    chown -R user:user /home/user
    chmod -R u+rwX,go+rX "$ROOT"
    chmod 777 "$ROOT" "$ROOT/env" "$ROOT/config" "$ROOT/scripts" "$ROOT/out"

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
