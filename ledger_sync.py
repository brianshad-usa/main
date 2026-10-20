#!/usr/bin/env python3
"""
ledger_sync.py
--------------
Pick the most-advanced editorial ledger among several candidate copies and write
it to editorial/ledger.json, so dedup (the 182-day per-idea cooldown + anti-repeat
rules in editorial_engine) stays correct no matter which persistence path last
succeeded.

The ledger is an append-only log ({"posts": [...]}), so "most posts" is the
newest. We reconcile across candidates because the pipeline no longer depends on
pushing to the protected 'main' branch: state is persisted to the non-protected
'social-state' branch AND (belt-and-suspenders) to an Actions cache, and either
one surviving is enough to prevent a duplicate post.

Usage:
    python ledger_sync.py restore CANDIDATE1 [CANDIDATE2 ...]
        Choose the candidate with the most posts (ties: first given) and write it
        to editorial/ledger.json. Missing/unreadable candidates are ignored. If
        none are usable, editorial/ledger.json is left as-is.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(HERE, "editorial", "ledger.json")


def _count(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        posts = data.get("posts", [])
        return len(posts) if isinstance(posts, list) else -1
    except Exception:
        return -1


def restore(candidates):
    best_path, best_n = None, -1
    for path in candidates:
        n = _count(path)
        label = f"{path}: {n} posts" if n >= 0 else f"{path}: unreadable/absent"
        print(f"[ledger-sync]   candidate {label}")
        if n > best_n:
            best_path, best_n = path, n

    if best_path is None or best_n < 0:
        existing = _count(LEDGER_PATH)
        print(f"[ledger-sync] no usable candidate; keeping editorial/ledger.json "
              f"({existing} posts).")
        return

    if os.path.abspath(best_path) == os.path.abspath(LEDGER_PATH):
        print(f"[ledger-sync] editorial/ledger.json is already the most advanced "
              f"({best_n} posts).")
        return

    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(best_path, encoding="utf-8") as src:
        payload = src.read()
    with open(LEDGER_PATH, "w", encoding="utf-8") as dst:
        dst.write(payload)
    print(f"[ledger-sync] restored editorial/ledger.json from {best_path} "
          f"({best_n} posts).")


def main(argv):
    if len(argv) >= 2 and argv[1] == "restore":
        restore(argv[2:])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
