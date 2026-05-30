FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        libc-bin
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    mkdir -p /home/user/encoding_task/raw
    mkdir -p /home/user/encoding_task/processed

    python3 - <<'PY'
from pathlib import Path

text = (
    "id;name;city;segment\n"
    "1;André Martin;Montréal;retail\n"
    "2;Björk Gudmundsdóttir;Reykjavík;music\n"
    "3;François Dupont;Québec;enterprise\n"
    "4;Marta Peña;Bogotá;smb\n"
    "5;Jürgen Müller;Zürich;enterprise\n"
    "6;Chloë Dubois;Genève;retail\n"
)

path = Path("/home/user/encoding_task/raw/customers_latin1.csv")
path.write_bytes(text.encode("iso-8859-1"))
PY

    chmod 755 /home/user
    chmod 755 /home/user/encoding_task
    chmod 755 /home/user/encoding_task/raw
    chmod 644 /home/user/encoding_task/raw/customers_latin1.csv
    chmod 777 /home/user/encoding_task/processed

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
