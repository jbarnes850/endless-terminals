# test_final_state.py
from pathlib import Path
import re

import pytest


WORKDIR = Path("/home/user/operator-work")
RAW_BUNDLE = Path("/home/user/operator-work/manifests/raw/bundle.yaml")
NORMALIZED_BUNDLE = Path("/home/user/operator-work/manifests/normalized/bundle.normalized.yaml")
MIGRATION_REPORT = Path("/home/user/operator-work/reports/migration-report.tsv")
VERIFICATION_LOG = Path("/home/user/operator-work/reports/verification.log")

EXPECTED_NORMALIZED_CONTENT = """---
apiVersion: v1
kind: Namespace
metadata:
  name: operators
  labels:
    owner: platform
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sample-operator-controller-manager
  namespace: platform-system
  labels:
    app.kubernetes.io/name: sample-operator
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-operator-controller-manager
  namespace: operators
  annotations:
    platform.example.com/namespace-scope: "operators"
spec:
  replicas: 1
  selector:
    matchLabels:
      control-plane: controller-manager
  template:
    metadata:
      labels:
        control-plane: controller-manager
        namespace: keep-this-label
    spec:
      serviceAccountName: sample-operator-controller-manager
      containers:
        - name: kube-rbac-proxy
          image: quay.io/brancz/kube-rbac-proxy:v0.13.1
          env:
            - name: WATCH_NAMESPACE
              value: proxy-system
          ports:
            - containerPort: 8443
              name: https
        - name: manager
          image: registry.internal.example.com/platform/sample-operator:2.4.1
          imagePullPolicy: IfNotPresent
          env:
            - name: WATCH_NAMESPACE
              value: platform-system
            - name: LOG_LEVEL
              value: debug
            - name: FEATURE_GATES
              value: StableOnly
            - name: ENABLE_WEBHOOKS
              value: "true"
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sample-operator-manager-rolebinding
  labels:
    namespace: do-not-change-this-label
subjects:
  - kind: ServiceAccount
    name: sample-operator-controller-manager
    namespace: platform-system
  - kind: User
    name: ci-bot@example.com
    namespace: external-directory
roleRef:
  kind: ClusterRole
  name: sample-operator-manager-role
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: v1
kind: Service
metadata:
  name: sample-operator-metrics
  namespace: operators
spec:
  selector:
    control-plane: controller-manager
  ports:
    - name: https
      port: 8443
      targetPort: https
"""

EXPECTED_REPORT_CONTENT = """field\told\tnew\tstatus
manager_image\tquay.io/example/sample-operator:1.8.0\tregistry.internal.example.com/platform/sample-operator:2.4.1\tchanged
serviceaccount_namespace\toperators\tplatform-system\tchanged
clusterrolebinding_subject_namespace\toperators\tplatform-system\tchanged
watch_namespace\toperators\tplatform-system\tchanged
enable_webhooks\tMISSING\t"true"\tchanged
"""

EXPECTED_VERIFICATION_LOG_CONTENT = """normalized_file=/home/user/operator-work/manifests/normalized/bundle.normalized.yaml
report_file=/home/user/operator-work/reports/migration-report.tsv
comment_lines_remaining=0
targeted_checks=pass
"""


def read_text(path: Path) -> str:
    assert path.exists(), f"Required deliverable is missing: {path}"
    assert path.is_file(), f"Required deliverable path is not a regular file: {path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "path",
    [
        NORMALIZED_BUNDLE,
        MIGRATION_REPORT,
        VERIFICATION_LOG,
    ],
)
def test_required_deliverable_files_exist(path: Path):
    assert path.exists(), f"Required deliverable file was not created: {path}"
    assert path.is_file(), f"Required deliverable path is not a regular file: {path}"


def test_normalized_bundle_matches_expected_file_byte_for_byte():
    actual = read_text(NORMALIZED_BUNDLE)
    assert actual == EXPECTED_NORMALIZED_CONTENT, (
        f"{NORMALIZED_BUNDLE} does not exactly match the expected normalized YAML. "
        "Check document separators, removed comments, indentation, trailing whitespace, "
        "targeted image/env/namespace edits, preserved unrelated namespaces, and final newline."
    )


def test_migration_report_matches_expected_file_byte_for_byte():
    actual = read_text(MIGRATION_REPORT)
    assert actual == EXPECTED_REPORT_CONTENT, (
        f"{MIGRATION_REPORT} does not exactly match the expected TSV report. "
        "It must contain six lines, literal tab separators, correct old/new values from raw and "
        "normalized bundles, and a final newline."
    )


def test_verification_log_matches_expected_file_byte_for_byte():
    actual = read_text(VERIFICATION_LOG)
    assert actual == EXPECTED_VERIFICATION_LOG_CONTENT, (
        f"{VERIFICATION_LOG} does not exactly match the expected verification log. "
        "It must report zero remaining comment-only lines and targeted_checks=pass."
    )


