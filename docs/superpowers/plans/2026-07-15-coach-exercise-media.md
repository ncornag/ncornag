# Coach skill exercise media & metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the coach skill's gym exercise cards an optional demo GIF and
target-muscle tag, sourced from a vendored snapshot of the
[hasaneyldrm/exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset),
matched by name with the coach reviewing every match (never auto-picked), and
retrofit `running/gym-week10.html` as the first real example.

**Architecture:** A trimmed, one-time local snapshot of the upstream dataset
(`.claude/skills/coach/data/exercises.json`) backs a new deterministic engine
script, `exercise-media.py`, in the same style as `parse-log.py`: a `search`
subcommand fuzzy-matches an exercise name and prints ranked JSON candidates
(Claude judges which, if any, is a real match), and a `fetch` subcommand
vendors the matched record's thumbnail + GIF into `running/assets/exercises/`
(idempotent, skips existing files). `SKILL.md` documents the workflow;
`build.sh`'s allowlist is extended so the vendored media actually deploys.

**Tech Stack:** Python 3 stdlib only (matches the existing coach scripts — no
`requests`, no third-party deps), plain-assert tests run via
`python3 test-*.py` (no pytest), static HTML/CSS for the gym cards.

## Global Constraints

- Coach-skill scripts are stdlib-only Python, print machine JSON to stdout
  and progress/errors to stderr — the existing convention in `parse-log.py`.
- **Never auto-accept the highest fuzzy-match score.** Token overlap can rank
  the wrong exercise highest (verified: "hip raise (bent knee)" outscores
  every real calf-raise variant for "Calf Raise Bent-Knee"). A match is only
  used after Claude confirms, by reading the candidate's name/target, that it
  is the same movement.
- Any vendored Gym visual media must carry the attribution
  `© Gym visual — https://gymvisual.com/` wherever it's displayed.
- `build.sh` is an explicit allowlist (see its own header comment) — a new
  public path must be added there explicitly or it will not deploy.
- `running/gym-week3.html` through `gym-week9.html` are frozen — out of
  scope, not touched by this plan.
- Vendored media filenames are kebab-case of the athlete's own exercise name
  (not the dataset id), so the same slug is reused — no re-fetch — if the
  exercise recurs in a later week.
- `dist/` is a gitignored build artifact — never commit it.

---

### Task 1: Vendor the trimmed exercises-dataset snapshot

**Files:**
- Create: `.claude/skills/coach/data/exercises.json`

**Interfaces:**
- Produces: a JSON array on disk, each element with exactly the keys `id`,
  `name`, `target`, `muscle_group`, `secondary_muscles`, `equipment`,
  `image`, `gif_url`, `attribution` (types: all `str` except
  `secondary_muscles: list[str]`). Tasks 2+ read this file as their default
  data source.

- [ ] **Step 1: Download the upstream dataset**

Run: `curl -sL https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/data/exercises.json -o /tmp/exercises-full.json`

Expected: exits 0, `/tmp/exercises-full.json` exists and is roughly 16MB.

- [ ] **Step 2: Verify the download's shape**

Run: `python3 -c "import json; d=json.load(open('/tmp/exercises-full.json')); print(len(d)); print(sorted(d[0].keys()))"`

Expected output:
```
1324
['attribution', 'body_part', 'category', 'created_at', 'equipment', 'gif_url', 'id', 'image', 'instructions', 'instruction_steps', 'media_id', 'muscle_group', 'name', 'secondary_muscles', 'target']
```

- [ ] **Step 3: Trim and vendor the snapshot**

Run:
```bash
mkdir -p .claude/skills/coach/data
python3 - <<'PYEOF'
import json

with open("/tmp/exercises-full.json", encoding="utf-8") as f:
    records = json.load(f)

FIELDS = ("id", "name", "target", "muscle_group", "secondary_muscles",
          "equipment", "image", "gif_url", "attribution")
trimmed = [{k: r[k] for k in FIELDS} for r in records]

with open(".claude/skills/coach/data/exercises.json", "w", encoding="utf-8") as f:
    json.dump(trimmed, f, ensure_ascii=False, indent=2)

print(f"wrote {len(trimmed)} records")
PYEOF
```

Expected output: `wrote 1324 records`

- [ ] **Step 4: Verify the vendored file**

