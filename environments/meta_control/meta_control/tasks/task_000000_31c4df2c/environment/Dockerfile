FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-yaml \
        python3-pytest \
        ca-certificates
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/operator-docs-lab/config/samples
    mkdir -p /home/user/operator-docs-lab/docs
    mkdir -p /home/user/operator-docs-lab/hack

    cat > /home/user/operator-docs-lab/config/samples/cache_v1alpha1_memcached.yaml <<'EOF'
apiVersion: cache.example.com/v1alpha1
kind: Memcached
metadata:
  name: sample-cache
  namespace: demo-cache
  annotations:
    docs.example.com/description: "Primary Memcached cache managed by the example operator."
spec:
  size: 3
  image: memcached:1.6
EOF

    cat > /home/user/operator-docs-lab/config/samples/cache_v1alpha1_backup.yaml <<'EOF'
apiVersion: cache.example.com/v1alpha1
kind: BackupPolicy
metadata:
  name: nightly-backup
  namespace: demo-cache
  annotations:
    docs.example.com/description: "Nightly backup policy for cache data."
spec:
  schedule: "0 2 * * *"
---
apiVersion: cache.example.com/v1alpha1
kind: RestoreJob
metadata:
  name: latest-restore
  namespace: demo-cache
spec:
  backupName: nightly-backup
EOF

    cat > /home/user/operator-docs-lab/config/samples/rbac_cluster_role.yaml <<'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cache-operator-reader
  annotations:
    docs.example.com/description: "Cluster-wide read permissions required by the cache operator."
rules:
  - apiGroups:
      - cache.example.com
    resources:
      - memcacheds
      - backuppolicies
    verbs:
      - get
      - list
      - watch
EOF

    cat > /home/user/operator-docs-lab/hack/generate_manifest_docs.py <<'EOF'
#!/usr/bin/env python3
from pathlib import Path
import yaml

ROOT = Path("/home/user/operator-docs-lab")
SAMPLES = ROOT / "config" / "samples"
OUT = ROOT / "docs" / "manifests.md"

def first_yaml_document(path):
    with path.open("r", encoding="utf-8") as fh:
        docs = list(yaml.safe_load_all(fh))
    return docs[0] if docs else None

def main():
    lines = ["# Kubernetes Manifests", ""]
    for path in sorted(SAMPLES.glob("*.yaml")):
        doc = first_yaml_document(path)
        if not doc:
            continue
        api_version = doc.get("apiVersion", "")
        kind = doc.get("kind", "")
        metadata = doc.get("metadata") or {}
        name = metadata.get("name", "")
        namespace = metadata.get("namespace", "(cluster-scoped)")
        annotations = metadata.get("annotations") or {}
        description = annotations.get("docs.example.com/description", "No description provided.")

        lines.extend([
            f"## {kind}: {name}",
            "",
            f"- Source: `config/samples/{path.name}`",
            f"- API Version: `{api_version}`",
            f"- Namespace: `{namespace}`",
            "",
            description,
            "",
        ])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
EOF

    cat > /home/user/operator-docs-lab/hack/lint_markdown.py <<'EOF'
#!/usr/bin/env python3
import re
import sys
from pathlib import Path

def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)

def main():
    if len(sys.argv) != 2:
        fail("usage: lint_markdown.py <file>")
    path = Path(sys.argv[1])
    if not path.exists():
        fail(f"missing file: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        fail("file must end with newline")
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if line.rstrip() != line:
            fail(f"trailing whitespace on line {i}")
    if not lines or lines[0] != "# Kubernetes Manifests":
        fail("first line must be '# Kubernetes Manifests'")
    if len(lines) < 2 or lines[1] != "":
        fail("heading must be followed by a blank line")
    for i, line in enumerate(lines, 1):
        if line.startswith("## ") and not re.match(r"^## [A-Za-z0-9]+: [a-z0-9-]+$", line):
            fail(f"bad section heading on line {i}: {line}")
    print("markdown lint passed")

if __name__ == "__main__":
    main()
EOF

    chmod 755 /home/user/operator-docs-lab/hack/generate_manifest_docs.py
    chmod 755 /home/user/operator-docs-lab/hack/lint_markdown.py

    chown -R user:user /home/user/operator-docs-lab
    chmod -R u+rwX,go+rX /home/user/operator-docs-lab
    chmod 755 /home/user

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
