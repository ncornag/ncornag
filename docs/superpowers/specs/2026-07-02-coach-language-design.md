# Coach skill language preference — design

**Date:** 2026-07-02
**Status:** Approved (brainstorming)

## Summary

The `coach` skill currently hardcodes its output language by convention: the
plan file (`dements-2026-plan.html`) is written in English, the gym files
(`gimnasio-semana<N>.html`) in Spanish. Make the language an explicit,
athlete-chosen setting instead: a `language` field in the athlete profile
(`running/data/user.md`), asked once (on the first session where it's
missing) and then used for every session's chat, coach commentary, gym
tables, and log entries. As part of adopting this for the current athlete
(English), rename and translate the seven existing gym-week files from
Spanish to English.

## Decisions (locked)

| Topic | Decision |
| --- | --- |
| Storage | A `## Language` section in `running/data/user.md` (new), `- language: <name>` — pure coach-prose, not engine-parsed. Same category as `equipment`/`terrain from home`. |
| When asked | Only when the field is absent from the profile — the coach asks once, before anything else that session, then writes the answer back to the profile. Every later session reads it silently; never re-asked unless the athlete asks to change it. |
| Scope of "language" | Everything: the live `/coach` chat replies, coach-block prose, gym-table content, and `coach-log.md` entries. |
| Engine | No changes. `parse-log.py` / `user_profile.py` never read `language` — it is Claude-only, consumed when writing prose. |
| Gym file naming | Renamed to match the chosen language's convention. For the current athlete: `gimnasio-semana<N>.html` → `gym-week<N>.html`, and `gym_prefix` in the profile updates to match. `parse_gym_files`' regex is already prefix-agnostic (`re.escape(gym_prefix) + r"(\d+)(?:-(\d+))?\.html$"`), so no engine code changes — only the profile value and the files on disk move together. |
| Historical record | `running/coach-log.md`'s past entries, and the two prior `docs/superpowers/{specs,plans}/*.md` design docs, are **not** rewritten — they describe what was true when written. `dist/` is a build artifact (`bash build.sh` regenerates it) and is never hand-edited. |

## `user.md` changes

New section, placed after `## Paths` (both are session-meta fields):

```markdown
## Language

- language: English
```

## `SKILL.md` changes

1. **New first step** (before today's A1 "Sync Garmin, then run the engine"):
   read the profile's `## Language` section. If `language:` is present, use
   it for the whole session (chat + every document written). If absent, ask
   the athlete which language they'd like before doing anything else, then
   write `- language: <name>` into a new `## Language` section in
   `running/data/user.md`.
2. **Coach Voice**: add "write in the athlete's profile language" alongside
   the existing zone/voice rules.
3. **Gym programming → Template bullet**: replace the hardcoded
   `GIMNASIO SEMANA N` example with the language-neutral pattern — a stacked
   two-line title, `<TOPIC><br><UNIT> <span>N</span>` (e.g. `GYM<br>WEEK 8` in
   English) — and update the filename example to the athlete's current
   `gym_prefix` (`gym-week3-5.html`).
4. **Feedback log**: note that `coach-log.md` entries are written in the
   profile's language.

## Migration: rename + translate the seven existing gym files

One-time data migration to bring the current athlete's gym files in line
with the newly-recorded `language: English`:

1. `git mv` each `running/gimnasio-semana<N>.html` → `running/gym-week<N>.html`
   for N = 3, 4, 5, 6, 7, 8, 9.
2. Translate each file's visible text from Spanish to English: `<html lang="es">`
   → `lang="en"`, `<title>`, header title/subtitle, stat-pill labels, warmup
   text, all six exercise cards (names, position/execution cues, watch-outs),
   and the expected/warning footer lists. CSS, class names, and HTML
   structure stay byte-identical — only text nodes change, so each file's
   translation is checked by diffing structure (tag/attribute counts) before
   and after.
3. `running/data/user.md`: `gym_prefix: gimnasio-semana` → `gym_prefix: gym-week`;
   add the new `## Language` section (`language: English`).
4. `running/index.html`: update the gym card's `href` (→ `gym-week8.html`,
   the current gym file) and label (`Gimnasio — Semana 8` → `Gym — Week 8`).
5. Re-run `python3 .claude/skills/coach/parse-log.py` and re-apply the
   engine-owned `// sync:gymlinks` block in `dements-2026-plan.html` (per
   SKILL.md's existing rename/split rule in "Gym programming → Linking") so
   the plan file's JS gym-link map matches the new filenames. This is a
   deterministic, engine-owned region — not hand-edited.

## Testing / verification

- Re-run the engine after the migration; the `// sync:gymlinks`,
  `<!-- sync:days:wN -->`, `<!-- sync:actuals:wN -->`, and volume/HRE chart
  regions must produce **zero diff** on a second pass (existing idempotency
  contract, unaffected by this change).
- `git diff` review: only the 7 renamed+translated gym files, `index.html`'s
  gym card, `user.md`, `dements-2026-plan.html`'s `sync:gymlinks` block, and
  `SKILL.md` should show changes. HTML stays well-formed (tags balanced) in
  every touched file.
- Spot-check each translated gym file against its Spanish original for
  fidelity: same number of exercises, same load/rep/tempo numbers, same
  safety warnings — nothing lost or invented in translation.
- `test-parse-log.py` needs no changes (its `"gimnasio-semana"` fixture
  tests prefix-agnostic behavior, not the real filenames).

## Out of scope

- Translating `running/coach-log.md`'s existing entries or the prior design
  docs (historical record).
- Regenerating `dist/` or deploying (`bash build.sh` / Cloudflare) — that is
  a separate, explicit action if/when the athlete wants to publish.
- Any engine (`parse-log.py`/`user_profile.py`) changes — `language` is
  coach-prose only.
- Supporting more than one language *at once* for the same athlete (the
  field holds a single current value; changing it is a future explicit
  request, not part of this design).
