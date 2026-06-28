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
**skipping any file already on disk**, then rebuilds the monthly
`running/data/<YYYY-MM>.csv` summaries from the `.fit` files via the Garmin FIT
SDK. Each row also carries an `hr_seconds` column — a `bpm:secs|…` histogram
built from the per-second HR record stream — which the coach engine buckets into
time-in-zone (so a `--no-download` rebuild is enough to backfill it on existing
`.fit`). `.tcx` files are archive-only; the CSVs the coach reads are built from
`.fit`. The script bootstraps its own venv (`.claude/skills/garmin/.venv`) on
first run.

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