Run: `python3 -c "import json; d=json.load(open('.claude/skills/coach/data/exercises.json')); print(len(d)); print(sorted(d[0].keys()))"` and `du -h .claude/skills/coach/data/exercises.json`

Expected: `1324` records, keys exactly
`['attribution', 'equipment', 'gif_url', 'id', 'image', 'muscle_group', 'name', 'secondary_muscles', 'target']`,
file size well under 1MB (roughly 350-450K).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/coach/data/exercises.json
git commit -m "feat(coach): vendor trimmed exercises-dataset snapshot"
```

---

### Task 2: Exercise name matching (`exercise-media.py search`)

**Files:**
- Create: `.claude/skills/coach/exercise-media.py`
- Test: `.claude/skills/coach/test-exercise-media.py`

**Interfaces:**
- Consumes: `.claude/skills/coach/data/exercises.json` (Task 1) as the
  default `--data` path.
- Produces: `normalize_tokens(name: str) -> set[str]`,
  `score_candidates(query: str, records: list[dict]) -> list[dict]` (each
  result is the original record dict plus `"score": float`, sorted
  descending, entries with zero overlap excluded), `slugify(name: str) -> str`
  (kebab-case), `load_records(data_path: str) -> list[dict]`,
  `default_data_path() -> str`. CLI: `exercise-media.py search "<name>"
  [--top N] [--data FILE]` prints the top `N` (default 5) scored candidates
  as JSON to stdout. Task 3 extends this same file/module.

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/coach/test-exercise-media.py`:

```python
#!/usr/bin/env python3
"""Plain-assert tests for exercise-media.py helpers. Run: python3 test-exercise-media.py"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "exercise_media", os.path.join(HERE, "exercise-media.py"))
em = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(em)


def test_normalize_tokens_lowercases_and_strips_punctuation():
    assert em.normalize_tokens("One-Arm Bent-Over Row") == {"one", "arm", "bent", "over", "row"}


def test_score_candidates_exact_match_scores_one():
    records = [{"id": "1", "name": "dead bug"}, {"id": "2", "name": "sit-up"}]
    scored = em.score_candidates("Dead Bug", records)
    assert scored[0]["id"] == "1"
    assert scored[0]["score"] == 1.0


def test_score_candidates_excludes_disjoint_names():
    records = [{"id": "1", "name": "dead bug"}, {"id": "2", "name": "barbell squat"}]
    scored = em.score_candidates("side plank", records)
    assert scored == []


def test_score_candidates_ranks_partial_overlap_below_exact():
    records = [
        {"id": "1", "name": "dumbbell single leg calf raise"},
        {"id": "2", "name": "single leg calf raise"},
    ]
    scored = em.score_candidates("Single-Leg Calf Raise", records)
    assert scored[0]["id"] == "2"
    assert scored[0]["score"] == 1.0
    assert scored[1]["id"] == "1"
    assert scored[1]["score"] < 1.0


def test_slugify_kebab_cases_the_name():
    assert em.slugify("Dead Bug") == "dead-bug"
    assert em.slugify("One-Arm Bent-Over Row") == "one-arm-bent-over-row"


if __name__ == "__main__":
    test_normalize_tokens_lowercases_and_strips_punctuation()
    test_score_candidates_exact_match_scores_one()
    test_score_candidates_excludes_disjoint_names()
    test_score_candidates_ranks_partial_overlap_below_exact()
    test_slugify_kebab_cases_the_name()
    print("OK")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 .claude/skills/coach/test-exercise-media.py`

Expected: fails with `FileNotFoundError` (or similar) because
`exercise-media.py` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/coach/exercise-media.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 .claude/skills/coach/test-exercise-media.py`

Expected: `OK`

- [ ] **Step 5: Manually verify the CLI against the real vendored data**

Run: `python3 .claude/skills/coach/exercise-media.py search "Dead Bug" --top 3`

Expected: JSON array whose first element has `"id": "0276"`, `"name": "dead bug"`, `"score": 1.0`.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/coach/exercise-media.py .claude/skills/coach/test-exercise-media.py
git commit -m "feat(coach): add exercise-media.py search — fuzzy name matching"
```

---

### Task 3: Media vendoring (`exercise-media.py fetch`)

**Files:**
- Modify: `.claude/skills/coach/exercise-media.py`
- Modify: `.claude/skills/coach/test-exercise-media.py`

