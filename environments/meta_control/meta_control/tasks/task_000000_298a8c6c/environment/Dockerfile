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

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/ops-triage

    cat > /home/user/ops-triage/incidents.jsonl <<'EOF'
{"incident_id":"INC-1042","service":"checkout-api","severity":"high","started":"2026-02-14T09:12:00Z","status":"investigating","owner":"mira","next_action":"compare error budget burn against the last deploy window"}
{"incident_id":"INC-1043","service":"search-indexer","severity":"low","started":"2026-02-14T09:40:00Z","status":"resolved","owner":"nolan","next_action":"archive the temporary shard allocation notes"}
{"incident_id":"INC-1044","service":"billing-worker","severity":"critical","started":"2026-02-14T10:05:00Z","status":"mitigating","owner":"sana","next_action":"confirm queue drain rate remains above the recovery threshold"}
{"incident_id":"INC-1045","service":"metrics-gateway","severity":"medium","started":"2026-02-14T10:22:00Z","status":"monitoring","owner":"devon","next_action":"watch p95 ingest latency for two consecutive scrape intervals"}
{"incident_id":"INC-1046","service":"auth-session","severity":"high","started":"2026-02-14T10:31:00Z","status":"investigating","owner":"li","next_action":"check whether token refresh failures correlate with cache evictions"}
EOF

    cat > /home/user/ops-triage/.markdownlint.json <<'EOF'
{
  "default": true,
  "MD013": false,
  "MD033": true,
  "MD041": true,
  "MD022": true,
  "MD032": true,
  "MD031": true,
  "MD047": true,
  "MD058": true
}
EOF

    cat > /home/user/ops-triage/check_markdown.py <<'PY'
#!/usr/bin/env python3
import sys
from pathlib import Path

def fail(msg):
    print(msg, file=sys.stderr)
    return 1

def is_table_row(line):
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")

def main():
    if len(sys.argv) != 2:
        return fail("usage: check_markdown.py <markdown-file>")

    path = Path(sys.argv[1])
    if not path.is_file():
        return fail(f"not a file: {path}")

    data = path.read_bytes()
    if not data.endswith(b"\n"):
        return fail("MD047: file must end with a single newline")

    text = data.decode("utf-8")
    lines = text.splitlines()

    if not lines:
        return fail("empty markdown file")

    if not lines[0].startswith("# "):
        return fail("MD041: first line must be a top-level heading")

    in_fence = False
    fence_marker = None

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = None
            continue

        if in_fence:
            continue

        if stripped.startswith("#"):
            prev_blank = idx == 1 or lines[idx - 2].strip() == ""
            next_blank = idx == len(lines) or lines[idx].strip() == ""
            if not prev_blank or not next_blank:
                return fail(f"MD022: heading at line {idx} must be surrounded by blank lines")

        if is_table_row(line):
            prev_blank = idx == 1 or lines[idx - 2].strip() == ""
            if prev_blank:
                if idx == len(lines):
                    return fail(f"MD058: table at line {idx} is incomplete")
                sep_index = idx
                if sep_index >= len(lines):
                    return fail(f"MD058: table at line {idx} lacks separator")
                sep = lines[sep_index].strip()
                if not is_table_row(sep):
                    return fail(f"MD058: table at line {idx} lacks separator row")
                cells = [cell.strip() for cell in sep.strip("|").split("|")]
                if not cells or any(set(cell) - set("-: ") or "-" not in cell for cell in cells):
                    return fail(f"MD058: invalid table separator at line {idx + 1}")

    if in_fence:
        return fail("MD031: fenced code block is not closed")

    for idx, line in enumerate(lines, start=1):
        if is_table_row(line):
            before_ok = idx == 1 or lines[idx - 2].strip() == "" or is_table_row(lines[idx - 2])
            after_ok = idx == len(lines) or lines[idx].strip() == "" or is_table_row(lines[idx])
            if not before_ok or not after_ok:
                return fail(f"MD032/MD058: table row at line {idx} must be in a separated table block")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

    chmod 0755 /home/user/ops-triage/check_markdown.py
    chown -R user:user /home/user/ops-triage
    chmod 0755 /home/user
    chmod 0755 /home/user/ops-triage
    chmod 0644 /home/user/ops-triage/incidents.jsonl
    chmod 0644 /home/user/ops-triage/.markdownlint.json

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
