# Coach Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `sync-training-plan` skill into a two-way `coach` that recalls past feedback, asks the athlete targeted questions, applies confirmed run/gym changes, maintains per-week gym tables (range-named when identical), and keeps all running pages linked.

**Architecture:** A deterministic Python engine (`parse-log.py`) gains additive gym-file discovery and per-week gym links; the `SKILL.md` instructions are rewritten around an interactive loop (sync → recall → check-in → respond/propose → write HTML → log → verify). Feedback persists to `running/coach-log.md`. Gym tables are per-week HTML files reusing the existing template, with identical consecutive weeks merged into `gimnasio-semana<N-M>.html`.

**Tech Stack:** Python 3 (stdlib only), static HTML/CSS/JS, Markdown. No test framework is installed — engine tests are plain-`assert` scripts run with `python3`; HTML/skill changes are verified by re-running the engine and checking zero-diff + `git diff`.

---

## File Structure

| File | Responsibility | Change |
| --- | --- | --- |
| `.claude/skills/coach/parse-log.py` | Deterministic engine; now also discovers gym files and emits per-week gym links | Move + modify |
| `.claude/skills/coach/SKILL.md` | Coach instructions: the interactive loop, log, gym programming | Move + rewrite |
| `.claude/skills/coach/test-parse-log.py` | Plain-assert unit tests for the new engine helpers | Create |
| `running/coach-log.md` | Persistent athlete-feedback journal (coach memory) | Create |
| `running/dements-2026-plan.html` | Plan; gym-link JS replaced with `// sync:gymlinks` block | Modify |
| `running/gimnasio-semana3-5.html` | Foundation gym table (weeks 3–5), renamed from `gimnasio-semana3.html`, label fixed, back-link added | Rename + modify |
| `running/index.html` | Hub; gym card label/href point at the current gym file | Modify |
| `running/running-zones.html` | Add back-to-index link | Modify |

**Note on scope:** Just-in-time gym authoring means only gym weeks up to `current_week+1` need a file. After this plan, gym chips in weeks **6+** become unlinked until the coach reaches them — this is by design, not a regression to fix here.

---

## Task 1: Rename the skill directory to `coach`

**Files:**
- Move: `.claude/skills/sync-training-plan/` → `.claude/skills/coach/`

- [ ] **Step 1: Move the directory with git**

```bash
cd /Users/ncornag/Dropbox/workspace/personal/profile
git mv .claude/skills/sync-training-plan .claude/skills/coach
rm -rf .claude/skills/coach/__pycache__
```

- [ ] **Step 2: Verify the engine still runs from the new path**

Run:
```bash
python3 .claude/skills/coach/parse-log.py --no-refresh --today 2026-05-29 > /tmp/coach-engine.json
python3 -c "import json; d=json.load(open('/tmp/coach-engine.json')); print('current_week', d['current_week'], 'activities', d['activity_count'])"
```
Expected: prints `current_week 3 activities <n>` with no traceback. (The engine derives repo root three levels up from the script, so the new path still resolves correctly.)

- [ ] **Step 3: Commit**

```bash
git add -A .claude/skills
git commit -m "refactor: rename sync-training-plan skill directory to coach"
```

---

## Task 2: Engine — discover gym files and map them to weeks (TDD)

**Files:**
- Modify: `.claude/skills/coach/parse-log.py`
- Test: `.claude/skills/coach/test-parse-log.py`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/coach/test-parse-log.py`:

```python
#!/usr/bin/env python3
"""Plain-assert tests for parse-log.py helpers. Run: python3 test-parse-log.py"""
import importlib.util
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "parse_log", os.path.join(HERE, "parse-log.py"))
pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pl)


def test_parse_gym_files_single_and_range():
    with tempfile.TemporaryDirectory() as d:
        for name in ("gimnasio-semana3-5.html", "gimnasio-semana7.html",
                     "theme.css", "index.html"):
            open(os.path.join(d, name), "w").close()
        m = pl.parse_gym_files(d)
        assert m == {3: "gimnasio-semana3-5.html",
                     4: "gimnasio-semana3-5.html",
                     5: "gimnasio-semana3-5.html",
                     7: "gimnasio-semana7.html"}, m


def test_parse_gym_files_empty():
    with tempfile.TemporaryDirectory() as d:
        assert pl.parse_gym_files(d) == {}


