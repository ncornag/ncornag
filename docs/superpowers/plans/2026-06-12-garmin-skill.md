# Garmin Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the Garmin data-fetch out of the `coach` skill into its own user-invocable `garmin` skill that downloads `.fit`+`.tcx` on/after a date and rebuilds the coach CSVs.

**Architecture:** A new `garmin` skill (SKILL.md + the moved `download-garmin.py` + a pure `config.py`) owns all Garmin knowledge — login, the archive path (read from `running/data/user.md`), and the CSV rebuild. `coach/parse-log.py` becomes pure CSV aggregation; the coach's first step invokes the `garmin` skill, then runs the engine.

**Tech Stack:** Python 3 (stdlib + `garminconnect`, `garmin-fit-sdk`, `curl_cffi` in a skill-local venv); Markdown SKILL files; plain-assert tests via `importlib`.

---

## File structure

| File | Responsibility | Action |
| --- | --- | --- |
| `running/data/user.md` | Per-machine archive path (`log_dir:`). | Create |
| `.claude/skills/garmin/config.py` | Pure parser: read `log_dir` from `user.md`. Importable without the venv. | Create |
| `.claude/skills/garmin/test-config.py` | Plain-assert tests for the parser. | Create |
| `.claude/skills/garmin/download-garmin.py` | Garmin download (`.fit`+`.tcx`) + CSV rebuild. | Move from `running/` + edit |
| `.claude/skills/garmin/SKILL.md` | User-facing `garmin` skill doc. | Create |
| `.claude/skills/coach/parse-log.py` | Pure CSV aggregation (no Garmin). | Edit (decouple) |
| `.claude/skills/coach/SKILL.md` | Coach: invoke `garmin`, then the engine. | Edit (A1 + Files) |
| `.gitignore` | Ignore the skill-local venv. | Edit |
| `build.sh` | Comment now that the script left `running/`. | Edit (comment) |

`config.py` is split out from `download-garmin.py` on purpose: `download-garmin.py` bootstraps a venv and imports third-party packages at module load, so it cannot be imported by a unit test. `config.py` is pure stdlib and is the only piece that needs testing.

---

### Task 1: Config file `running/data/user.md`

**Files:**
- Create: `running/data/user.md`

- [ ] **Step 1: Create the config file**

```markdown
# Running data config

Per-machine paths for the garmin skill, kept out of the committed scripts.

- log_dir: /Users/ncornag/Library/CloudStorage/GoogleDrive-ncornag@gmail.com/My Drive/personal/running/log
```

- [ ] **Step 2: Commit**

```bash
git add running/data/user.md
git commit -m "feat(running): add user.md holding the activity-log archive path"
```

---

### Task 2: Pure config parser + test

**Files:**
- Create: `.claude/skills/garmin/config.py`
- Test: `.claude/skills/garmin/test-config.py`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/garmin/test-config.py`:

```python
#!/usr/bin/env python3
"""Plain-assert tests for config.py. Run: python3 test-config.py"""
import importlib.util
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "garmin_config", os.path.join(HERE, "config.py"))
cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg)


def test_parse_log_dir_bulleted():
    assert cfg.parse_log_dir("- log_dir: /a/b/c\n") == "/a/b/c"


def test_parse_log_dir_plain():
    assert cfg.parse_log_dir("log_dir: /x/y\n") == "/x/y"


def test_parse_log_dir_path_with_spaces():
    text = "# config\n- log_dir: /Users/me/My Drive/running/log\n"
    assert cfg.parse_log_dir(text) == "/Users/me/My Drive/running/log"


def test_parse_log_dir_missing_key():
    assert cfg.parse_log_dir("# config\nno key here\n") is None


def test_read_log_dir_missing_file_exits():
    with tempfile.TemporaryDirectory() as d:
        try:
            cfg.read_log_dir(os.path.join(d, "user.md"))
            assert False, "expected SystemExit for a missing file"
        except SystemExit:
            pass


def test_read_log_dir_happy_path():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("- log_dir: /tmp/log\n")
        assert cfg.read_log_dir(p) == "/tmp/log"