**Interfaces:**
- Consumes: `slugify`, `load_records`, `default_data_path` from Task 2.
- Produces: `media_paths(repo: str, slug: str) -> dict` (keys `dir`,
  `image_abs`, `gif_abs`, `image_rel`, `gif_rel`), `fetch_media(record:
  dict, slug: str, repo: str) -> dict` (keys `image`, `gif`, `attribution` —
  the two relative paths plus the record's attribution string; idempotent,
  skips any file that already exists at its `*_abs` path). CLI:
  `exercise-media.py fetch <id> <slug> [--repo DIR] [--data FILE]` prints
  that dict as JSON. Task 5 (the retrofit) calls this CLI directly.

- [ ] **Step 1: Write the failing tests**

In `.claude/skills/coach/test-exercise-media.py`, find the top imports:

```python
import importlib.util
import os
```

Replace with:

```python
import importlib.util
import os
import tempfile
```

Then append these functions before the `if __name__ == "__main__":` block:

```python
def test_media_paths_derives_relative_and_absolute_paths():
    paths = em.media_paths("/repo", "dead-bug")
    assert paths["image_rel"] == "assets/exercises/dead-bug.jpg"
    assert paths["gif_rel"] == "assets/exercises/dead-bug.gif"
    assert paths["image_abs"] == "/repo/running/assets/exercises/dead-bug.jpg"
    assert paths["gif_abs"] == "/repo/running/assets/exercises/dead-bug.gif"


def test_fetch_media_skips_files_that_already_exist():
    with tempfile.TemporaryDirectory() as d:
        paths = em.media_paths(d, "dead-bug")
        os.makedirs(paths["dir"], exist_ok=True)
        with open(paths["image_abs"], "wb") as f:
            f.write(b"cached-jpg")
        with open(paths["gif_abs"], "wb") as f:
            f.write(b"cached-gif")
        record = {"id": "0276", "name": "dead bug", "image": "images/x.jpg",
                   "gif_url": "videos/x.gif", "attribution": "© Gym visual"}
        result = em.fetch_media(record, "dead-bug", d)
        with open(paths["image_abs"], "rb") as f:
            assert f.read() == b"cached-jpg"
        with open(paths["gif_abs"], "rb") as f:
            assert f.read() == b"cached-gif"
        assert result == {"image": "assets/exercises/dead-bug.jpg",
                           "gif": "assets/exercises/dead-bug.gif",
                           "attribution": "© Gym visual"}
```

Update the `if __name__ == "__main__":` block to also call the two new tests
before `print("OK")`:

```python
if __name__ == "__main__":
    test_normalize_tokens_lowercases_and_strips_punctuation()
    test_score_candidates_exact_match_scores_one()
    test_score_candidates_excludes_disjoint_names()
    test_score_candidates_ranks_partial_overlap_below_exact()
    test_slugify_kebab_cases_the_name()
    test_media_paths_derives_relative_and_absolute_paths()
    test_fetch_media_skips_files_that_already_exist()
    print("OK")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 .claude/skills/coach/test-exercise-media.py`

Expected: fails with `AttributeError: module 'exercise_media' has no attribute 'media_paths'`.

- [ ] **Step 3: Write the implementation**

In `.claude/skills/coach/exercise-media.py`, change the imports at the top
from:

```python
import argparse
import json
import os
import re
import sys
```

to:

```python
import argparse
import json
import os
import re
import sys
import urllib.request

RAW_BASE = "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main"
```

Then insert these two functions between `load_records` and `default_data_path`:

```python
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
```

Finally, in `main()`, replace:

```python
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
```

with:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 .claude/skills/coach/test-exercise-media.py`

Expected: `OK`

- [ ] **Step 5: Manually verify the CLI end-to-end against the real network**

Run:
```bash
mkdir -p /tmp/exercise-media-smoketest
python3 .claude/skills/coach/exercise-media.py fetch 0276 dead-bug --repo /tmp/exercise-media-smoketest
ls -la /tmp/exercise-media-smoketest/running/assets/exercises/
```

Expected: prints a JSON object with `"image": "assets/exercises/dead-bug.jpg"`,
`"gif": "assets/exercises/dead-bug.gif"`, `"attribution": "© Gym visual — https://gymvisual.com/"`;
the `ls` shows both `dead-bug.jpg` and `dead-bug.gif` with non-zero size.
Clean up: `rm -rf /tmp/exercise-media-smoketest`.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/coach/exercise-media.py .claude/skills/coach/test-exercise-media.py
git commit -m "feat(coach): add exercise-media.py fetch — vendor demo media"
```

