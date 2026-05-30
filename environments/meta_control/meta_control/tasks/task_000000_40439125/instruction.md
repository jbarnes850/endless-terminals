You are helping manage certificates for a small set of local microservice endpoints in a container workspace. All files you need are under `/home/user/cert-audit`.

There are three PEM certificate files in `/home/user/cert-audit/certs`:

- `/home/user/cert-audit/certs/orders.pem`
- `/home/user/cert-audit/certs/payments.pem`
- `/home/user/cert-audit/certs/inventory.pem`

There is also a hostname mapping file at `/home/user/cert-audit/services.tsv`. It is tab-separated with a header row and these columns:

- `service`
- `expected_dns`

Your job is to determine which service certificate should be rotated next. A certificate must be selected for rotation if it fails hostname validation against its `expected_dns` value. If more than one certificate fails hostname validation, choose the one expiring soonest. If none fail hostname validation, choose the certificate expiring soonest overall.

Use the certificate data in the PEM files and the hostnames in `/home/user/cert-audit/services.tsv`. Do not assume the filename alone proves the certificate is valid for that service; inspect the certificate Subject Alternative Name DNS entries and expiration dates.

Create exactly one report file at:

`/home/user/cert-audit/rotation_decision.txt`

The automated test will check the file format exactly. The file must contain exactly these five lines, in this order:

1. `selected_service=<service name>`
2. `selected_certificate=/home/user/cert-audit/certs/<service name>.pem`
3. `reason=<one short reason>`
4. `checked_services=<comma-separated service names in alphabetical order>`
5. `verification=complete`

Formatting requirements:

- Do not include extra blank lines.
- Do not include quotes around values.
- The `<service name>` must be one of `inventory`, `orders`, or `payments`.
- The `reason` value must be short and human-readable. It must mention whether the selected certificate was chosen because of a hostname mismatch or because it expires soonest.
- The `checked_services` line must list all three services alphabetically as `inventory,orders,payments`.

Before finishing, verify your report file exists and that its contents match the required five-line format.
