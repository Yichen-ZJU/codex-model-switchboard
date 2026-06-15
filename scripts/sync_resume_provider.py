#!/usr/bin/env python3
"""Sync Codex /resume metadata to the provider used by the current launcher."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from pathlib import Path


def backup(paths: list[Path], backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if not path.exists():
            continue
        target = backup_dir / path.name
        if path.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)


def sync_rollouts(codex_home: Path, provider: str, dry_run: bool) -> tuple[int, int]:
    sessions = codex_home / "sessions"
    scanned = 0
    changed = 0
    if not sessions.exists():
        return scanned, changed

    for path in sessions.rglob("rollout-*.jsonl"):
        scanned += 1
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
        except OSError:
            continue
        if not lines:
            continue
        try:
            first = json.loads(lines[0])
        except Exception:
            continue
        if first.get("type") != "session_meta":
            continue
        payload = first.get("payload") or {}
        if payload.get("source") != "cli":
            continue
        if payload.get("thread_source") not in (None, "", "user"):
            continue

        before = dict(payload)
        payload["source"] = "cli"
        payload["thread_source"] = "user"
        payload["model_provider"] = provider
        first["payload"] = payload
        new_first = json.dumps(first, ensure_ascii=False, separators=(",", ":")) + "\n"
        if before != payload or lines[0] != new_first:
            changed += 1
            if not dry_run:
                path.write_text(new_first + "".join(lines[1:]), encoding="utf-8")

    return scanned, changed


def sync_sqlite(codex_home: Path, provider: str, model: str, dry_run: bool) -> int:
    db = codex_home / "state_5.sqlite"
    if not db.exists():
        return 0

    with sqlite3.connect(db) as con:
        rows = con.execute(
            """
            select count(*) from threads
            where source in ('cli', 'unknown')
              and (thread_source is null or thread_source = '' or thread_source = 'user')
              and rollout_path like ?
            """,
            (str(codex_home / "sessions") + "/%",),
        ).fetchone()[0]
        if dry_run:
            return rows
        con.execute(
            """
            update threads
            set
              model_provider = ?,
              model = ?,
              source = case when source = 'unknown' then 'cli' else source end,
              thread_source = case when thread_source is null or thread_source = '' then 'user' else thread_source end,
              has_user_event = 1,
              archived = 0
            where source in ('cli', 'unknown')
              and (thread_source is null or thread_source = '' or thread_source = 'user')
              and rollout_path like ?
            """,
            (provider, model, str(codex_home / "sessions") + "/%"),
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", required=True, type=Path)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    codex_home = args.codex_home.expanduser().resolve()
    if not codex_home.exists():
        raise SystemExit(f"CODEX_HOME does not exist: {codex_home}")

    if not args.dry_run and not args.no_backup:
        stamp = time.strftime("%Y%m%d%H%M%S")
        backup(
            [codex_home / "state_5.sqlite", codex_home / "sessions"],
            codex_home / f"backup-before-provider-sync-{stamp}",
        )

    scanned, rollout_changed = sync_rollouts(codex_home, args.provider, args.dry_run)
    sqlite_rows = sync_sqlite(codex_home, args.provider, args.model, args.dry_run)
    print(
        json.dumps(
            {
                "codex_home": str(codex_home),
                "provider": args.provider,
                "model": args.model,
                "rollouts_scanned": scanned,
                "rollouts_changed": rollout_changed,
                "sqlite_candidate_rows": sqlite_rows,
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