---

### Task 4: Document the workflow in SKILL.md

**Files:**
- Modify: `.claude/skills/coach/SKILL.md`

**Interfaces:**
- Consumes: the `search`/`fetch` CLI from Tasks 2–3, the CSS class names
  `.ex-media`/`.ex-target`/`.media-attribution` used by Task 5.
- Produces: no code — updated skill documentation, read by future `/coach`
  sessions.

- [ ] **Step 1: Add two rows to the Files table**

In `.claude/skills/coach/SKILL.md`, find this row (part of the Files table):

```
| the gym files (profile `gym_prefix`) | Per-week gym tables, `<gym_prefix><N>.html` (range-named when identical, e.g. `<gym_prefix>3-5.html`). |
```

Replace it with itself plus two new rows immediately after:

```
| the gym files (profile `gym_prefix`) | Per-week gym tables, `<gym_prefix><N>.html` (range-named when identical, e.g. `<gym_prefix>3-5.html`). |
| `.claude/skills/coach/data/exercises.json` | Vendored snapshot of the [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) (id/name/target/muscle_group/secondary_muscles/equipment/media paths) — used to match an exercise name to a demo GIF + target muscle. Refresh manually per Notes; never engine-generated. |
| `.claude/skills/coach/exercise-media.py` | Matching/vendoring engine for exercise demo media — `search` (fuzzy match, judge the result yourself), `fetch` (vendor image+GIF for a confirmed match). Run it, use its JSON. |
```

- [ ] **Step 2: Add a "Demo media" bullet to Gym programming**

In the same file, find the `## Gym programming` section's bullet list. Locate
this bullet (the one starting with `- **Progression:**`) and the one right
after it (starting with `- **Dedup → ranges:**`):

```
- **Progression:** evolve content by phase — foundation (bodyweight, form) → strength
  (add load) → vert/power (step-ups, eccentric descents) → taper (reduce volume) — and by
  athlete feedback (e.g. swap an exercise that aggravates a joint).
- **Dedup → ranges:** if a week's programme is identical to the previous week's, do **not**
```

Insert a new bullet between them so the result reads:

```
- **Progression:** evolve content by phase — foundation (bodyweight, form) → strength
  (add load) → vert/power (step-ups, eccentric descents) → taper (reduce volume) — and by
  athlete feedback (e.g. swap an exercise that aggravates a joint).
- **Demo media:** after writing an exercise's cues, run `python3
  .claude/skills/coach/exercise-media.py search "<exercise name>"` and read
  the candidates it returns — name, target, equipment, score. **Never accept
  the top score blindly**: token overlap can rank a wrong exercise highest
  (e.g. "hip raise (bent knee)" outscores real calf-raise variants for
  "Calf Raise Bent-Knee" — a different movement entirely). Only proceed on a
  candidate you are confident, from its name and target muscle, is the same
  movement. On a confident match, run `python3
  .claude/skills/coach/exercise-media.py fetch <id> <slug>` (`<slug>` = the
  exercise's own name, kebab-cased, e.g. `dead-bug`) to vendor its thumbnail
  + GIF into `running/assets/exercises/`, then add `<img class="ex-media"
  src="assets/exercises/<slug>.gif" alt="<name> demo" loading="lazy">` next
  to the exercise name in `.ex-num-name`, and `<div
  class="ex-target">Target: <muscle></div>` immediately after `.ex-header`.
  Add `<div class="media-attribution">Exercise demo images © Gym visual —
  https://gymvisual.com/</div>` once per page, right after the `.exercises`
  grid closes, the first time any card on that page gets a demo image. **No
  confident match → leave the card exactly as-is, silently** — this dataset
  skews toward equipped gym-machine names and misses several of this plan's
  trail-specific bodyweight/isometric moves; that is expected, not an error.
