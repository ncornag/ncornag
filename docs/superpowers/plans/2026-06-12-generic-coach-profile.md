# Generic Coach via Athlete Profile — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **SINGLE COMMIT:** This whole plan lands as ONE commit. Do NOT commit per task. Tasks edit + verify only; the final task (Task 5) stages everything and makes one commit.

**Goal:** Make the `coach` skill generic by moving every athlete- and plan-specific value out of `coach/SKILL.md` and `coach/parse-log.py` into `running/data/user.md`, which `parse-log.py` reads at runtime.

**Architecture:** `user.md` becomes the athlete + plan profile (structured markdown). A new pure-stdlib `user_profile.py` in the coach skill parses the structured subset (zones, plan baseline, plan_start, hilly_elev, plan_file, gym_prefix); `parse-log.py` loads it in `main()` and populates its module-level constants. The coach reads the whole file as prose. Zero behavior change — output JSON must be identical to today.

**Tech Stack:** Python 3 stdlib only (no deps; system `python3` is 3.14); structured markdown; plain-assert tests via importlib.

---

## File structure

| File | Responsibility | Action |
| --- | --- | --- |
| `running/data/user.md` | Athlete + plan profile (was: just `log_dir`). | Rewrite |
| `.claude/skills/coach/user_profile.py` | Pure-stdlib parser: user.md → engine dict. | Create |
| `.claude/skills/coach/test-user-profile.py` | Plain-assert tests for the parser. | Create |
| `.claude/skills/coach/parse-log.py` | Loads the profile; constants come from it. | Edit |
| `.claude/skills/coach/test-parse-log.py` | `parse_gym_files` now takes a `gym_prefix`. | Edit |
| `.claude/skills/coach/SKILL.md` | Generic: reads the profile, no baked-in identity. | Edit |

**Why `user_profile.py` (not `profile.py`):** `profile` is a stdlib module name; a local `profile.py` risks shadowing/collision. `user_profile` is collision-free. Function: `read_profile(path)`. Mirrors the garmin skill's `config.py`/`test-config.py` pattern.

---

### Task 1: Rewrite `running/data/user.md` as the athlete profile

**Files:**
- Rewrite: `running/data/user.md`

This migrates the existing engine values (the 26-week `PLAN`, zone cutoffs, `plan_start`, `hilly_elev`, race, file names) into the profile, preserves the existing `log_dir`, and seeds the new prose sections. No commit.

- [ ] **Step 1: Overwrite `running/data/user.md` with exactly this content**

```markdown
# Athlete & training profile

<!-- Read in full by the coach skill as planning context. parse-log.py and the
     garmin skill parse the structured bits: the `key: value` lines and the two
     tables below (HR zones, Training plan). Hand-edit freely. -->

## Paths

- log_dir: /Users/ncornag/Library/CloudStorage/GoogleDrive-ncornag@gmail.com/My Drive/personal/running/log
- plan_file: dements-2026-plan.html
- gym_prefix: gimnasio-semana

## Athlete

- age: 57

Injury history — coach conservatively and never push through warning signs.
(Add specifics here: past injuries, niggles to watch, recovery constraints.)

## HR zones

Lab-calibrated. VT1 151, VT2 173. Z2 (135–151) is the athlete's aerobic focus.

| zone | from_bpm |
| Z1 | 0 |
| Z2 | 135 |
| Z3 | 152 |
| Z4 | 163 |
| Z5 | 174 |

- polarized_target: 80/20

## Goal race

- name: Marató dels Dements
- terrain: Serra d'Espadà

(Distance and elevation are the last row of the Training plan table below — 42.5 km, 3808 m D+; the race is plan week 26.)

## Equipment

_(Coach reads this when prescribing sessions. List shoes, watch / HR strap, poles, vest, and any treadmill or gym access.)_

## Terrain from home

_(Coach reads this when prescribing sessions. List the routes you can run from home with their distance and elevation — e.g. "River loop — 8 km, 40 m D+, flat"; "Hill repeats — 5 km, 300 m D+, trail".)_

## Training principles

- principle: smart beats heroic

(The plan is polarized ~80% easy / ~20% hard, minimal Z3. Vert specificity, power-hike practice, eccentric descents, back-to-back long days.)

## Training plan

- plan_start: 2026-05-11
- hilly_elev: 30

| week | km | elev |
| 1 | 25 | 0 |
| 2 | 25 | 0 |
| 3 | 21 | 0 |
| 4 | 22 | 0 |
| 5 | 23 | 80 |
| 6 | 17 | 30 |
| 7 | 28 | 300 |
| 8 | 33 | 500 |
| 9 | 38 | 700 |
| 10 | 25 | 350 |
| 11 | 45 | 1000 |
| 12 | 50 | 1200 |
| 13 | 52 | 1400 |
| 14 | 56 | 1600 |
| 15 | 32 | 500 |
| 16 | 45 | 1500 |
| 17 | 35 | 700 |
| 18 | 60 | 2000 |
| 19 | 38 | 800 |
| 20 | 68 | 2600 |
| 21 | 75 | 2900 |
| 22 | 65 | 2200 |
| 23 | 48 | 1400 |
| 24 | 28 | 600 |
| 25 | 22 | 300 |
| 26 | 42.5 | 3808 |
```

