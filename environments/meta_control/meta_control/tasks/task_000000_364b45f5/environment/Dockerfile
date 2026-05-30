FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        bash \
        coreutils \
        gawk \
        passwd
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/process_audit

    cat > /home/user/process_audit/worker_events.log <<'EOF'
2026-02-14T09:00:00Z|2401|ingest-alpha|START|batch=morning queue=raw
2026-02-14T09:02:10Z|2402|parser-beta|START|batch=morning queue=parse
2026-02-14T09:04:45Z|2403|enricher-gamma|START|batch=morning queue=enrich
2026-02-14T09:10:00Z|2401|ingest-alpha|STOP|exit=0 processed=180
2026-02-14T09:12:15Z|2404|shipper-delta|START|batch=morning queue=ship
2026-02-14T09:14:00Z|2402|parser-beta|STOP|exit=0 processed=176
2026-02-14T09:15:30Z|2405|parser-beta|START|batch=retry queue=parse
2026-02-14T09:18:10Z|2403|enricher-gamma|STOP|exit=1 reason=upstream_timeout
2026-02-14T09:20:00Z|2406|ingest-alpha|START|batch=late queue=raw
2026-02-14T09:21:25Z|2404|shipper-delta|STOP|exit=0 shipped=176
2026-02-14T09:23:40Z|2407|metrics-epsilon|START|batch=monitor queue=metrics
2026-02-14T09:25:00Z|2406|ingest-alpha|STOP|exit=0 processed=42
2026-02-14T09:26:35Z|2408|enricher-gamma|START|batch=recover queue=enrich
2026-02-14T09:28:00Z|2405|parser-beta|STOP|exit=0 processed=44
2026-02-14T09:29:30Z|2409|shipper-delta|START|batch=late queue=ship
EOF

    cat > /home/user/process_audit/make_summary.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
log="/home/user/process_audit/worker_events.log"
out="/home/user/process_audit/active_worker_summary.txt"
awk -F'|' '$4=="START"{pid[$2]=$3 "|" $1 "|" $5} END{
  print "ACTIVE_WORKER_SUMMARY"
  print "source=" log
  print "active_count=" length(pid)
  for (p in pid) {
    split(pid[p], a, "|")
    print "PID=" p " WORKER=" a[1] " STARTED_AT=" a[2] " DETAIL=" a[3]
  }
  print "verification=manual_artifact_checked"
}' "$log" > "$out"
echo "summary written to $out"
EOF

    chown -R user:user /home/user/process_audit
    chmod 755 /home/user
    chmod 755 /home/user/process_audit
    chmod 644 /home/user/process_audit/worker_events.log
    chmod 755 /home/user/process_audit/make_summary.sh

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