- **Dedup → ranges:** if a week's programme is identical to the previous week's, do **not**
```

- [ ] **Step 3: Update the Template bullet to mention the optional classes**

In the same section, find:

```
- **Template:** copy the structure and CSS of the current foundation table
  (`<gym_prefix>3-5.html`, e.g. `gym-week3-5.html`): theme bootstrap, a stacked
  two-line title in the profile's language (e.g. `GYM<br>WEEK N` in English,
  `GIMNASIO<br>SEMANA N` in Spanish), phase subtitle, stat pills, warmup card,
  exercise grid (`.exercise` with `.cues` and `.ex-watch`), and the
  expected/warning footer. Include the back-to-index link
  (`<a href="index.html">‹ Running</a>` right after `<body>`).
```

Replace with:

```
- **Template:** copy the structure and CSS of the current foundation table
  (`<gym_prefix>3-5.html`, e.g. `gym-week3-5.html`): theme bootstrap, a stacked
  two-line title in the profile's language (e.g. `GYM<br>WEEK N` in English,
  `GIMNASIO<br>SEMANA N` in Spanish), phase subtitle, stat pills, warmup card,
  exercise grid (`.exercise` with `.cues`, `.ex-watch`, and optionally
  `.ex-media`/`.ex-target` — see "Demo media" below), and the
  expected/warning footer. Include the back-to-index link
  (`<a href="index.html">‹ Running</a>` right after `<body>`).
```

- [ ] **Step 4: Add a Notes bullet about the vendored snapshot**

In the `## Notes` section, find the last bullet:

```
- StrengthTraining activities count as sessions but contribute 0 km; they show as `gym`
  in the actuals panel. When coaching a week with a gym session, read that week's gym file
  (`weeks[].gym_file` from the engine) for the exercise list and cues so feedback is
  specific to what the athlete actually did.
```

Append a new bullet right after it:

```
- StrengthTraining activities count as sessions but contribute 0 km; they show as `gym`
  in the actuals panel. When coaching a week with a gym session, read that week's gym file
  (`weeks[].gym_file` from the engine) for the exercise list and cues so feedback is
  specific to what the athlete actually did.
- `.claude/skills/coach/data/exercises.json` is a **vendored snapshot**, not
  engine output — refresh it only when you need newer dataset coverage: `curl
  -sL https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/data/exercises.json
  -o /tmp/exercises-full.json`, then trim each record to
  `id`/`name`/`target`/`muscle_group`/`secondary_muscles`/`equipment`/`image`/`gif_url`/`attribution`
  and overwrite the vendored file. `running/assets/exercises/*.jpg`/`*.gif`
  are real vendored image data (© Gym visual — see the dataset's
  [NOTICE.md](https://github.com/hasaneyldrm/exercises-dataset/blob/main/NOTICE.md))
  — never regenerated or deleted by the engine.
```

- [ ] **Step 5: Verify the edits landed**

Run: `grep -c "exercise-media.py\|ex-media\|ex-target\|media-attribution" .claude/skills/coach/SKILL.md`

Expected: a count of `8` or more (non-zero, confirming all four edits are present).

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/coach/SKILL.md
git commit -m "docs(coach): document exercise demo-media workflow in SKILL.md"
```

---

### Task 5: Retrofit `running/gym-week10.html`

**Files:**
- Modify: `running/gym-week10.html`

**Interfaces:**
- Consumes: `exercise-media.py search`/`fetch` CLI (Tasks 2–3).
- Produces: `running/assets/exercises/single-leg-calf-raise.{jpg,gif}`,
  `single-leg-glute-bridge.{jpg,gif}`, `dead-bug.{jpg,gif}`,
  `one-arm-bent-over-row.{jpg,gif}` — consumed by Task 6's build verification.

- [ ] **Step 1: Confirm the matches**

Run each of these and note the top result's `id`:

```bash
python3 .claude/skills/coach/exercise-media.py search "Bulgarian Split Squat" --top 3
python3 .claude/skills/coach/exercise-media.py search "Single-Leg Calf Raise" --top 3
python3 .claude/skills/coach/exercise-media.py search "Single-Leg Glute Bridge" --top 3
python3 .claude/skills/coach/exercise-media.py search "Dead Bug" --top 3
python3 .claude/skills/coach/exercise-media.py search "Side Plank" --top 3
python3 .claude/skills/coach/exercise-media.py search "High Step-up + Eccentric Descent" --top 3
python3 .claude/skills/coach/exercise-media.py search "One-Arm Bent-Over Row" --top 3
python3 .claude/skills/coach/exercise-media.py search "Calf Raise Bent-Knee" --top 3
```

Expected (already verified during design): confident matches only for
Single-Leg Calf Raise (id `0409`, `dumbbell single leg calf raise`),
Single-Leg Glute Bridge (id `3645`, `single leg bridge with outstretched
leg`), Dead Bug (id `0276`, `dead bug`), and One-Arm Bent-Over Row (id
`0292`, `dumbbell one arm bent-over row`). The other four return no
confident match (top hits describe a different exercise, e.g. "hip raise
(bent knee)" for Calf Raise Bent-Knee) — do not use them.

- [ ] **Step 2: Vendor the four confirmed exercises' media**

```bash
python3 .claude/skills/coach/exercise-media.py fetch 0409 single-leg-calf-raise
python3 .claude/skills/coach/exercise-media.py fetch 3645 single-leg-glute-bridge
python3 .claude/skills/coach/exercise-media.py fetch 0276 dead-bug
python3 .claude/skills/coach/exercise-media.py fetch 0292 one-arm-bent-over-row
ls -la running/assets/exercises/
```

Expected: 8 files (4 `.jpg` + 4 `.gif`), each non-zero size.

- [ ] **Step 3: Add the CSS rules**

In `running/gym-week10.html`, find:

```css
    .ex-watch strong {
      color: var(--warn);
      font-weight: 600;
    }

    /* Footer */