- [ ] **Step 2: Verify garmin's reader still finds `log_dir`**

Run: `python3 .claude/skills/garmin/test-config.py`
Expected: `OK` (config.py's `log_dir:` regex still matches the bulleted line under `## Paths`).

No commit.

---

### Task 2: Create `user_profile.py` parser + tests (TDD)

**Files:**
- Create: `.claude/skills/coach/user_profile.py`
- Test: `.claude/skills/coach/test-user-profile.py`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/coach/test-user-profile.py`:

```python
#!/usr/bin/env python3
"""Plain-assert tests for user_profile.py. Run: python3 test-user-profile.py"""
import importlib.util
import os
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "user_profile", os.path.join(HERE, "user_profile.py"))
up = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(up)

ZONES = "| Z1 | 0 |\n| Z2 | 135 |\n| Z3 | 152 |\n| Z4 | 163 |\n| Z5 | 174 |\n"
PLAN = "| 1 | 25 | 0 |\n| 2 | 17 | 30 |\n| 3 | 42.5 | 3808 |\n"
FULL = (
    "## Paths\n- plan_file: p.html\n- gym_prefix: gym-week\n\n"
    "## HR zones\n" + ZONES +
    "\n## Training plan\n- plan_start: 2026-05-11\n- hilly_elev: 30\n\n" + PLAN
)


def test_parse_zone_cutoffs():
    assert up.parse_zone_cutoffs(ZONES) == [135, 152, 163, 174]


def test_parse_plan_preserves_int_and_float():
    # "25" stays int, "42.5" stays float (so JSON output matches the old PLAN).
    assert up.parse_plan(PLAN) == [(25, 0), (17, 30), (42.5, 3808)]


def test_parse_plan_sorts_by_week():
    out_of_order = "| 3 | 5 | 0 |\n| 1 | 9 | 0 |\n| 2 | 7 | 0 |\n"
    assert up.parse_plan(out_of_order) == [(9, 0), (7, 0), (5, 0)]


def test_read_profile_happy_path():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write(FULL)
        prof = up.read_profile(p)
        assert prof["plan_file"] == "p.html"
        assert prof["gym_prefix"] == "gym-week"
        assert prof["plan_start"] == date(2026, 5, 11)
        assert prof["hilly_elev"] == 30
        assert prof["zone_cutoffs"] == [135, 152, 163, 174]
        assert prof["plan"] == [(25, 0), (17, 30), (42.5, 3808)]


def test_read_profile_missing_file_exits():
    with tempfile.TemporaryDirectory() as d:
        try:
            up.read_profile(os.path.join(d, "nope.md"))
            assert False, "expected SystemExit"
        except SystemExit:
            pass


def test_read_profile_missing_plan_exits():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("## Paths\n- plan_file: p.html\n- gym_prefix: g\n## HR zones\n" + ZONES
                    + "- plan_start: 2026-05-11\n- hilly_elev: 30\n")  # no plan table
        try:
            up.read_profile(p)
            assert False, "expected SystemExit"
        except SystemExit:
            pass


