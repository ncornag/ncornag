---
name: sync-training-plan
description: Update the Dements 2026 trail-running training plan with logged activity data and add trail-running coach feedback. Use when the user wants to sync their running log, update the training plan, fold logged runs into the plan, or get coach feedback on their training week. Reads tcx CSV exports, maps activities to plan weeks, classifies heart-rate zones, and writes actuals panels, coach commentary, a next-week adjustment and a volume-chart overlay into running/dements-2026-plan.html.
user-invocable: true
---

# Sync Training Plan

Fold logged running data into `running/dements-2026-plan.html` and, acting as the
athlete's trail-running coach, write feedback on the week and adjust the plan
ahead.

## Files

| File                                             | Role                                                                                           |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `.claude/skills/sync-training-plan/parse-log.py` | Data engine — run it, use its JSON                                                             |
| `running/dements-2026-plan.html`                 | The plan — the file you edit                                                                   |
| `running/running-zones.html`                     | The athlete's lab HR zones — read for coach analysis                                           |
| `running/gimnasio-semana3.html`                  | The gym strength programme — read for coach context on StrengthTraining sessions for each week |
| `running/data/tcx-*.csv`                         | Activity exports (refreshed by the engine)                                                     |

The athlete is **57, with an injury history**; the plan's own principle is
"smart beats heroic." Coach accordingly — conservative, never push through
warning signs.

## Workflow

Do these steps in order. Steps 2–7 all edit `running/dements-2026-plan.html`.

### 1. Run the engine

```
python3 .claude/skills/sync-training-plan/parse-log.py
```

It refreshes the monthly CSVs (via `running/tcx-to-csv.sh`) and prints a JSON
summary on stdout. Parse that JSON — every later step uses it. If
`refresh_errors` is non-empty (e.g. Google Drive offline) that is fine: the
engine fell back to existing CSVs. Tell the user which weeks have data.

Key JSON fields: `current_week`, `weeks[]` (each with `status`, `plan_km`,
`plan_elev`, `actual_km`, `actual_elev`, `km_pct`, `polarized`, `avg_hr`,
`zone_km`, `activities[]`, `has_data`, `data_hash`, `actuals_html`,
`plan_days[]`), and `chart_js`.

`plan_days[]` is the planned day grid extracted from the HTML week card. Each
entry is `{"day":"Mon","type":"z2","km":"5km","label":"Z2"}`. `type` values:
`z2` / `z4` / `strides` / `trail-z2` / `trail-hike` / `rec` / `gym` / `rest`.
An empty list means the week card has no day grid (typically W1–W2). Use this
array when writing coach blocks so every factual claim about remaining sessions,
gym days, and session order is correct.

### 2. One-time setup (skip if already present)

Check `running/dements-2026-plan.html` for the marker `/* sync:styles */`. If it
is absent, this is the first run:

- Insert the **CSS block** (below) immediately before `</style>`.
- Mark the volume chart's render code: find the `weeks.forEach(w => {` block and
  its matching closing `});`, and replace that whole block with the engine's
  `chart_js` value, fenced by JS-comment markers each on their own line (a `<!--
-->` HTML comment is not valid inside `<script>`):
  ```
      // sync:chart
  <chart_js from JSON>
      // /sync:chart
  ```
  `maxKm`, `maxEl` and `chart` are declared just above and stay in scope.

### 3. Write the actuals panel for each week with data

For every `weeks[]` entry where `has_data` is true, in the matching `<div
class="week" id="wN">`, locate the `<div class="week-notes">…</div>` inside
`.week-body`. Immediately **after** the week-notes closing `</div>`, maintain:

```
      <!-- sync:actuals:wN -->
<actuals_html from JSON>
      <!-- /sync:actuals:wN -->
```

The engine's `actuals_html` is already rendered HTML — drop it in verbatim. If
the delimiters already exist, replace only what is between them. This is
deterministic: re-running with the same data must produce zero diff here.

### 4. Write the coach block for each week with data

Immediately after each `<!-- /sync:actuals:wN -->`, maintain a coach block:

```
      <!-- sync:coach:wN -->
      <div class="coach" data-hash="<data_hash from JSON>">
        <div class="coach-head">🧭 Coach</div>
        <div class="coach-body"><CONTENT></div>
      </div>
      <!-- /sync:coach:wN -->
```

**Idempotency:** if the block already exists and its `data-hash` attribute
equals the week's `data_hash` from the JSON, leave it untouched. Only
(re)write the block when the hash differs or the block is missing.

Write `<CONTENT>` as the athlete's **trail-running coach** — see Coach Voice
below. Write a full analysis for the current week and the most recently
completed week; for older weeks a one or two sentence note is enough.

A `done` or `current` week with **no** logged data still gets a coach block
(no actuals panel) flagging the missing data — silence on a missed week is bad
coaching.

### 5. Update week status

For every week, make the card match the JSON `status`:

- `done` → status badge `<span class="done-badge">Done ✓</span>`; remove
  `current`/`open` from the `<div class="week …">` class list.
- `current` → status badge `<span class="current-badge">Current</span>`; add
  `current` and `open` to the week div's classes.
- `upcoming` → no status badge; no `current`/`open`.

The status badge lives in `<div class="week-title">`. Replace any existing
status badge (`done-badge`, `current-badge`). **Preserve** `race-badge` and
`qualifier-badge` — those are not status badges. Keep `recovery-week` /
`race-week` / `qualifier-week` classes untouched.

### 6. Refresh the volume chart

Replace everything between `// sync:chart` and `// /sync:chart` with the
engine's `chart_js` value. This redraws each past week's bar as a planned track
with an actual fill. Deterministic — zero diff when data is unchanged.

Also keep the `weeks[]` array's per-entry `done` / `current` flags in sync with
each week's `status`: done weeks get `done: true`, the current week gets
`current: true` (and not `done`), upcoming weeks have neither. Preserve every
entry's `reco` / `peak` / `race` / `color` / `km` / `elev`.

### 7. Adjust the next week (only when warranted)

You may adjust **only** week `current_week + 1`. Adjust when the data clearly
calls for it, for example:

- The current or just-finished week is **>20% under** plan volume, or notably
  over.
- HR shows easy runs creeping into Z3+ (`polarized.tempo_pct` or `hard_pct`
  high when the week should be easy) — a sign of fatigue or pacing drift.
- A pattern of missed sessions.

When you adjust:

- Edit that week's day cells and the `week-km` / `week-elev` totals. Keep
  changes **small and specific** (e.g. trim one long run by 1–2 km), never a
  wholesale rewrite.
- Save the originals as `data-plan-km` / `data-plan-elev` attributes on that
  week's `<div class="week-stats">` (only if not already saved).
- Add `<span class="adjusted">adjusted</span>` to that week's `week-title`.
- Explain every change in the **current week's** coach block.

This must be reversible and idempotent: re-derive the adjustment from the JSON
baseline (`plan_km`/`plan_elev`) plus current data every run. If a previously
adjusted week is no longer warranted, restore the originals from
`data-plan-*`, remove the attributes and the `adjusted` badge.

The volume chart shows the original plan baseline; week-card adjustments are
not reflected in the chart.

### 8. Verify

- Re-run the engine and re-apply steps 3, 6: the deterministic regions
  (actuals panels, chart, CSS) must produce **zero diff** on the second pass.
- `git diff running/dements-2026-plan.html` — review that only intended
  regions changed and the HTML is well-formed (tags balanced).
- Summarise for the user: weeks updated, key coach points, any adjustment made.

## Coach Voice

