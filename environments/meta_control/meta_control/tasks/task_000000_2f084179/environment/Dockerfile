FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        tzdata \
        ca-certificates
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/monitoring/data
    mkdir -p /home/user/monitoring/out

    cat > /home/user/monitoring/data/alert_windows.csv <<'EOF'
service,utc_start,severity
checkout-api,2026-01-12T14:30:00Z,page
billing-worker,2026-01-12T16:00:00Z,ticket
search-indexer,2026-01-13T02:15:00Z,page
EOF

    cat > /home/user/monitoring/alert_env.conf <<'EOF'
ALERT_TZ=UTC
ALERT_LOCALE=C
EOF

    cat > /home/user/monitoring/render_alerts.py <<'EOF'
#!/usr/bin/env python3
import csv
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import locale

BASE = Path("/home/user/monitoring")
DATA = BASE / "data" / "alert_windows.csv"
OUT = BASE / "out" / "alert_windows.log"
CONF = BASE / "alert_env.conf"

def load_conf(path):
    values = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, v = raw.split("=", 1)
            values[k.strip()] = v.strip()
    return values

def main():
    conf = load_conf(CONF)

    # Intentional trap: the config file uses ALERT_TZ / ALERT_LOCALE,
    # but this renderer initially looks for TZ_NAME / LC_TIME_NAME.
    tz_name = conf.get("TZ_NAME", "UTC")
    loc_name = conf.get("LC_TIME_NAME", "C")

    try:
        locale.setlocale(locale.LC_TIME, loc_name)
    except locale.Error:
        locale.setlocale(locale.LC_TIME, "C")

    tz = ZoneInfo(tz_name)

    rows = []
    with DATA.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt_utc = datetime.strptime(row["utc_start"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
            local_dt = dt_utc.astimezone(tz)
            rows.append((dt_utc, row["service"], local_dt, row["severity"]))

    rows.sort(key=lambda item: item[0])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        f.write(f"ALERT_WINDOWS tz={tz_name} locale={loc_name}\n")
        for _, service, local_dt, severity in rows:
            weekday = local_dt.strftime("%a")
            stamp = local_dt.strftime("%Y-%m-%d %H:%M %Z")
            f.write(f"{service}|{weekday}|{stamp}|severity={severity}\n")

if __name__ == "__main__":
    main()
EOF

    chown -R user:user /home/user/monitoring
    chmod -R u+rwX,go+rX /home/user/monitoring
    chmod +x /home/user/monitoring/render_alerts.py

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
