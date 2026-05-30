You’re helping a data analyst finish a small CSV encoding cleanup in `/home/user/encoding_task`.

The source file is `/home/user/encoding_task/raw/customers_latin1.csv`. It is a semicolon-delimited CSV exported from an older system and encoded as ISO-8859-1 / Latin-1. It contains customer names and cities with accented characters. Please convert it to a UTF-8 CSV for downstream tools.

Create the final output file at:

`/home/user/encoding_task/processed/customers_utf8.csv`

Requirements for `/home/user/encoding_task/processed/customers_utf8.csv`:

1. It must be UTF-8 encoded text.
2. It must use commas as delimiters, not semicolons.
3. It must contain exactly one header row followed by exactly six data rows.
4. The header must be exactly:
   `id,name,city,segment`
5. Preserve the original field values exactly except for the delimiter and encoding conversion.
6. The accented characters must display correctly in UTF-8, not as replacement characters, escape sequences, or mojibake.
7. The final file must end with a single newline.

Also create a verification log at:

`/home/user/encoding_task/processed/verification.log`

The verification log must be plain UTF-8 text with exactly these four lines, in this order, using `PASS` or `FAIL` as appropriate:

`utf8_valid: PASS|FAIL`  
`comma_delimited: PASS|FAIL`  
`row_count: PASS|FAIL`  
`accented_text_preserved: PASS|FAIL`

Before you stop, inspect the produced CSV itself and make sure the log reflects the actual file contents. Do not treat a command exiting successfully as sufficient; the deliverable is only complete if the CSV content is valid and the verification log records all four checks as `PASS`.
