# Generic coach via an athlete profile — design

**Date:** 2026-06-12
**Status:** Approved (brainstorming)

## Summary

Make the `coach` skill **generic** by extracting every athlete- and race-specific
value out of `coach/SKILL.md` and `coach/parse-log.py` into `running/data/user.md`,
which becomes the single **athlete + plan profile**. The coach reads the profile
for all context and voice; the deterministic engine reads the structured subset it
computes with. New profile sections (equipment, terrain-from-home) give the coach
the athlete's capabilities and constraints to plan training. This is a
**zero-behavior-change refactor** — the migrated values must reproduce today's
engine output exactly.

## Decisions (locked)

| Topic | Decision |
| --- | --- |
| Depth | **Fully generic engine** — zones, plan_start, total_weeks, the weekly plan baseline, race identifiers, and file names all move to `user.md`; `parse-log.py` reads them. |
| Format | **Structured markdown** — human-readable sections + small tables + `key: value` lines, parsed with stdlib regex. No new dependency (engine stays pure-stdlib on system python). |
| One file | All of it lives in `running/data/user.md` (the same file the garmin skill already reads for `log_dir`). |
| Engine-parsed vs prose | Engine parses ONLY what it computes with (zones, plan baseline, plan_start, hilly_elev, plan_file, gym_prefix). Equipment, terrain, injury narrative, philosophy are **prose** the coach reads. |
| Reader module | New pure-stdlib `.claude/skills/coach/profile.py` parses `user.md`; `parse-log.py` imports it; `test-profile.py` tests it (mirrors `config.py`/`test-config.py`). |
| `running-zones.html` | **Stays as-is** (rendered lab page, not engine-read). Regenerating it from the profile is out of scope. |
| `dements-2026-plan.html` | **Stays** — the rendered plan the coach edits; the baseline relocates to `user.md`, HTML `weeks[]` still kept in sync as today. |
| garmin skill | Unchanged beyond continuing to read `log_dir` from `user.md`. |

## Architecture — one profile, two readers

`user.md` is the athlete + plan profile. Two skills read it, each taking only what
it needs:

- **`garmin` skill** — reads `log_dir` (unchanged; its `config.py`).
- **`coach` skill** — `profile.py` (new, pure stdlib) parses the structured bits
  into a dict; `parse-log.py` consumes it. The coach (Claude) reads the whole file
  as planning context.

The engine's parseable surface is bounded: HR-zone lower bounds, the week→km/elev
baseline table, `plan_start`, `hilly_elev`, `plan_file`, `gym_prefix`. Everything
else is free prose.

## `user.md` schema

```markdown
# Athlete & training profile
<!-- Read by the coach skill (all of it) and parsed by parse-log.py + the
     garmin skill (the `key: value` lines and the two tables). Hand-edit freely. -->

## Paths
- log_dir: /Users/ncornag/Library/CloudStorage/GoogleDrive-ncornag@gmail.com/My Drive/personal/running/log
- plan_file: dements-2026-plan.html
- gym_prefix: gimnasio-semana

## Athlete
- age: 57

(Free prose: injury history, what to watch, constraints.)

## HR zones
Lab-calibrated. VT1 151, VT2 173.

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

(Distance/elev/date are the last plan row + the plan span.)

## Equipment

(Prose / list — coach-only. Athlete fills in.)

## Terrain from home

(Prose / list of routes with distance + elevation — coach-only. Athlete fills in.)

## Training principles
- principle: smart beats heroic

(Free prose.)

## Training plan
- plan_start: 2026-05-11
- hilly_elev: 30

| week | km | elev |
| 1 | 25 | 0 |
| 2 | 25 | 0 |
| … | … | … |
| 26 | 42.5 | 3808 |
```

The 26 plan rows are migrated verbatim from the current `PLAN` array in
`parse-log.py`:

```
(25,0) (25,0) (21,0) (22,0) (23,80) (17,30) (28,300) (33,500) (38,700) (25,350)
(45,1000) (50,1200) (52,1400) (56,1600) (32,500) (45,1500) (35,700) (60,2000)
(38,800) (68,2600) (75,2900) (65,2200) (48,1400) (28,600) (22,300) (42.5,3808)
```

