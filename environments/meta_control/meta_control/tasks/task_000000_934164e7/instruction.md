You are helping the monitoring team finish a small distributed-system alert setup in a Linux container. The service is a three-node toy “orders” cluster, and its local diagnostic artifacts are already present under `/home/user/cluster_observability/`.

Please determine which single node should receive a new alert by inspecting the existing evidence in these files:

- `/home/user/cluster_observability/topology.txt`
- `/home/user/cluster_observability/node-a/health.txt`
- `/home/user/cluster_observability/node-b/health.txt`
- `/home/user/cluster_observability/node-c/health.txt`
- `/home/user/cluster_observability/node-a/metrics.prom`
- `/home/user/cluster_observability/node-b/metrics.prom`
- `/home/user/cluster_observability/node-c/metrics.prom`
- `/home/user/cluster_observability/recent-events.log`

The monitoring team only wants an alert when the evidence converges on the node that is causing replicated request instability, not merely a node that has one suspicious metric. Use the files to rule out plausible false leads before deciding.

Create exactly one new file:

`/home/user/cluster_observability/alert_decision.log`

The file must contain exactly 6 non-empty lines, in this exact format:

1. `CHECKPOINT topology=<short finding>`
2. `CHECKPOINT health=<short finding>`
3. `CHECKPOINT metrics=<short finding>`
4. `CHECKPOINT events=<short finding>`
5. `ALERT node=<node-name> reason=<short reason>`
6. `STOP verified=<yes-or-no>`

Formatting requirements for automated checking:

- `<node-name>` must be one of `node-a`, `node-b`, or `node-c`.
- The final `STOP` line must use `verified=yes` only if you have inspected enough evidence to justify the alert choice.
- Each `<short finding>` and `<short reason>` must be lowercase words joined by hyphens only, with no spaces. Examples of valid style are `leader-is-node-x`, `latency-normal`, or `events-match-node-y`.
- Do not include extra blank lines, timestamps, markdown, commentary, or additional files.
- The alert decision must identify the one node that is actually causing the cluster instability according to the combined topology, health, metrics, and recent event evidence.

After creating `/home/user/cluster_observability/alert_decision.log`, verify that the file exists and has the required six-line format, then stop.