def test_normalized_bundle_formatting_invariants_are_satisfied():
    actual = read_text(NORMALIZED_BUNDLE)

    assert actual.startswith("---\n"), (
        f"{NORMALIZED_BUNDLE} must begin with a YAML document separator line containing exactly '---'."
    )
    assert actual.endswith("\n"), f"{NORMALIZED_BUNDLE} must end with a newline."

    lines = actual.splitlines()
    separator_line_numbers = [i + 1 for i, line in enumerate(lines) if line == "---"]
    assert separator_line_numbers == [1, 8, 16, 56, 73], (
        f"{NORMALIZED_BUNDLE} has incorrect YAML document separators. "
        f"Expected separator lines [1, 8, 16, 56, 73], found {separator_line_numbers}."
    )

    malformed_separators = [
        (i + 1, line) for i, line in enumerate(lines) if line.strip() == "---" and line != "---"
    ]
    assert not malformed_separators, (
        f"{NORMALIZED_BUNDLE} contains document separator lines with surrounding whitespace: "
        f"{malformed_separators!r}"
    )

    comment_only_lines = [
        i + 1 for i, line in enumerate(lines) if line.lstrip(" \t").startswith("#")
    ]
    assert not comment_only_lines, (
        f"{NORMALIZED_BUNDLE} still contains comment-only lines at line(s): {comment_only_lines}."
    )

    trailing_whitespace_lines = [
        i + 1 for i, line in enumerate(actual.splitlines()) if line.endswith((" ", "\t"))
    ]
    assert not trailing_whitespace_lines, (
        f"{NORMALIZED_BUNDLE} contains trailing spaces or tabs at line(s): "
        f"{trailing_whitespace_lines}."
    )


def test_targeted_transformations_and_preserved_unrelated_values_are_present():
    actual = read_text(NORMALIZED_BUNDLE)

    required_snippets = [
        "kind: ServiceAccount\nmetadata:\n  name: sample-operator-controller-manager\n  namespace: platform-system\n",
        "        - name: manager\n"
        "          image: registry.internal.example.com/platform/sample-operator:2.4.1\n"
        "          imagePullPolicy: IfNotPresent\n"
        "          env:\n"
        "            - name: WATCH_NAMESPACE\n"
        "              value: platform-system\n"
        "            - name: LOG_LEVEL\n"
        "              value: debug\n"
        "            - name: FEATURE_GATES\n"
        "              value: StableOnly\n"
        "            - name: ENABLE_WEBHOOKS\n"
        "              value: \"true\"\n"
        "          resources:\n",
        "  - kind: ServiceAccount\n    name: sample-operator-controller-manager\n    namespace: platform-system\n",
    ]
    for snippet in required_snippets:
        assert snippet in actual, (
            f"{NORMALIZED_BUNDLE} is missing required normalized content:\n{snippet}"
        )

    preserved_snippets = [
        "kind: Deployment\nmetadata:\n  name: sample-operator-controller-manager\n  namespace: operators\n",
        '    platform.example.com/namespace-scope: "operators"\n',
        "        namespace: keep-this-label\n",
        "        - name: kube-rbac-proxy\n"
        "          image: quay.io/brancz/kube-rbac-proxy:v0.13.1\n"
        "          env:\n"
        "            - name: WATCH_NAMESPACE\n"
        "              value: proxy-system\n",
        "  labels:\n    namespace: do-not-change-this-label\n",
        "  - kind: User\n    name: ci-bot@example.com\n    namespace: external-directory\n",
        "kind: Service\nmetadata:\n  name: sample-operator-metrics\n  namespace: operators\n",
    ]
    for snippet in preserved_snippets:
        assert snippet in actual, (
            f"{NORMALIZED_BUNDLE} failed to preserve unrelated content; missing snippet:\n{snippet}"
        )

    assert actual.count("registry.internal.example.com/platform/sample-operator:2.4.1") == 1, (
        "The normalized manager image must appear exactly once."
    )
    assert "quay.io/example/sample-operator:1.8.0" not in actual, (
        "The old manager image is still present in the normalized bundle."
    )


