FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        coreutils \
        gawk \
        sed \
        grep \
        findutils

    python3 -m pip install --no-cache-dir pytest

    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    mkdir -p /home/user/support_tickets

    cat > /home/user/support_tickets/ticket_export.tsv <<'EOF'
TicketID	OpenedAt	Requester	Dept	AssetTag	Hostname	Issue	Serial	LastSeen	OwnerEmail	Status	Priority
TCK-4101	2026-02-03 08:17	Mina Patel	Finance	AT-00931	fin-lap-014	VPN client fails	SN8K21F	2026-02-03 08:10	mina.patel@example.com	Open	High
TCK-4102	2026-02-03 08:31	Owen Briggs	Sales	AT-00442	sls-dsk-022	Monitor flicker	SN1P77Q	2026-02-02 17:55	owen.briggs@example.com	Closed	Medium
TCK-4103	2026-02-03 08:49	Lena Zhou	Engineering	AT-01007	eng-lap-108	Disk encryption prompt loop	SN4D88M	2026-02-03 08:42	lena.zhou@example.com	Waiting	Critical
TCK-4104	2026-02-03 09:04	Carlos Nunez	Support	AT-00219	sup-dsk-009	Keyboard replacement	SN6H45T	2026-02-01 13:12	carlos.nunez@example.com	Open	Low
TCK-4105	2026-02-03 09:22	Asha Rao	Finance	AT-00944	fin-lap-021	Email archive missing	SN2B90L	2026-02-03 09:18	asha.rao@example.com	Open	Medium
TCK-4106	2026-02-03 09:39	Peter Holm	Legal	AT-00618	leg-lap-033	Unable to print	SN3C11R	2026-02-03 09:01	peter.holm@example.com	Pending	High
TCK-4107	2026-02-03 09:58	Nora Kim	HR	AT-00752	hr-lap-017	Password reset loop	SN9X02A	2026-02-03 09:53	nora.kim@example.com	Waiting	High
TCK-4108	2026-02-03 10:11	Eli Turner	Engineering	AT-01018	eng-wks-044	Build tools corrupted	SN7V34E	2026-02-03 10:07	eli.turner@example.com	Open	Critical
TCK-4109	2026-02-03 10:26	Fatima Noor	Sales	AT-00467	sls-lap-031	CRM shortcut missing	SN5J66K	2026-02-03 09:41	fatima.noor@example.com	Waiting	Low
TCK-4110	2026-02-03 10:44	Ben Archer	Operations	AT-00385	ops-dsk-012	Shared drive access denied	SN0L13Z	2026-02-03 10:40	ben.archer@example.com	Open	High
EOF

    chown -R user:user /home/user
    chmod 755 /home/user
    chmod 775 /home/user/support_tickets
    chmod 664 /home/user/support_tickets/ticket_export.tsv

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