if __name__ == "__main__":
    test_parse_log_dir_bulleted()
    test_parse_log_dir_plain()
    test_parse_log_dir_path_with_spaces()
    test_parse_log_dir_missing_key()
    test_read_log_dir_missing_file_exits()
    test_read_log_dir_happy_path()
    print("OK")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 .claude/skills/garmin/test-config.py`
Expected: FAIL — `FileNotFoundError`/`ModuleNotFoundError` because `config.py` does not exist yet.

- [ ] **Step 3: Write the parser**

Create `.claude/skills/garmin/config.py`:

```python
"""Read per-machine config for the garmin skill from running/data/user.md.

Kept separate from download-garmin.py so the parser is importable by tests
without triggering that script's venv bootstrap. Pure stdlib."""
import re
from pathlib import Path

_LOG_DIR_RE = re.compile(r"^\s*[-*]?\s*log_dir\s*:\s*(.+?)\s*$", re.MULTILINE)


def parse_log_dir(text):
    """Return the log_dir value from user.md contents, or None if absent."""
    m = _LOG_DIR_RE.search(text)
    return m.group(1).strip() if m else None


def read_log_dir(config_path):
    """Read the log_dir path from the user.md at config_path.

    Raises SystemExit with a clear message if the file or the key is missing."""
    path = Path(config_path)
    if not path.exists():
        raise SystemExit(
            f"missing {path} — create it with a line:\n"
            f"  log_dir: /path/to/your/activity/log")
    value = parse_log_dir(path.read_text(encoding="utf-8"))
    if not value:
        raise SystemExit(
            f"no 'log_dir:' line in {path} — add e.g.\n"
            f"  log_dir: /path/to/your/activity/log")
    return value
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 .claude/skills/garmin/test-config.py`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/garmin/config.py .claude/skills/garmin/test-config.py
git commit -m "feat(garmin): add config parser for the activity-log archive path"
```

---

### Task 3: Move the download script + repoint paths + wire config + venv hygiene

**Files:**
- Move: `running/download-garmin.py` → `.claude/skills/garmin/download-garmin.py`
- Modify: the moved file (path constants, LOG_DIR, usage docstring)
- Modify: `.gitignore`
- Modify: `build.sh` (comment)
- Delete: `running/.venv/`

- [ ] **Step 1: Move the file with git**

```bash
git mv running/download-garmin.py .claude/skills/garmin/download-garmin.py
```

- [ ] **Step 2: Repoint the venv/REPO constants**

In `.claude/skills/garmin/download-garmin.py`, replace:

```python
REPO = Path(__file__).resolve().parent.parent          # .../profile
RUNNING_DIR = Path(__file__).resolve().parent          # .../profile/running
VENV_DIR = RUNNING_DIR / ".venv"
```

with:

```python
SKILL_DIR = Path(__file__).resolve().parent            # .../.claude/skills/garmin
REPO = Path(__file__).resolve().parents[3]             # .../profile
VENV_DIR = SKILL_DIR / ".venv"
```

(`parents[3]` walks garmin → skills → .claude → profile. `RUNNING_DIR` is removed; it was only used for `VENV_DIR`.)

- [ ] **Step 3: Wire LOG_DIR to the config parser**

In the same file, the third-party import section currently begins:

```python
from garminconnect import Garmin
from garmin_fit_sdk import Decoder, Stream
```

Add the config import immediately after those two lines:

```python
from garminconnect import Garmin
from garmin_fit_sdk import Decoder, Stream

from config import read_log_dir
```

(`config.py` is a stdlib sibling; `sys.path[0]` is the script dir when run, so `import config` resolves both before and after the venv re-exec.)

Then replace the hardcoded archive block:

```python
LOG_DIR = Path("/Users/ncornag/Library/CloudStorage/"
               "GoogleDrive-ncornag@gmail.com/My Drive/personal/running/log")
DATA_DIR = REPO / "running" / "data"
TOKEN_STORE = os.path.expanduser("~/.garminconnect")
```

with:

```python
DATA_DIR = REPO / "running" / "data"
LOG_DIR = Path(read_log_dir(DATA_DIR / "user.md"))
TOKEN_STORE = os.path.expanduser("~/.garminconnect")
```

