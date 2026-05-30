You are helping a data analyst clean up a small CSV export. The current input file is at `/home/user/analyst_workspace/raw/customer_export_legacy.csv`, but that file is now considered a legacy source and must not remain as the final source of truth.

Please create the canonical processed CSV at:

`/home/user/analyst_workspace/processed/customer_contact_canonical.csv`

The canonical CSV must contain exactly 4 comma-separated columns, in this exact order:

1. `customer_id`
2. `email`
3. `signup_date`
4. `region`

The legacy CSV has more columns than needed. Preserve the header row and all data rows, but only keep the four required columns listed above, reordered into the canonical order. Do not add quoting, spaces, extra blank lines, or additional columns.

After creating the canonical file, retire the legacy input by moving it to:

`/home/user/analyst_workspace/archive/customer_export_legacy.csv.retired`

The original path `/home/user/analyst_workspace/raw/customer_export_legacy.csv` should no longer exist when you are done.

Finally, create a verification log at:

`/home/user/analyst_workspace/processed/customer_contact_canonical.verify.log`

The log must contain exactly these three lines, in this order, with the actual values filled in from the final filesystem state:

```text
canonical_path=/home/user/analyst_workspace/processed/customer_contact_canonical.csv
canonical_rows=<number of lines in the canonical CSV, including the header>
legacy_path_retired=<yes-or-no>
```

Use `yes` only if `/home/user/analyst_workspace/raw/customer_export_legacy.csv` is gone and `/home/user/analyst_workspace/archive/customer_export_legacy.csv.retired` exists. Otherwise use `no`.

Before finishing, make sure you verify the canonical CSV and the verification log from the processed directory, not from the retired legacy file.