Zone cutoffs are the `from_bpm` of Z2..Z5 = `[135, 152, 163, 174]`, matching
`hr_zone()`'s current `<135 / <152 / <163 / <174` ladder. This makes 152 (not the
prose's "151") the single source for the Z2/Z3 boundary.

## `profile.py` (new, pure stdlib)

Parses `running/data/user.md` and returns a dict, e.g.:

```python
{
  "plan_file": "dements-2026-plan.html",
  "gym_prefix": "gimnasio-semana",
  "zone_cutoffs": [135, 152, 163, 174],     # Z2..Z5 lower bounds
  "plan_start": date(2026, 5, 11),
  "hilly_elev": 30,
  "plan": [(25.0, 0), (25.0, 0), ...],      # 26 (km, elev) tuples
}
```

Parsing contract (all stdlib `re`):
- `key: value` lines (`plan_file`, `gym_prefix`, `plan_start`, `hilly_elev`)
  read by a labeled-line regex (same style as `config.py`'s `log_dir`).
- The **HR zones** table → ordered `from_bpm` values; cutoffs = bounds of Z2..Z5.
- The **Training plan** table → list of `(km, elev)` by ascending week.
- Missing file / missing required field → `SystemExit` with a clear "fill in
  running/data/user.md" message (matching `config.py`).

`profile.py` does NOT need `log_dir` (that's the garmin skill's concern) — no
overlap between the two readers.

## `parse-log.py` changes

- `main()` loads the profile once via `profile.read_profile(<repo>/running/data/user.md)`,
  then assigns the module-level names from it before any computation:
  `PLAN_START`, `TOTAL_WEEKS = len(plan)`, `PLAN`, `ZONE_CUTOFFS`, `HILLY_ELEV`.
  Helper signatures (`hr_zone`, `week_range`, `week_of`, `aggregate`) are unchanged;
  they read the module-level names — smallest diff, matches existing style.
- `hr_zone()` becomes a loop over `ZONE_CUTOFFS` instead of the hardcoded ladder.
- The plan-HTML path and gym glob/regex use `plan_file` / `gym_prefix` from the
  profile instead of the `dements-2026-plan.html` / `gimnasio-semana` literals.
- The module-level constants `PLAN_START`, `TOTAL_WEEKS`, `PLAN`, `HRE_HILLY_ELEV`
  are removed as literals (kept as names, populated from the profile). They start
  as `None`/placeholder and are set in `main()`.

## `coach/SKILL.md` changes

Strip every athlete/race specific; replace with "read the profile":
- Opening identity ("coach for **Marató dels Dements** … athlete is **57** …
  'smart beats heroic'") → "Read the athlete profile in `running/data/user.md`
  (athlete, goal race, zones, equipment, terrain, principles, plan) and coach
  from it."
- **Coach Voice**: hardcoded zone numbers and race name → "use the profile's
  zones / goal race." Add a bullet: factor the profile's **equipment** and
  **terrain-from-home** into session prescriptions.
- **Files** table and step references to `dements-2026-plan.html` /
  `gimnasio-semana<N>` → "the plan file / gym files named in the profile."
- The coach's mechanics (sync → check-in → adjust → record; gym programming; HTML
  sync regions) are unchanged — only the baked-in identity moves out.

## Testing

- **`test-profile.py`** (new, pure stdlib via importlib): zones table → cutoffs;
  plan table → baseline; `key: value` reads; missing-field → `SystemExit`.
- **`test-parse-log.py`** stays green (`parse_gym_files`/`render_gym_links_js`
  take `gym_prefix`).
- **End-to-end parity:** running `parse-log.py --today 2026-06-12` after migration
  must produce byte-identical JSON to before the refactor (capture the current
  output first as the baseline). Zero behavior change.

## Out of scope

- Regenerating `running-zones.html` from the profile.
- Renaming the plan/gym files away from Dements/Spanish names (profile points at
  whatever they're called).
- Any garmin-skill change beyond reading `log_dir`.
- Engine consumption of equipment/terrain (those are coach-prose only).
