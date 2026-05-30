#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time


SESSION_DB = Path("/Users/jarrodbarnes/.codex/session-history/codex_sessions.sqlite")


def session_row(session_id: str) -> dict[str, str] | None:
    with sqlite3.connect(SESSION_DB) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT session_id, last_ts, title, cwd, git_repo
            FROM sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def session_source(session_id: str) -> str | None:
    with sqlite3.connect(SESSION_DB) as conn:
        row = conn.execute(
            """
            SELECT source_path
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
    return str(row[0]) if row is not None else None


def file_mtime(path: str | None) -> float | None:
    if not path:
        return None
    candidate = Path(path)
    return candidate.stat().st_mtime if candidate.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Heartbeat a Codex session by watching its indexed row and raw log.")
    parser.add_argument("session_id")
    parser.add_argument("--interval-sec", type=float, default=300)
    parser.add_argument("--iterations", type=int, default=0, help="0 means run until killed.")
    parser.add_argument("--out", type=Path, default=Path("/tmp/codex-session-heartbeat.jsonl"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    iterations = 0
    while True:
        row = session_row(args.session_id)
        source = session_source(args.session_id)
        event = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "session_id": args.session_id,
            "indexed": row is not None,
            "session": row,
            "source_path": source,
            "source_mtime": file_mtime(source),
        }
        with args.out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        print(json.dumps(event, sort_keys=True), flush=True)
        iterations += 1
        if args.iterations and iterations >= args.iterations:
            break
        time.sleep(args.interval_sec)


if __name__ == "__main__":
    main()