```

Replace with:

```css
    .ex-watch strong {
      color: var(--warn);
      font-weight: 600;
    }

    .ex-media {
      width: 44px;
      height: 44px;
      border-radius: 4px;
      object-fit: cover;
      border: 1px solid var(--border);
      flex-shrink: 0;
      align-self: center;
    }

    .ex-target {
      font-size: .62rem;
      letter-spacing: .04em;
      color: var(--muted);
      margin-bottom: .6rem;
    }

    .media-attribution {
      font-size: .58rem;
      color: var(--muted);
      text-align: right;
      margin: -1rem 0 1rem;
    }

    /* Footer */
```

- [ ] **Step 4: Update the Single-Leg Calf Raise card**

Find:

```html
    <!-- 2 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">2</div>
          <div class="ex-name">Single-Leg<br>Calf Raise</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            leg</span></div>
      </div>

      <div class="ex-label">Position</div>
```

Replace with:

```html
    <!-- 2 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">2</div>
          <img class="ex-media" src="assets/exercises/single-leg-calf-raise.gif" alt="Single-Leg Calf Raise demo" loading="lazy">
          <div class="ex-name">Single-Leg<br>Calf Raise</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            leg</span></div>
      </div>
      <div class="ex-target">Target: calves</div>

      <div class="ex-label">Position</div>
```

- [ ] **Step 5: Update the Single-Leg Glute Bridge card**

Find:

```html
    <!-- 3 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">3</div>
          <div class="ex-name">Single-Leg<br>Glute Bridge</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            leg</span></div>
      </div>

      <div class="ex-label">Position</div>
```

Replace with:

```html
    <!-- 3 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">3</div>
          <img class="ex-media" src="assets/exercises/single-leg-glute-bridge.gif" alt="Single-Leg Glute Bridge demo" loading="lazy">
          <div class="ex-name">Single-Leg<br>Glute Bridge</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            leg</span></div>
      </div>
      <div class="ex-target">Target: glutes</div>

      <div class="ex-label">Position</div>
```

- [ ] **Step 6: Update the Dead Bug card**

Find:

```html
    <!-- 4 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">4</div>
          <div class="ex-name">Dead<br>Bug</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            side</span></div>
      </div>

      <div class="ex-label">Position</div>
```

Replace with:

```html
    <!-- 4 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">4</div>
          <img class="ex-media" src="assets/exercises/dead-bug.gif" alt="Dead Bug demo" loading="lazy">
          <div class="ex-name">Dead<br>Bug</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            side</span></div>
      </div>
      <div class="ex-target">Target: abs</div>

      <div class="ex-label">Position</div>
```

- [ ] **Step 7: Update the One-Arm Bent-Over Row card**

Find:

```html
    <!-- 7 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">7</div>
          <div class="ex-name">One-Arm<br>Bent-Over Row</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            arm</span></div>
      </div>

      <div class="ex-label">Position</div>
