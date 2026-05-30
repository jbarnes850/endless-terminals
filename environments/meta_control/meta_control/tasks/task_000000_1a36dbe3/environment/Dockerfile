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
        ca-certificates
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/automation_lab/workflows
    mkdir -p /home/user/automation_lab/tools
    mkdir -p /home/user/automation_lab/logs
    mkdir -p /home/user/automation_lab/out

    cat > /home/user/automation_lab/workflows/backup_reports.env <<'EOF'
ID=backup_reports
ENABLED=true
SCHEDULER=cron
CRON_EXPR=17 2 * * *
ON_CALENDAR=
COMMAND=scripts/backup_reports.sh
DESCRIPTION=Archive generated reporting CSV files
EOF

    cat > /home/user/automation_lab/workflows/inventory_snapshot.env <<'EOF'
ID=inventory_snapshot
ENABLED=true
SCHEDULER=systemd
CRON_EXPR=
ON_CALENDAR=Mon..Fri 06:10
COMMAND=scripts/inventory_snapshot.sh
DESCRIPTION=Capture weekday inventory snapshot
EOF

    cat > /home/user/automation_lab/workflows/partner_sync.env <<'EOF'
ID=partner_sync
ENABLED=true
SCHEDULER=cron
CRON_EXPR=*/20 8-18 * * 1-5
ON_CALENDAR=
COMMAND=scripts/partner_sync.sh
DESCRIPTION=Synchronize partner feed during business hours
EOF

    cat > /home/user/automation_lab/workflows/cache_warm.env <<'EOF'
ID=cache_warm
ENABLED=true
SCHEDULER=systemd
CRON_EXPR=
ON_CALENDAR=*-*-* 04:45:00
COMMAND=scripts/cache_warm.sh
DESCRIPTION=Warm API cache before morning traffic
EOF

    cat > /home/user/automation_lab/workflows/legacy_cleanup.env <<'EOF'
ID=legacy_cleanup
ENABLED=false
SCHEDULER=cron
CRON_EXPR=0 0 * * 0
ON_CALENDAR=
COMMAND=scripts/legacy_cleanup.sh
DESCRIPTION=Deprecated cleanup job
EOF

    cat > /home/user/automation_lab/tools/render_schedules.py <<'EOF'
#!/usr/bin/env python3
"""
Intentionally incomplete helper for the automation scheduling lab.

This script exits successfully and writes plausible artifacts, but it only
renders the first enabled systemd workflow it encounters. Students may repair
or replace this helper; final artifact correctness is what matters.
"""
from pathlib import Path

LAB = Path("/home/user/automation_lab")
WORKFLOWS = LAB / "workflows"
OUT = LAB / "out"
SYSTEMD = OUT / "systemd-user"


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SYSTEMD.mkdir(parents=True, exist_ok=True)

    workflows = [parse_env(path) for path in sorted(WORKFLOWS.glob("*.env"))]
    enabled = [wf for wf in workflows if wf.get("ENABLED") == "true"]

    cron_jobs = sorted(
        (wf for wf in enabled if wf.get("SCHEDULER") == "cron"),
        key=lambda wf: wf.get("ID", ""),
    )

    cron_lines = [
        "SHELL=/bin/bash",
        "PATH=/usr/local/bin:/usr/bin:/bin",
    ]
    for wf in cron_jobs:
        workflow_id = wf["ID"]
        cron_lines.append(
            f"{wf['CRON_EXPR']} cd {LAB} && /bin/bash {wf['COMMAND']} "
            f">> {LAB}/logs/{workflow_id}.log 2>&1 # {workflow_id}: {wf['DESCRIPTION']}"
        )
    (OUT / "user.crontab").write_text("\n".join(cron_lines) + "\n", encoding="utf-8")

    # Deliberate bug: only render the first enabled systemd workflow.
    systemd_workflows = sorted(
        (wf for wf in enabled if wf.get("SCHEDULER") == "systemd"),
        key=lambda wf: wf.get("ID", ""),
    )
    if systemd_workflows:
        wf = systemd_workflows[0]
        workflow_id = wf["ID"]
        service = (
            "[Unit]\n"
            f"Description={wf['DESCRIPTION']}\n"
            "\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"WorkingDirectory={LAB}\n"
            f"ExecStart=/bin/bash {wf['COMMAND']}\n"
        )
        timer = (
            "[Unit]\n"
            f"Description=Timer for {wf['DESCRIPTION']}\n"
            "\n"
            "[Timer]\n"
            f"OnCalendar={wf['ON_CALENDAR']}\n"
            "Persistent=true\n"
            "\n"
            "[Install]\n"
            "WantedBy=timers.target\n"
        )
        (SYSTEMD / f"{workflow_id}.service").write_text(service, encoding="utf-8")
        (SYSTEMD / f"{workflow_id}.timer").write_text(timer, encoding="utf-8")

    (OUT / "verification.log").write_text(
        "command_status=ok\n"
        "artifact_presence=ok\n"
        "cron_validity=unchecked\n"
        "systemd_validity=unchecked\n"
        "semantic_result=unchecked\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

    chmod 755 /home/user
    chmod -R u+rwX,go+rX /home/user/automation_lab
    chmod 664 /home/user/automation_lab/workflows/*.env
    chmod 664 /home/user/automation_lab/tools/render_schedules.py
    chown -R user:user /home/user/automation_lab
    chown user:user /home/user

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
