You are helping a technical writer tidy the documentation layout for a small project. Work only under `/home/user/docs_project`.

The project already contains this directory structure:

- `/home/user/docs_project/source/`
- `/home/user/docs_project/public/`
- `/home/user/docs_project/checks/`

The canonical source file is:

- `/home/user/docs_project/source/getting-started.md`

Please organize the published documentation by creating a symbolic link:

- Link path: `/home/user/docs_project/public/start-here.md`
- Link target: `/home/user/docs_project/source/getting-started.md`

The link must be a real symbolic link, not a copied file and not a hard link. Use the absolute target path shown above.

After creating the symbolic link, verify it instead of assuming success from quiet command output. Then create a verification report at:

- `/home/user/docs_project/checks/link-report.txt`

The report must contain exactly three lines in this format:

```text
link_path=/home/user/docs_project/public/start-here.md
is_symlink=yes
target=/home/user/docs_project/source/getting-started.md
```

Do not add extra blank lines or commentary. The automated check will inspect the symlink itself and the exact contents of `/home/user/docs_project/checks/link-report.txt`.

When you are done, stop only after confirming that the report exists and matches the required format.
