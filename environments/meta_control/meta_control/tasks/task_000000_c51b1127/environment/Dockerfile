FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        sqlite3 \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/log-investigation

    python3 <<'PY'
import sqlite3
from pathlib import Path

db_path = Path("/home/user/log-investigation/access_logs.sqlite")
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

cur.execute("""
CREATE TABLE access_events (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status INTEGER NOT NULL,
    bytes INTEGER NOT NULL,
    user_agent TEXT NOT NULL,
    request_id TEXT NOT NULL
)
""")

rows = []

def add(ts, method, path, status, bytes_=1234, ua="Mozilla/5.0", rid=None):
    if rid is None:
        rid = f"req-{len(rows)+1:04d}"
    rows.append((ts, method, path, status, bytes_, ua, rid))

# Outside-window HTTP 500 distractors
add("2024-04-18T13:58:11", "GET", "/api/search", 500, 842, "curl/8.1")
add("2024-04-18T13:59:02", "GET", "/api/report/export", 500, 912, "Mozilla/5.0")
add("2024-04-18T13:59:41", "POST", "/api/auth/login", 500, 367, "Mozilla/5.0")
add("2024-04-18T14:10:01", "GET", "/api/search", 500, 776, "curl/8.1")
add("2024-04-18T14:11:22", "GET", "/api/report/export", 500, 1042, "Mozilla/5.0")
add("2024-04-18T14:12:03", "GET", "/api/catalog", 500, 690, "Mozilla/5.0")

# Incident-window HTTP 500 evidence rows
for ts in [
    "2024-04-18T14:00:03",
    "2024-04-18T14:01:17",
    "2024-04-18T14:02:29",
    "2024-04-18T14:04:45",
    "2024-04-18T14:07:14",
    "2024-04-18T14:09:58",
]:
    add(ts, "GET", "/api/search", 500, 815, "Mozilla/5.0")

for ts in [
    "2024-04-18T14:00:12",
    "2024-04-18T14:00:59",
    "2024-04-18T14:01:36",
    "2024-04-18T14:02:04",
    "2024-04-18T14:03:51",
    "2024-04-18T14:05:23",
    "2024-04-18T14:06:08",
    "2024-04-18T14:08:40",
    "2024-04-18T14:09:12",
]:
    add(ts, "GET", "/api/report/export", 500, 1096, "Mozilla/5.0")

for ts in [
    "2024-04-18T14:00:48",
    "2024-04-18T14:04:10",
    "2024-04-18T14:06:31",
]:
    add(ts, "POST", "/api/auth/login", 500, 401, "Mozilla/5.0")

for ts in [
    "2024-04-18T14:02:44",
    "2024-04-18T14:03:18",
    "2024-04-18T14:05:57",
    "2024-04-18T14:08:05",
]:
    add(ts, "GET", "/api/catalog", 500, 724, "Mozilla/5.0")

# Incident-window non-500 distractors across required paths and statuses
non_500_rows = [
    ("2024-04-18T14:00:05", "GET", "/healthz", 200, 24, "kube-probe/1.28"),
    ("2024-04-18T14:00:18", "GET", "/static/app.js", 200, 43122, "Mozilla/5.0"),
    ("2024-04-18T14:00:31", "GET", "/api/search", 200, 2048, "Mozilla/5.0"),
    ("2024-04-18T14:00:44", "POST", "/api/auth/login", 302, 128, "Mozilla/5.0"),
    ("2024-04-18T14:01:02", "GET", "/api/catalog", 200, 3180, "Mozilla/5.0"),
    ("2024-04-18T14:01:23", "GET", "/api/report/export", 200, 6200, "Mozilla/5.0"),
    ("2024-04-18T14:01:47", "GET", "/static/app.js", 304 if False else 200, 43122, "Mozilla/5.0"),
    ("2024-04-18T14:02:11", "POST", "/api/auth/login", 201, 96, "Mozilla/5.0"),
    ("2024-04-18T14:02:33", "GET", "/healthz", 204, 0, "kube-probe/1.28"),
    ("2024-04-18T14:02:58", "GET", "/api/search", 404, 512, "Mozilla/5.0"),
    ("2024-04-18T14:03:09", "GET", "/api/catalog", 200, 3021, "Mozilla/5.0"),
    ("2024-04-18T14:03:27", "GET", "/static/app.js", 200, 43122, "Mozilla/5.0"),
    ("2024-04-18T14:03:42", "GET", "/api/report/export", 302, 144, "Mozilla/5.0"),
    ("2024-04-18T14:04:04", "GET", "/healthz", 200, 24, "kube-probe/1.28"),
    ("2024-04-18T14:04:32", "GET", "/api/search", 200, 2101, "Mozilla/5.0"),
    ("2024-04-18T14:04:58", "GET", "/api/catalog", 404, 640, "Mozilla/5.0"),
    ("2024-04-18T14:05:16", "GET", "/static/app.js", 200, 43122, "Mozilla/5.0"),
    ("2024-04-18T14:05:41", "POST", "/api/auth/login", 302, 128, "Mozilla/5.0"),
    ("2024-04-18T14:06:02", "GET", "/api/report/export", 200, 5900, "Mozilla/5.0"),
    ("2024-04-18T14:06:24", "GET", "/healthz", 204, 0, "kube-probe/1.28"),
    ("2024-04-18T14:06:49", "GET", "/api/search", 200, 1988, "Mozilla/5.0"),
    ("2024-04-18T14:07:03", "GET", "/static/app.js", 200, 43122, "Mozilla/5.0"),
    ("2024-04-18T14:07:36", "GET", "/api/catalog", 200, 3333, "Mozilla/5.0"),
    ("2024-04-18T14:08:12", "GET", "/api/report/export", 404, 700, "Mozilla/5.0"),
    ("2024-04-18T14:08:27", "GET", "/healthz", 200, 24, "kube-probe/1.28"),
    ("2024-04-18T14:08:53", "POST", "/api/auth/login", 201, 104, "Mozilla/5.0"),
    ("2024-04-18T14:09:07", "GET", "/static/app.js", 200, 43122, "Mozilla/5.0"),
    ("2024-04-18T14:09:31", "GET", "/api/search", 302, 160, "Mozilla/5.0"),
    ("2024-04-18T14:09:45", "GET", "/api/catalog", 204, 0, "Mozilla/5.0"),
]
for ts, method, path, status, bytes_, ua in non_500_rows:
    add(ts, method, path, status, bytes_, ua)

# A small amount of additional plausible traffic outside the incident window
extra_rows = [
    ("2024-04-18T13:55:10", "GET", "/healthz", 200, 24, "kube-probe/1.28"),
    ("2024-04-18T13:56:25", "GET", "/static/app.js", 200, 43122, "Mozilla/5.0"),
    ("2024-04-18T14:12:44", "GET", "/healthz", 200, 24, "kube-probe/1.28"),
    ("2024-04-18T14:13:08", "GET", "/api/search", 200, 1901, "Mozilla/5.0"),
]
for ts, method, path, status, bytes_, ua in extra_rows:
    add(ts, method, path, status, bytes_, ua)

cur.executemany(
    """
    INSERT INTO access_events
        (ts, method, path, status, bytes, user_agent, request_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    rows,
)
conn.commit()
conn.close()
PY

    chown -R user:user /home/user/log-investigation
    chmod 755 /home/user
    chmod 775 /home/user/log-investigation
    chmod 664 /home/user/log-investigation/access_logs.sqlite

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
