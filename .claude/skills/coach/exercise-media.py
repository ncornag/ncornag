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
import urllib.request

RAW_BASE = "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main"


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


def media_paths(repo: str, slug: str) -> dict:
    exercises_dir = os.path.join(repo, "running", "assets", "exercises")
    return {
        "dir": exercises_dir,
        "image_abs": os.path.join(exercises_dir, f"{slug}.jpg"),
        "gif_abs": os.path.join(exercises_dir, f"{slug}.gif"),
        "image_rel": f"assets/exercises/{slug}.jpg",
        "gif_rel": f"assets/exercises/{slug}.gif",
    }


def fetch_media(record: dict, slug: str, repo: str) -> dict:
    paths = media_paths(repo, slug)
    os.makedirs(paths["dir"], exist_ok=True)
    downloads = [(record["image"], paths["image_abs"]),
                 (record["gif_url"], paths["gif_abs"])]
    for upstream_path, dest in downloads:
        if os.path.exists(dest):
            print(f"skip (already vendored): {dest}", file=sys.stderr)
            continue
        url = f"{RAW_BASE}/{upstream_path}"
        print(f"fetching {url}", file=sys.stderr)
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
    return {
        "image": paths["image_rel"],
        "gif": paths["gif_rel"],
        "attribution": record["attribution"],
    }


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

    fetch_p = sub.add_parser("fetch", help="vendor media for a matched id")
    fetch_p.add_argument("id")
    fetch_p.add_argument("slug")
    fetch_p.add_argument("--repo", help="repo root (default: inferred from script location)")
    fetch_p.add_argument("--data", help="path to exercises.json (default: <script dir>/data/exercises.json)")

    args = ap.parse_args()
    data_path = args.data or default_data_path()
    records = load_records(data_path)

    if args.command == "search":
        results = score_candidates(args.query, records)[:args.top]
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.command == "fetch":
        record = next((r for r in records if r["id"] == args.id), None)
        if record is None:
            print(f"error: no exercise with id {args.id!r} in {data_path}", file=sys.stderr)
            sys.exit(1)
        repo = os.path.abspath(args.repo) if args.repo \
            else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        result = fetch_media(record, args.slug, repo)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