Write as an experienced trail/ultra coach who knows this athlete and this race
(Marató dels Dements — 42.5 km, 3,808 m D+, Serra d'Espadà). Be direct,
specific, and encouraging; never generic.

- **Use the lab zones** from `running-zones.html`: Z1 `<135`, **Z2 135–151**
  (the athlete's focus), Z3 151–162, Z4 162–173, Z5 `>173`; VT1 151, VT2 173.
- **Check polarized discipline** — the plan is ~80% easy / ~20% hard, minimal
  Z3. Use the `polarized` percentages. Easy runs drifting into Z3 is the most
  common base-phase mistake; call it out.
- **Cite the data**: volume vs plan (`km_pct`), elevation, `avg_hr`,
  consistency, specific runs from `activities[]`.
- **Use `plan_days[]` for schedule facts**: before writing phrases like
  "gym on Tue/Thu", "three runs remain", "your long run is Saturday", derive
  those claims directly from `plan_days[]`. Count remaining run-type days
  (type `z2`, `z4`, `strides`, `trail-z2`, `trail-hike`, `rec`) after the last
  logged activity's date; list gym days by day name; never infer schedule from
  prose. If `plan_days` is empty, omit schedule-specific claims.
- Cover, in 3–6 sentences: how the week went, what was good, what to watch,
  and concrete guidance for the weeks ahead. Reference plan principles when
  relevant (vert specificity, power-hike practice, eccentric descents,
  back-to-back long days, "smart beats heroic").
- Wrap key phrases in `<strong>`. If you adjusted the next week, state exactly
  what changed and why.

## CSS block

Insert verbatim before `</style>` on first run:

```css
/* sync:styles */
/* injected by the sync-training-plan skill — do not edit by hand */
.actuals {
  margin-top: 0.7rem;
  background: var(--surface2);
  border-left: 2px solid #2ecc8a;
  border-radius: 4px;
  padding: 0.5rem 0.65rem;
}
.actuals-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.35rem;
}
.actuals-title {
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.actuals-sum {
  font-size: 0.62rem;
  font-weight: 500;
  color: var(--text);
  text-align: right;
}
.act-row {
  display: grid;
  grid-template-columns: 3.6rem 1.2rem 1fr 2.8rem 2.2rem 1.6rem 3.6rem;
  gap: 0.3rem;
  align-items: center;
  font-size: 0.62rem;
  color: var(--muted);
  padding: 0.14rem 0;
}
.act-when,
.act-km {
  color: var(--text);
}
.act-ico {
  text-align: center;
}
.act-zone {
  font-weight: 500;
  text-align: center;
}
.act-zone.z1 {
  color: #3a7bd5;
}
.act-zone.z2 {
  color: #2ecc8a;
}
.act-zone.z3 {
  color: #f0c040;
}
.act-zone.z4 {
  color: #f07030;
}
.act-zone.z5 {
  color: #d03050;
}
.act-pace {
  text-align: right;
}
.coach {
  margin-top: 0.5rem;
  background: var(--surface2);
  border-left: 2px solid #f07030;
  border-radius: 4px;
  padding: 0.55rem 0.65rem;
}
.coach-head {
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #f07030;
  margin-bottom: 0.3rem;
}
.coach-body {
  font-size: 0.66rem;
  color: var(--muted);
  line-height: 1.65;
}
.coach-body strong {
  color: var(--text);
}
.coach-body p {
  margin-bottom: 0.4rem;
}
.coach-body p:last-child {
  margin-bottom: 0;
}
.adjusted {
  display: inline-block;
  background: #f07030;
  color: #fff;
  font-size: 0.56rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  padding: 0.1rem 0.35rem;
  border-radius: 2px;
}
.vol-bar-track {
  background: var(--border);
  position: relative;
}
.vol-bar-fill {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 2px 2px 0 0;
  box-shadow: 0 -1px 0 rgba(255, 255, 255, 0.45) inset;
}
/* /sync:styles */
```

## Notes

- The engine owns the canonical plan baseline and all date math — never
  recompute week dates or zone boundaries by hand; use its JSON.
- Activities before 2026-05-11 or after the 26-week window are ignored.
- StrengthTraining activities count as sessions but contribute 0 km; they show
  as `gym` in the actuals panel. When coaching on a week that includes a gym
  session, read `running/gimnasio-3.html` for the exercise list and cues
  so your feedback is specific to what the athlete actually did in that week (3)
