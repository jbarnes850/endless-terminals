You’re helping with an IT support ticket about a slow internal asset lookup. The affected ticket workspace is `/home/user/tickets/TK-2048/`.

The SQLite database is located at:

`/home/user/tickets/TK-2048/asset_cache.db`

The support team has already provided a verification helper:

`/home/user/tickets/TK-2048/check_lookup.sh`

Please optimize the database lookup performance for the ticket without changing the helper script or replacing the database. The lookup is for asset records by hostname, so apply the appropriate database-level optimization inside the existing SQLite database.

Important: some successful database changes may produce little or no terminal output. Do not stop just because a command is quiet. After making the optimization, run the provided verification helper and use its result to create the required ticket log.

Create this final log file:

`/home/user/tickets/TK-2048/resolution.log`

The file must contain exactly three lines in this format:

`ticket=TK-2048`  
`status=optimized`  
`verification=&lt;the single-line output from /home/user/tickets/TK-2048/check_lookup.sh&gt;`

Do not add extra blank lines or comments. The verification line must include the exact single-line output produced by the helper after your optimization is in place.

Before finishing, confirm that `/home/user/tickets/TK-2048/resolution.log` exists and contains the required three-line format.