```

Replace with:

```html
    <!-- 7 -->
    <div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-num">7</div>
          <img class="ex-media" src="assets/exercises/one-arm-bent-over-row.gif" alt="One-Arm Bent-Over Row demo" loading="lazy">
          <div class="ex-name">One-Arm<br>Bent-Over Row</div>
        </div>
        <div class="ex-sets">3 × 8<br><span
            style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
            arm</span></div>
      </div>
      <div class="ex-target">Target: upper back</div>

      <div class="ex-label">Position</div>
```

- [ ] **Step 8: Add the shared attribution line**

Find:

```html
  </div>

  <div class="footer">
```

(this is the `.exercises` grid's closing tag, immediately before the footer
— there is exactly one occurrence of `</div>` followed by a blank line then
`<div class="footer">` in this file). Replace with:

```html
  </div>

  <div class="media-attribution">Exercise demo images © Gym visual — https://gymvisual.com/</div>

  <div class="footer">
```

- [ ] **Step 9: Verify well-formedness and scope of the diff**

Run:
```bash
python3 -c "
from html.parser import HTMLParser
class Check(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
    def handle_starttag(self, tag, attrs):
        if tag not in ('img', 'br', 'link', 'meta', 'input'):
            self.stack.append(tag)
    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, f'mismatch at {tag}, stack tail={self.stack[-3:]}'
        self.stack.pop()
c = Check()
c.feed(open('running/gym-week10.html', encoding='utf-8').read())
assert not c.stack, f'unclosed tags: {c.stack}'
print('balanced OK')
"
grep -c 'class="ex-media"' running/gym-week10.html
grep -c 'class="ex-target"' running/gym-week10.html
git diff --stat running/gym-week10.html
```

Expected: `balanced OK`; both grep counts are `4`; `git diff --stat` shows
only `running/gym-week10.html` changed with a modest insertion count (roughly
20–30 lines) — review the full diff and confirm the 4 untouched cards
(Bulgarian Split Squat, Side Plank, High Step-up + Eccentric Descent, Calf
Raise Bent-Knee) show **no** changes.

- [ ] **Step 10: Commit**

```bash
git add running/gym-week10.html running/assets/exercises/
git commit -m "feat(coach): add demo media to 4 gym-week10 exercises"
```

---

### Task 6: Deploy the vendored media (`build.sh`)

**Files:**
- Modify: `build.sh`

**Interfaces:**
- Consumes: `running/assets/exercises/*` (Task 5).
- Produces: `dist/running/assets/exercises/*` when `bash build.sh` runs
  (gitignored build output — never committed).

- [ ] **Step 1: Add the copy step**

In `build.sh`, find:

```bash
rm -rf dist
mkdir -p dist/running
cp -R "${ROOT[@]}" dist/
# /running: ship only the rendered pages and their stylesheet.
cp running/*.html running/theme.css dist/running/
```

Replace with:

```bash
rm -rf dist
mkdir -p dist/running
cp -R "${ROOT[@]}" dist/
# /running: ship only the rendered pages, their stylesheet, and vendored assets.
cp running/*.html running/theme.css dist/running/
cp -R running/assets dist/running/
```

- [ ] **Step 2: Run the build and verify**

Run:
```bash
bash build.sh
find dist/running/assets -type f | sort
```

Expected: the `find` output lists all 8 files vendored in Task 5:
```
dist/running/assets/exercises/dead-bug.gif
dist/running/assets/exercises/dead-bug.jpg
dist/running/assets/exercises/one-arm-bent-over-row.gif
dist/running/assets/exercises/one-arm-bent-over-row.jpg
dist/running/assets/exercises/single-leg-calf-raise.gif
dist/running/assets/exercises/single-leg-calf-raise.jpg
dist/running/assets/exercises/single-leg-glute-bridge.gif
dist/running/assets/exercises/single-leg-glute-bridge.jpg
```

- [ ] **Step 3: Commit**

```bash
git add build.sh
git commit -m "build: publish running/assets in the deployed site"
```

---

## Final verification (after all tasks)

- [ ] Re-run `python3 .claude/skills/coach/test-exercise-media.py` → `OK`.
- [ ] Re-run `python3 .claude/skills/coach/test-parse-log.py` and
  `python3 .claude/skills/coach/test-user-profile.py` → both still pass
  (this plan doesn't touch those files, but confirm no accidental breakage).
- [ ] `git log --oneline -8` shows the 6 commits from this plan in order.
- [ ] `git status` is clean (no untracked files besides the gitignored
  `dist/`).
