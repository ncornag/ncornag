# Coach skill — design

**Date:** 2026-05-29
**Status:** Approved (brainstorming)

## Summary

Evolve the `sync-training-plan` skill into a real two-way **`coach`**: each run it
syncs logged activity (as today), but also recalls past feedback, asks the athlete
targeted questions, answers theirs, and — with confirmation — adjusts upcoming runs
and the gym programme. Gym tables become per-week (`gimnasio-semana<N>.html`), evolving
by training phase and feedback, with identical consecutive weeks merged into a single
range-named file. Cross-file linking is cleaned up so every running page is navigable.

The athlete is **57 with an injury history**; the plan principle is "smart beats
heroic." All coaching stays conservative and never pushes through warning signs.

## Decisions (locked)

| Topic | Decision |
| --- | --- |
| Feedback capture | Ask in-session, **persist to a log** the coach reads every run (memory). |
| Gym tables | **Just-in-time, evolving**; identical consecutive weeks merged into `gimnasio-semana<N-M>.html`. |
| Acting scope | May change **upcoming runs** and the **gym table**, but **proposes the change and applies only after the athlete confirms**. |
| Log format/location | **Markdown** at `running/coach-log.md`, human-readable and hand-editable. |
| Feedback in plan HTML | **Keep HTML as-is** — no new athlete-note markup; the coach-block prose absorbs the conversation. |
| Skill rename | `sync-training-plan` → `coach`; invocation `/coach`; **no alias**. |
| Page nav | Minimal **back-to-index** links on gym/zones pages (index is the hub), not a full nav bar. |
| Past gym weeks | **Frozen** unless athlete feedback corrects a niggle. |

## Architecture

Two collaborating parts, unchanged in spirit from today:

- **Engine — `parse-log.py`** (deterministic): owns date math, zone classification,
  per-week aggregation, and the rendered deterministic HTML fragments. Additive
  changes only (see below). Never recompute its outputs by hand.
- **Skill — `SKILL.md`** (Claude, the coach): runs the engine, holds the
  conversation, writes qualitative coach commentary, authors gym tables, and
  maintains the log.

### Directory / file changes

- Move `.claude/skills/sync-training-plan/` → `.claude/skills/coach/`
  (`SKILL.md`, `parse-log.py`, `__pycache__` regenerates).
- New: `running/coach-log.md`.
- New (created over time): `running/gimnasio-semana<N>.html` /
  `running/gimnasio-semana<N-M>.html`.
- Edited: `running/index.html` (gym card label + target), `running/running-zones.html`
  (back link), existing/forthcoming gym files (back link), `running/dements-2026-plan.html`
  (gym-link JS block).

## The coaching loop (`/coach` run order)

1. **Sync** — run `python3 .claude/skills/coach/parse-log.py`; parse its JSON.
2. **Recall** — read `running/coach-log.md`: past feedback, unresolved "open threads"
   (e.g. "watching knee"), prior recommendations and whether applied.
3. **Check-in (interactive)** — ask the athlete **2–4 targeted questions** driven by
   the data + open threads (pace/HR anomalies, gym niggles, missed sessions), and
   invite their own questions. If the athlete reports nothing, proceed on data alone.
4. **Respond & propose** — answer the athlete's questions in chat. When data/feedback
   warrants a change to **upcoming runs** (week `current_week+1` only) or the **gym
   table**, propose the *specific* change and **apply only after explicit
   confirmation**.
5. **Write to HTML** — the existing deterministic + coach steps (below).
6. **Log** — append/update today's entry in `running/coach-log.md`.
7. **Verify** — deterministic regions produce zero diff on a second engine pass;
   `git diff` shows only intended regions.

### HTML write steps (carried over from current skill)

These keep their current contracts and markers, unchanged:

- One-time CSS/`chart_js` setup (`/* sync:styles */`, `// sync:chart`).
- Per-week day grid (`<!-- sync:days:wN -->`), actuals panel (`<!-- sync:actuals:wN -->`),
  coach block (`<!-- sync:coach:wN -->` with `data-hash` idempotency), week status badge.
