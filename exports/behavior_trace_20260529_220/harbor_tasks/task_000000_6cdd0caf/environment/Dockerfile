FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-pytest \
        ca-certificates
    python3 -m pip install --no-cache-dir --upgrade pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    mkdir -p /home/user/research_cluster/bin
    mkdir -p /home/user/research_cluster/datasets/raw/alpha
    mkdir -p /home/user/research_cluster/datasets/raw/beta
    mkdir -p /home/user/research_cluster/datasets/raw/gamma
    mkdir -p /home/user/research_cluster/datasets/manifests/shards
    mkdir -p /home/user/research_cluster/run_logs

    printf 'alpha sample 001\ncondition=control\nvalue=17\n' > /home/user/research_cluster/datasets/raw/alpha/a001.txt
    printf 'alpha sample 002\ncondition=treated\nvalue=23\n' > /home/user/research_cluster/datasets/raw/alpha/a002.txt
    printf 'alpha sample 003\ncondition=control\nvalue=19\n' > /home/user/research_cluster/datasets/raw/alpha/a003.txt
    printf 'alpha sample 004\ncondition=treated\nvalue=29\n' > /home/user/research_cluster/datasets/raw/alpha/a004.txt

    printf 'beta sample 001\ncondition=control\nvalue=31\n' > /home/user/research_cluster/datasets/raw/beta/b001.txt
    printf 'beta sample 002\ncondition=treated\nvalue=37\n' > /home/user/research_cluster/datasets/raw/beta/b002.txt
    printf 'beta sample 003\ncondition=control\nvalue=41\n' > /home/user/research_cluster/datasets/raw/beta/b003.txt

    printf 'gamma sample 001\ncondition=control\nvalue=43\n' > /home/user/research_cluster/datasets/raw/gamma/g001.txt
    printf 'gamma sample 002\ncondition=treated\nvalue=47\n' > /home/user/research_cluster/datasets/raw/gamma/g002.txt
    printf 'gamma sample 003\ncondition=control\nvalue=53\n' > /home/user/research_cluster/datasets/raw/gamma/g003.txt
    printf 'gamma sample 004\ncondition=treated\nvalue=59\n' > /home/user/research_cluster/datasets/raw/gamma/g004.txt
    printf 'gamma sample 005\ncondition=control\nvalue=61\n' > /home/user/research_cluster/datasets/raw/gamma/g005.txt

    cat > /home/user/research_cluster/bin/scan_shard.py <<'PY'
#!/usr/bin/env python3
import hashlib
import os
import sys
import time
from pathlib import Path

BASE = Path("/home/user/research_cluster")
RAW = BASE / "datasets" / "raw"
SHARDS = BASE / "datasets" / "manifests" / "shards"

ASSIGNMENTS = {
    0: [
        ("alpha", "a001.txt"),
        ("alpha", "a004.txt"),
        ("beta", "b003.txt"),
        ("gamma", "g003.txt"),
    ],
    1: [
        ("alpha", "a002.txt"),
        ("beta", "b001.txt"),
        ("gamma", "g001.txt"),
        ("gamma", "g004.txt"),
    ],
    2: [
        ("alpha", "a003.txt"),
        ("beta", "b002.txt"),
        ("gamma", "g002.txt"),
        ("gamma", "g005.txt"),
    ],
}

def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"0", "1", "2"}:
        print("usage: scan_shard.py {0|1|2}", file=sys.stderr)
        return 2

    shard = int(sys.argv[1])
    records = list(ASSIGNMENTS[shard])

    # Seeded distributed-debugging bug: shard 1 silently omits its last record
    # unless the full-scan environment variable is present for that worker.
    if shard == 1 and os.environ.get("RESEARCH_SCAN_FULL") != "1":
        records = records[:-1]

    SHARDS.mkdir(parents=True, exist_ok=True)
    out_path = SHARDS / f"shard_{shard}.tsv"
    tmp_path = SHARDS / f".shard_{shard}.tsv.tmp"

    with tmp_path.open("w", encoding="utf-8", newline="") as out:
        for dataset, filename in records:
            path = RAW / dataset / filename
            data = path.read_bytes()
            size = len(data)
            sha256 = hashlib.sha256(data).hexdigest()
            record_id = Path(filename).stem
            out.write(f"{dataset}\t{shard}\t{record_id}\t{filename}\t{size}\t{sha256}\n")
            out.flush()
            time.sleep(0.08)

    tmp_path.replace(out_path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

    cat > /home/user/research_cluster/bin/merge_manifests.py <<'PY'
#!/usr/bin/env python3
from pathlib import Path
import sys

BASE = Path("/home/user/research_cluster")
SHARDS = BASE / "datasets" / "manifests" / "shards"
OUT = BASE / "datasets" / "manifests" / "final_manifest.tsv"
HEADER = "dataset\tshard\trecord_id\tfilename\tsize_bytes\tsha256"

def sort_key(row):
    fields = row.rstrip("\n").split("\t")
    dataset, shard, record_id, filename = fields[0], fields[1], fields[2], fields[3]
    try:
        shard_num = int(shard)
    except ValueError:
        shard_num = 10**9
    return (dataset, shard_num, record_id, filename)

def main() -> int:
    rows = []
    for shard in range(3):
        path = SHARDS / f"shard_{shard}.tsv"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(line.rstrip("\n"))

    rows.sort(key=sort_key)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_name(".final_manifest.tsv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as out:
        out.write(HEADER + "\n")
        for row in rows:
            out.write(row + "\n")
    tmp.replace(OUT)

    print(f"merged {len(rows)} records")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

    chmod 755 /home/user/research_cluster/bin/scan_shard.py
    chmod 755 /home/user/research_cluster/bin/merge_manifests.py

    chmod 755 /home
    chmod -R a+rwX /home/user
    find /home/user/research_cluster/datasets/raw -type f -exec chmod 644 {} \;
    chmod 755 /home/user/research_cluster/bin/scan_shard.py /home/user/research_cluster/bin/merge_manifests.py
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
