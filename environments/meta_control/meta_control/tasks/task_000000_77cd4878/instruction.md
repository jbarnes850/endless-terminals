You are helping a backup operator validate a restored firewall policy in a non-root training container. The restore has left an old firewall rule file in place, but the service now reads its active policy from a newer directory. Your job is to move the restored allow rule into the active firewall policy location, retire the stale restored file, and write a verification log that proves you checked the new source of truth rather than the old one.

The writable working area is under `/home/user/backup-restore-firewall`.

Initial files you should expect:
- `/home/user/backup-restore-firewall/restored/iptables-restore.rules`
  - This is the stale restored firewall format. It contains the backup operator’s intended allow rule for the backup restore listener.
  - Do not leave this file as the source of truth when you are done.
- `/home/user/backup-restore-firewall/active/firewall.policy`
  - This is the currently active firewall policy file that the simulated service reads.
  - Update this file so that it includes the restored allow rule in the same simple line-oriented format already used by this file.
- `/home/user/backup-restore-firewall/bin/check-firewall`
  - This executable simulates the firewall service verifier.
  - It reads only `/home/user/backup-restore-firewall/active/firewall.policy`.
  - It does not read the restored file.
  - Use it to verify the final active policy.

The goal is to allow the backup restore listener while preserving the existing active policy semantics. The restored rule is in the stale restored file; migrate the equivalent allow entry into the active policy file. Then retire the stale restored file by renaming or moving it so that the original path `/home/user/backup-restore-firewall/restored/iptables-restore.rules` no longer exists.

Create a verification log at exactly:

`/home/user/backup-restore-firewall/verify/firewall-restore-check.log`

The automated checker will read this log, so use exactly this four-line format:

1. `active_policy=/home/user/backup-restore-firewall/active/firewall.policy`
2. `stale_policy_retired=yes`
3. `backup_restore_listener=allowed`
4. `service_check=PASS`

Do not put extra lines before, after, or between these four lines.

Before finishing, make sure the active policy file, not the stale restored file, is the place where the allow rule exists. Also make sure the checker executable reports success based on the active policy. Stop once the active policy is updated, the stale restored path is retired, and the verification log has exactly the required contents.