if __name__ == "__main__":
    test_parse_gym_files_single_and_range()
    test_parse_gym_files_empty()
    print("OK")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: FAIL with `AttributeError: module 'parse_log' has no attribute 'parse_gym_files'`.

- [ ] **Step 3: Implement `parse_gym_files` in `parse-log.py`**

Add near the other regex helpers (after the `_DAY_CELL_RE` block, before `parse_plan_days`):

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
        if not m:
            continue
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if hi < lo:
            lo, hi = hi, lo
        for wk in range(lo, hi + 1):
            mapping[wk] = os.path.basename(path)
    return mapping
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: prints `OK`.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/coach/parse-log.py .claude/skills/coach/test-parse-log.py
git commit -m "feat: discover gym files and map them to plan weeks"
```

---

## Task 3: Engine — emit `gym_links_js` (TDD)

**Files:**
- Modify: `.claude/skills/coach/parse-log.py`
- Test: `.claude/skills/coach/test-parse-log.py`

- [ ] **Step 1: Add the failing test**

Append these two tests to `test-parse-log.py` (and add their calls to the `__main__` block):

```python
def test_render_gym_links_js_has_map_and_walker():
    js = pl.render_gym_links_js({3: "gimnasio-semana3-5.html",
                                 4: "gimnasio-semana3-5.html"})
    assert '3: "gimnasio-semana3-5.html"' in js, js
    assert "document.querySelectorAll('.week[id]')" in js, js
    assert ".day.gym .day-km" in js, js


def test_render_gym_links_js_empty():
    js = pl.render_gym_links_js({})
    assert "const gymFiles = {}" in js, js
```

Update the `__main__` block to:

```python
if __name__ == "__main__":
    test_parse_gym_files_single_and_range()
    test_parse_gym_files_empty()
    test_render_gym_links_js_has_map_and_walker()
    test_render_gym_links_js_empty()
    print("OK")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: FAIL with `AttributeError: module 'parse_log' has no attribute 'render_gym_links_js'`.

- [ ] **Step 3: Implement `render_gym_links_js`**

Add it directly after `parse_gym_files` in `parse-log.py`:

```python
def render_gym_links_js(gym_files):
    """JS that links each week's gym day-chip to its mapped gym file.

    Emitted between the `// sync:gymlinks` markers in the plan HTML. Iterates
    every .week[id="wN"] so it covers future weeks too, not only those with
    logged data. Deterministic — identical input yields identical output.
    """
    if gym_files:
        entries = ", ".join(f"{wk}: {json.dumps(name)}"
                            for wk, name in sorted(gym_files.items()))
        obj = "{ " + entries + " }"
    else:
        obj = "{}"
    return (
        f"    const gymFiles = {obj};\n"
        "    document.querySelectorAll('.week[id]').forEach(wk => {\n"
        "      const n = parseInt(wk.id.slice(1), 10);\n"
        "      const file = gymFiles[n];\n"
        "      if (!file) return;\n"
        "      wk.querySelectorAll('.day.gym .day-km').forEach(el => {\n"
        "        el.innerHTML = `<a href=\"${file}\">${el.textContent}</a>`;\n"
        "      });\n"
        "    });"
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: prints `OK`.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/coach/parse-log.py .claude/skills/coach/test-parse-log.py
git commit -m "feat: render per-week gym-link JS block"
```

---

## Task 4: Engine — wire gym data into the JSON output

**Files:**
- Modify: `.claude/skills/coach/parse-log.py:443-483` (the `main` function)

- [ ] **Step 1: Add gym discovery and per-week `gym_file` in `main`**

In `main`, the block currently reads:

```python
    html_path = os.path.join(repo, "running", "dements-2026-plan.html")
    plan_days_by_week = parse_plan_days(html_path)
    weeks = aggregate(activities, today, plan_days_by_week)
    cw = week_of(today)
```

Replace it with:

```python
    running_dir = os.path.join(repo, "running")
    html_path = os.path.join(running_dir, "dements-2026-plan.html")
    plan_days_by_week = parse_plan_days(html_path)
    gym_files = parse_gym_files(running_dir)
    weeks = aggregate(activities, today, plan_days_by_week)
    for w in weeks:
        w["gym_file"] = gym_files.get(w["week"])
    cw = week_of(today)
```

- [ ] **Step 2: Add the three new top-level JSON fields**

The final `print(json.dumps({...}))` currently ends with:

```python
        "activity_count": len(activities),
        "weeks": weeks,
        "chart_js": render_chart_js(weeks),
    }, indent=2, ensure_ascii=False))
```

Replace with:

```python
        "activity_count": len(activities),
        "gym_files": gym_files,
        "current_gym_file": gym_files.get(cw),
        "weeks": weeks,
        "chart_js": render_chart_js(weeks),
        "gym_links_js": render_gym_links_js(gym_files),
    }, indent=2, ensure_ascii=False))
```

- [ ] **Step 3: Run the engine and confirm the new fields are present**

(The current gym file on disk is still `gimnasio-semana3.html`; Task 6 renames it. So week 3 maps to that file for now.)

Run:
```bash
python3 .claude/skills/coach/parse-log.py --no-refresh --today 2026-05-29 > /tmp/coach-engine.json
python3 -c "import json; d=json.load(open('/tmp/coach-engine.json')); print('current_gym_file:', d['current_gym_file']); print('gym_files:', d['gym_files']); print('has gym_links_js:', 'gym_links_js' in d); print('w3 gym_file:', d['weeks'][2]['gym_file'])"
```
Expected: `current_gym_file: gimnasio-semana3.html`, `gym_files: {'3': 'gimnasio-semana3.html'}`, `has gym_links_js: True`, `w3 gym_file: gimnasio-semana3.html`.

- [ ] **Step 4: Re-run the unit tests (no regression)**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: prints `OK`.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/coach/parse-log.py
git commit -m "feat: emit gym_files, current_gym_file and gym_links_js in engine output"
```

---

## Task 5: Plan HTML — replace the hardcoded gym link with the `// sync:gymlinks` block

**Files:**
- Modify: `running/dements-2026-plan.html:3024-3026`

- [ ] **Step 1: Capture the engine's gym-link JS**

Run:
```bash
python3 .claude/skills/coach/parse-log.py --no-refresh --today 2026-05-29 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['gym_links_js'])"
```
Keep the printed block; it is what goes between the markers.

- [ ] **Step 2: Replace the hardcoded link block**

In `running/dements-2026-plan.html`, find this exact block (currently around line 3024):

```javascript
    document.querySelectorAll('.day.gym .day-km').forEach(el => {
      el.innerHTML = `<a href="gimnasio-semana3.html">${el.textContent}</a>`;
    });
```

Replace it with the markers wrapping the captured `gym_links_js` (illustrative — use the exact output from Step 1):

```javascript
    // sync:gymlinks
    const gymFiles = { 3: "gimnasio-semana3.html" };
    document.querySelectorAll('.week[id]').forEach(wk => {
      const n = parseInt(wk.id.slice(1), 10);
      const file = gymFiles[n];
      if (!file) return;
      wk.querySelectorAll('.day.gym .day-km').forEach(el => {
        el.innerHTML = `<a href="${file}">${el.textContent}</a>`;
      });
    });
    // /sync:gymlinks
```

- [ ] **Step 3: Verify zero-diff on a second engine pass**

Re-run Step 1's command and confirm its output (between the markers) is byte-identical to what is now in the file. Then:
```bash
python3 -c "import re; h=open('running/dements-2026-plan.html').read(); assert h.count('// sync:gymlinks')==1 and h.count('// /sync:gymlinks')==1, 'markers'; print('markers OK')"
```
Expected: `markers OK`.

- [ ] **Step 4: Smoke-check the page is well-formed**

Run: `python3 -c "import html.parser,sys
class P(html.parser.HTMLParser): pass
P().feed(open('running/dements-2026-plan.html').read()); print('parsed OK')"`
Expected: `parsed OK` (no exception).

- [ ] **Step 5: Commit**

```bash
git add running/dements-2026-plan.html
git commit -m "feat: link gym day-chips per week via sync:gymlinks block"
```

---

## Task 6: Migrate the gym table to the range-named per-week scheme

**Files:**
- Rename: `running/gimnasio-semana3.html` → `running/gimnasio-semana3-5.html`
- Modify: the renamed file's title, subtitle, `<title>`, and add a back-to-index link

The current file is week 3's foundation table (mislabeled "Semana 1") and was used for weeks 3–5. Rename it to the range that reflects that and fix the labels.

- [ ] **Step 1: Rename the file**

```bash
git mv running/gimnasio-semana3.html running/gimnasio-semana3-5.html
```

- [ ] **Step 2: Fix the document `<title>`**

In `running/gimnasio-semana3-5.html`, change:
```html
  <title>Gimnasio Semana 1 — Vuelta al Trail</title>
```
to:
```html
  <title>Gimnasio Semana 3–5 — Vuelta al Trail</title>
```

- [ ] **Step 3: Fix the header title and subtitle**

Change:
```html
    <div class="title">GIMNASIO<br>SEMANA <span>1</span></div>
    <div class="subtitle">Vuelta al Trail · Fase de fundación · Nico</div>
```
to:
```html
    <div class="title">GIMNASIO<br>SEMANA <span>3–5</span></div>
    <div class="subtitle">Vuelta al Trail · Fase de fundación · Nico</div>
```

- [ ] **Step 4: Add a back-to-index link**

Immediately after the opening `<body>` line and before the `<button class="theme-toggle"...>` line, insert:
```html
  <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
```

- [ ] **Step 5: Verify the engine now maps weeks 3–5 to the renamed file**

Run:
```bash
python3 .claude/skills/coach/parse-log.py --no-refresh --today 2026-05-29 \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['gym_files']); print('current_gym_file:', d['current_gym_file'])"
```
Expected: `{'3': 'gimnasio-semana3-5.html', '4': 'gimnasio-semana3-5.html', '5': 'gimnasio-semana3-5.html'}` and `current_gym_file: gimnasio-semana3-5.html`.

- [ ] **Step 6: Re-apply the `sync:gymlinks` block with the updated map**

Re-run the command from Task 5 Step 1 and replace the content between `// sync:gymlinks` and `// /sync:gymlinks` in `running/dements-2026-plan.html` with the new output (now `{ 3: "gimnasio-semana3-5.html", 4: "gimnasio-semana3-5.html", 5: "gimnasio-semana3-5.html" }`).

- [ ] **Step 7: Commit**

```bash
git add running/gimnasio-semana3-5.html running/dements-2026-plan.html
git commit -m "feat: adopt range-named per-week gym table (weeks 3-5) and fix labels"
```

---

## Task 7: Fix cross-page linking (index + zones)

**Files:**
- Modify: `running/index.html:173-180`
- Modify: `running/running-zones.html` (after `<body>`)

- [ ] **Step 1: Point the index gym card at the current gym file with the right label**

In `running/index.html`, change:
```html
    <a class="link-card" href="gimnasio-semana3.html">
      <div class="link-icon">🏋️</div>
      <div class="link-info">
        <div class="link-name">Gimnasio — Semana 1</div>
        <div class="link-desc">Gym strength training programme, week 1</div>
      </div>
      <div class="link-arrow">›</div>
    </a>
```
to:
```html
    <a class="link-card" href="gimnasio-semana3-5.html">
      <div class="link-icon">🏋️</div>
      <div class="link-info">
        <div class="link-name">Gimnasio — Semana 3–5</div>
        <div class="link-desc">Gym strength training programme, current block</div>
      </div>
      <div class="link-arrow">›</div>
    </a>
```

- [ ] **Step 2: Add a back-to-index link to the zones page**

In `running/running-zones.html`, the body starts:
```html
<body>
  <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>
```
Insert a link between those two lines:
```html
<body>
  <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
  <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>
```

- [ ] **Step 3: Verify links resolve to existing files**

Run:
```bash
python3 -c "
import re,os
os.chdir('running')
for f in ['index.html','running-zones.html','gimnasio-semana3-5.html']:
    for href in re.findall(r'href=\"([^\"#:]+\.html)\"', open(f).read()):
        assert os.path.exists(href), f'{f} -> missing {href}'
print('all html links resolve')"
```
Expected: `all html links resolve`.

- [ ] **Step 4: Commit**

```bash
git add running/index.html running/running-zones.html
git commit -m "feat: fix gym card label/target and add back-to-index links"
```

---

## Task 8: Seed the feedback log

**Files:**
- Create: `running/coach-log.md`

- [ ] **Step 1: Create the log with its header**

Create `running/coach-log.md`:

```markdown
# Coach log — Dements 2026

Running journal of athlete feedback and coach responses. The coach reads this
every time `/coach` runs (memory), then appends or updates today's entry. You may
edit it by hand. Newest entries first. One entry per date.

Entry shape:

    ## YYYY-MM-DD · Week N
    **You:** what the athlete reported / asked.
    **Coach:** answers, any change proposed and whether applied, open threads to watch.

---

<!-- entries below, newest first -->
```

- [ ] **Step 2: Commit**

```bash
git add running/coach-log.md
git commit -m "feat: add coach feedback log"
```

---

## Task 9: Rewrite SKILL.md as the interactive coach

**Files:**
- Modify: `.claude/skills/coach/SKILL.md`

This rewrites the front matter and workflow. The **CSS block** section and the
**Coach Voice** section are unchanged in substance — keep them as they currently
are in the file (only the file moved in Task 1). The changes below replace the
front matter, the Files table, and the Workflow, and add three new sections.

- [ ] **Step 1: Replace the YAML front matter**

Replace lines 1–5 (the `--- … ---` block) with:

```markdown
---
name: coach
description: Acts as the athlete's trail-running coach for the Dements 2026 race. Use when the user runs /coach, wants to sync their running log, get feedback on a training week, give feedback to their coach, ask a training question, or update the gym programme. Syncs logged TCX activity into running/dements-2026-plan.html, recalls past feedback from running/coach-log.md, asks targeted check-in questions, applies confirmed run/gym adjustments, maintains per-week gym tables, and writes coach commentary.
user-invocable: true
---
```

- [ ] **Step 2: Replace the intro + Files table**

Replace the current intro paragraph and Files table (the `# Sync Training Plan`
heading through the end of the Files table, down to the "smart beats heroic"
paragraph) with:

```markdown
# Coach

You are the athlete's trail-running coach for the **Marató dels Dements** (42.5 km,
3,808 m D+, Serra d'Espadà). Each run of this skill is a coaching session: sync the
logged data, recall what the athlete told you before, ask how things are going,
answer their questions, adjust the plan (with their OK), and record the exchange.

## Files

| File | Role |
| --- | --- |
| `.claude/skills/coach/parse-log.py` | Data engine — run it, use its JSON. Never recompute its outputs by hand. |
| `running/coach-log.md` | Athlete-feedback journal — your memory. Read every run, append/update each run. |
| `running/dements-2026-plan.html` | The plan — the file you edit. |
| `running/running-zones.html` | The athlete's lab HR zones — read for coach analysis. |
| `running/gimnasio-semana<N>.html` | Per-week gym tables (range-named when identical, e.g. `gimnasio-semana3-5.html`). |
| `running/data/tcx-*.csv` | Activity exports (refreshed by the engine). |

The athlete is **57, with an injury history**; the plan's own principle is
"smart beats heroic." Coach accordingly — conservative, never push through
warning signs.
```

- [ ] **Step 3: Replace the "## Workflow" heading and step 1 intro with the new loop overview**

Replace the `## Workflow` line and its lead paragraph ("Do these steps in order…")
with:

```markdown
## Workflow

A `/coach` run has three movements: **A. Listen** (sync data + recall log + check in
with the athlete), **B. Act** (answer questions, propose and — once confirmed — apply
changes), **C. Record** (write the HTML, update gym tables, append the log, verify).

Steps 3–10 edit `running/dements-2026-plan.html`. Do them in order.

### A1. Run the engine

```
python3 .claude/skills/coach/parse-log.py
```

It refreshes the monthly CSVs and prints a JSON summary on stdout. Parse it — every
later step uses it. If `refresh_errors` is non-empty (e.g. Google Drive offline) that
is fine: the engine fell back to existing CSVs. Tell the user which weeks have data.

Key JSON fields: `current_week`, `current_gym_file`, `gym_files` (week→file map),
`gym_links_js`, and `weeks[]` (each with `status`, `plan_km`, `plan_elev`,
`actual_km`, `actual_elev`, `km_pct`, `polarized`, `avg_hr`, `zone_km`,
`activities[]`, `has_data`, `data_hash`, `actuals_html`, `plan_days[]`,
`logged_days`, `days_html`, `gym_file`), plus `chart_js`.

`plan_days[]` is the planned day grid extracted from the HTML week card. Each entry is
`{"day":"Mon","type":"z2","km":"5km","elev":"","label":"Z2"}`. `type` values: `z2` /
`z4` / `strides` / `trail-z2` / `trail-hike` / `rec` / `gym` / `rest`. Use this array
for every factual claim about remaining sessions, gym days, and session order.

`logged_days` is a sorted list of weekday abbreviations for days with at least one
logged activity that week. `days_html` is the regenerated `<div class="days">…</div>`
block with a green `.day-done-dot` in each logged chip (null when `plan_days` is empty).

### A2. Recall the log

Read `running/coach-log.md` start to finish. Note the most recent entries, any **open
threads** (niggles you said you'd watch, questions you deferred, changes you proposed
but didn't apply), and prior recommendations. Carry these into the check-in.

### A3. Check in with the athlete (interactive)

Ask the athlete **2–4 targeted questions**, driven by the data and open threads — not a
generic survey. Examples: an easy run whose `avg_hr` landed in Z3 ("did that feel hard,
or was it terrain?"); a reported niggle from a past entry ("how's the knee since last
week?"); a missed or short session; a gym session that week. Invite their own questions
too. If the athlete has nothing to report, say so and proceed on the data alone.

### B1. Respond and propose (interactive)

Answer the athlete's questions directly as their coach. When the data or their feedback
warrants a change, propose a **specific, small** change and get explicit confirmation
before applying it. You may change two things:

- **Upcoming runs** — only week `current_week + 1` (see step 10).
- **The gym table** — the current or upcoming gym week (see "Gym programming").

Never change runs or the gym silently. If the athlete declines, record that you offered
and they declined, and leave the plan as the engine baseline dictates.
```

- [ ] **Step 4: Renumber the existing deterministic steps and keep their contracts**

The existing steps "2. One-time setup", "3. Refresh the day-chip grid", "4. Write the
actuals panel", "5. Write the coach block", "6. Update week status", "7. Refresh the
volume chart", "8. Adjust the next week", "9. Verify" keep their bodies **verbatim**,
renumbered as **C1–C8** with these two edits:

  1. In the renumbered "One-time setup" step (was 2), append a third bullet after the
     chart bullet:

```markdown
- Mark the gym links: find the `document.querySelectorAll('.day.gym .day-km')` block
  near the end of `<script>` and replace it with the engine's `gym_links_js`, fenced by
  `// sync:gymlinks` / `// /sync:gymlinks` markers each on its own line. On later runs,
  replace only what is between the markers (deterministic — zero diff when `gym_files`
  is unchanged).
```

  2. In the renumbered "Adjust the next week" step (was 8), change the opening sentence
     from "You may adjust **only** week `current_week + 1`." to:

```markdown
You may adjust **only** week `current_week + 1`, and **only after the athlete confirmed
the change in step B1**. The triggers below are when to *propose* an adjustment, not to
apply one unprompted.
```

- [ ] **Step 5: Add the "Gym programming" section**

After the renumbered verify step (C8) and before "## Coach Voice", insert:

```markdown
## Gym programming

Maintain per-week gym tables as the plan advances — just-in-time, not all 26 at once.

- **Coverage:** ensure every gym week from gym-start (week 3) through `current_week + 1`
  has a file in `running/`. Past gym weeks are **frozen** — only revisit one to address a
  niggle the athlete reported.
- **Template:** copy the structure and CSS of the current foundation table
  (`gimnasio-semana3-5.html`): theme bootstrap, `GIMNASIO SEMANA N` title, phase
  subtitle, stat pills, warmup card, exercise grid (`.exercise` with `.cues` and
  `.ex-watch`), and the expected/warning footer. Include the back-to-index link
  (`<a href="index.html">‹ Running</a>` right after `<body>`).
- **Progression:** evolve content by phase — foundation (bodyweight, form) → strength
  (add load) → vert/power (step-ups, eccentric descents) → taper (reduce volume) — and by
  athlete feedback (e.g. swap an exercise that aggravates a joint).
- **Dedup → ranges:** if a week's programme is identical to the previous week's, do **not**
  create a new file. Name the shared file `gimnasio-semana<N-M>.html` (e.g.
  `gimnasio-semana3-5.html` covers weeks 3–5). When a later week diverges, split: shrink the
  range and create the new file. The files must tile the gym weeks without overlap.
- **Linking:** after creating, renaming, or splitting a gym file, re-run the engine and
  re-apply the `// sync:gymlinks` block (C1) and the index gym card so links stay correct.
  The engine derives the week→file map from the filenames — you do not hand-edit the map.
```

- [ ] **Step 6: Add the "Feedback log" section**

After "Gym programming", insert:

```markdown
## Feedback log

`running/coach-log.md` is your memory. Newest entry first, one entry per date.

- **Read** it in step A2, every run.
- **Write** after the session: append a new dated entry, or update today's entry in place
  if `/coach` was already run today (never duplicate a date). Capture, briefly: what the
  athlete reported or asked (**You:**), and your response — answers given, any change
  proposed and whether it was applied or declined, and open threads to watch (**Coach:**).
- Keep entries short and factual; the prose coaching lives in the plan's coach blocks.
```

- [ ] **Step 7: Update the trailing Notes**

In the final "## Notes" section, replace the last bullet (the one mentioning
`running/gimnasio-3.html` / "week (3)") with:

```markdown
- StrengthTraining activities count as sessions but contribute 0 km; they show as `gym`
  in the actuals panel. When coaching a week with a gym session, read that week's gym file
  (`weeks[].gym_file` from the engine) for the exercise list and cues so feedback is
  specific to what the athlete actually did.
```

- [ ] **Step 8: Verify the rewritten SKILL.md is coherent**

Run:
```bash
python3 -c "
t=open('.claude/skills/coach/SKILL.md').read()
assert t.startswith('---\nname: coach\n'), 'front matter'
for s in ['## Gym programming','## Feedback log','sync:gymlinks','coach-log.md','A2. Recall','B1. Respond']:
    assert s in t, f'missing: {s}'
assert 'gimnasio-3.html' not in t, 'stale path remains'
print('SKILL.md OK')"
```
Expected: `SKILL.md OK`.

- [ ] **Step 9: Commit**

```bash
git add .claude/skills/coach/SKILL.md
git commit -m "feat: rewrite coach skill as interactive feedback loop with gym programming"
```

---

## Task 10: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Engine + unit tests green**

Run: `python3 .claude/skills/coach/test-parse-log.py`
Expected: `OK`.

- [ ] **Step 2: Deterministic regions are zero-diff**

Re-run the engine and confirm the `gym_links_js` between the markers in the plan HTML
matches the fresh output:
```bash
python3 .claude/skills/coach/parse-log.py --no-refresh --today 2026-05-29 \
  | python3 -c "
import sys,json,re
d=json.load(sys.stdin)
h=open('running/dements-2026-plan.html').read()
block=re.search(r'// sync:gymlinks\n(.*?)\n\s*// /sync:gymlinks', h, re.S).group(1)
assert d['gym_links_js'].strip() == block.strip(), 'gymlinks drift'
print('gymlinks zero-diff OK')"
```
Expected: `gymlinks zero-diff OK`.

- [ ] **Step 3: All inter-page HTML links resolve**

Run:
```bash
python3 -c "
import re,os
os.chdir('running')
pages=['index.html','running-zones.html','dements-2026-plan.html','gimnasio-semana3-5.html']
for f in pages:
    for href in re.findall(r'href=\"([^\"#:]+\.html)\"', open(f).read()):
        assert os.path.exists(href), f'{f} -> missing {href}'
print('all html links resolve')"
```
Expected: `all html links resolve`.

- [ ] **Step 4: Review the full diff**

Run: `git log --oneline -10` and `git diff --stat HEAD~9..HEAD`
Confirm only the intended files changed: the skill move + edits, the four running HTML
files, and `running/coach-log.md`.

- [ ] **Step 5: Manual smoke (optional)**

Open `running/index.html` in a browser; click through to the plan and confirm a gym
day-chip in weeks 3–5 links to `gimnasio-semana3-5.html`, and each page has a working
back-to-index link.

---

## Self-Review notes

- **Spec coverage:** rename (T1, T9) · interactive loop A/B/C (T9) · coach-log.md format
  (T8, T9) · per-week gym tables + range dedup (T6, T9) · engine gym discovery/links (T2–T5)
  · linking cleanup (T6, T7) · confirmation-gated run/gym changes (T9 step 4) · keep-HTML-as-is
  (no athlete-note markup added) · back-to-index nav (T6, T7).
- **Just-in-time consequence:** gym chips in weeks 6+ are unlinked until the coach authors
  those weeks — documented as intended in File Structure, not a bug.
- **Type/name consistency:** `parse_gym_files`, `render_gym_links_js`, `gym_files`,
  `current_gym_file`, `gym_links_js`, `gym_file` (per week), and the `// sync:gymlinks`
  markers are used identically across Tasks 2–6, 9 and 10.
