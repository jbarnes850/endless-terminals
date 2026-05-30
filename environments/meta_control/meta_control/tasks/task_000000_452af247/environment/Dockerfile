FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        bash \
        grep \
        gawk \
        coreutils

    pip3 install --no-cache-dir pytest

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/projects/shopsite/logs
    mkdir -p /home/user/projects/shopsite/scripts
    mkdir -p /home/user/projects/shopsite/reports

    cat > /home/user/projects/shopsite/logs/access.log <<'EOF'
2026-02-14T09:00:01Z 10.4.2.11 GET /health 200 18 "-" "kube-probe/1.27"
2026-02-14T09:00:03Z 10.4.2.15 GET /assets/app.css 200 1842 "https://shop.example/" "Mozilla/5.0"
2026-02-14T09:01:10Z 10.4.2.21 POST /api/cart 200 312 "https://shop.example/cart" "Mozilla/5.0"
2026-02-14T09:02:44Z 10.4.2.31 POST /api/checkout 500 91 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:03:12Z 10.4.2.41 POST /api/checkout?coupon=WINTER 502 87 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:04:02Z 10.4.2.44 POST /api/checkout-preview 503 99 "https://shop.example/admin" "Mozilla/5.0"
2026-02-14T09:05:18Z 10.4.2.45 POST /api/checkout 200 424 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:06:55Z 10.4.2.51 GET /api/checkout 405 66 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:07:26Z 10.4.2.52 POST /api/checkout?payment=card 500 93 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:08:09Z 10.4.2.60 POST /api/orders 503 74 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:08:45Z 10.4.2.61 POST /api/checkout?retry=1 503 95 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:09:14Z 10.4.2.62 POST /api/checkout?retry=2 504 91 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:10:01Z 10.4.2.63 POST /api/checkout 302 58 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:11:33Z 10.4.2.64 POST /api/checkout?coupon=SPRING 502 88 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:12:20Z 10.4.2.65 POST /api/checkout/refund 500 81 "https://shop.example/admin" "Mozilla/5.0"
2026-02-14T09:13:07Z 10.4.2.66 POST /api/checkout?source=mobile 500 90 "https://m.shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:14:44Z 10.4.2.67 POST /api/checkout?source=mobile 599 101 "https://m.shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:15:28Z 10.4.2.68 GET /assets/logo.svg 304 0 "https://shop.example/" "Mozilla/5.0"
2026-02-14T09:16:03Z 10.4.2.69 POST /api/checkout?retry=3 503 94 "https://shop.example/checkout" "Mozilla/5.0"
2026-02-14T09:17:49Z 10.4.2.70 POST /api/checkout 501 89 "https://shop.example/checkout" "Mozilla/5.0"
EOF

    cat > /home/user/projects/shopsite/scripts/summarize_checkout_errors.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /home/user/projects/shopsite/reports
grep ' /api/checkout ' /home/user/projects/shopsite/logs/access.log \
  | awk '$5 ~ /^5/ { total++; if (first == "") first=$1; last=$1; counts[$5]++ } END { printf "TOTAL_FAILED_CHECKOUTS=%d\n", total; printf "FIRST_FAILED_CHECKOUT=%s\n", first; printf "LAST_FAILED_CHECKOUT=%s\n", last; printf "STATUS_COUNTS="; sep=""; for (code in counts) { printf "%s%s:%d", sep, code, counts[code]; sep="," } printf "\n" }' \
  > /home/user/projects/shopsite/reports/error_summary.txt
echo "wrote /home/user/projects/shopsite/reports/error_summary.txt"
EOF

    chmod 755 /home/user/projects/shopsite/scripts/summarize_checkout_errors.sh
    chmod 644 /home/user/projects/shopsite/logs/access.log

    chown -R user:user /home/user/projects

    chmod 755 /home/user
    chmod 755 /home/user/projects
    chmod 755 /home/user/projects/shopsite
    chmod 755 /home/user/projects/shopsite/logs
    chmod 755 /home/user/projects/shopsite/scripts
    chmod 775 /home/user/projects/shopsite/reports

    apt-get clean
    rm -rf /var/lib/apt/lists/*

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
