You are helping maintain Kubernetes manifests for an operator bundle in a Linux container. Work only under `/home/user/operator-work`. The input manifests are in `/home/user/operator-work/manifests/raw/bundle.yaml`, a multi-document YAML file. Do not assume that Kubernetes-specific tools such as `kubectl`, `kustomize`, `helm`, or `yq` are installed; this task is specifically intended to be completed with standard shell text-processing tools, especially `awk` and `sed`.

Create a normalized deployment manifest and a migration report.

Final deliverables:

1. Create `/home/user/operator-work/manifests/normalized/bundle.normalized.yaml`.

   This file must contain every YAML document from `/home/user/operator-work/manifests/raw/bundle.yaml` in the same order, separated by document separators exactly as described below.

   Required normalization rules:

   - The output must begin with `---` on its own line.
   - Every document boundary must be represented by exactly one line containing `---`.
   - The output must end with a newline.
   - Remove all comment-only lines from every document. A comment-only line is any line whose first non-space character is `#`.
   - Remove trailing spaces and trailing tabs from every line.
   - Preserve indentation and all non-comment content otherwise, except for the specific substitutions below.
   - In every `Deployment` document only:
     - Under the container named `manager`, change the image from whatever is currently present to `registry.internal.example.com/platform/sample-operator:2.4.1`.
     - Under the same `manager` container, ensure these environment variables exist exactly once in the `env:` list:
       - `WATCH_NAMESPACE` with value `platform-system`
       - `LOG_LEVEL` with value `debug`
       - `ENABLE_WEBHOOKS` with value `"true"`
     - If any of those variables already exist under the `manager` container, update only their `value:` line.
     - If any are missing, add them under the same `env:` list using the same indentation style as existing env entries.
     - Do not add these variables to sidecar containers or any other document.
   - In every `ServiceAccount` document only:
     - Change the namespace value to `platform-system`.
   - In every `ClusterRoleBinding` document only:
     - Under every subject whose `kind:` is `ServiceAccount`, set its `namespace:` to `platform-system`.
     - Do not change namespaces in unrelated metadata or other documents unless specifically required above.
   - Do not alter document kind names, object names, labels, annotations, probes, resource limits, ports, or non-targeted environment variables.

   Important: a naïve single global substitution for `namespace:` is not acceptable because it will modify fields that must stay unchanged. Also, if an attempted approach produces an unchanged file or keeps changing the wrong namespace fields, stop repeating that approach and switch to a different text-processing strategy that tracks document kind and local context.

2. Create `/home/user/operator-work/reports/migration-report.tsv`.

   The report must be tab-separated text with exactly six lines. There must be no extra blank lines.

   Line 1 must be the header exactly:

   `field	old	new	status`

   Lines 2 through 6 must appear in this exact order and use exactly one tab between columns:

   - `manager_image`
   - `serviceaccount_namespace`
   - `clusterrolebinding_subject_namespace`
   - `watch_namespace`
   - `enable_webhooks`

   For each row:
   - The `old` column must contain the value that was present in the raw bundle before your normalization.
   - The `new` column must contain the value present in the normalized bundle.
   - The `status` column must be `changed` if the old and new values differ, otherwise `unchanged`.

   If a required environment variable was missing in the raw bundle, use `MISSING` as the old value.

3. Create `/home/user/operator-work/reports/verification.log`.

   This file must be plain text and must contain exactly these four lines, in this order:

   - `normalized_file=/home/user/operator-work/manifests/normalized/bundle.normalized.yaml`
   - `report_file=/home/user/operator-work/reports/migration-report.tsv`
   - `comment_lines_remaining=<N>`
   - `targeted_checks=<RESULT>`

   Replace `<N>` with the number of comment-only lines remaining in the normalized YAML file. Replace `<RESULT>` with `pass` only if you have verified that the normalized bundle contains the required image, the required namespace updates, and the required manager env values while preserving unrelated namespace values. Otherwise use `fail`.

Before finishing, verify your output using shell commands. The automated checker will inspect the exact files above, their formatting, and the targeted transformations.
