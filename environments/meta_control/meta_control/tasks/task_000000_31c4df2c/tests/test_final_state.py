# test_final_state.py
from pathlib import Path
import re
import subprocess


ROOT = Path("/home/user/operator-docs-lab")
SAMPLES = ROOT / "config" / "samples"
DOCS = ROOT / "docs"
MANIFESTS_MD = DOCS / "manifests.md"
VERIFICATION_LOG = DOCS / "verification.log"
LINTER = ROOT / "hack" / "lint_markdown.py"

EXPECTED_MANIFESTS = """# Kubernetes Manifests

## BackupPolicy: nightly-backup

- Source: `config/samples/cache_v1alpha1_backup.yaml`
- API Version: `cache.example.com/v1alpha1`
- Namespace: `demo-cache`

Nightly backup policy for cache data.

## RestoreJob: latest-restore

- Source: `config/samples/cache_v1alpha1_backup.yaml`
- API Version: `cache.example.com/v1alpha1`
- Namespace: `demo-cache`

No description provided.

## Memcached: sample-cache

- Source: `config/samples/cache_v1alpha1_memcached.yaml`
- API Version: `cache.example.com/v1alpha1`
- Namespace: `demo-cache`

Primary Memcached cache managed by the example operator.

## ClusterRole: cache-operator-reader

- Source: `config/samples/rbac_cluster_role.yaml`
- API Version: `rbac.authorization.k8s.io/v1`
- Namespace: `(cluster-scoped)`

Cluster-wide read permissions required by the cache operator.
"""

EXPECTED_VERIFICATION_LOG = """generated=/home/user/operator-docs-lab/docs/manifests.md
lint=pass
manifest_sections=4
verified=pass
"""

EXPECTED_SECTION_HEADINGS = [
    "## BackupPolicy: nightly-backup",
    "## RestoreJob: latest-restore",
    "## Memcached: sample-cache",
    "## ClusterRole: cache-operator-reader",
]

EXPECTED_SOURCES = [
    "- Source: `config/samples/cache_v1alpha1_backup.yaml`",
    "- Source: `config/samples/cache_v1alpha1_backup.yaml`",
    "- Source: `config/samples/cache_v1alpha1_memcached.yaml`",
    "- Source: `config/samples/rbac_cluster_role.yaml`",
]


def read_text(path: Path) -> str:
    assert path.exists(), f"Missing required final artifact: {path}"
    assert path.is_file(), f"Required final artifact is not a regular file: {path}"
    return path.read_text(encoding="utf-8")


def test_final_manifests_markdown_exists_and_matches_exact_expected_contents():
    actual = read_text(MANIFESTS_MD)
    assert actual == EXPECTED_MANIFESTS, (
        f"{MANIFESTS_MD} does not match the exact required final Markdown.\n"
        "It must document all four YAML documents, including the second document "
        "in /home/user/operator-docs-lab/config/samples/cache_v1alpha1_backup.yaml, "
        "with the exact required formatting, ordering, descriptions, and namespace text."
    )


def test_final_manifests_has_required_heading_blank_line_and_final_newline():
    text = read_text(MANIFESTS_MD)
    lines = text.splitlines()

    assert text.endswith("\n"), f"{MANIFESTS_MD} must end with a final newline."
    assert lines, f"{MANIFESTS_MD} must not be empty."
    assert lines[0] == "# Kubernetes Manifests", (
        f"First line of {MANIFESTS_MD} must be exactly '# Kubernetes Manifests'."
    )
    assert len(lines) > 1 and lines[1] == "", (
        f"The title in {MANIFESTS_MD} must be followed by exactly one blank line."
    )


def test_final_manifests_has_no_trailing_whitespace_on_any_line():
    text = read_text(MANIFESTS_MD)
    bad_lines = [
        line_number
        for line_number, line in enumerate(text.splitlines(), start=1)
        if line.rstrip() != line
    ]
    assert not bad_lines, (
        f"{MANIFESTS_MD} contains trailing whitespace on line(s): {bad_lines}. "
        "No line may have trailing spaces or tabs."
    )


def test_final_manifests_documents_exactly_four_sections_in_required_order():
    text = read_text(MANIFESTS_MD)
    headings = [line for line in text.splitlines() if line.startswith("## ")]

    assert headings == EXPECTED_SECTION_HEADINGS, (
        f"{MANIFESTS_MD} must contain exactly these four second-level headings "
        "in filename/document order:\n"
        + "\n".join(EXPECTED_SECTION_HEADINGS)
        + "\nActual headings were:\n"
        + "\n".join(headings)
    )

    assert len(headings) == 4, (
        f"{MANIFESTS_MD} must contain exactly 4 manifest sections, one for each "
        f"YAML document found directly in {SAMPLES}. Found {len(headings)}."
    )