- [ ] **Step 4: Update the script's own usage docstring**

Near the top of the file the docstring has `python3 download-garmin.py` examples and a venv-bootstrap comment mentioning `running/.venv`. Update the run examples to the new path and the bootstrap comment. Replace:

```python
itself inside that venv, so plain `python3 download-garmin.py` just works.

Usage:
  python3 download-garmin.py                       # from 2026-01-01 to today
  python3 download-garmin.py --start 2026-05-01    # custom start date
  python3 download-garmin.py --end 2026-06-30      # custom end date
  python3 download-garmin.py --no-download          # only rebuild CSVs from existing .fit
  python3 download-garmin.py --no-csv               # only download, skip CSV build
```

with:

```python
itself inside that venv, so plain `python3 download-garmin.py` just works.

Usage:
  python3 .claude/skills/garmin/download-garmin.py                    # 2026-01-01 to today
  python3 .claude/skills/garmin/download-garmin.py --start 2026-05-01 # custom start date
  python3 .claude/skills/garmin/download-garmin.py --end 2026-06-30   # custom end date
  python3 .claude/skills/garmin/download-garmin.py --no-download      # only rebuild CSVs
  python3 .claude/skills/garmin/download-garmin.py --no-csv           # only download
```

And replace the venv-bootstrap comment:

```python
# Re-exec inside running/.venv with the required third-party deps installed.
```

with:

```python
# Re-exec inside the skill-local .venv with the required third-party deps installed.
```

- [ ] **Step 5: Update `.gitignore` (before the new venv is created)**

Replace in `.gitignore`:

```
# Auto-managed venv for running/download-garmin.py
running/.venv/
```

with:

```
# Auto-managed venv for the garmin skill's download-garmin.py
.claude/skills/garmin/.venv/
```

- [ ] **Step 6: Update the `build.sh` comment**

Replace in `build.sh`:

```bash
# Only the running/ *pages* ship; raw data (running/data/*.csv), the
# download-garmin.py helper, and coach-log.md stay in the repo but are never uploaded.
```

with:

```bash
# Only the running/ *pages* ship; raw data (running/data/*.csv) and coach-log.md
# stay in the repo but are never uploaded. The garmin skill (and its
# download-garmin.py) lives under .claude/ and is never part of the build.
```

- [ ] **Step 7: Remove the orphaned venv**

```bash
rm -rf running/.venv
```

- [ ] **Step 8: Verify the move — rebuild CSVs from existing `.fit` and confirm zero diff**

Run (Drive must be online; this creates the skill-local venv on first run, then rebuilds the 2026 CSVs from the `.fit` already on disk):

```bash
python3 .claude/skills/garmin/download-garmin.py --no-download
git diff --stat running/data
```

Expected: the command prints `Wrote N activities to .../tcx-2026-*.csv` for each 2026 month, and `git diff --stat running/data` shows **no changes** (byte-identical rebuild → config + paths wired correctly). If Drive is offline, the command prints no "Wrote" lines and also leaves the CSVs unchanged.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(garmin): move download-garmin.py into the garmin skill and read the archive path from user.md"
```

---

### Task 4: Download `.tcx` alongside `.fit`

**Files:**
- Modify: `.claude/skills/garmin/download-garmin.py` (`fit_filename` → `activity_basename`, `download_all` loop)

- [ ] **Step 1: Verify the TCX format enum exists**

Run:

```bash
.claude/skills/garmin/.venv/bin/python -c "from garminconnect import Garmin; print([f.name for f in Garmin.ActivityDownloadFormat])"
```

Expected: a list that includes `'TCX'` and `'ORIGINAL'`. (If the member is named differently in this version, use that name in Step 3.)

- [ ] **Step 2: Rename the filename helper to a base (extension-less) stem**

In `download-garmin.py`, replace:

```python
def fit_filename(a: dict) -> str:
    """Build the coach-convention name: YYYY-MM-DD-HH-MM_<Type>.fit."""
    dt = parse_start(a)
    type_key = (a.get("activityType") or {}).get("typeKey", "")
    return f"{dt:%Y-%m-%d-%H-%M}_{suffix_for(type_key)}.fit"
