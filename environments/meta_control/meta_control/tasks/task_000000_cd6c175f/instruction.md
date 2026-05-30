I need you to update the hostname-resolution source of truth for a small configuration-manager workspace under `/home/user/cm-dns`.

The workspace currently has an old hostname mapping file at `/home/user/cm-dns/legacy/hosts.static` and a newer DNS override file at `/home/user/cm-dns/current/dns-overrides.zone`. The configuration manager has been changed so that `/home/user/cm-dns/current/dns-overrides.zone` is now the only authoritative location. Please migrate the active hostname mappings into the new file, retire the old file so it cannot be mistaken for the active source, and write a verification log.

Final required state:

1. `/home/user/cm-dns/current/dns-overrides.zone` must exist.
2. It must contain exactly one active hostname-resolution record per line, using this format:
   `HOSTNAME A IPV4_ADDRESS`
3. The migrated records must preserve the hostname-to-IP semantics from the legacy file.
4. Lines in `/home/user/cm-dns/current/dns-overrides.zone` must be sorted lexicographically by hostname.
5. The file must not contain comments, blank lines, aliases, TTL values, or extra whitespace. Each line must have exactly three fields separated by a single space.
6. `/home/user/cm-dns/legacy/hosts.static` must no longer exist as a regular file after the migration. It should be retired in a way that makes it clear it is not authoritative anymore.
7. Create `/home/user/cm-dns/current/resolution-verification.log`.

The verification log is important because automated checks will inspect it. It must contain exactly these five lines, in this exact key/value format, with no extra lines:

`source_of_truth=/home/user/cm-dns/current/dns-overrides.zone`  
`legacy_regular_file=absent`  
`record_count=N`  
`first_record=HOSTNAME A IPV4_ADDRESS`  
`last_record=HOSTNAME A IPV4_ADDRESS`

Replace `N`, `HOSTNAME`, and `IPV4_ADDRESS` with values computed from the final `/home/user/cm-dns/current/dns-overrides.zone`, not from the retired legacy file. The first and last records must reflect the sorted final DNS override file.

Before finishing, verify the final state by reading the new source of truth at `/home/user/cm-dns/current/dns-overrides.zone`, not the legacy path.