def test_final_manifests_includes_multidocument_restore_job_section():
    text = read_text(MANIFESTS_MD)

    assert "## RestoreJob: latest-restore" in text, (
        f"{MANIFESTS_MD} is missing the RestoreJob section from the second YAML "
        "document in /home/user/operator-docs-lab/config/samples/cache_v1alpha1_backup.yaml."
    )
    assert (
        "## RestoreJob: latest-restore\n\n"
        "- Source: `config/samples/cache_v1alpha1_backup.yaml`\n"
        "- API Version: `cache.example.com/v1alpha1`\n"
        "- Namespace: `demo-cache`\n\n"
        "No description provided."
    ) in text, (
        "The RestoreJob section must use the backup sample source, demo-cache "
        "namespace, and exactly 'No description provided.' because it has no "
        "docs.example.com/description annotation."
    )


def test_final_manifests_uses_cluster_scoped_namespace_for_cluster_role():
    text = read_text(MANIFESTS_MD)
    assert (
        "## ClusterRole: cache-operator-reader\n\n"
        "- Source: `config/samples/rbac_cluster_role.yaml`\n"
        "- API Version: `rbac.authorization.k8s.io/v1`\n"
        "- Namespace: `(cluster-scoped)`\n\n"
        "Cluster-wide read permissions required by the cache operator."
    ) in text, (
        "The ClusterRole section must document the missing metadata.namespace as "
        "exactly `(cluster-scoped)` and preserve its annotation description."
    )


def test_final_manifests_has_exact_source_lines_for_all_documents_in_order():
    text = read_text(MANIFESTS_MD)
    source_lines = [line for line in text.splitlines() if line.startswith("- Source: ")]

    assert source_lines == EXPECTED_SOURCES, (
        f"{MANIFESTS_MD} must have one source line per YAML document, sorted by "
        "source filename and document order. The two documents from "
        "cache_v1alpha1_backup.yaml must both be represented before the other files.\n"
        f"Expected: {EXPECTED_SOURCES}\n"
        f"Actual:   {source_lines}"
    )


def test_final_manifests_contains_no_placeholder_or_extra_sections():
    text = read_text(MANIFESTS_MD)
    headings = re.findall(r"^## .+$", text, flags=re.MULTILINE)

    unexpected_headings = [
        heading for heading in headings if heading not in EXPECTED_SECTION_HEADINGS
    ]
    assert not unexpected_headings, (
        f"{MANIFESTS_MD} contains unexpected extra manifest section heading(s): "
        f"{unexpected_headings}"
    )

    assert "<Kind>" not in text and "<metadata.name>" not in text, (
        f"{MANIFESTS_MD} still contains template placeholder text."
    )
    assert "<description>" not in text, (
        f"{MANIFESTS_MD} still contains a template description placeholder."
    )


def test_repository_markdown_linter_passes_on_final_manifest_page():
    assert LINTER.exists(), f"Missing Markdown lint script: {LINTER}"
    assert LINTER.is_file(), f"Markdown lint path is not a file: {LINTER}"

    result = subprocess.run(
        [str(LINTER), str(MANIFESTS_MD)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        "The repository Markdown lint check must pass for the final artifact.\n"
        f"Command: {LINTER} {MANIFESTS_MD}\n"
        f"Exit code: {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_verification_log_exists_and_matches_exact_required_contents():
    actual = read_text(VERIFICATION_LOG)
    assert actual == EXPECTED_VERIFICATION_LOG, (
        f"{VERIFICATION_LOG} must contain exactly four required lines recording "
        "the generated file, lint pass, manifest_sections=4, and verified=pass."
    )


def test_verification_log_section_count_matches_markdown_heading_count():
    markdown = read_text(MANIFESTS_MD)
    log = read_text(VERIFICATION_LOG)

    heading_count = len([line for line in markdown.splitlines() if line.startswith("## ")])
    expected_line = f"manifest_sections={heading_count}"

    assert "manifest_sections=4" in log, (
        f"{VERIFICATION_LOG} must record manifest_sections=4 after verifying all "
        "YAML documents were documented."
    )
    assert expected_line in log, (
        f"{VERIFICATION_LOG} section count does not match {MANIFESTS_MD}. "
        f"Expected log line: {expected_line}"
    )
    assert "verified=pass" in log.splitlines(), (
        f"{VERIFICATION_LOG} must include exactly 'verified=pass' after final verification."
    )