- Next-week run adjustment (week `current_week+1` only, reversible via `data-plan-*`,
  `adjusted` badge) — now gated behind athlete confirmation per the acting-scope decision.
- Coach Voice rules unchanged (lab zones, polarized discipline, cite data, use
  `plan_days[]` for schedule facts).

## `running/coach-log.md` format

Append-only markdown, **newest entry first**, with a fixed top header explaining the
file. One entry per date; if `/coach` is re-run the same day, **update that entry in
place** rather than duplicating.

```
# Coach log — Dements 2026

Running journal of athlete feedback and coach responses. The coach reads this every
run for memory; you may edit it by hand.

---

## 2026-05-29 · Week 3
**You:** knee twinge in Bulgarian split squats Thu; Sat long run felt great; can I add a 4th run?
**Coach:** swapped split squat → step-ups in the gym table (applied); held W4 long run
at 7 km — consistency before a 4th run (explained). Watching: knee >48 h.
```

"Open threads" (niggles to watch, deferred questions) are tracked by the coach by
scanning prior entries; no separate machinery.

## Per-week gym tables

- Each gym week → `running/gimnasio-semana<N>.html`, built from the **exact structure
  and CSS of the current `gimnasio-semana3.html`** (theme bootstrap, header title
  `GIMNASIO SEMANA N`, phase subtitle, stat pills, warmup card, exercise grid with
  cues/`ex-watch`, expected/warning footer). Content (exercises, sets, cues, load) is
  authored by the coach per **training phase** (foundation → strength → vert/power →
  taper) and athlete feedback.
- **Just-in-time:** each run, ensure every gym week from gym-start (week 3) through
  `current_week+1` has a file. Past weeks are **frozen** unless feedback corrects a
  niggle.
- **Dedup → ranges:** if a week's programme is identical to the previous week's, do
  not create a new file; name the shared file `gimnasio-semana<N-M>.html` (e.g.
  `gimnasio-semana3-5.html` covers weeks 3–5). The set of files should tile the gym
  weeks without overlap.
- Each gym file includes the standard **back-to-index** nav link.

### Gym-chip linking (engine-owned)

`parse-log.py` gains:

- **Discovery:** scan `running/gimnasio-semana*.html`, parse both single (`semana3`)
  and range (`semana3-5`) filenames into a `week → file` map.
- **Per-week output:** add `gym_file` to each `weeks[]` entry (null if no file yet).
- **`gym_links_js`:** a JS block (fenced by `// sync:gymlinks` / `// /sync:gymlinks`)
  that, for every `.week[id="wN"]`, links that week's `.day.gym .day-km` to its mapped
  file. Replaces the current hardcoded block at `dements-2026-plan.html:3025`. Covers
  future weeks too (data not required). Deterministic — zero diff when files unchanged.
- Expose the **current week's gym file** (for the index link).

*Alternative considered and rejected:* writing hrefs directly into `days_html` — only
covers weeks with logged data, so future gym chips would be unlinked. The JS map covers
all weeks.

## Linking cleanup ("all html properly linked")

- `gimnasio-semana3.html` is currently mistitled **"Semana 1"** internally and in
  `index.html`. Correct labels to the real week number.
- Gym + zones pages get a small **back-to-index** link, matching existing style
  (`index.html` remains the hub that links out to plan, zones, current gym).
- `index.html` gym card points to the **current week's gym file** with the correct
  label; the coach keeps it current each run.

## Engine changes summary (`parse-log.py`)

Additive only; every existing JSON field and rendered fragment stays identical:

- Gym-file discovery → `week → file` map (parses single + range filenames).
- `gym_file` per `weeks[]` entry.
- `gym_links_js` output + `// sync:gymlinks` markers contract.
- Current-week gym file exposed for the index link.

## Out of scope

- Auto-generating all 26 gym weeks upfront (explicitly just-in-time instead).
- Athlete-note markup or a journal panel in the plan HTML (HTML stays as-is).
- A full per-page nav bar (only back-to-index links).
- Rewriting frozen past gym weeks except to correct a reported niggle.