```

with:

```python
def activity_basename(a: dict) -> str:
    """Coach-convention stem WITHOUT extension: YYYY-MM-DD-HH-MM_<Type>."""
    dt = parse_start(a)
    type_key = (a.get("activityType") or {}).get("typeKey", "")
    return f"{dt:%Y-%m-%d-%H-%M}_{suffix_for(type_key)}"
```

- [ ] **Step 3: Download both formats in `download_all`, each skipping existing files**

Replace the whole `download_all` body. Current:

```python
def download_all(start: date, end: date, no_prompt: bool = False) -> int:
    client = login(no_prompt=no_prompt)
    activities = client.get_activities_by_date(start.isoformat(), end.isoformat())
    print(f"Garmin returned {len(activities)} activities "
          f"in {start}..{end}")
    new = 0
    for a in activities:
        try:
            name = fit_filename(a)
        except Exception as exc:              # noqa: BLE001 - skip unparseable
            print(f"  skip activity {a.get('activityId')}: {exc}")
            continue
        year_dir = LOG_DIR / f"{parse_start(a):%Y}"
        year_dir.mkdir(parents=True, exist_ok=True)
        dest = year_dir / name
        if dest.exists():
            continue                          # already downloaded
        blob = client.download_activity(
            a["activityId"], dl_fmt=ActivityDownloadFormat.ORIGINAL)
        dest.write_bytes(extract_fit(blob))
        print(f"  downloaded {name}")
        new += 1
    print(f"Downloaded {new} new .fit file(s)")
    return new
```

New:

```python
def download_all(start: date, end: date, no_prompt: bool = False) -> int:
    client = login(no_prompt=no_prompt)
    activities = client.get_activities_by_date(start.isoformat(), end.isoformat())
    print(f"Garmin returned {len(activities)} activities "
          f"in {start}..{end}")
    # (extension, Garmin format, post-processor). ORIGINAL ships a zip holding
    # the .fit; TCX is returned as raw XML, so it is written through unchanged.
    formats = [
        (".fit", ActivityDownloadFormat.ORIGINAL, extract_fit),
        (".tcx", ActivityDownloadFormat.TCX, lambda b: b),
    ]
    new = 0
    for a in activities:
        try:
            base = activity_basename(a)
        except Exception as exc:              # noqa: BLE001 - skip unparseable
            print(f"  skip activity {a.get('activityId')}: {exc}")
            continue
        year_dir = LOG_DIR / f"{parse_start(a):%Y}"
        year_dir.mkdir(parents=True, exist_ok=True)
        for ext, fmt, post in formats:
            dest = year_dir / f"{base}{ext}"
            if dest.exists():
                continue                      # already downloaded
            blob = client.download_activity(a["activityId"], dl_fmt=fmt)
            dest.write_bytes(post(blob))
            print(f"  downloaded {dest.name}")
            new += 1
    print(f"Downloaded {new} new file(s)")
    return new
```

- [ ] **Step 4: Verify no stale references to the old helper name**

Run:

```bash
grep -n "fit_filename" .claude/skills/garmin/download-garmin.py
```

Expected: **no output** (the only caller was inside `download_all`, now updated).

- [ ] **Step 5: Verify against real Garmin data**

This step is network-bound — run it against the user's Garmin account. Because 2026 already has paired `.fit`+`.tcx` for every activity, a re-run of an already-synced range must download **nothing**:

```bash
python3 .claude/skills/garmin/download-garmin.py --start 2026-01-01 --end 2026-06-12 --no-csv
```

Expected: `Downloaded 0 new file(s)` (every `.fit` and `.tcx` already on disk is skipped). To confirm a fresh `.tcx` would be written, this is exercised naturally on the next genuinely-new activity; do not fabricate one.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/garmin/download-garmin.py
git commit -m "feat(garmin): download .tcx alongside .fit, skipping files already on disk"
```

---

### Task 5: Create the `garmin` SKILL.md

**Files:**
- Create: `.claude/skills/garmin/SKILL.md`

- [ ] **Step 1: Write the skill doc**

Create `.claude/skills/garmin/SKILL.md`:

```markdown
---
name: garmin
description: Download Garmin Connect activities (.fit + .tcx) on or after a given date into the local archive and rebuild the coach's monthly CSVs. Use when the user runs /garmin, wants to sync or download Garmin activities, or refresh the running data the coach reads. The coach skill invokes this in no-prompt mode before analysing a week.
user-invocable: true
---

# Garmin

Download Garmin Connect activities into the local log archive and rebuild the
monthly summary CSVs the `coach` skill reads. This skill owns all Garmin
knowledge — login, the archive location, and the FIT-SDK CSV build.

## Invocation

Optional argument: a **start date** (`YYYY-MM-DD`). Every activity on or after
that date is downloaded; with no argument the script default (`2026-01-01`) is
used. The end date is always today.

```
/garmin 2026-05-01
```

## What it does

Run the worker:

```
python3 .claude/skills/garmin/download-garmin.py --start <date>
```

For each activity in the range it downloads **both** formats into the year folder
under the configured archive (`YYYY-MM-DD-HH-MM_<Type>.fit` and `.tcx`),
**skipping any file already on disk**, then rebuilds `running/data/tcx-*.csv` from
the `.fit` files via the Garmin FIT SDK. `.tcx` files are archive-only; the CSVs
the coach reads are built from `.fit`. The script bootstraps its own venv
(`.claude/skills/garmin/.venv`) on first run.

## Run modes

- **Interactive** (a human runs `/garmin`): Garmin login/MFA prompts are allowed.
  Tokens cache in `~/.garminconnect`, so later runs need no login.
- **No-prompt** (the `coach` skill calls this): add `--no-prompt`. With no cached
  token the download is skipped and the CSVs are rebuilt from `.fit` already on
  disk — it never blocks.

## Configuration

`running/data/user.md` holds the per-machine archive path:

```markdown
- log_dir: /absolute/path/to/your/activity/log
```

If the file or the `log_dir:` line is missing, the script exits with a message
telling you to create it.

## Credentials

Set `GARMIN_EMAIL` / `GARMIN_PASSWORD` in the environment, or you are prompted
(interactive mode only). MFA codes are prompted interactively when Garmin
requires one.

## Flags

`--start` / `--end` (date range), `--no-download` (only rebuild CSVs from existing
`.fit`), `--no-csv` (only download), `--no-prompt` (never prompt; used by the
coach).
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/garmin/SKILL.md
git commit -m "feat(garmin): add the garmin skill doc"
```

---

### Task 6: Decouple `parse-log.py` from Garmin

**Files:**
- Modify: `.claude/skills/coach/parse-log.py`
- Test: `.claude/skills/coach/test-parse-log.py` (run only — no change)

- [ ] **Step 1: Trim the module docstring**

Replace the top docstring (lines 1–25) intro + steps. Replace:

```python
"""parse-log.py - Aggregate logged TCX activities against the Dements 2026 plan.

Part of the sync-training-plan skill. This script does the deterministic work so
Claude does not have to: it refreshes the monthly activity CSVs, maps every
logged activity onto a plan week, classifies average heart rate into a
lab-calibrated training zone, aggregates per week, and prints a JSON summary on
stdout for the skill to act on. All progress/errors go to stderr.

Steps:
  1. Refresh CSVs by running running/download-garmin.py (downloads new Garmin
     .fit activities from the plan start onward and rebuilds the monthly CSVs
     with the Garmin FIT SDK). Failures (e.g. Drive offline, or a Garmin login
     is needed) are recorded and the script falls back to existing CSVs.
  2. Read every running/data/tcx-*.csv.
  3. Map each activity to a plan week (week 1 = Mon 2026-05-11; week N spans
     [start+(N-1)*7, +6d]). Activities outside the plan range are ignored.
  4. Classify average HR into Z1-Z5 from the VT1/VT2 zones in running-zones.html.
  5. Aggregate per week and emit JSON.

Usage:
  parse-log.py [--no-refresh] [--today YYYY-MM-DD] [--data-dir DIR] [--repo DIR]
```

with:

```python
"""parse-log.py - Aggregate logged TCX activities against the Dements 2026 plan.

Part of the coach skill. This script does the deterministic work so Claude does
not have to: it reads the monthly activity CSVs (refreshed separately by the
garmin skill), maps every logged activity onto a plan week, classifies average
heart rate into a lab-calibrated training zone, aggregates per week, and prints
a JSON summary on stdout for the skill to act on. All progress/errors go to
stderr.

Steps:
  1. Read every running/data/tcx-*.csv.
  2. Map each activity to a plan week (week 1 = Mon 2026-05-11; week N spans
     [start+(N-1)*7, +6d]). Activities outside the plan range are ignored.
  3. Classify average HR into Z1-Z5 from the VT1/VT2 zones in running-zones.html.
  4. Aggregate per week and emit JSON.

Usage:
  parse-log.py [--today YYYY-MM-DD] [--data-dir DIR] [--repo DIR]
```

- [ ] **Step 2: Remove the `subprocess` import**

Delete this line from the import block:

```python
import subprocess
```

- [ ] **Step 3: Delete the `refresh_csvs` function**

Remove the entire function (and its preceding blank line):

```python
def refresh_csvs(repo, today, log):
    """Download new Garmin .fit activities and rebuild the monthly CSVs.

    Delegates to running/download-garmin.py, which downloads any new .fit files
    from the plan start onward and (re)writes running/data/tcx-*.csv from them
    via the Garmin FIT SDK. A non-empty log here (e.g. Drive offline, or a
    Garmin login is needed) is fine — the engine then falls back to the CSVs
    already on disk."""
    script = os.path.join(repo, "running", "download-garmin.py")
    if not os.path.exists(script):
        log.append(f"download-garmin.py not found at {script}; skipped refresh")
        return
    try:
        r = subprocess.run([sys.executable, script,
                            "--start", PLAN_START.isoformat(), "--no-prompt"],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            log.append(r.stderr.strip() or "garmin refresh failed")
    except Exception as exc:  # noqa: BLE001 - report any refresh failure
        log.append(str(exc))
```

- [ ] **Step 4: Update the `build_activity` docstring path reference**

Replace:

```python
    Columns are the raw Garmin FIT SDK session field names written by
    running/download-garmin.py (total_distance in metres, enhanced_avg_speed in
    m/s, etc.). The full set of SDK fields is present in the row; we read the
```

with:

```python
    Columns are the raw Garmin FIT SDK session field names written by the garmin
    skill's download-garmin.py (total_distance in metres, enhanced_avg_speed in
    m/s, etc.). The full set of SDK fields is present in the row; we read the
```

- [ ] **Step 5: Remove the `--no-refresh` argparse option**

Replace:

```python
    ap = argparse.ArgumentParser(description="Aggregate TCX logs vs the Dements plan.")
    ap.add_argument("--no-refresh", action="store_true",
                    help="skip running download-garmin.py; use existing CSVs only")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
```

with:

```python
    ap = argparse.ArgumentParser(description="Aggregate TCX logs vs the Dements plan.")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
```

- [ ] **Step 6: Remove the refresh call and `refresh_log` from `main`**

Replace:

```python
    refresh_log, errors = [], []
    if not args.no_refresh:
        refresh_csvs(repo, today, refresh_log)
    for msg in refresh_log:
        print(f"refresh: {msg}", file=sys.stderr)

    activities = read_activities(data_dir, errors)
```

with:

```python
    errors = []
    activities = read_activities(data_dir, errors)
```

- [ ] **Step 7: Drop `refresh_errors` from the JSON output**

Replace:

```python
        "data_dir": data_dir,
        "refresh_errors": refresh_log,
        "csv_errors": errors,
```

with:

```python
        "data_dir": data_dir,
        "csv_errors": errors,
```

- [ ] **Step 8: Run the existing tests to confirm no regression**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: `OK`

- [ ] **Step 9: Confirm the engine still runs and `refresh_errors` is gone**

Run:

```bash
python3 .claude/skills/coach/parse-log.py --today 2026-06-12 | python3 -c "import sys,json; d=json.load(sys.stdin); print('refresh_errors' in d, d['activity_count'])"
```

Expected: `False <some integer ≥ 0>` (no `refresh_errors` key; CSVs read from disk).

