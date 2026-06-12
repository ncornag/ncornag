# Garmin skill — design

**Date:** 2026-06-12
**Status:** Approved (brainstorming)

## Summary

Split the Garmin data-fetch responsibility out of the `coach` skill into its own
user-invocable **`garmin`** skill. Today `coach/parse-log.py` silently shells out
to `running/download-garmin.py` on every run to download `.fit` activities and
rebuild the monthly CSVs. After the split:

- **`garmin`** owns all Garmin knowledge — login, credentials, the download
  archive location, and the CSV rebuild. You invoke it with a date and it
  downloads every activity **on or after** that date as **both `.fit` and `.tcx`**
  (skipping anything already on disk), then rebuilds `running/data/tcx-*.csv` from
  the `.fit` files.
- **`coach` + `parse-log.py`** become pure analysis — read the CSVs, aggregate
  against the plan, render the HTML. No Garmin knowledge. The coach's first step
  invokes the `garmin` skill, then runs `parse-log.py`.

## Decisions (locked)

| Topic | Decision |
| --- | --- |
| Skill name | **`garmin`**, user-invocable. Invocation `/garmin [start-date]`. |
| Download formats | Download **both `.fit` (ORIGINAL) and `.tcx` (TCX)** per activity. |
| Skip policy | **Never re-download** a file already on disk (per-format `if dest.exists(): continue`). |
| `.tcx` role | **Archive only** — parallel to how 2016–2025 are archived as `.tcx`. CSVs are still built from `.fit`. |
| Coupling | **Decouple.** `parse-log.py` stops auto-downloading; the coach invokes the `garmin` skill, then runs the engine. |
| Script location | **Move** the download script into the skill dir: `.claude/skills/garmin/download-garmin.py`. |
| Venv | **Skill-local** at `.claude/skills/garmin/.venv`; orphaned `running/.venv` removed. |
| Download folder | **Configured** in a committed `running/data/user.md` (`log_dir:` key), out of the script. |
| Run modes | **Interactive** (human `/garmin`, prompts allowed for MFA) and **`--no-prompt`** (coach call, never blocks). |
| `.tcx` log archive rule | Honoured — the skill only ever **creates new** `.tcx`, never modifies/moves/deletes existing ones. |

## Architecture

Two skills, one clean seam between "get the data" and "analyze the data".

### `garmin` skill (new) — get the data

- **`.claude/skills/garmin/SKILL.md`** (user-invocable): documents the date
  argument and the two run modes; instructs running the script.
- **`.claude/skills/garmin/download-garmin.py`** (moved from `running/`): the
  deterministic worker. Logs into Garmin, downloads `.fit`+`.tcx`, rebuilds CSVs.

Responsibilities owned here: Garmin login/creds, `LOG_DIR` (the archive), the
venv, the FIT SDK decode, and the monthly CSV rebuild.

### `coach` skill + `parse-log.py` — analyze the data

- **`parse-log.py`** becomes pure aggregation: reads existing `tcx-*.csv`,
  classifies zones, aggregates per week, renders HTML fragments. No subprocess,
  no Garmin.
- **`coach/SKILL.md`** step A1 is rewritten to invoke the `garmin` skill first,
  then run the engine.

## Component detail

### 1. `running/data/user.md` (new, committed)

Holds the machine-specific archive path, kept out of the committed script.
Plain markdown with one key the script scans for:

```markdown
# Running data config

Per-machine paths for the garmin skill, kept out of the committed scripts.

- log_dir: /Users/ncornag/Library/CloudStorage/GoogleDrive-ncornag@gmail.com/My Drive/personal/running/log
```

Parsing contract: scan lines for `log_dir:` (an optional leading `- `/`* ` bullet
is allowed); the remainder of the line, trimmed, is `LOG_DIR`. Missing file or
missing key → exit with a clear error: "create running/data/user.md with a
`log_dir:` line." `DATA_DIR` (CSV target) stays repo-relative (`REPO/running/data`)
— only the absolute archive path is configurable.

### 2. `download-garmin.py` (moved + extended)

