You are helping prepare a firewall deployment artifact for an edge-computing IoT gateway. The container does not grant root privileges, so do not try to actually modify the system firewall. Instead, generate the exact auditable command record that the deployment runner will consume later.

Read the existing policy file at:

`/home/user/iot-edge/device-policy.env`

It contains shell-style key/value lines for one IoT device deployment, including:

- `DEVICE_ID`
- `INTERFACE`
- `ALLOW_CIDR`
- `ALLOW_TCP_PORT`
- `DEFAULT_INPUT_POLICY`
- `RULESET_NAME`

Create exactly one file:

`/home/user/iot-edge/firewall.apply.log`

The file must contain exactly one line and must end with a newline. The line must use this exact pipe-delimited format:

`APPLY|device=<DEVICE_ID>|ruleset=<RULESET_NAME>|action=<ACTION>|iface=<INTERFACE>|src=<ALLOW_CIDR>|proto=tcp|dport=<ALLOW_TCP_PORT>|default_input=<DEFAULT_INPUT_POLICY>|status=ready`

Requirements:

1. Substitute every placeholder using the values from `/home/user/iot-edge/device-policy.env`.
2. The `<ACTION>` value must be exactly `allow`.
3. Preserve the order of fields exactly as shown.
4. Do not add extra spaces, quotes, comments, timestamps, or additional lines.
5. Do not change `/home/user/iot-edge/device-policy.env`.
6. Verify the final file before you finish, because the automated check will require the complete one-line record, not just a partially correct firewall rule.

This is intended to be a simple terminal task: produce the deployment log artifact only.