if __name__ == "__main__":
    test_parse_zone_cutoffs()
    test_parse_plan_preserves_int_and_float()
    test_parse_plan_sorts_by_week()
    test_read_profile_happy_path()
    test_read_profile_missing_file_exits()
    test_read_profile_missing_plan_exits()
    print("OK")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 .claude/skills/coach/test-user-profile.py`
Expected: FAIL — `FileNotFoundError`/`ModuleNotFoundError` (user_profile.py doesn't exist).

- [ ] **Step 3: Write the parser**

Create `.claude/skills/coach/user_profile.py`:

```python
"""Parse the athlete + training profile from running/data/user.md.

Pure stdlib so it is importable by tests and by parse-log.py without any
dependency. The coach skill reads the whole file as prose context; this parser
extracts only the structured values the engine computes with. Named
`user_profile` (not `profile`) to avoid shadowing the stdlib `profile` module."""
import re
from datetime import datetime
from pathlib import Path

_ZONE_ROW = re.compile(r"^\s*\|\s*(Z[1-5])\s*\|\s*(\d+)\s*\|\s*$", re.MULTILINE)
_PLAN_ROW = re.compile(
    r"^\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)\s*\|\s*$", re.MULTILINE)


def _num(s):
    """'25' -> int 25, '42.5' -> float 42.5 (preserves the old PLAN's types)."""
    s = s.strip()
    return float(s) if "." in s else int(s)


