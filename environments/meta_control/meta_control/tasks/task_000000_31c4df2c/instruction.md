You’re helping maintain a small Kubernetes operator repository in `/home/user/operator-docs-lab`. The repository contains Kubernetes manifest samples under `/home/user/operator-docs-lab/config/samples/` and a documentation helper script at `/home/user/operator-docs-lab/hack/generate_manifest_docs.py`.

Please generate and lint a Markdown documentation page for the operator manifests.

Final deliverable:

Create or update exactly this file:

`/home/user/operator-docs-lab/docs/manifests.md`

The file must be valid Markdown and must document every Kubernetes YAML manifest found directly in:

`/home/user/operator-docs-lab/config/samples/`

The documentation format must be exactly:

1. First line:
   `# Kubernetes Manifests`

2. A blank line.

3. One section per YAML document discovered in the sample manifests, sorted alphabetically by source filename and then by document order within that file.

4. Each section must use this exact format:

   ```markdown
   ## &lt;Kind&gt;: &lt;metadata.name&gt;

   - Source: `config/samples/&lt;filename&gt;`
   - API Version: `&lt;apiVersion&gt;`
   - Namespace: `&lt;metadata.namespace&gt;`

   &lt;description&gt;
   ```

5. If `metadata.namespace` is missing, write exactly:
   ```markdown
   - Namespace: `(cluster-scoped)`
   ```

6. The description paragraph must be selected as follows:
   - If the manifest has annotation `docs.example.com/description`, use that exact annotation value.
   - Otherwise, use exactly:
     `No description provided.`

7. There must be one blank line between sections and no trailing whitespace on any line.

After generating the file, run the repository’s Markdown lint check:

`/home/user/operator-docs-lab/hack/lint_markdown.py /home/user/operator-docs-lab/docs/manifests.md`

Important: do not stop just because a generation or lint command exits successfully. Before finishing, inspect or otherwise verify that `/home/user/operator-docs-lab/docs/manifests.md` actually contains one section for every YAML document in `/home/user/operator-docs-lab/config/samples/`, including multi-document YAML files. If the helper script produces an incomplete page, fix the generation logic or the output file so that the deliverable itself is correct.

When you are done, create this verification log:

`/home/user/operator-docs-lab/docs/verification.log`

The log must contain exactly four lines in this format:

```text
generated=/home/user/operator-docs-lab/docs/manifests.md
lint=pass
manifest_sections=&lt;number of documented sections&gt;
verified=pass
```

Replace `&lt;number of documented sections&gt;` with the actual number of documented manifest sections in `docs/manifests.md`.