- [ ] **Step 10: Verify no stale refresh references remain**

Run:

```bash
grep -n "refresh_csvs\|no_refresh\|no-refresh\|refresh_log\|refresh_errors\|^import subprocess" .claude/skills/coach/parse-log.py
```

Expected: **no output**.

- [ ] **Step 11: Commit**

```bash
git add .claude/skills/coach/parse-log.py
git commit -m "refactor(coach): make parse-log.py pure aggregation, drop the Garmin refresh"
```

---

### Task 7: Point the coach at the `garmin` skill

**Files:**
- Modify: `.claude/skills/coach/SKILL.md` (Files table + step A1)

- [ ] **Step 1: Update the Files table row for the CSVs**

Replace:

```markdown
| `running/data/tcx-*.csv` | Activity exports (refreshed by the engine). |
```

with:

```markdown
| `running/data/tcx-*.csv` | Activity exports (refreshed by the `garmin` skill, read by the engine). |
```

- [ ] **Step 2: Rewrite step A1**

Replace the whole A1 section:

```markdown
### A1. Run the engine

```
python3 .claude/skills/coach/parse-log.py
```

It refreshes the monthly CSVs (via `running/download-garmin.py`, which downloads
new Garmin `.fit` activities and rebuilds them with the Garmin FIT SDK) and
prints a JSON summary on stdout. Parse that JSON — every later step uses it. If
`refresh_errors` is non-empty (e.g. Google Drive offline, or a Garmin login is
needed) that is fine: the engine fell back to existing CSVs. Tell the user which
weeks have data.
```

with:

```markdown
### A1. Sync Garmin, then run the engine

First **invoke the `garmin` skill** to refresh the data, with start date
`2026-05-11` (the plan start) in no-prompt mode so it never blocks on a Garmin
login. It downloads any new `.fit`/`.tcx` activities and rebuilds the monthly
CSVs. If it reports it could not reach Garmin (Drive offline, or a login is
needed), that is fine — proceed on the existing CSVs.

Then run the engine:

```
python3 .claude/skills/coach/parse-log.py
```

It prints a JSON summary on stdout. Parse that JSON — every later step uses it.
Tell the user which weeks have data.
```

- [ ] **Step 3: Verify no stale refresh wording remains in the coach doc**

Run:

```bash
grep -n "refresh_errors\|download-garmin\|refreshes the monthly" .claude/skills/coach/SKILL.md
```

Expected: **no output**.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/coach/SKILL.md
git commit -m "feat(coach): invoke the garmin skill for data sync instead of refreshing inline"
```

---

## Self-review

**Spec coverage:**
- Skill named `garmin`, user-invocable → Task 5. ✔
- Download both `.fit` + `.tcx`, skip existing → Task 4. ✔
- `.tcx` archive-only, CSVs from `.fit` → Task 4 (CSV build untouched). ✔
- Decouple `parse-log.py`; coach invokes the skill → Tasks 6, 7. ✔
- Move script into skill dir; fix path constants → Task 3. ✔
- Skill-local venv; delete `running/.venv` → Task 3 (steps 2, 5, 7). ✔
- Download folder via `running/data/user.md` (`log_dir:`) → Tasks 1, 2, 3. ✔
- Two run modes (interactive / `--no-prompt`) → Task 5 doc; flag already exists. ✔
- `.tcx` archive rule (only create new) → Task 4 skip-if-exists guard. ✔
- Housekeeping: `.gitignore`, `build.sh` comment → Task 3 (steps 5, 6). ✔
- `user.md` parser test → Task 2. ✔
- Historical plan doc untouched → not referenced by any task. ✔

**Placeholder scan:** none — every code/edit step shows full content.

**Type/name consistency:** `parse_log_dir`/`read_log_dir` defined in Task 2 and imported in Task 3 (`from config import read_log_dir`). `activity_basename` defined and called in Task 4 (replaces `fit_filename`, verified gone in 4.4). `formats` tuple shape `(ext, fmt, post)` consistent within `download_all`. `LOG_DIR`/`DATA_DIR` order: `DATA_DIR` defined before `LOG_DIR` uses it (Task 3.3).
