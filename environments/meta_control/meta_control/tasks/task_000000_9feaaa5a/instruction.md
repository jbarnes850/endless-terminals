You’re helping an edge computing engineer do a quick connectivity diagnostic for an IoT deployment workspace.

There is a small inventory file at `/home/user/edge_diagnostics/device_inventory.txt`. It lists IoT device names and their management endpoints. Some commands you run may produce little or no terminal output, so do not assume the task is complete just because the shell is quiet.

Please create exactly one diagnostic report file at:

`/home/user/edge_diagnostics/reports/connectivity_report.txt`

The report must be plain UTF-8 text and must contain exactly 5 lines, in this exact order and format:

1. `EDGE CONNECTIVITY REPORT`
2. `Inventory: /home/user/edge_diagnostics/device_inventory.txt`
3. `Devices checked: N`
4. `Reachable: R`
5. `Unreachable: U`

Where:
- `N` is the total number of non-comment, non-blank device entries in `/home/user/edge_diagnostics/device_inventory.txt`.
- `R` is the number of those devices whose endpoint is reachable from the container.
- `U` is the number of those devices whose endpoint is not reachable from the container.
- `R + U` must equal `N`.

Inventory file format:
- Blank lines may appear and must be ignored.
- Lines beginning with `#` must be ignored.
- Valid device lines use this format: `device_name endpoint`
- The endpoint may be a hostname, IPv4 address, or loopback address.

Use a network diagnostic appropriate for checking whether each endpoint is reachable from this environment. After writing the report, run a verification step that confirms the file exists and that the three counts are internally consistent. The final answer should only be a brief confirmation that the report was created and verified; do not include command transcripts.
