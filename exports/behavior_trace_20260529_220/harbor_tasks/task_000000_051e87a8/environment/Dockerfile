FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    REPO=/home/user/ml-data-repo

    rm -rf "$REPO"
    mkdir -p \
        "$REPO/data/raw/train" \
        "$REPO/data/raw/validation" \
        "$REPO/data/raw/test" \
        "$REPO/data/notes" \
        "$REPO/scripts" \
        "$REPO/tmp"

    cat > "$REPO/README.md" <<'EOF'
# ML Data Repository

This repository contains JSONL training-data shards for a manifest generation task.
EOF

    cat > "$REPO/.gitignore" <<'EOF'
tmp/
*.tmp
.cache.jsonl
EOF

    cat > "$REPO/data/raw/train/shard-000.jsonl" <<'EOF'
{"id":"tr-000-001","text":"warm start sample","label":"keep"}
{"id":"tr-000-002","text":"gradient checkpoint note","label":"keep"}
{"id":"tr-000-003","text":"bad OCR span removed","label":"drop"}
EOF

    cat > "$REPO/data/raw/train/shard-001.jsonl" <<'EOF'
{"id":"tr-001-001","text":"tokenizer regression example","label":"keep"}
{"id":"tr-001-002","text":"long context packing case","label":"keep"}
EOF

    cat > "$REPO/data/raw/validation/shard-000.jsonl" <<'EOF'
{"id":"va-000-001","text":"heldout factuality prompt","label":"keep"}
{"id":"va-000-002","text":"heldout math prompt","label":"keep"}
{"id":"va-000-003","text":"heldout code prompt","label":"keep"}
{"id":"va-000-004","text":"heldout safety prompt","label":"drop"}
EOF

    cat > "$REPO/data/raw/test/shard-000.jsonl" <<'EOF'
{"id":"te-000-001","text":"final benchmark item","label":"keep"}
EOF

    cat > "$REPO/data/raw/test/shard-001.jsonl" <<'EOF'
{"id":"te-001-001","text":"adversarial paraphrase one","label":"keep"}
{"id":"te-001-002","text":"adversarial paraphrase two","label":"keep"}
{"id":"te-001-003","text":"adversarial paraphrase three","label":"drop"}
{"id":"te-001-004","text":"adversarial paraphrase four","label":"keep"}
{"id":"te-001-005","text":"adversarial paraphrase five","label":"keep"}
EOF

    cat > "$REPO/data/notes/schema.md" <<'EOF'
# Data schema

Each JSONL row is a training example with id, text, and label fields.
EOF

    cat > "$REPO/scripts/make_manifest.py" <<'EOF'
#!/usr/bin/env python3
"""
Misleading helper script for the task.

This script intentionally uses filesystem discovery rather than Git tracking
information, labels validation as val, and does not create the verification log.
It exits successfully while producing a semantically incorrect manifest.
"""
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
out = repo / "training_data_manifest.tsv"

rows = []
for path in sorted((repo / "data" / "raw").rglob("*.jsonl")):
    rel = path.relative_to(repo).as_posix()
    split = path.relative_to(repo / "data" / "raw").parts[0]
    if split == "validation":
        split = "val"
    count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    rows.append((rel, count, split))

with out.open("w", encoding="utf-8") as fh:
    fh.write("git_path\trecord_count\tsplit\n")
    for rel, count, split in rows:
        fh.write(f"{rel}\t{count}\t{split}\n")
EOF
    chmod 755 "$REPO/scripts/make_manifest.py"

    chown -R user:user /home/user

    cd "$REPO"
    runuser -u user -- git init -b main
    runuser -u user -- git config --local user.name "Task User"
    runuser -u user -- git config --local user.email "task.user@example.com"
    runuser -u user -- git add \
        README.md \
        .gitignore \
        data/raw/train/shard-000.jsonl \
        data/raw/train/shard-001.jsonl \
        data/raw/validation/shard-000.jsonl \
        data/raw/test/shard-000.jsonl \
        data/raw/test/shard-001.jsonl \
        data/notes/schema.md \
        scripts/make_manifest.py
    runuser -u user -- git commit -m "Initial tracked training data shards"

    cat > "$REPO/data/raw/train/debug-sample.jsonl" <<'EOF'
{"id":"dbg-001","text":"debug one","label":"keep"}
{"id":"dbg-002","text":"debug two","label":"keep"}
{"id":"dbg-003","text":"debug three","label":"keep"}
{"id":"dbg-004","text":"debug four","label":"keep"}
{"id":"dbg-005","text":"debug five","label":"keep"}
{"id":"dbg-006","text":"debug six","label":"keep"}
EOF

    cat > "$REPO/data/raw/validation/local-copy.jsonl" <<'EOF'
{"id":"local-001","text":"local validation copy one","label":"keep"}
{"id":"local-002","text":"local validation copy two","label":"keep"}
EOF

    cat > "$REPO/tmp/generated_manifest.tsv" <<'EOF'
git_path	record_count	split
data/raw/train/debug-sample.jsonl	6	train
EOF

    cat > "$REPO/data/raw/train/.cache.jsonl" <<'EOF'
{"id":"cache-001","text":"cache one","label":"keep"}
{"id":"cache-002","text":"cache two","label":"keep"}
{"id":"cache-003","text":"cache three","label":"keep"}
{"id":"cache-004","text":"cache four","label":"keep"}
{"id":"cache-005","text":"cache five","label":"keep"}
{"id":"cache-006","text":"cache six","label":"keep"}
{"id":"cache-007","text":"cache seven","label":"keep"}
{"id":"cache-008","text":"cache eight","label":"keep"}
{"id":"cache-009","text":"cache nine","label":"keep"}
EOF

    cat > "$REPO/data/raw/test/shard-999.tmp" <<'EOF'
temporary ignored shard placeholder
EOF

    chown -R user:user /home/user
    chmod -R u+rwX,go+rX /home/user
    chmod 755 /home/user
    chmod 755 "$REPO"

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
