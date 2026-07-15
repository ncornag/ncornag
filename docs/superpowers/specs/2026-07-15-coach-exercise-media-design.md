# Coach skill exercise media & metadata — design

**Date:** 2026-07-15
**Status:** Approved (brainstorming)

## Summary

The coach skill's gym files (`running/gym-week<N>.html`) describe each exercise
in text only — a numbered card with Position/Execution cues and a Watch note,
no visual reference. Add an optional demo GIF thumbnail and a target-muscle tag
to each exercise card, sourced from the public
[hasaneyldrm/exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset)
(1,324 exercises, MIT-licensed metadata + © Gym visual media). Matching an
athlete's exercise name to a dataset record is fuzzy and sometimes wrong (see
below), so the coach reviews and accepts/rejects each candidate — it is never
an automated best-score pick.

## Decisions (locked)

| Topic | Decision |
| --- | --- |
| Fields added to a card | A small demo GIF thumbnail (`.ex-media`) and the dataset's `target` muscle (`.ex-target`). **Not** the dataset's `equipment` field — cards already state the athlete's actual implement/load (e.g. "12 kg kettlebell"), and a generic equipment tag would contradict it. |
| Matching | Never auto-accept the top fuzzy-score candidate. `exercise-media.py search` returns ranked candidates; Claude reads the candidate's name/target/instructions and only proceeds if it is confident it is the same movement. Tested against real data: a naive best-score pick would attach "hip raise (bent knee)" (a glute bridge) to "Calf Raise Bent-Knee" — wrong exercise, high token overlap. |
| No-match behavior | If no candidate is a confident match, leave the card exactly as it is today — no media, no tag, no error. This is expected, not an edge case: this dataset skews toward equipped gym-machine names and misses several of this plan's trail-specific bodyweight/isometric moves (Bulgarian split squat, side plank, the custom high step-up + eccentric descent). |
| Data source | A one-time vendored local snapshot, `.claude/skills/coach/data/exercises.json` (~400KB, trimmed from the 16MB upstream `data/exercises.json` to the fields below). Not fetched live on every `/coach` run — refreshed manually, rarely, per a documented command in SKILL.md Notes. |
| Media storage | Vendored on first confirmed use into `running/assets/exercises/<slug>.jpg` + `.gif`, `<slug>` derived from the athlete's own exercise name — kebab-case: lowercase, each run of non-alphanumeric characters collapsed to a single hyphen, leading/trailing hyphens stripped (e.g. "Dead Bug" → `dead-bug`, "One-Arm Bent-Over Row" → `one-arm-bent-over-row`) — not the dataset id, so the same slug is reused (no re-fetch) if the same exercise recurs in a later week. |
| Attribution | One shared line per gym-file page ("Exercise demo images © Gym visual — https://gymvisual.com/"), added only if the page has at least one vendored image — satisfies the dataset's per-use attribution requirement without repeating it on every card. |
| Licensing risk | The dataset's own `NOTICE.md` states the media's redistribution permission was granted to that repo specifically ("cloning this repo is not a license"). This was flagged to and accepted by the athlete; out of scope to resolve further here. |
| Deploy | `build.sh` currently ships only `running/*.html` + `theme.css`; `running/assets` is added to its copy list so vendored media actually reaches the live site. |
| Scope | Ship the capability in SKILL.md now, **and** retrofit `running/gym-week10.html` (the currently-open week) as the first real example, using only the confidently-matched exercises. Weeks 3–9 (frozen) are untouched. |

## New files

### `.claude/skills/coach/data/exercises.json`

A trimmed, vendored snapshot of the upstream dataset — one array of 1,324
objects, each:

```json
{
  "id": "0276",
  "name": "dead bug",
  "target": "abs",
  "muscle_group": "hip flexors",
  "secondary_muscles": ["hip flexors", "lower back"],
  "equipment": "body weight",
  "image": "images/0276-iny3m5y.jpg",
  "gif_url": "videos/0276-iny3m5y.gif",
  "attribution": "© Gym visual — https://gymvisual.com/"
}
```

