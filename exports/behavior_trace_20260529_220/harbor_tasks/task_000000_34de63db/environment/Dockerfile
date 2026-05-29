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

    REPO=/home/user/observability-dashboard

    rm -rf "$REPO"
    mkdir -p "$REPO/env"
    mkdir -p "$REPO/grafana/provisioning/datasources"
    mkdir -p "$REPO/grafana/dashboards/archive"
    mkdir -p "$REPO/scripts"

    cat > "$REPO/README.md" <<'EOF'
# Observability Dashboard

The dashboard loader reads .env.local at repository root.

Do not rely on archived dashboards or old production env files when choosing the datasource UID.
The active production dashboard is the service overview dashboard under grafana/dashboards/.
EOF

    cat > "$REPO/.env.example" <<'EOF'
DASHBOARD_DATASOURCE_UID=prometheus_default
DASHBOARD_ENV=development
EOF

    cat > "$REPO/env/.env.dev" <<'EOF'
DASHBOARD_DATASOURCE_UID=prometheus_dev
DASHBOARD_ENV=development
EOF

    cat > "$REPO/env/.env.staging" <<'EOF'
DASHBOARD_DATASOURCE_UID=prometheus_stage
DASHBOARD_ENV=staging
EOF

    cat > "$REPO/env/.env.production.old" <<'EOF'
DASHBOARD_DATASOURCE_UID=prometheus_prod_legacy
DASHBOARD_ENV=production
EOF

    cat > "$REPO/grafana/provisioning/datasources/datasources.yml" <<'EOF'
apiVersion: 1

datasources:
  - name: Prometheus Dev
    type: prometheus
    uid: prometheus_dev
    url: http://prometheus-dev:9090
    access: proxy
    isDefault: false
  - name: Prometheus Stage
    type: prometheus
    uid: prometheus_stage
    url: http://prometheus-stage:9090
    access: proxy
    isDefault: false
  - name: Prometheus Production
    type: prometheus
    uid: prom-prod-primary
    url: http://prometheus-prod:9090
    access: proxy
    isDefault: true
  - name: Prometheus Production Legacy
    type: prometheus
    uid: prometheus_prod_legacy
    url: http://prometheus-legacy:9090
    access: proxy
    isDefault: false
EOF

    cat > "$REPO/grafana/dashboards/service-overview.json" <<'EOF'
{
  "title": "Service Overview",
  "tags": ["production", "active"],
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus",
        "current": {
          "text": "Prometheus Production",
          "value": "prom-prod-primary"
        }
      }
    ]
  },
  "panels": [
    {
      "title": "Request Rate",
      "datasource": {
        "type": "prometheus",
        "uid": "prom-prod-primary"
      },
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[5m]))"
        }
      ]
    },
    {
      "title": "Error Rate",
      "datasource": {
        "type": "prometheus",
        "uid": "prom-prod-primary"
      },
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m]))"
        }
      ]
    }
  ]
}
EOF

    cat > "$REPO/grafana/dashboards/latency-drilldown.json" <<'EOF'
{
  "title": "Latency Drilldown",
  "tags": ["staging", "diagnostic"],
  "panels": [
    {
      "title": "p95 Latency",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus_stage"
      },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
        }
      ]
    }
  ]
}
EOF

    cat > "$REPO/grafana/dashboards/archive/service-overview-old.json" <<'EOF'
{
  "title": "Service Overview Old",
  "tags": ["production", "archived"],
  "panels": [
    {
      "title": "Request Rate",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus_prod_legacy"
      },
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[5m]))"
        }
      ]
    }
  ]
}
EOF

    cat > "$REPO/scripts/render-dashboard-env.py" <<'EOF'
#!/usr/bin/env python3
from pathlib import Path

env = Path("/home/user/observability-dashboard/.env.local")
if not env.exists():
    raise SystemExit("missing .env.local")

values = {}
for line in env.read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        values[key] = value

required = ["DASHBOARD_DATASOURCE_UID", "DASHBOARD_ENV"]
missing = [key for key in required if key not in values]
if missing:
    raise SystemExit("missing keys: " + ",".join(missing))

print(f"datasource={values['DASHBOARD_DATASOURCE_UID']}")
print(f"environment={values['DASHBOARD_ENV']}")
EOF

    rm -f "$REPO/.env.local" "$REPO/config-selection.log"

    chown -R user:user /home/user
    chmod -R u+rwX,go+rX "$REPO"
    chmod +x "$REPO/scripts/render-dashboard-env.py"

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
