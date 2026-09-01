---
name: garmin
description: Download Garmin Connect activities (.fit + .tcx) on or after a given date into the local archive and rebuild the coach's monthly CSVs. Use when the user runs /garmin, wants to sync or download Garmin activities, or refresh the running data the coach reads. The coach skill invokes this in no-prompt mode before analysing a week. Also pushes a gym week's HTML table to Garmin Connect as a strength workout — use when the user wants a gym week on the watch; the coach skill invokes this after writing a week's gym page.
user-invocable: true
---

# Garmin

Download Garmin Connect activities into the local log archive and rebuild the
monthly summary CSVs the `coach` skill reads. This skill owns all Garmin
knowledge — login, the archive location, the FIT-SDK CSV build, and the
workout API.

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
**skipping any file already on disk**, then rebuilds the monthly
`running/data/<YYYY-MM>.csv` summaries from the `.fit` files via the Garmin FIT
SDK. Each row also carries an `hr_seconds` column — a `bpm:secs|…` histogram
built from the per-second HR record stream — which the coach engine buckets into
time-in-zone (so a `--no-download` rebuild is enough to backfill it on existing
`.fit`). The script bootstraps its own venv (`.claude/skills/garmin/.venv`) on
first run.

`.fit` is authoritative, but some activities have none — phone-recorded ones ship
a GPX-only archive, so the `.fit` download is skipped with a `skip … zip
contained no .fit file` line (one bad export never aborts the run). For those the
builder falls back to the `.tcx`, which yields fewer columns (no running dynamics
or temperature) and a **derived** total ascent: the altitude stream is smoothed
and summed with a hysteresis threshold, ±5% against Garmin's own figure. The
`.tcx` archive is only ever read, never modified.

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

## Workouts

The other direction: turn a gym week the coach has written into a strength
workout on the watch.

```
python3 .claude/skills/garmin/upload-workout.py --week 17
python3 .claude/skills/garmin/upload-workout.py --week 17 --dry-run
```

`running/<gym_prefix><N>.html` is the source of truth — the script reads that
page's exercise cards (name, sets/reps or hold, load badge, cues) and builds one
repeat group holding every exercise in page order: 30 s rest between them, 90 s
after the last, 20 s outside the group. Range-named gym files
(`gym-week3-5.html`) are resolved the same way the coach engine resolves them.

The workout is named `week <N>`. If Garmin already has one with that name it is
**updated in place**, keeping its `workoutId` so anything scheduled on the
calendar still points at it; otherwise a new one is created. Nothing is ever
deleted. Two workouts sharing the name is an error — the script stops and asks
you to remove the duplicate in Garmin Connect.

Two conventions the HTML leaves implicit, both taken from the athlete's own
hand-built workouts:

- A **rep** count is already per side — `3 × 8 / leg` becomes an 8-rep step.
- A **timed hold** is not — `3 × 40s / side` becomes one 80 s step covering both.

A load badge reading `<n> kg` becomes the step's weight in kilograms. Anything
else (`bodyweight`, `band · ankles`) is sent as **0 kg** — Garmin has no
"bodyweight" value, a step is a number plus a unit.

Garmin only accepts exercise names from its own catalogue, so each gym-page name
is mapped in `EXERCISES` in `workout.py`. A name that is not there stops the run
and is reported by name — add it as `'<page name lowercased>': ('<CATEGORY>',
'<EXERCISE_NAME>')` rather than letting a near-miss through. Mixed set counts on
one page also stop the run, since a circuit is a single repeat group.

Flags: `--week` (required), `--dry-run` (print the circuit, contact nobody),
`--json PATH` (also write the generated payload). Login is the same as above;
this script has no `--no-prompt` mode, so the coach only calls it when a cached
token exists.

## Tests

```
python3 .claude/skills/garmin/test-config.py
python3 .claude/skills/garmin/test-workout.py
```

Plain asserts, no test runner. `workout.py` and `config.py` are pure stdlib and
importable without the venv, which is why the parsing lives there rather than in
the scripts that log in.