Dropped fields: `category`/`body_part` (redundant with `target`), the 9-language
`instructions`/`instruction_steps` blobs (the bulk of the 16MB — the coach
writes its own cues, it doesn't need generic multilingual instructions),
`media_id`, `created_at`.

Refresh procedure (documented in SKILL.md Notes, not automated): re-fetch
`https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/data/exercises.json`
and re-run the same trim.

### `.claude/skills/coach/exercise-media.py`

Same shape as `parse-log.py`: a deterministic engine script, stdout is JSON,
docstring explains purpose/usage. Two subcommands:

```
exercise-media.py search "<exercise name>" [--top N] [--data FILE]
```
Normalizes both the query and every candidate name (lowercase, strip
non-alphanumerics to spaces, split to a token set), scores each candidate
`len(query_tokens & candidate_tokens) / max(len(query_tokens), len(candidate_tokens))`,
and prints the top `N` (default 5) with score > 0 as JSON:
```json
[{"id": "0409", "name": "dumbbell single leg calf raise", "score": 0.8,
  "target": "calves", "muscle_group": "hamstrings", "equipment": "dumbbell",
  "image": "images/...", "gif_url": "videos/..."}]
```

```
exercise-media.py fetch <id> <slug> [--repo DIR]
```
Looks up `id` in the snapshot, downloads its `image` and `gif_url` from
`https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/<path>`
(stdlib `urllib.request`, matching `parse-log.py`'s no-third-party-deps
convention) into `<repo>/running/assets/exercises/<slug>.jpg` and `.gif`.
Idempotent — skips any file that already exists. Prints the relative paths +
attribution as JSON:
```json
{"image": "assets/exercises/dead-bug.jpg", "gif": "assets/exercises/dead-bug.gif",
 "attribution": "© Gym visual — https://gymvisual.com/"}
```

### `.claude/skills/coach/test-exercise-media.py`

Plain-assert tests in the existing style (`test-parse-log.py`), covering the
pure scoring/normalization function against fixed fixtures (exact match scores
1.0, disjoint names score 0, partial overlap ranks as expected) and the
slug/path computation used by `fetch`'s idempotency check. No network calls in
tests.

## Card markup change

In an exercise's `.ex-header`, add a thumbnail next to the name:

```html
<div class="ex-num-name">
  <div class="ex-num">2</div>
  <img class="ex-media" src="assets/exercises/single-leg-calf-raise.gif"
       alt="Single-Leg Calf Raise demo" loading="lazy">
  <div class="ex-name">Single-Leg<br>Calf Raise</div>
</div>
```

And immediately after `.ex-header`, before the "Position" label:

```html
<div class="ex-target">Target: calves</div>
```

New CSS (added to the current foundation gym file, which is what future weeks
copy per SKILL.md's existing Template rule):

```css
.ex-media {
  width: 44px;
  height: 44px;
  border-radius: 4px;
  object-fit: cover;
  border: 1px solid var(--border);
  flex-shrink: 0;
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
```

Once per page, only if at least one exercise got a demo image, right after the
`.exercises` grid:

```html
<div class="media-attribution">Exercise demo images © Gym visual — https://gymvisual.com/</div>
```

## `SKILL.md` changes

1. **Files table**: add rows for `.claude/skills/coach/data/exercises.json`
   (vendored exercise-dataset snapshot) and `.claude/skills/coach/exercise-media.py`
   (matching/vendoring engine).
2. **Gym programming**: new step after cues are written for an exercise —
   run `exercise-media.py search "<name>"`, judge the candidates (read
   name/target, not just the score), and only on a confident match run
   `fetch` and add the `.ex-media`/`.ex-target` markup + page attribution
   line. No match → leave the card as-is, silently.
3. **Template bullet**: note the card now optionally carries `.ex-media` +
   `.ex-target`, and the CSS above is part of what's copied forward.
4. **Notes**: document the snapshot refresh command, and that
   `running/assets/exercises/` media is real image data (not engine output) —
   never regenerated by `parse-log.py`.

## `build.sh` change

Add `running/assets` to the copy step so vendored media reaches the deploy:

```bash
cp -R running/assets dist/running/
```

(Create `running/assets/exercises/` as part of this change if it doesn't
already hold files.)

## Retrofit: `running/gym-week10.html`

Apply to the 4 exercises with a confirmed match (instructions verified against
the dataset, not just name score):

| Card | Matched dataset record | target |
| --- | --- | --- |
| Single-Leg Calf Raise | `dumbbell single leg calf raise` (id 0409) | calves |
| Single-Leg Glute Bridge | `single leg bridge with outstretched leg` (id 3645) | glutes |
| Dead Bug | `dead bug` (id 0276) | abs |
| One-Arm Bent-Over Row | `dumbbell one arm bent-over row` (id 0292) | upper back |

Left untouched (no confident match): Bulgarian Split Squat, Side Plank, High
Step-up + Eccentric Descent, Calf Raise Bent-Knee.

## Testing / verification

- `python3 .claude/skills/coach/test-exercise-media.py` passes.
- `exercise-media.py search` and `fetch` run standalone from the repo root
  and produce the documented JSON shapes.
- `bash build.sh` output includes `dist/running/assets/exercises/*.gif` for
  the 4 vendored exercises.
- `git diff` review of `gym-week10.html`: only the 4 matched cards and the one
  attribution line change; HTML stays well-formed (tags balanced); the other
  4 cards are byte-identical to before.
- Re-running `exercise-media.py fetch` for an already-vendored slug is a
  no-op (idempotent — zero new network calls, zero file changes).

## Out of scope

- Automated/periodic refresh of the vendored dataset snapshot (manual,
  documented command only).
- Retrofitting gym-week3–9 (frozen weeks, per SKILL.md's existing rule —
  revisit only for a reported niggle).
- Resolving the media-reuse licensing question beyond flagging it (see
  Decisions table).
- Any `parse-log.py`/`user_profile.py` engine changes — this is unrelated to
  activity-log parsing.
- Non-English languages in the vendored snapshot (dataset offers 9 languages
  of instructions; unused since Claude writes its own cues in the athlete's
  profile language, and instructions are dropped from the snapshot entirely).
