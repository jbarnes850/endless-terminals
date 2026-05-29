FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        jq \
        ca-certificates

    python3 -m pip install --no-cache-dir pytest jsonschema

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/docs_meta/source

    cat > /home/user/docs_meta/source/schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Documentation Page Metadata",
  "x-metadata": {
    "version": "1.4.2"
  },
  "type": "object",
  "required": ["slug", "title", "section", "status", "word_count"],
  "additionalProperties": false,
  "properties": {
    "slug": {
      "type": "string",
      "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"
    },
    "title": {
      "type": "string",
      "minLength": 5
    },
    "section": {
      "type": "string",
      "enum": ["getting-started", "reference", "tutorials"]
    },
    "status": {
      "type": "string",
      "enum": ["draft", "review", "published"]
    },
    "word_count": {
      "type": "integer",
      "minimum": 100
    }
  }
}
EOF

    cat > /home/user/docs_meta/source/pages.json <<'EOF'
[
  {
    "slug": "installation-guide",
    "title": "Installation Guide",
    "section": "getting-started",
    "status": "published",
    "word_count": 840
  },
  {
    "slug": "quickstart",
    "title": "Quickstart Tutorial",
    "section": "tutorials",
    "status": "review",
    "word_count": 620
  },
  {
    "slug": "api-auth",
    "title": "API Authentication",
    "section": "reference",
    "status": "published",
    "word_count": 510
  },
  {
    "slug": "bad Slug",
    "title": "Bad Slug Example",
    "section": "reference",
    "status": "draft",
    "word_count": 210
  },
  {
    "slug": "tiny-note",
    "title": "Tiny",
    "section": "tutorials",
    "status": "published",
    "word_count": 42
  },
  {
    "slug": "orphan-page",
    "title": "Orphan Page",
    "section": "appendix",
    "status": "draft",
    "word_count": 300
  }
]
EOF

    rm -f /home/user/docs_meta/validation_report.json

    chown -R user:user /home/user/docs_meta
    chmod 755 /home/user
    chmod 777 /home/user/docs_meta /home/user/docs_meta/source
    chmod 666 /home/user/docs_meta/source/schema.json /home/user/docs_meta/source/pages.json

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
