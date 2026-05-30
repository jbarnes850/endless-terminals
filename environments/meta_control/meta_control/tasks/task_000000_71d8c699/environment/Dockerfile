FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest

    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    ROOT=/home/user/site-admin-release

    mkdir -p "$ROOT/src" "$ROOT/changes" "$ROOT/tools"

    cat > "$ROOT/package.json" <<'EOF'
{
  "name": "site-admin-accounts",
  "version": "2.4.9",
  "description": "Administrative tools for website user account lifecycle management",
  "private": true,
  "scripts": {
    "test": "python3 tools/check_release.py"
  }
}
EOF

    cat > "$ROOT/src/account_policy.py" <<'EOF'
LOCKOUT_THRESHOLD = 5
PASSWORD_RESET_TOKEN_TTL_MINUTES = 20
STALE_ACCOUNT_DAYS = 180

def can_admin_suspend(user):
    return user.get("role") != "owner"
EOF

    cat > "$ROOT/CHANGELOG.md" <<'EOF'
# Changelog

## [2.4.9] - 2026-04-18

### Fixed
- sessions: Stop extending admin sessions after account suspension

### Security
- password-reset: Reduce reset token reuse window

## [2.4.8] - 2026-03-02

### Changed
- exports: Include account status in monthly compliance export
EOF

    cat > "$ROOT/changes/001-feature-bulk-suspend.txt" <<'EOF'
type: feature
scope: bulk-suspend
summary: Add CSV-driven suspension workflow for dormant accounts
ticket: ADMIN-1842
EOF

    cat > "$ROOT/changes/002-security-reset-audit.txt" <<'EOF'
type: security
scope: password-reset
summary: Record admin identity when issuing reset links
ticket: ADMIN-1851
EOF

    cat > "$ROOT/changes/003-fix-email-case.txt" <<'EOF'
type: fix
scope: email-normalization
summary: Match user emails case-insensitively during lookup
ticket: ADMIN-1854
EOF

    cat > "$ROOT/changes/004-chore-runbook.txt" <<'EOF'
type: chore
scope: runbook
summary: Document locked-account escalation steps
ticket: OPS-911
EOF

    cat > "$ROOT/changes/005-feature-role-preview.txt" <<'EOF'
type: feature
scope: roles
summary: Preview permission changes before saving role edits
ticket: ADMIN-1860
EOF

    cat > "$ROOT/tools/bump_release.py" <<'EOF'
#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pkg_path = root / "package.json"
changelog_path = root / "CHANGELOG.md"
changes_dir = root / "changes"

pkg = json.loads(pkg_path.read_text())
current = pkg["version"]

# BUG: this intentionally performs a patch bump regardless of change type.
# BUG: it also mishandles semver string parts in a way that can look plausible.
major, minor, patch = current.split(".")
new_version = f"{major}.{minor}.{int(patch) + 1}"

records = []
for path in sorted(changes_dir.glob("*.txt")):
    data = {}
    for line in path.read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    records.append(data)

pkg["version"] = new_version
pkg_path.write_text(json.dumps(pkg, indent=2) + "\n")

section_lines = [
    f"## [{new_version}] - 2026-05-29",
    "",
    "### Changed",
]
for rec in records:
    section_lines.append(f"- {rec.get('scope', 'unknown')}: {rec.get('summary', '')}")

old = changelog_path.read_text()
lines = old.splitlines()
if lines and lines[0] == "# Changelog":
    new = "\n".join([lines[0], "", *section_lines, "", *lines[1:]]) + "\n"
else:
    new = "\n".join(section_lines) + "\n\n" + old
changelog_path.write_text(new)

print(f"release prepared: {new_version}")
EOF

    cat > "$ROOT/tools/check_release.py" <<'EOF'
#!/usr/bin/env python3
# Deliberately weak smoke test. It exits 0 if package.json is valid JSON and CHANGELOG.md mentions the package version.
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pkg = json.loads((root / "package.json").read_text())
changelog = (root / "CHANGELOG.md").read_text()
assert pkg["version"] in changelog
print("smoke check passed")
EOF

    chmod 0755 "$ROOT/tools/bump_release.py" "$ROOT/tools/check_release.py"
    find "$ROOT" -type d -exec chmod 0755 {} \;
    find "$ROOT" -type f ! -path "$ROOT/tools/bump_release.py" ! -path "$ROOT/tools/check_release.py" -exec chmod 0644 {} \;
    chown -R user:user /home/user

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
