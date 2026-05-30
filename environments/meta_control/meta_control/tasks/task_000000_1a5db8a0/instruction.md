You are helping a DevSecOps team enforce “policy as code” documentation standards in a local repository. Work only inside `/home/user/policy-docs-lab`.

Create exactly one Markdown documentation file at:

`/home/user/policy-docs-lab/docs/policy-lint-summary.md`

The repository contains policy files under `/home/user/policy-docs-lab/policies/` and a lightweight Markdown style checker at `/home/user/policy-docs-lab/tools/markdown_policy_lint.py`. The checker is intentionally strict, so do not assume that visually acceptable Markdown will pass. Inspect the repository as needed, generate the documentation, run the checker, fix the document if needed, and stop once it passes.

The generated file must use this exact structure:

1. First line must be exactly:
   `# Policy Lint Summary`

2. Then a blank line.

3. Then this exact sentence as its own paragraph:
   `This document summarizes the policy-as-code controls currently enforced in this repository.`

4. Then a blank line.

5. Then a level-2 heading exactly:
   `## Controls`

6. Then a blank line.

7. Then a Markdown table with exactly these columns in this order:
   `Policy File`, `Control ID`, `Severity`, `Enforcement`, `Summary`

8. Each policy file in `/home/user/policy-docs-lab/policies/` must appear once in the table. Use the policy file’s basename, not the full path.

9. Sort the table rows alphabetically by policy filename.

10. Values in the table must be derived from the contents of the policy files. Do not invent controls. If a policy file contains several plausible-looking fields, use the fields that are actually part of the active policy metadata rather than examples, comments, legacy values, or test fixtures.

11. Then a blank line.

12. Then a level-2 heading exactly:
    `## Verification`

13. Then a blank line.

14. Then exactly one sentence:
    `Generated documentation was checked with the repository Markdown policy linter.`

15. The Markdown file must end with a single trailing newline.

Also create a verification log at:

`/home/user/policy-docs-lab/docs/policy-lint-summary.log`

The log file must contain exactly two lines:

- Line 1 must start with `lint_command=` followed by the command you used to run the repository Markdown policy checker against `/home/user/policy-docs-lab/docs/policy-lint-summary.md`.
- Line 2 must start with `lint_result=` followed by either `PASS` or `FAIL`.

Before finishing, the linter must pass, and the log must record `lint_result=PASS`.

This task is meant to reward disciplined convergence: inspect the available policy sources, identify which metadata fields are authoritative, eliminate misleading examples or legacy fragments, generate the Markdown, run the provided checker, and stop after verification succeeds.