def _value(text, key):
    """Read a `key: value` line (optionally bulleted), or None if absent."""
    m = re.search(rf"^\s*[-*]?\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def parse_zone_cutoffs(text):
    """Z2..Z5 lower bounds (the hr_zone cutoffs) from the HR-zones table."""
    zones = {z: int(v) for z, v in _ZONE_ROW.findall(text)}
    return [zones[z] for z in ("Z2", "Z3", "Z4", "Z5") if z in zones]


def parse_plan(text):
    """List of (km, elev) ordered by week from the Training-plan table."""
    rows = [(int(w), _num(km), int(elev)) for w, km, elev in _PLAN_ROW.findall(text)]
    rows.sort(key=lambda r: r[0])
    return [(km, elev) for _, km, elev in rows]


def read_profile(config_path):
    """Read the structured engine values from the user.md at config_path.

    Raises SystemExit with a clear message if the file or a required
    field/table is missing or malformed."""
    path = Path(config_path)
    if not path.exists():
        raise SystemExit(
            f"missing {path} — create the athlete profile (see the coach skill).")
    text = path.read_text(encoding="utf-8")

    def need(key):
        v = _value(text, key)
        if v is None:
            raise SystemExit(f"{path}: missing required '{key}:' line")
        return v

    plan = parse_plan(text)
    cutoffs = parse_zone_cutoffs(text)
    if not plan:
        raise SystemExit(f"{path}: no Training plan table rows found")
    if len(cutoffs) != 4:
        raise SystemExit(f"{path}: HR zones table must define Z2..Z5 lower bounds")
    try:
        plan_start = datetime.strptime(need("plan_start"), "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"{path}: plan_start must be YYYY-MM-DD")
    return {
        "plan_file": need("plan_file"),
        "gym_prefix": need("gym_prefix"),
        "plan_start": plan_start,
        "hilly_elev": int(need("hilly_elev")),
        "zone_cutoffs": cutoffs,
        "plan": plan,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 .claude/skills/coach/test-user-profile.py`
Expected: `OK`

No commit.

---

### Task 3: Refactor `parse-log.py` to read the profile (zero behavior change)

**Files:**
- Modify: `.claude/skills/coach/parse-log.py`
- Modify: `.claude/skills/coach/test-parse-log.py`

- [ ] **Step 1: Capture the pre-refactor JSON baseline**

The engine output (minus the `generated` timestamp) must be identical after the refactor. Capture it now, while `parse-log.py` is still the original:

```bash
python3 .claude/skills/coach/parse-log.py --today 2026-06-12 \
  | python3 -c "import sys,json; d=json.load(sys.stdin); d.pop('generated'); print(json.dumps(d,sort_keys=True))" \
  > /tmp/coach-baseline.json
wc -c /tmp/coach-baseline.json
```
Expected: a non-empty byte count (the baseline is saved).

- [ ] **Step 2: Add the profile import**

In `parse-log.py`, the imports end with `from datetime import date, datetime, timedelta`. Add the profile import right after it (local module, like garmin's `from config import ...`):

```python
from datetime import date, datetime, timedelta

from user_profile import read_profile
```

- [ ] **Step 3: Replace the hardcoded plan/zone constants with profile-fed placeholders**

Replace EXACTLY:
```python
PLAN_START = date(2026, 5, 11)   # Monday of plan week 1
TOTAL_WEEKS = 26

# Planned weekly volume (km) and elevation (m D+). Canonical baseline - mirrors
# the weeks[] array in dements-2026-plan.html. Index 0 == week 1.
PLAN = [
    (25, 0), (25, 0), (21, 0), (22, 0), (23, 80), (17, 30),
    (28, 300), (33, 500), (38, 700), (25, 350), (45, 1000), (50, 1200),
    (52, 1400), (56, 1600), (32, 500), (45, 1500), (35, 700), (60, 2000),
    (38, 800), (68, 2600), (75, 2900), (65, 2200), (48, 1400), (28, 600),
    (22, 300), (42.5, 3808),
]
```
with:
```python
# Athlete- and plan-specific values are loaded from the profile
# (running/data/user.md) by main(); the coach skill itself is generic.
PLAN_START = None     # date — profile plan_start
TOTAL_WEEKS = None    # int — len(PLAN)
PLAN = None           # list[(km, elev)] — profile Training-plan table
ZONE_CUTOFFS = None   # [int,int,int,int] — profile HR-zone Z2..Z5 lower bounds
```

- [ ] **Step 4: Make `hr_zone` use the profile cutoffs**

Replace EXACTLY:
```python
def hr_zone(hr):
    """Map an average HR to a lab-calibrated zone (VT1 151, VT2 173)."""
    if hr is None:
        return None
    if hr < 135:
        return "Z1"
    if hr < 152:
        return "Z2"
    if hr < 163:
        return "Z3"
    if hr < 174:
        return "Z4"
    return "Z5"
```
with:
```python
def hr_zone(hr):
    """Map an average HR to a zone using the profile's ZONE_CUTOFFS."""
    if hr is None:
        return None
    for i, cutoff in enumerate(ZONE_CUTOFFS):
        if hr < cutoff:
            return ZONES[i]
    return ZONES[-1]
```

- [ ] **Step 5: Make `parse_gym_files` take a `gym_prefix`; drop the module-level regex**

Replace EXACTLY:
```python
_GYM_FILE_RE = re.compile(r"gimnasio-semana(\d+)(?:-(\d+))?\.html$")


def parse_gym_files(running_dir):
    """Map each plan week to its gym HTML file.

    Scans running/gimnasio-semana*.html. A single-week file
    (gimnasio-semana3.html) maps week 3; a range file (gimnasio-semana3-5.html)
    maps weeks 3, 4 and 5. Files are processed in sorted order so overlaps
    resolve deterministically (later filename wins).
    """
    mapping = {}
    for path in sorted(glob.glob(os.path.join(running_dir, "gimnasio-semana*.html"))):
        m = _GYM_FILE_RE.search(os.path.basename(path))
```
with:
```python
def parse_gym_files(running_dir, gym_prefix):
    """Map each plan week to its gym HTML file.

    Scans running/<gym_prefix>*.html. A single-week file (<prefix>3.html) maps
    week 3; a range file (<prefix>3-5.html) maps weeks 3, 4 and 5. Files are
    processed in sorted order so overlaps resolve deterministically (later
    filename wins).
    """
    file_re = re.compile(re.escape(gym_prefix) + r"(\d+)(?:-(\d+))?\.html$")
    mapping = {}
    for path in sorted(glob.glob(os.path.join(running_dir, gym_prefix + "*.html"))):
        m = file_re.search(os.path.basename(path))
```

- [ ] **Step 6: Set `HRE_HILLY_ELEV` from the profile**

Replace EXACTLY:
```python
HRE_HILLY_ELEV = 30   # m D+ — matches the plan's "flat" cutoff
```
with:
```python
HRE_HILLY_ELEV = None   # m D+ — set from the profile's hilly_elev in main()
```

- [ ] **Step 7: Load the profile in `main()` and feed the globals**

Replace EXACTLY:
```python
    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today \
        else date.today()

    errors = []
    activities = read_activities(data_dir, errors)
```
with:
```python
    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today \
        else date.today()

    prof = read_profile(os.path.join(repo, "running", "data", "user.md"))
    global PLAN_START, TOTAL_WEEKS, PLAN, ZONE_CUTOFFS, HRE_HILLY_ELEV
    PLAN_START = prof["plan_start"]
    PLAN = prof["plan"]
    TOTAL_WEEKS = len(PLAN)
    ZONE_CUTOFFS = prof["zone_cutoffs"]
    HRE_HILLY_ELEV = prof["hilly_elev"]

    errors = []
    activities = read_activities(data_dir, errors)
```

- [ ] **Step 8: Use the profile's `plan_file` and `gym_prefix` in `main()`**

Replace EXACTLY:
```python
    running_dir = os.path.join(repo, "running")
    html_path = os.path.join(running_dir, "dements-2026-plan.html")
    plan_days_by_week = parse_plan_days(html_path)
    gym_files = parse_gym_files(running_dir)
```
with:
```python
    running_dir = os.path.join(repo, "running")
    html_path = os.path.join(running_dir, prof["plan_file"])
    plan_days_by_week = parse_plan_days(html_path)
    gym_files = parse_gym_files(running_dir, prof["gym_prefix"])
```

- [ ] **Step 9: Genericize the remaining docstrings / description**

9a. Module docstring — replace EXACTLY:
```python
"""parse-log.py - Aggregate logged TCX activities against the Dements 2026 plan.

Part of the coach skill. This script does the deterministic work so Claude does
not have to: it reads the monthly activity CSVs (refreshed separately by the
garmin skill), maps every logged activity onto a plan week, classifies average
heart rate into a lab-calibrated training zone, aggregates per week, and prints
a JSON summary on stdout for the skill to act on. All progress/errors go to
stderr.

Steps:
  1. Read every running/data/<YYYY-MM>.csv.
  2. Map each activity to a plan week (week 1 = Mon 2026-05-11; week N spans
     [start+(N-1)*7, +6d]). Activities outside the plan range are ignored.
  3. Classify average HR into Z1-Z5 from the VT1/VT2 zones in running-zones.html.
  4. Aggregate per week and emit JSON.
```
with:
```python
"""parse-log.py - Aggregate logged activities against the athlete's training plan.

Part of the coach skill. This script does the deterministic work so Claude does
not have to: it reads the monthly activity CSVs (refreshed separately by the
garmin skill), maps every logged activity onto a plan week, classifies average
heart rate into a training zone, aggregates per week, and prints a JSON summary
on stdout for the skill to act on. Athlete- and plan-specific values (zones,
plan start, the weekly baseline, file names) come from the profile in
running/data/user.md. All progress/errors go to stderr.

Steps:
  1. Read every running/data/<YYYY-MM>.csv.
  2. Map each activity to a plan week (week 1 starts at the profile's plan_start;
     week N spans [start+(N-1)*7, +6d]). Activities outside the plan range are
     ignored.
  3. Classify average HR into zones from the profile's HR-zone cutoffs.
  4. Aggregate per week and emit JSON.
```

9b. `parse_plan_days` docstring — replace EXACTLY:
```python
    """Extract the planned day grid for each week from dements-2026-plan.html.
```
with:
```python
    """Extract the planned day grid for each week from the plan file.
```

9c. argparse description — replace EXACTLY:
```python
    ap = argparse.ArgumentParser(description="Aggregate TCX logs vs the Dements plan.")
```
with:
```python
    ap = argparse.ArgumentParser(description="Aggregate logged activities vs the training plan.")
```

- [ ] **Step 10: Update `test-parse-log.py` for the new `parse_gym_files` signature**

In `.claude/skills/coach/test-parse-log.py`, replace EXACTLY:
```python
        m = pl.parse_gym_files(d)
        assert m == {3: "gimnasio-semana3-5.html",
```
with:
```python
        m = pl.parse_gym_files(d, "gimnasio-semana")
        assert m == {3: "gimnasio-semana3-5.html",
```
and replace EXACTLY:
```python
        assert pl.parse_gym_files(d) == {}
```
with:
```python
        assert pl.parse_gym_files(d, "gimnasio-semana") == {}
```

- [ ] **Step 11: Run the unit tests**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: `OK`
Run: `python3 .claude/skills/coach/test-user-profile.py`
Expected: `OK`

- [ ] **Step 12: Verify zero behavior change against the baseline**

```bash
python3 .claude/skills/coach/parse-log.py --today 2026-06-12 \
  | python3 -c "import sys,json; d=json.load(sys.stdin); d.pop('generated'); print(json.dumps(d,sort_keys=True))" \
  > /tmp/coach-after.json
diff /tmp/coach-baseline.json /tmp/coach-after.json && echo "PARITY OK"
```
Expected: no diff output, then `PARITY OK`. If there is ANY diff, the migration changed behavior — investigate (likely an int/float mismatch in the plan table or a zone-cutoff/plan-start discrepancy) and fix before proceeding.

- [ ] **Step 13: Confirm no athlete/plan specifics remain in parse-log.py**

```bash
grep -nE "2026-05-11|dements|Dements|gimnasio-semana|running-zones|\(25, 0\)|VT1 151" .claude/skills/coach/parse-log.py || echo "(clean)"
```
Expected: `(clean)`.

No commit.

---

### Task 4: Genericize `coach/SKILL.md`

**Files:**
- Modify: `.claude/skills/coach/SKILL.md`

Strip every athlete/race/zone specific and the hardcoded file names; the coach reads them from the profile. FIRST read `.claude/skills/coach/SKILL.md` in full, then apply the edits below.

- [ ] **Step 1: Description (frontmatter) — replace EXACTLY**
```
description: Acts as the athlete's trail-running coach for the Dements 2026 race. Use when the user runs /coach, wants to sync their running log, get feedback on a training week, give feedback to their coach, ask a training question, or update the gym programme. Syncs logged TCX activity into running/dements-2026-plan.html, recalls past feedback from running/coach-log.md, asks targeted check-in questions, applies confirmed run/gym adjustments, maintains per-week gym tables, and writes coach commentary.
```
with:
```
description: Acts as the athlete's trail-running coach, reading the athlete + training profile from running/data/user.md (goal race, HR zones, equipment, terrain, principles, and the week-by-week plan). Use when the user runs /coach, wants to sync their running log, get feedback on a training week, give feedback to their coach, ask a training question, or update the gym programme. Syncs logged activity into the plan file named in the profile, recalls past feedback from running/coach-log.md, asks targeted check-in questions, applies confirmed run/gym adjustments, maintains per-week gym tables, and writes coach commentary.
```

- [ ] **Step 2: Opening identity — replace EXACTLY**
```
You are the athlete's trail-running coach for the **Marató dels Dements** (42.5 km,
3,808 m D+, Serra d'Espadà). Each run of this skill is a coaching session: sync the
logged data, recall what the athlete told you before, ask how things are going,
answer their questions, adjust the plan (with their OK), and record the exchange.
```
with:
```
You are the athlete's trail-running coach. **Read the athlete + training profile in
`running/data/user.md` first** — it holds the athlete (age, injury history), the goal
race, the HR zones, equipment, terrain from home, training principles, and the
week-by-week plan; coach from it and never assume facts it doesn't state. Each run of
this skill is a coaching session: sync the logged data, recall what the athlete told
you before, ask how things are going, answer their questions, adjust the plan (with
their OK), and record the exchange.

Throughout this skill, **"the plan file"** means the HTML named by `plan_file` in the
profile, and **the gym files** are `<gym_prefix><N>.html` (both from the profile).
```

- [ ] **Step 3: Files table — replace EXACTLY**
```
| `.claude/skills/coach/parse-log.py` | Data engine — run it, use its JSON. Never recompute its outputs by hand. |
| `running/coach-log.md` | Athlete-feedback journal — your memory. Read every run, append/update each run. |
| `running/dements-2026-plan.html` | The plan — the file you edit. |
| `running/running-zones.html` | The athlete's lab HR zones — read for coach analysis. |
| `running/gimnasio-semana<N>.html` | Per-week gym tables (range-named when identical, e.g. `gimnasio-semana3-5.html`). |
```
with:
```
| `running/data/user.md` | The athlete + training profile — read it in full every run; the engine parses its structured tables. |
| `.claude/skills/coach/parse-log.py` | Data engine — run it, use its JSON. Never recompute its outputs by hand. |
| `running/coach-log.md` | Athlete-feedback journal — your memory. Read every run, append/update each run. |
| the plan file (profile `plan_file`) | The plan — the file you edit. |
| `running/running-zones.html` | A rendered view of the athlete's lab HR zones (source of truth is the profile). |
| the gym files (profile `gym_prefix`) | Per-week gym tables, `<gym_prefix><N>.html` (range-named when identical, e.g. `<gym_prefix>3-5.html`). |
```

- [ ] **Step 4: Athlete/principle line — replace EXACTLY**
```
The athlete is **57, with an injury history**; the plan's own principle is
"smart beats heroic." Coach accordingly — conservative, never push through
warning signs.
```
with:
```
Read the athlete's age, injury history, and guiding **principle** from the profile
(`running/data/user.md`). Coach to them — conservative, never push through warning
signs.
```

- [ ] **Step 5: Coach Voice — race + zones — replace EXACTLY**
```
Write as an experienced trail/ultra coach who knows this athlete and this race
(Marató dels Dements — 42.5 km, 3,808 m D+, Serra d'Espadà). Be direct,
specific, and encouraging; never generic.

- **Use the lab zones** from `running-zones.html`: Z1 `<135`, **Z2 135–151**
  (the athlete's focus), Z3 151–162, Z4 162–173, Z5 `>173`; VT1 151, VT2 173.
```
with:
```
Write as an experienced trail/ultra coach who knows this athlete and their goal
race (read the **goal race** — name, terrain, distance/elevation from the plan's
final week — from the profile). Be direct, specific, and encouraging; never generic.

- **Use the HR zones from the profile** (`running/data/user.md`): the zone table
  gives each zone's lower bound, plus VT1/VT2. Z2 is the athlete's easy-aerobic focus.
- **Factor in the athlete's equipment and terrain-from-home** (both in the profile)
  when prescribing sessions — match vert/distance targets to routes they can actually
  run from home, and to the gear they have.
```

- [ ] **Step 6: Replace remaining hardcoded plan-file references**

Replace every remaining literal `running/dements-2026-plan.html` in the file with `the plan file`. There are several (in the workflow intro line "Steps C1–C8 edit …", step C1, the C8 `git diff …` line, etc.). Use a global replace:

```bash
cd /Users/ncornag/Dropbox/workspace/personal/profile
python3 - <<'PY'
import pathlib
p = pathlib.Path(".claude/skills/coach/SKILL.md")
t = p.read_text()
t = t.replace("`running/dements-2026-plan.html`", "the plan file")
t = t.replace("running/dements-2026-plan.html", "the plan file")
p.write_text(t)
print("replaced")
PY
```

- [ ] **Step 7: Genericize the gym-file naming in the Gym programming + Notes sections**

The Gym programming section names files as `gimnasio-semana<N>.html` / `gimnasio-semana3-5.html` and the foundation template `gimnasio-semana3-5.html`. Replace the naming convention references so they read from the profile's `gym_prefix`, keeping the current value as the example. Apply:

```bash
cd /Users/ncornag/Dropbox/workspace/personal/profile
python3 - <<'PY'
import pathlib
p = pathlib.Path(".claude/skills/coach/SKILL.md")
t = p.read_text()
# gym file naming -> profile gym_prefix (current value kept as the example)
t = t.replace("`gimnasio-semana<N>.html`", "`<gym_prefix><N>.html`")
t = t.replace("`gimnasio-semana<N-M>.html`", "`<gym_prefix><N-M>.html`")
t = t.replace("`gimnasio-semana3-5.html`", "`<gym_prefix>3-5.html` (e.g. `gimnasio-semana3-5.html`)")
p.write_text(t)
print("replaced")
PY
```

- [ ] **Step 8: Genericize the `running-zones.html` zone reference in Notes/engine prose**

Search for any remaining instruction to read zones from `running-zones.html` and point it at the profile. Replace EXACTLY (in the Notes section, if present — the zone-boundary list):
```
- **Use the lab zones** from `running-zones.html`
```
(If this exact text no longer exists after Step 5, skip — Step 5 already handled it.) Then confirm via the grep in Step 9.

- [ ] **Step 9: Verify no athlete/race/zone specifics survive in SKILL.md**

```bash
grep -niE "dements|maró|marató|espad|\b57\b|injury history|smart beats heroic|<135|135–151|VT1 151|VT2 173|gimnasio-semana[0-9]" .claude/skills/coach/SKILL.md || echo "(clean)"
```
Expected: `(clean)`. (The string `gimnasio-semana` may still appear ONLY inside the example `e.g. \`gimnasio-semana3-5.html\`` from Step 7 — that example is allowed; the regex above intentionally flags only `gimnasio-semana<digit>` which that example contains, so if it fires, confirm the only hit is that single allowed example and move on.)

Also confirm the profile is referenced:
```bash
grep -c "running/data/user.md" .claude/skills/coach/SKILL.md
```
Expected: a count ≥ 3.

No commit.

---

### Task 5: Final parity gate + single commit

**Files:** none new — this stages and commits everything from Tasks 1–4.

- [ ] **Step 1: Full test + parity sweep**

```bash
cd /Users/ncornag/Dropbox/workspace/personal/profile
python3 .claude/skills/coach/test-user-profile.py
python3 .claude/skills/coach/test-parse-log.py
python3 .claude/skills/garmin/test-config.py
python3 .claude/skills/coach/parse-log.py --today 2026-06-12 \
  | python3 -c "import sys,json; d=json.load(sys.stdin); d.pop('generated'); print(json.dumps(d,sort_keys=True))" \
  > /tmp/coach-after.json
diff /tmp/coach-baseline.json /tmp/coach-after.json && echo "PARITY OK"
```
Expected: three `OK` lines and `PARITY OK` with no diff.

- [ ] **Step 2: Stage exactly the feature's files and commit once**

```bash
cd /Users/ncornag/Dropbox/workspace/personal/profile
git add running/data/user.md \
        .claude/skills/coach/user_profile.py \
        .claude/skills/coach/test-user-profile.py \
        .claude/skills/coach/parse-log.py \
        .claude/skills/coach/test-parse-log.py \
        .claude/skills/coach/SKILL.md \
        docs/superpowers/specs/2026-06-12-generic-coach-profile-design.md \
        docs/superpowers/plans/2026-06-12-generic-coach-profile.md
git commit -m "feat(coach): make the coach generic by reading the athlete profile from user.md"
git show --stat HEAD
```
Expected: one commit containing the 8 files; `git status --short` clean afterward.

---

## Self-review

**Spec coverage:**
- Fully generic engine (zones, plan_start, total_weeks, plan baseline, race ids, file names → user.md; parse-log reads all) → Tasks 1, 3. ✔
- Structured markdown format → Task 1 schema, Task 2 parser. ✔
- One file holds everything incl. existing log_dir → Task 1 (log_dir preserved; garmin test in 1.2). ✔
- Engine parses only computed values; equipment/terrain are prose → Task 1 sections + Task 2 parser scope. ✔
- New pure-stdlib reader + test, mirrors config.py pattern → Task 2. ✔
- running-zones.html stays; reference points to profile → Task 4 (Files row, Step 5/8). ✔
- dements-2026-plan.html stays; baseline relocates → Tasks 1, 3, 4. ✔
- garmin unchanged beyond reading log_dir → verified Task 1.2. ✔
- Zero-behavior-change parity → Task 3 steps 1 & 12, Task 5 step 1. ✔
- Coach reads equipment/terrain for planning → Task 4 step 5 bullet. ✔
- Tests: test-user-profile.py (new), test-parse-log.py green → Tasks 2, 3. ✔

**Placeholder scan:** The `_(…)_` prose in user.md Equipment/Terrain are intended file content (athlete fills them), not plan placeholders — every plan step shows exact content/commands.

**Type/name consistency:** `read_profile` defined in Task 2, imported in Task 3 step 2. Dict keys (`plan_file`, `gym_prefix`, `plan_start`, `hilly_elev`, `zone_cutoffs`, `plan`) match between Task 2's return and Task 3 step 7/8 usage. `parse_gym_files(running_dir, gym_prefix)` signature matches between Task 3 step 5 and the Task 3 step 10 test update. `ZONE_CUTOFFS`/`HRE_HILLY_ELEV`/`PLAN`/`PLAN_START`/`TOTAL_WEEKS` names consistent across steps 3, 4, 6, 7. Module named `user_profile` consistently (file, import, test loader).
```