- **Path constants** recomputed for the new location:
  `SKILL_DIR = Path(__file__).resolve().parent`,
  `REPO = Path(__file__).resolve().parents[3]`,
  `VENV_DIR = SKILL_DIR / ".venv"`. `DATA_DIR = REPO / "running" / "data"`
  unchanged. `LOG_DIR` now read from `user.md` (see above) instead of hardcoded.
- **Both-format download.** The per-activity loop downloads each format
  independently, each with its own skip-if-exists guard, naming files
  `YYYY-MM-DD-HH-MM_<Type>.{fit,tcx}` (the existing convention, already used by
  the paired 2026 files):
  - `.fit` via `ActivityDownloadFormat.ORIGINAL`, unzipped with the existing
    `extract_fit`.
  - `.tcx` via `ActivityDownloadFormat.TCX`, written raw (Garmin returns TCX as
    raw XML, not zipped).
- **CSV rebuild unchanged** — still reads `.fit` only via the FIT SDK and writes
  `running/data/tcx-*.csv`. A month is only rewritten when it has ≥1 `.fit` row,
  so an offline Drive cannot clobber existing CSVs.
- **Flags unchanged:** `--start`, `--end`, `--no-download`, `--no-csv`,
  `--no-prompt`. (A `--no-tcx`/`--no-fit` is out of scope — YAGNI.)

### 3. `garmin/SKILL.md` (new)

- **Input:** optional start date. `/garmin 2026-05-01` → activities on/after that
  date; no date → script default (`2026-01-01`). End date defaults to today.
- **Workflow:** resolve the date → run
  `python3 .claude/skills/garmin/download-garmin.py --start <date>` → report new
  `.fit`/`.tcx` counts, months rebuilt, and any login/skip issues.
- **Two modes, both documented:**
  - Interactive (human): prompts allowed so Garmin MFA/login works.
  - `--no-prompt` (coach call): on no cached token it skips the download and
    rebuilds CSVs from `.fit` already on disk — never blocks.

### 4. `parse-log.py` (decoupled)

Delete `refresh_csvs()`, its call site, the `--no-refresh` flag, the `subprocess`
import, and the `refresh_errors` field in the JSON output. Trim "step 1" from the
module docstring. The engine now only ever reads existing CSVs.

### 5. `coach/SKILL.md` (step A1 rewrite)

A1 becomes two moves: **invoke the `garmin` skill** with the plan-start date
(`2026-05-11`) in no-prompt mode, then run `parse-log.py`. The "if `refresh_errors`
is non-empty…" paragraph is replaced with: "if `garmin` reports it couldn't reach
Garmin, proceed on existing CSVs and tell the user which weeks have data." The
Files table reference to `running/download-garmin.py` is updated to the new path
and reframed as owned by the `garmin` skill.

### 6. Housekeeping

- **`.gitignore`:** replace `running/.venv/` with `.claude/skills/garmin/.venv/`.
- **Delete `running/.venv`** (gitignored, regenerable; the moved script recreates
  a skill-local one on first run).
- **`build.sh`:** update the line-16 comment that names the script's old path.
  `build.sh` copies nothing from `.claude/`, so the build is unaffected.

## Data flow (after)

```
/garmin 2026-05-01  ──►  download-garmin.py
                           ├─ read LOG_DIR from running/data/user.md
                           ├─ Garmin login
                           ├─ per activity: download .fit + .tcx (skip existing)
                           └─ rebuild running/data/tcx-*.csv from .fit
/coach  ──►  (A1) invoke garmin skill (start 2026-05-11, --no-prompt)
             (A1) parse-log.py  ──►  read tcx-*.csv ──► aggregate ──► render plan HTML
```

## Testing

- `test-parse-log.py` stays as-is (covers `parse_gym_files` /
  `render_gym_links_js`; no refresh logic). Still passes after the decoupling.
- Add a small unit test for the `user.md` `log_dir` parser (pure string parsing,
  no network) — happy path, bulleted line, and missing-key error.
- No download/network unit tests (Garmin login is network-bound).

## Out of scope

- Building CSVs from `.tcx` (pre-2026 archives stay archive-only; the plan window
  is `.fit`-based).
- `--no-tcx` / `--no-fit` toggles.
- Changing the deployment / `build.sh` copy set beyond the one comment.
- Touching the historical plan doc `docs/superpowers/plans/2026-05-29-coach-skill.md`.