def test_manager_environment_variables_exist_exactly_once_and_sidecar_is_unchanged():
    actual = read_text(NORMALIZED_BUNDLE)

    manager_block_match = re.search(
        r"        - name: manager\n(?P<block>.*?)(?=\n---|\n        - name:|\Z)",
        actual,
        flags=re.DOTALL,
    )
    assert manager_block_match, "Could not locate the manager container block in the normalized bundle."
    manager_block = manager_block_match.group("block")

    expected_env_entries = {
        "WATCH_NAMESPACE": "platform-system",
        "LOG_LEVEL": "debug",
        "FEATURE_GATES": "StableOnly",
        "ENABLE_WEBHOOKS": '"true"',
    }
    for name, value in expected_env_entries.items():
        entry = f"            - name: {name}\n              value: {value}\n"
        assert manager_block.count(entry) == 1, (
            f"Manager env var {name} must appear exactly once with value {value}; "
            f"found {manager_block.count(entry)} matching entries."
        )

    assert manager_block.find("- name: ENABLE_WEBHOOKS") > manager_block.find("- name: FEATURE_GATES"), (
        "ENABLE_WEBHOOKS must be inserted after the existing FEATURE_GATES entry in the manager env list."
    )
    assert manager_block.find("- name: ENABLE_WEBHOOKS") < manager_block.find("          resources:"), (
        "ENABLE_WEBHOOKS must be inserted before the manager resources section."
    )

    sidecar_block_match = re.search(
        r"        - name: kube-rbac-proxy\n(?P<block>.*?)(?=\n        - name: manager\n)",
        actual,
        flags=re.DOTALL,
    )
    assert sidecar_block_match, "Could not locate the kube-rbac-proxy sidecar container block."
    sidecar_block = sidecar_block_match.group("block")

    assert "            - name: WATCH_NAMESPACE\n              value: proxy-system\n" in sidecar_block, (
        "The sidecar WATCH_NAMESPACE value must remain proxy-system."
    )
    assert "LOG_LEVEL" not in sidecar_block and "ENABLE_WEBHOOKS" not in sidecar_block, (
        "Manager-only env vars were incorrectly added to the sidecar container."
    )


def test_migration_report_has_exact_tsv_structure_no_extra_blank_lines():
    actual = read_text(MIGRATION_REPORT)

    lines = actual.splitlines()
    assert len(lines) == 6, (
        f"{MIGRATION_REPORT} must contain exactly six lines including the header; found {len(lines)}."
    )
    assert all(line for line in lines), f"{MIGRATION_REPORT} must not contain blank lines."

    expected_fields = [
        "field",
        "manager_image",
        "serviceaccount_namespace",
        "clusterrolebinding_subject_namespace",
        "watch_namespace",
        "enable_webhooks",
    ]
    for index, line in enumerate(lines):
        columns = line.split("\t")
        assert len(columns) == 4, (
            f"Line {index + 1} of {MIGRATION_REPORT} must contain exactly four tab-separated "
            f"columns; found {len(columns)} columns in {line!r}."
        )
        assert columns[0] == expected_fields[index], (
            f"Line {index + 1} of {MIGRATION_REPORT} has the wrong field name. "
            f"Expected {expected_fields[index]!r}, found {columns[0]!r}."
        )
        assert "  " not in line, (
            f"Line {index + 1} of {MIGRATION_REPORT} appears to contain alignment spaces; "
            "the report must use exactly one tab between columns."
        )


def test_verification_log_values_are_consistent_with_normalized_bundle():
    normalized = read_text(NORMALIZED_BUNDLE)
    verification = read_text(VERIFICATION_LOG)

    comment_lines_remaining = sum(
        1 for line in normalized.splitlines() if line.lstrip(" \t").startswith("#")
    )
    assert f"comment_lines_remaining={comment_lines_remaining}\n" in verification, (
        f"{VERIFICATION_LOG} does not accurately report the number of comment-only lines "
        f"remaining in {NORMALIZED_BUNDLE}."
    )
    assert "comment_lines_remaining=0\n" in verification, (
        f"{VERIFICATION_LOG} must report comment_lines_remaining=0."
    )
    assert "targeted_checks=pass\n" in verification, (
        f"{VERIFICATION_LOG} must report targeted_checks=pass after verifying required edits "
        "and preserved unrelated namespace values."
    )


def test_raw_input_bundle_still_exists_and_contains_initial_values_needed_for_report():
    assert RAW_BUNDLE.exists(), f"Raw input bundle is missing: {RAW_BUNDLE}"
    assert RAW_BUNDLE.is_file(), f"Raw input path is not a regular file: {RAW_BUNDLE}"

    raw = RAW_BUNDLE.read_text(encoding="utf-8")
    required_raw_values = [
        "          image: quay.io/example/sample-operator:1.8.0\n",
        "  namespace: operators\n",
        "    namespace: operators\n",
        "              value: operators\n",
        "              value: info\n",
        "            - name: FEATURE_GATES\n              value: StableOnly\n",
    ]
    for snippet in required_raw_values:
        assert snippet in raw, (
            f"The raw input bundle no longer contains an expected original value needed to derive "
            f"the migration report: {snippet!r}"
        )
    assert "ENABLE_WEBHOOKS" not in raw, (
        "The raw input bundle should not be modified to contain ENABLE_WEBHOOKS; "
        "the report old value for enable_webhooks must derive from it being missing."
    )