FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pytest \
        tzdata \
        ca-certificates
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/clockutil/out

    cat > /home/user/clockutil/deadline.env <<'EOF'
APP_TZ=Europe/Berlin
APP_LOCALE=C
DEADLINE_EPOCH=1704067200
EOF

    cat > /home/user/clockutil/format_deadline.py <<'EOF'
#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path

BASE = Path("/home/user/clockutil")
CONFIG = BASE / "deadline.env"
OUT = BASE / "out" / "deadline_report.txt"

def read_env(path):
    values = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values

def main():
    cfg = read_env(CONFIG)
    epoch = int(cfg["DEADLINE_EPOCH"])

    # BUG: ignores APP_TZ and APP_LOCALE; formats in UTC.
    dt = datetime.utcfromtimestamp(epoch)
    rendered = dt.strftime("%a %Y-%m-%d %H:%M:%S UTC")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        f"timezone=UTC\n"
        f"locale=default\n"
        f"deadline={rendered}\n"
    )

if __name__ == "__main__":
    main()
EOF

    chmod 0755 /home/user/clockutil/format_deadline.py
    chmod 0664 /home/user/clockutil/deadline.env
    chmod 0775 /home/user/clockutil /home/user/clockutil/out

    chown -R user:user /home/user/clockutil
    chown user:user /home/user

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
