#!/usr/bin/env python3
"""exercise-media.py - Match an exercise name against the vendored exercises
dataset and vendor its demo media.

Part of the coach skill. Two subcommands:
  search  - fuzzy-match a query name against data/exercises.json, print
            ranked candidates as JSON. Claude reviews the candidates and
            decides whether any is genuinely the same exercise - this
            script never auto-picks the top score (token overlap can rank a
            wrong exercise highest, e.g. "hip raise (bent knee)" outscores
            real calf-raise variants for "Calf Raise Bent-Knee").
  fetch   - given a dataset id and a slug (derived from the athlete's own
            exercise name), download that record's thumbnail + GIF from the
            upstream exercises-dataset repo into running/assets/exercises/,
            skipping any file that already exists.

The vendored dataset (data/exercises.json) is a trimmed, one-time snapshot
of https://github.com/hasaneyldrm/exercises-dataset - see SKILL.md Notes for
the refresh command. All progress/errors go to stderr.

Usage:
  exercise-media.py search "<exercise name>" [--top N] [--data FILE]
  exercise-media.py fetch <id> <slug> [--repo DIR] [--data FILE]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys


def normalize_tokens(name: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9]+", " ", name.lower()).split())


def score_candidates(query: str, records: list[dict]) -> list[dict]:
    query_tokens = normalize_tokens(query)
    scored = []
    for rec in records:
        rec_tokens = normalize_tokens(rec["name"])
        overlap = len(query_tokens & rec_tokens)
        if overlap == 0:
            continue
        score = overlap / max(len(query_tokens), len(rec_tokens))
        scored.append({**rec, "score": round(score, 4)})
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored


def slugify(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def load_records(data_path: str) -> list[dict]:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def default_data_path() -> str:
    return os.path.join(os.path.dirname(__file__), "data", "exercises.json")


def main():
    ap = argparse.ArgumentParser(
        description="Match/vendor demo media from the exercises-dataset.")
    sub = ap.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="fuzzy-match a query name")
    search_p.add_argument("query")
    search_p.add_argument("--top", type=int, default=5)
    search_p.add_argument("--data", help="path to exercises.json (default: <script dir>/data/exercises.json)")

    args = ap.parse_args()
    data_path = args.data or default_data_path()
    records = load_records(data_path)

    if args.command == "search":
        results = score_candidates(args.query, records)[:args.top]
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
