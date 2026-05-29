You are helping an observability engineer finish a small dashboard environment-configuration cleanup in a Linux container.

The working directory is `/home/user/observability-dashboard`. The repository contains a lightweight dashboard configuration with several plausible environment files and dashboard JSON snippets. The dashboard loader reads only one environment file: `/home/user/observability-dashboard/.env.local`.

Your job is to determine the correct value for the dashboard datasource environment variable and write the final environment configuration. There are several misleading candidate values in the repository, so do not guess from a filename alone. Use the evidence in the repository to narrow the choice until only one value is consistent with the dashboard configuration.

Final state required:

1. Create or replace `/home/user/observability-dashboard/.env.local`.
2. The file `/home/user/observability-dashboard/.env.local` must contain exactly two lines, in this exact order:
   - first line: `DASHBOARD_DATASOURCE_UID=` followed immediately by the single correct datasource UID you determined from the repository
   - second line: `DASHBOARD_ENV=production`
3. Create or replace `/home/user/observability-dashboard/config-selection.log`.
4. The log file must be plain UTF-8 text and must contain exactly five lines in this exact key/value format:
   - `hypotheses_checked=<integer>`
   - `rejected=<comma-separated list>`
   - `selected=<selected datasource UID>`
   - `evidence=<relative path inside /home/user/observability-dashboard that proves the selected UID is the one used by the production dashboard>`
   - `verified=true`

Additional formatting rules for `/home/user/observability-dashboard/config-selection.log`:
- `hypotheses_checked` must be the number of unique datasource UID candidates you explicitly considered from the repository.
- `rejected` must list only rejected datasource UID candidates, separated by commas with no spaces. If there is more than one rejected candidate, list them in lexicographic order.
- `selected` must exactly match the UID used in `.env.local`.
- `evidence` must be a relative path, not an absolute path.
- Do not include comments, blank lines, extra whitespace, or additional lines in either output file.

Before finishing, verify that `/home/user/observability-dashboard/.env.local` and `/home/user/observability-dashboard/config-selection.log` match the requested formats exactly.
