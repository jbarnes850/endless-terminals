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

    useradd -m -s /bin/bash user

    mkdir -p /home/user/capacity_planner/data

    cat > /home/user/capacity_planner/data/services.csv <<'EOF'
service,team,tier,cpu_limit_millicores,memory_limit_mib
api-gateway,platform,gold,2000,4096
billing-worker,finance,silver,1500,2048
catalog-search,commerce,gold,4000,8192
email-sender,growth,bronze,1000,1024
image-resizer,media,silver,2500,3072
inventory-sync,commerce,silver,1200,2048
metrics-rollup,platform,bronze,800,1536
recommendation-api,ml,gold,6000,12288
report-export,finance,bronze,1800,4096
session-store,platform,gold,3000,6144
EOF

    cat > /home/user/capacity_planner/data/usage.json <<'EOF'
{
  "samples": [
    {
      "service": "api-gateway",
      "cpu_used_millicores": 1600,
      "memory_used_mib": 3000
    },
    {
      "service": "billing-worker",
      "cpu_used_millicores": 900,
      "memory_used_mib": 1900
    },
    {
      "service": "catalog-search",
      "cpu_used_millicores": 3100,
      "memory_used_mib": 7000
    },
    {
      "service": "email-sender",
      "cpu_used_millicores": 810,
      "memory_used_mib": 600
    },
    {
      "service": "image-resizer",
      "cpu_used_millicores": 2100,
      "memory_used_mib": 2600
    },
    {
      "service": "inventory-sync",
      "cpu_used_millicores": 500,
      "memory_used_mib": 1200
    },
    {
      "service": "metrics-rollup",
      "cpu_used_millicores": 650,
      "memory_used_mib": 1400
    },
    {
      "service": "recommendation-api",
      "cpu_used_millicores": 4500,
      "memory_used_mib": 11000
    },
    {
      "service": "report-export",
      "cpu_used_millicores": 1000,
      "memory_used_mib": 3400
    },
    {
      "service": "session-store",
      "cpu_used_millicores": 2600,
      "memory_used_mib": 5000
    },
    {
      "service": "orphan-debug-job",
      "cpu_used_millicores": 9999,
      "memory_used_mib": 9999
    }
  ]
}
EOF

    rm -rf /home/user/capacity_planner/outputs

    chown -R user:user /home/user/capacity_planner
    chmod -R u+rwX,go+rX /home/user/capacity_planner

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
