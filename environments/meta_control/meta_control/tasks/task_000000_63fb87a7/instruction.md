You are helping as the on-call SRE for an uptime monitoring issue in a non-root Linux container. The real host firewall cannot be modified here, so this environment uses a user-writable firewall policy workspace under `/home/user/firewall-lab`.

The monitoring probe is defined in `/home/user/firewall-lab/monitor_probe.json`. It represents an external uptime checker that must be allowed through the application firewall. The candidate firewall snippets are stored in `/home/user/firewall-lab/candidates/`. Each candidate is a small nftables-style policy fragment, and only one of them is the correct production-ready rule for the probe.

Your job is to inspect the available evidence, choose the one candidate firewall rule that would allow the uptime monitor without broadly opening access, install it as the active policy, and write a concise verification log.

Final required state:

1. The file `/home/user/firewall-lab/active_policy.nft` must contain exactly the contents of the single best candidate file from `/home/user/firewall-lab/candidates/`.
   - Do not concatenate candidates.
   - Do not invent a new rule.
   - Do not modify the selected candidate content.
   - Preserve the selected candidate’s line endings and final newline.

2. Create `/home/user/firewall-lab/verification.log` with exactly four lines in this format:

   ```text
   probe_source=<IPv4 address from the probe definition>
   probe_port=<TCP port from the probe definition>
   selected_candidate=<candidate filename only>
   status=verified
   ```

   Example format only:
   ```text
   probe_source=192.0.2.10
   probe_port=443
   selected_candidate=example.nft
   status=verified
   ```

3. Your choice should be based on the probe definition and the candidate firewall snippets:
   - The selected rule must allow the probe source IP.
   - The selected rule must allow the probe TCP destination port.
   - The selected rule should not allow unrelated source IPs or an unrelated destination port.
   - If there are candidates that look partially correct, eliminate them using the evidence instead of trying unrelated changes.

4. Before finishing, verify that `/home/user/firewall-lab/active_policy.nft` matches the selected candidate exactly and that `/home/user/firewall-lab/verification.log` follows the required four-line format.

Stop once those two files are correct.
