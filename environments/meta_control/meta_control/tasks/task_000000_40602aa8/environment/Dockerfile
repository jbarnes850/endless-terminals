FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pytest \
        ca-certificates
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/log-audit/daily

    cat > /home/user/log-audit/daily/web-2024-03-18.log <<'EOF'
2024-03-18T08:00:01Z INFO service=frontend msg="boot complete"
2024-03-18T08:02:15Z WARN service=frontend msg="slow upstream response"
2024-03-18T08:07:44Z ERROR service=auth msg="token validation failed"
2024-03-18T08:09:10Z INFO service=frontend msg="request completed"
EOF

    cat > /home/user/log-audit/daily/web-2024-03-19.log <<'EOF'
2024-03-19T09:00:01Z INFO service=frontend msg="boot complete"
2024-03-19T09:03:20Z WARN service=payments msg="retry scheduled"
2024-03-19T09:04:11Z WARN service=payments msg="retry scheduled"
2024-03-19T09:08:55Z ERROR service=payments msg="gateway timeout"
2024-03-19T09:12:02Z INFO service=frontend msg="request completed"
EOF

    cat > /home/user/log-audit/daily/web-2024-03-20.log <<'EOF'
2024-03-20T10:00:01Z INFO service=frontend msg="boot complete"
2024-03-20T10:01:17Z WARN service=frontend msg="cache nearing capacity"
2024-03-20T10:02:05Z INFO service=frontend msg="request completed"
2024-03-20T10:04:48Z ERROR service=search msg="index shard unavailable"
2024-03-20T10:05:31Z ERROR service=search msg="index shard unavailable"
2024-03-20T10:06:44Z WARN service=search msg="fallback query path"
EOF

    cat > /home/user/log-audit/daily/web-2024-03-21.log <<'EOF'
2024-03-21T11:00:01Z INFO service=frontend msg="boot complete"
2024-03-21T11:02:09Z INFO service=frontend msg="request completed"
2024-03-21T11:03:33Z WARN service=auth msg="password reset spike"
2024-03-21T11:04:10Z ERROR service=auth msg="oauth provider unavailable"
2024-03-21T11:05:22Z INFO service=frontend msg="request completed"
2024-03-21T11:06:01Z error service=debug msg="lowercase should not count"
2024-03-21T11:07:45Z warn service=debug msg="lowercase should not count"
2024-03-21T11:08:03Z ERROR service=frontend msg="response serialization failed"
EOF

    rm -f /home/user/log-audit/current.log
    ln -s /home/user/log-audit/daily/web-2024-03-19.log /home/user/log-audit/current.log

    chown -R user:user /home/user/log-audit
    chown -h user:user /home/user/log-audit/current.log

    chmod 755 /home/user
    chmod 775 /home/user/log-audit
    chmod 775 /home/user/log-audit/daily
    chmod 644 /home/user/log-audit/daily/web-2024-03-18.log
    chmod 644 /home/user/log-audit/daily/web-2024-03-19.log
    chmod 644 /home/user/log-audit/daily/web-2024-03-20.log
    chmod 644 /home/user/log-audit/daily/web-2024-03-21.log

    # Make modification times intentionally unhelpful for choosing the latest log.
    touch -t 202403181200 /home/user/log-audit/daily/web-2024-03-18.log
    touch -t 202403221200 /home/user/log-audit/daily/web-2024-03-19.log
    touch -t 202403201200 /home/user/log-audit/daily/web-2024-03-20.log
    touch -t 202403211200 /home/user/log-audit/daily/web-2024-03-21.log

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
