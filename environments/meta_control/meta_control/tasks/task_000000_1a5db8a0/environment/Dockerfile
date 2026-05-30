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

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/policy-docs-lab/policies
    mkdir -p /home/user/policy-docs-lab/docs
    mkdir -p /home/user/policy-docs-lab/tools

    cat > /home/user/policy-docs-lab/policies/container_registry.yaml <<'EOF'
# Example shown in onboarding docs:
# control_id: REG-000
# severity: low
# enforcement: audit
# summary: Example registry rule only.

apiVersion: security.devsecops.local/v1
kind: Policy
metadata:
  name: container-registry-trust
  annotations:
    owner: platform-security
spec:
  control:
    id: REG-104
    severity: high
    enforcement: deny
    summary: Require container images to come from approved registries.
  match:
    resources:
      - Deployment
      - StatefulSet
EOF

    cat > /home/user/policy-docs-lab/policies/iam_mfa.yaml <<'EOF'
apiVersion: security.devsecops.local/v1
kind: Policy
metadata:
  name: iam-mfa-required
  labels:
    control_id: IAM-OLD
    severity: medium
spec:
  examples:
    - control_id: IAM-010
      severity: low
      enforcement: audit
      summary: Demonstration fixture; not an active control.
  control:
    id: IAM-201
    severity: critical
    enforcement: deny
    summary: Require multi-factor authentication for privileged IAM users.
EOF

    cat > /home/user/policy-docs-lab/policies/tls_minimum.yaml <<'EOF'
apiVersion: security.devsecops.local/v1
kind: Policy
metadata:
  name: tls-minimum-version
spec:
  deprecated_control:
    id: TLS-099
    severity: medium
    enforcement: audit
    summary: Legacy TLS check retained for migration notes.
  control:
    id: TLS-122
    severity: high
    enforcement: warn
    summary: Enforce TLS 1.2 or newer for public endpoints.
EOF

    cat > /home/user/policy-docs-lab/tools/markdown_policy_lint.py <<'EOF'
#!/usr/bin/env python3
import pathlib
import re
import sys

if len(sys.argv) != 2:
    print("usage: markdown_policy_lint.py <markdown-file>", file=sys.stderr)
    sys.exit(2)

path = pathlib.Path(sys.argv[1])
text = path.read_text()

errors = []

if not text.endswith("\n"):
    errors.append("file must end with trailing newline")
if text.endswith("\n\n"):
    errors.append("file must end with a single trailing newline")

lines = text.splitlines()

expected_prefix = [
    "# Policy Lint Summary",
    "",
    "This document summarizes the policy-as-code controls currently enforced in this repository.",
    "",
    "## Controls",
    "",
    "| Policy File | Control ID | Severity | Enforcement | Summary |",
    "| --- | --- | --- | --- | --- |",
]
if lines[:8] != expected_prefix:
    errors.append("header, introduction, controls heading, or table header does not match required format")

try:
    verification_idx = lines.index("## Verification")
except ValueError:
    verification_idx = -1
    errors.append("missing verification heading")

if verification_idx != -1:
    table_lines = lines[8:verification_idx]
    if not table_lines:
        errors.append("controls table has no rows")
    if table_lines and table_lines[-1] != "":
        errors.append("blank line required before verification heading")
    rows = table_lines[:-1] if table_lines and table_lines[-1] == "" else table_lines
    seen_files = []
    for row in rows:
        if not re.fullmatch(r"\| [a-z_]+\.yaml \| [A-Z]+-[0-9]{3} \| (low|medium|high|critical) \| (audit|warn|deny) \| [A-Z][^|]+\.", row):
            errors.append(f"malformed table row: {row}")
            continue
        parts = [p.strip() for p in row.strip("|").split("|")]
        seen_files.append(parts[0])
    if seen_files != sorted(seen_files):
        errors.append("policy rows must be sorted alphabetically by filename")
    if len(seen_files) != len(set(seen_files)):
        errors.append("duplicate policy filename in controls table")

expected_suffix = [
    "## Verification",
    "",
    "Generated documentation was checked with the repository Markdown policy linter.",
]
if verification_idx != -1 and lines[verification_idx:] != expected_suffix:
    errors.append("verification section does not match required format")

if errors:
    for err in errors:
        print(f"ERROR: {err}")
    sys.exit(1)

print("PASS")
EOF

    chmod 755 /home/user/policy-docs-lab/tools/markdown_policy_lint.py

    rm -f /home/user/policy-docs-lab/docs/policy-lint-summary.md
    rm -f /home/user/policy-docs-lab/docs/policy-lint-summary.log

    chown -R user:user /home/user/policy-docs-lab
    chmod -R u+rwX,go+rX /home/user/policy-docs-lab
    chmod 775 /home/user/policy-docs-lab
    chmod 775 /home/user/policy-docs-lab/policies
    chmod 775 /home/user/policy-docs-lab/docs
    chmod 775 /home/user/policy-docs-lab/tools

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
