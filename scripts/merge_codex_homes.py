#!/usr/bin/env python3
"""Merge terminal Codex histories into one canonical CODEX_HOME."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from pathlib import Path


def copy_file_if_newer(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime or src.stat().st_size > dst.stat().st_size:
        shutil.copy2(src, dst)


def merge_jsonl(target: Path, sources: list[Path], name: str) -> int:
    rows: list[tuple[object, str]] = []
    seen: set[str] = set()
    for home in sources + [target]:
        path = home / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip() or line in seen:
                continue
            seen.add(line)
            try:
                obj = json.loads(line)
            except Exception:
                obj = {}
            rows.append((obj, line))

    def sort_key(item: tuple[object, str]) -> tuple[str, str]:
        obj = item[0]
        if isinstance(obj, dict):
            return (str(obj.get("updated_at", obj.get("ts", ""))), str(obj.get("id", obj.get("session_id", ""))))
        return ("", item[1])

    rows.sort(key=sort_key)
    if rows:
        (target / name).write_text("\n".join(line for _, line in rows) + "\n", encoding="utf-8")
    return len(rows)


def rewrite_rollout_path(path: str, source_home: Path, target_home: Path) -> str:
    if not path:
        return path
    sessions = source_home / "sessions"
    try:
        rel = Path(path).relative_to(sessions)
    except ValueError:
        return path
    return str(target_home / "sessions" / rel)


def merge_sessions(target: Path, sources: list[Path]) -> int:
    copied = 0
    for home in sources:
        src = home / "sessions"
        if not src.exists():
            continue
        for file in src.rglob("*"):
            if not file.is_file():
                continue
            dst = target / "sessions" / file.relative_to(src)
            before = dst.exists()
            copy_file_if_newer(file, dst)
            if not before or dst.stat().st_size == file.stat().st_size:
                copied += 1
    return copied


def merge_threads(target: Path, sources: list[Path], include_vscode: bool) -> int:
    target_db = target / "state_5.sqlite"
    if not target_db.exists():
        return 0

    with sqlite3.connect(target_db) as tconn:
        tconn.row_factory = sqlite3.Row
        cols = [row["name"] for row in tconn.execute("pragma table_info(threads)")]
        insert_cols = ",".join(cols)
        placeholders = ",".join(["?"] * len(cols))
        updates = ",".join([f"{col}=excluded.{col}" for col in cols if col != "id"])
        sql = (
            f"insert into threads ({insert_cols}) values ({placeholders}) "
            f"on conflict(id) do update set {updates} "
            "where coalesce(excluded.updated_at_ms, 0) > coalesce(threads.updated_at_ms, 0) "
            "or excluded.updated_at > threads.updated_at"
        )
        merged = 0
        for home in sources:
            db = home / "state_5.sqlite"
            if not db.exists():
                continue
            with sqlite3.connect(db) as sconn:
                sconn.row_factory = sqlite3.Row
                for row in sconn.execute("select * from threads"):
                    if row["source"] == "vscode" and not include_vscode:
                        continue
                    values = []
                    keys = set(row.keys())
                    for col in cols:
                        val = row[col] if col in keys else None
                        if col == "rollout_path":
                            val = rewrite_rollout_path(val, home, target)
                        elif col == "source" and val == "unknown":
                            val = "cli"
                        elif col == "thread_source" and val in (None, ""):
                            val = "user"
                        elif col == "has_user_event" and row["source"] in ("cli", "unknown"):
                            val = 1
                        elif col == "archived" and row["source"] in ("cli", "unknown"):
                            val = 0
                        values.append(val)
                    tconn.execute(sql, values)
                    merged += 1
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--source", action="append", required=True, type=Path)
    parser.add_argument("--include-vscode", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    target = args.target.expanduser().resolve()
    sources = [source.expanduser().resolve() for source in args.source]
    target.mkdir(parents=True, exist_ok=True)

    if not args.no_backup:
        stamp = time.strftime("%Y%m%d%H%M%S")
        backup_dir = target / f"backup-before-home-merge-{stamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for name in ("history.jsonl", "session_index.jsonl", "state_5.sqlite"):
            path = target / name
            if path.exists():
                shutil.copy2(path, backup_dir / name)
        if (target / "sessions").exists():
            shutil.copytree(target / "sessions", backup_dir / "sessions")

    session_files = merge_sessions(target, sources)
    history_rows = merge_jsonl(target, sources, "history.jsonl")
    index_rows = merge_jsonl(target, sources, "session_index.jsonl")
    thread_rows = merge_threads(target, sources, args.include_vscode)
    print(
        json.dumps(
            {
                "target": str(target),
                "sources": [str(s) for s in sources],
                "session_files_seen": session_files,
                "history_rows": history_rows,
                "session_index_rows": index_rows,
                "thread_rows_merged": thread_rows,
                "include_vscode": args.include_vscode,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
