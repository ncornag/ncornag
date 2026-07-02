# Coach language preference + gym-week translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the athlete's language an explicit profile setting the `coach` skill asks for once and then uses everywhere, and bring the current athlete's seven gym-week files in line with it (Spanish → English, renamed to an English filename prefix).

**Architecture:** A new `## Language` section in `running/data/user.md` (pure coach-prose, no engine parsing) plus a new first step in `coach/SKILL.md` that reads it or asks for it. The seven existing `gimnasio-semana<N>.html` files are `git mv`'d to `gym-week<N>.html` and their visible text translated to English; `gym_prefix` in the profile, `index.html`'s gym card, and the plan file's engine-owned `// sync:gymlinks` block are updated to match.

**Tech Stack:** Static HTML/CSS/JS (no build step for `running/`), Python 3 stdlib (`parse-log.py`), Markdown profile.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-02-coach-language-design.md` — every task below implements one part of it.
- `language` is **never** read by `parse-log.py` / `user_profile.py` — it is coach-prose only.
- `running/coach-log.md`'s existing entries, the two prior `docs/superpowers/{specs,plans}/*.md` design docs, and `dist/` are **not** touched by this plan.
- Every gym-file translation changes **only visible text nodes** (titles, labels, cues, list items) — CSS, class names, attributes, and HTML structure stay byte-identical to the source file being translated.
- Translation glossary (apply consistently across every gym file):

  | Spanish | English |
  | --- | --- |
  | Gimnasio / Semana N | Gym / Week N |
  | Vuelta al Trail | Return to Trail |
  | Fase de fundación | Foundation phase |
  | Semana de descarga / descarga | Deload week / deload |
  | Fuerza + Vert | Strength + Vert |
  | Frecuencia | Frequency |
  | Días / Día | Days / Day |
  | Duración | Duration |
  | Cuando | When |
  | Después de correr | After running |
  | Series | Sets |
  | Descanso | Rest |
  | entre series | between sets |
  | Entre ejercicios | Between exercises |
  | Carga | Load |
  | Calentamiento | Warm-up |
  | Ejercicios | Exercises |
  | Posición | Position |
  | Ejecución | Execution |
  | Ojo: | Watch: |
  | Esperable esta semana | Expected this week |
  | Señales de alarma · parar y revisar | Warning signs · stop and reassess |
  | Sentadilla Búlgara | Bulgarian Split Squat |
  | Elevación de Talón Unilateral | Single-Leg Calf Raise |
  | Puente de Glúteos | Glute Bridge |
  | Puente de Glúteos a Una Pierna | Single-Leg Glute Bridge |
  | Plancha Lateral | Side Plank |
  | Step-up + Bajada Excéntrica | Step-up + Eccentric Descent |
  | Step-up Alto + Bajada Excéntrica | High Step-up + Eccentric Descent |
  | pierna / lado | leg / side |
  | talón(es) | heel(s) |
  | rodilla | knee |
  | cadera(s) | hip(s) |
  | glúteo(s) / culo | glute(s) |
  | isquios | hamstrings |
  | Aquiles | Achilles |
  | lumbar | lower back |
  | cuádriceps | quads |

- **Head/CSS reuse rule (all gym-file tasks):** the `<head>`/`<style>` block (current file's lines 1–385) is byte-identical across all seven gym files except two spots: `<html lang="es"` (line 2) and the `<title>` tag (line 7). Every gym-file task says "copy the current file's lines 1–385 verbatim, then apply the two substitutions below" instead of repeating 385 lines of CSS per task.
- **Structural verification rule (all gym-file tasks):** after writing a translated file, its tag histogram must exactly match the pre-translation original (`git show HEAD:running/<old-name>.html`) — see the verification step template in Task 2, reused identically in Tasks 3–8.

---

### Task 1: Language field + SKILL.md language step

**Files:**
- Modify: `running/data/user.md`
- Modify: `.claude/skills/coach/SKILL.md`

**Interfaces:**
- Produces: the `## Language` section convention (`- language: <name>`) that Task 9's `index.html`/SKILL.md example updates assume already exists as a pattern.

- [ ] **Step 1: Add the `## Language` section to the profile**

  In `running/data/user.md`, insert a new section immediately after the `## Paths` section (i.e. right before `## Athlete`):

  ```markdown
  ## Language

  - language: English
  ```

  Use the Edit tool with this exact anchor (from the current file):

  old_string:
  ```
  - gym_prefix: gimnasio-semana

  ## Athlete
  ```

  new_string:
  ```
  - gym_prefix: gimnasio-semana

  ## Language

  - language: English

  ## Athlete
  ```

  (Task 9 changes `gym_prefix` to `gym-week` — do not change it here, keep this step scoped to adding the Language section only.)

- [ ] **Step 2: Verify**

  Run: `sed -n '1,20p' running/data/user.md`
  Expected: the new `## Language` / `- language: English` section appears between `## Paths` and `## Athlete`.

- [ ] **Step 3: Add the "confirm language" step to SKILL.md's workflow**

  In `.claude/skills/coach/SKILL.md`, insert a new `### A0` step before `### A1. Sync Garmin, then run the engine`.

  old_string:
  ```
  Steps C1–C8 edit the plan file. Do the movements in order.

  ### A1. Sync Garmin, then run the engine
  ```

  new_string:
  ````
  Steps C1–C8 edit the plan file. Do the movements in order.

  ### A0. Confirm the athlete's language

  Check the profile's `## Language` section (`running/data/user.md`) for a
  `language:` field. If it is present, use that language for the rest of this
  session — your chat replies, the coach block prose (C4), gym-table content, and
  `coach-log.md` entries (see Feedback log). If it is **absent**, this is the
  athlete's first session: ask which language they'd like before doing anything
  else, then write their answer into a new `## Language` section in
  `running/data/user.md`:

  ```
  ## Language

  - language: <name>
  ```

  From then on every session reads it silently — never ask again unless the
  athlete asks to change it.

  ### A1. Sync Garmin, then run the engine
  ````

- [ ] **Step 4: Add the language rule to Coach Voice**

  old_string:
  ```
  - **Use the HR zones from the profile** (`running/data/user.md`): the zone table
    gives each zone's lower bound, plus VT1/VT2. Z2 is the athlete's easy-aerobic focus.
  ```

  new_string:
  ```
  - **Write in the athlete's profile language** (`## Language` in
    `running/data/user.md`) — chat replies, coach-block prose, gym-table content,
    and `coach-log.md` entries all follow it.
  - **Use the HR zones from the profile** (`running/data/user.md`): the zone table
    gives each zone's lower bound, plus VT1/VT2. Z2 is the athlete's easy-aerobic focus.
  ```

- [ ] **Step 5: Add the language note to the Feedback log section**

  old_string:
  ```
  - Keep entries short and factual; the prose coaching lives in the plan's coach blocks.
  ```

  new_string:
  ```
  - Keep entries short and factual; the prose coaching lives in the plan's coach blocks.
  - Written in the athlete's profile language (`## Language`, `running/data/user.md`).
  ```

- [ ] **Step 6: Verify**

  Run: `grep -n "A0. Confirm the athlete's language\|Write in the athlete's profile language\|Written in the athlete's profile language" .claude/skills/coach/SKILL.md`
  Expected: three matches, one per inserted spot.

- [ ] **Step 7: Commit**

  ```bash
  git add running/data/user.md .claude/skills/coach/SKILL.md
  git commit -m "feat(coach): add athlete language preference to profile + workflow"
  ```

---

### Task 2: Rename + translate gym-week 3

**Files:**
- Rename: `running/gimnasio-semana3.html` → `running/gym-week3.html`

- [ ] **Step 1: Rename**

  ```bash
  git mv running/gimnasio-semana3.html running/gym-week3.html
  ```

- [ ] **Step 2: Rewrite the head (2 substitutions on the copied lines 1–385)**

  Take the file's current lines 1–385 verbatim and apply:
  - Line 2: `<html lang="es" data-theme="dark">` → `<html lang="en" data-theme="dark">`
  - Line 7: `<title>Gimnasio Semana 3–5 — Vuelta al Trail</title>` → `<title>Gym Week 3–5 — Return to Trail</title>`

- [ ] **Step 3: Replace the body (everything from `<body>` to end of file) with this exact content**

  ```html
  <body>

    <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
    <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>

    <header>
      <div class="title">GYM<br>WEEK <span>3</span></div>
      <div class="subtitle">Return to Trail · Foundation phase · Nico</div>
      <div class="stats-row">
        <div class="stat-pill">Frequency <strong>2× / week</strong></div>
        <div class="stat-pill">Days <strong>Tue + Thu</strong></div>
        <div class="stat-pill">Duration <strong>~35 min</strong></div>
        <div class="stat-pill hi">When <strong>After running</strong></div>
        <div class="stat-pill">Rest <strong>90s between sets</strong></div>
        <div class="stat-pill">Between exercises <strong>2 min</strong></div>
      </div>
    </header>

    <div class="warmup-card">
      <div class="warmup-label">⚡ Warm-up · 5 min</div>
      <div class="warmup-body">
        Easy bike or jog 5 min → 10 leg swings each direction per leg → 10 bodyweight squats.
        <strong>Form > load</strong> — master the patterns before adding weight. Stop one rep before failure on each
        set.
      </div>
    </div>

    <div class="section-label">Exercises</div>

    <div class="exercises">

      <!-- 1 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">1</div>
            <div class="ex-name">Bulgarian<br>Split Squat</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Back foot on the bench, laces down</li>
          <li>Front foot forward — knee doesn't pass the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Lower until the thigh is ≈ parallel to the floor</li>
          <li>Torso slightly leaned forward</li>
          <li>Push through the whole foot, mainly the heel</li>
          <li>Back leg = support, 90% of the work is the front leg</li>
          <li><strong>Week 1: bodyweight</strong></li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> knee caving inward · weight on the back leg · front foot
          too close</div>
      </div>

      <!-- 2 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">2</div>
            <div class="ex-name">Single-Leg<br>Calf Raise</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Ball of the foot on the edge of a step, heel in the air</li>
          <li>Hold something for balance, not to support your weight</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Rise all the way up, squeeze at the top for 1 sec</li>
          <li><strong>Lower in 3 seconds</strong> — slow eccentric</li>
          <li>Heel below the step for full range of motion</li>
          <li>The slow descent strengthens the Achilles</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> lowering too fast — brake more than you think you need to</div>
      </div>

      <!-- 3 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">3</div>
            <div class="ex-name">Glute<br>Bridge</div>
          </div>
          <div class="ex-sets">3 × 15</div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, knees bent, feet hip-width apart</li>
          <li>Heels close to your glutes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Push through your heels</strong>, not your toes</li>
          <li>Rise until shoulders / hips / knees are in one line</li>
          <li>Squeeze your glutes, hold 2 sec at the top</li>
          <li>Ribs down — don't arch your lower back</li>
          <li>Drive up from your glutes, not your back</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hamstring cramps = bring your feet closer to your glutes</div>
      </div>

      <!-- 4 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">4</div>
            <div class="ex-name">Dead<br>Bug</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, arms straight up toward the ceiling</li>
          <li>Knees at 90° over your hips (tabletop)</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Lower back pressed to the floor</strong> — the key point</li>
          <li>Slowly extend the opposite arm + leg</li>
          <li>Without touching the floor, return, switch sides</li>
          <li>Flat back &gt; range of motion</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> back arching as you extend the leg → reduce the range</div>
      </div>

      <!-- 5 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">5</div>
            <div class="ex-name">Side<br>Plank</div>
          </div>
          <div class="ex-sets">3 × 20s<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Side plank on your forearm</li>
          <li>Body in a straight line from head to feet</li>
          <li>Hips stacked, not rotated or dropped</li>
          <li>Bottom leg on the floor, top leg stacked on top</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Brace your obliques and core, keep a straight line</li>
          <li>Breathe, don't hold your breath</li>
          <li>Primary work: adductors and lateral stabilizers</li>
          <li>Cut the time short if your hips drop — form &gt; duration</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hips dropping or rotating — cut the time before your form breaks</div>
      </div>

    </div>

    <div class="footer">
      <div class="footer-card expected">
        <div class="footer-title">✓ Expected this week</div>
        <ul class="footer-list">
          <li>Muscle soreness in glutes, adductors, and calves for 2–3 days</li>
          <li>Balance trouble in the split squat — completely normal</li>
          <li>You'll be surprised how hard bodyweight alone is</li>
          <li>Form > load. Master the patterns before adding weight</li>
        </ul>
      </div>
      <div class="footer-card warn">
        <div class="footer-title">⚠ Warning signs · stop and reassess</div>
        <ul class="footer-list">
          <li>Sharp pain (vs. muscle burn) anywhere</li>
          <li>Lower-back pain after dead bugs / bridges → poor activation</li>
          <li>Knee pain in the split squat → front foot or knee position is off</li>
          <li>Achilles discomfort &gt; 48h → reduce calf-raise volume</li>
        </ul>
      </div>
    </div>

    <script>
      function toggleTheme() {
        const html = document.documentElement;
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', html.dataset.theme); } catch (e) { }
      }
    </script>
  </body>

  </html>
  ```

- [ ] **Step 4: Structural verification**

  Run:
  ```bash
  diff <(git show HEAD:running/gimnasio-semana3.html | grep -o '<[a-zA-Z][a-zA-Z0-9-]*' | sort | uniq -c) \
       <(grep -o '<[a-zA-Z][a-zA-Z0-9-]*' running/gym-week3.html | sort | uniq -c)
  echo "div open=$(grep -o '<div' running/gym-week3.html | wc -l) close=$(grep -o '</div>' running/gym-week3.html | wc -l)"
  ```
  Expected: the `diff` prints nothing (identical tag histogram); the two `div` counts are equal.

- [ ] **Step 5: Commit**

  ```bash
  git add running/gimnasio-semana3.html running/gym-week3.html
  git commit -m "feat(coach): translate gym week 3 to English, rename to gym-week3.html"
  ```

---

### Task 3: Rename + translate gym-week 4

**Files:**
- Rename: `running/gimnasio-semana4.html` → `running/gym-week4.html`

- [ ] **Step 1: Rename**

  ```bash
  git mv running/gimnasio-semana4.html running/gym-week4.html
  ```

- [ ] **Step 2: Rewrite the head**

  Lines 1–385 verbatim, with:
  - Line 2: `<html lang="es"` → `<html lang="en"`
  - Line 7: `<title>Gimnasio Semana 4 — Vuelta al Trail</title>` → `<title>Gym Week 4 — Return to Trail</title>`

- [ ] **Step 3: Replace the body with this exact content**

  Same as Task 2's body except:
  - Title: `WEEK <span>4</span>`
  - Exercise 3 becomes weighted (name/position unchanged, sets and execution change), exercise 4's execution gains a 5th line and its watch note is longer. Exercises 1, 2, 5 and the footer are identical to Task 2.

  ```html
  <body>

    <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
    <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>

    <header>
      <div class="title">GYM<br>WEEK <span>4</span></div>
      <div class="subtitle">Return to Trail · Foundation phase · Nico</div>
      <div class="stats-row">
        <div class="stat-pill">Frequency <strong>2× / week</strong></div>
        <div class="stat-pill">Days <strong>Tue + Thu</strong></div>
        <div class="stat-pill">Duration <strong>~35 min</strong></div>
        <div class="stat-pill hi">When <strong>After running</strong></div>
        <div class="stat-pill">Rest <strong>90s between sets</strong></div>
        <div class="stat-pill">Between exercises <strong>2 min</strong></div>
      </div>
    </header>

    <div class="warmup-card">
      <div class="warmup-label">⚡ Warm-up · 5 min</div>
      <div class="warmup-body">
        Easy bike or jog 5 min → 10 leg swings each direction per leg → 10 bodyweight squats.
        <strong>Form > load</strong> — master the patterns before adding weight. Stop one rep before failure on each
        set.
      </div>
    </div>

    <div class="section-label">Exercises</div>

    <div class="exercises">

      <!-- 1 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">1</div>
            <div class="ex-name">Bulgarian<br>Split Squat</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Back foot on the bench, laces down</li>
          <li>Front foot forward — knee doesn't pass the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Lower until the thigh is ≈ parallel to the floor</li>
          <li>Torso slightly leaned forward</li>
          <li>Push through the whole foot, mainly the heel</li>
          <li>Back leg = support, 90% of the work is the front leg</li>
          <li><strong>Week 1: bodyweight</strong></li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> knee caving inward · weight on the back leg · front foot
          too close</div>
      </div>

      <!-- 2 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">2</div>
            <div class="ex-name">Single-Leg<br>Calf Raise</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Ball of the foot on the edge of a step, heel in the air</li>
          <li>Hold something for balance, not to support your weight</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Rise all the way up, squeeze at the top for 1 sec</li>
          <li><strong>Lower in 3 seconds</strong> — slow eccentric</li>
          <li>Heel below the step for full range of motion</li>
          <li>The slow descent strengthens the Achilles</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> lowering too fast — brake more than you think you need to</div>
      </div>

      <!-- 3 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">3</div>
            <div class="ex-name">Glute<br>Bridge</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">+
              8–12 kg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, knees bent, feet hip-width apart</li>
          <li>Heels close to your glutes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Loaded:</strong> 8 kg kettlebell across your hips (move up to 12 kg once it feels easy)</li>
          <li><strong>Push through your heels</strong>, not your toes</li>
          <li>Rise until shoulders / hips / knees are in one line</li>
          <li>Squeeze your glutes, hold 2 sec at the top</li>
          <li>Ribs down — don't arch your lower back</li>
          <li>Drive up from your glutes, not your back</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> rest the kettlebell over your hip bone, drive up from your glutes without jerking. Hamstring cramps = bring your feet closer to your glutes</div>
      </div>

      <!-- 4 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">4</div>
            <div class="ex-name">Dead<br>Bug</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, arms straight up toward the ceiling</li>
          <li>Knees at 90° over your hips (tabletop)</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Lower back pressed to the floor</strong> — the key point</li>
          <li>Slowly extend the opposite arm + leg</li>
          <li>Without touching the floor, return, switch sides</li>
          <li>Flat back &gt; range of motion</li>
          <li><strong>If it feels easy, do NOT add weight:</strong> slow to 3–4 sec per rep, extend the leg closer to the floor, and exhale hard to engage your core</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> this is an anti-extension control drill, not a strength move — adding weight recruits the psoas and arches your back. Back arching as you extend the leg → reduce the range</div>
      </div>

      <!-- 5 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">5</div>
            <div class="ex-name">Side<br>Plank</div>
          </div>
          <div class="ex-sets">3 × 20s<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Side plank on your forearm</li>
          <li>Body in a straight line from head to feet</li>
          <li>Hips stacked, not rotated or dropped</li>
          <li>Bottom leg on the floor, top leg stacked on top</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Brace your obliques and core, keep a straight line</li>
          <li>Breathe, don't hold your breath</li>
          <li>Primary work: adductors and lateral stabilizers</li>
          <li>Cut the time short if your hips drop — form &gt; duration</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hips dropping or rotating — cut the time before your form breaks</div>
      </div>

    </div>

    <div class="footer">
      <div class="footer-card expected">
        <div class="footer-title">✓ Expected this week</div>
        <ul class="footer-list">
          <li>Muscle soreness in glutes, adductors, and calves for 2–3 days</li>
          <li>Balance trouble in the split squat — completely normal</li>
          <li>You'll be surprised how hard bodyweight alone is</li>
          <li>Form > load. Master the patterns before adding weight</li>
        </ul>
      </div>
      <div class="footer-card warn">
        <div class="footer-title">⚠ Warning signs · stop and reassess</div>
        <ul class="footer-list">
          <li>Sharp pain (vs. muscle burn) anywhere</li>
          <li>Lower-back pain after dead bugs / bridges → poor activation</li>
          <li>Knee pain in the split squat → front foot or knee position is off</li>
          <li>Achilles discomfort &gt; 48h → reduce calf-raise volume</li>
        </ul>
      </div>
    </div>

    <script>
      function toggleTheme() {
        const html = document.documentElement;
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', html.dataset.theme); } catch (e) { }
      }
    </script>
  </body>

  </html>
  ```

- [ ] **Step 4: Structural verification**

  ```bash
  diff <(git show HEAD:running/gimnasio-semana4.html | grep -o '<[a-zA-Z][a-zA-Z0-9-]*' | sort | uniq -c) \
       <(grep -o '<[a-zA-Z][a-zA-Z0-9-]*' running/gym-week4.html | sort | uniq -c)
  echo "div open=$(grep -o '<div' running/gym-week4.html | wc -l) close=$(grep -o '</div>' running/gym-week4.html | wc -l)"
  ```
  Expected: no diff output; div counts equal.

- [ ] **Step 5: Commit**

  ```bash
  git add running/gimnasio-semana4.html running/gym-week4.html
  git commit -m "feat(coach): translate gym week 4 to English, rename to gym-week4.html"
  ```

---

### Task 4: Rename + translate gym-week 5

**Files:**
- Rename: `running/gimnasio-semana5.html` → `running/gym-week5.html`

- [ ] **Step 1: Rename**

  ```bash
  git mv running/gimnasio-semana5.html running/gym-week5.html
  ```

- [ ] **Step 2: Rewrite the head**

  Lines 1–385 verbatim, with:
  - Line 2: `<html lang="es"` → `<html lang="en"`
  - Line 7: `<title>Gimnasio Semana 5 — Vuelta al Trail</title>` → `<title>Gym Week 5 — Return to Trail</title>`

- [ ] **Step 3: Replace the body with this exact content**

  Same as Task 3's body except: title `WEEK <span>5</span>`, subtitle adds "+ first vert work", duration ~40 min, exercise 3's load is 12 kg (not 8–12 kg range), and a new exercise 6 (step-up) plus its footer line are added.

  ```html
  <body>

    <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
    <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>

    <header>
      <div class="title">GYM<br>WEEK <span>5</span></div>
      <div class="subtitle">Return to Trail · Foundation + first vert work · Nico</div>
      <div class="stats-row">
        <div class="stat-pill">Frequency <strong>2× / week</strong></div>
        <div class="stat-pill">Days <strong>Tue + Thu</strong></div>
        <div class="stat-pill">Duration <strong>~40 min</strong></div>
        <div class="stat-pill hi">When <strong>After running</strong></div>
        <div class="stat-pill">Rest <strong>90s between sets</strong></div>
        <div class="stat-pill">Between exercises <strong>2 min</strong></div>
      </div>
    </header>

    <div class="warmup-card">
      <div class="warmup-label">⚡ Warm-up · 5 min</div>
      <div class="warmup-body">
        Easy bike or jog 5 min → 10 leg swings each direction per leg → 10 bodyweight squats.
        <strong>Form > load</strong> — master the patterns before adding weight. Stop one rep before failure on each
        set.
      </div>
    </div>

    <div class="section-label">Exercises</div>

    <div class="exercises">

      <!-- 1 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">1</div>
            <div class="ex-name">Bulgarian<br>Split Squat</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Back foot on the bench, laces down</li>
          <li>Front foot forward — knee doesn't pass the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Lower until the thigh is ≈ parallel to the floor</li>
          <li>Torso slightly leaned forward</li>
          <li>Push through the whole foot, mainly the heel</li>
          <li>Back leg = support, 90% of the work is the front leg</li>
          <li><strong>Week 1: bodyweight</strong></li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> knee caving inward · weight on the back leg · front foot
          too close</div>
      </div>

      <!-- 2 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">2</div>
            <div class="ex-name">Single-Leg<br>Calf Raise</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Ball of the foot on the edge of a step, heel in the air</li>
          <li>Hold something for balance, not to support your weight</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Rise all the way up, squeeze at the top for 1 sec</li>
          <li><strong>Lower in 3 seconds</strong> — slow eccentric</li>
          <li>Heel below the step for full range of motion</li>
          <li>The slow descent strengthens the Achilles</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> lowering too fast — brake more than you think you need to</div>
      </div>

      <!-- 3 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">3</div>
            <div class="ex-name">Glute<br>Bridge</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">+
              12 kg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, knees bent, feet hip-width apart</li>
          <li>Heels close to your glutes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Loaded:</strong> 12 kg kettlebell across your hips (drop back to 8 kg if your form breaks)</li>
          <li><strong>Push through your heels</strong>, not your toes</li>
          <li>Rise until shoulders / hips / knees are in one line</li>
          <li>Squeeze your glutes, hold 2 sec at the top</li>
          <li>Ribs down — don't arch your lower back</li>
          <li>Drive up from your glutes, not your back</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> rest the kettlebell over your hip bone, drive up from your glutes without jerking. Hamstring cramps = bring your feet closer to your glutes</div>
      </div>

      <!-- 4 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">4</div>
            <div class="ex-name">Dead<br>Bug</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, arms straight up toward the ceiling</li>
          <li>Knees at 90° over your hips (tabletop)</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Lower back pressed to the floor</strong> — the key point</li>
          <li>Slowly extend the opposite arm + leg</li>
          <li>Without touching the floor, return, switch sides</li>
          <li>Flat back &gt; range of motion</li>
          <li><strong>If it feels easy, do NOT add weight:</strong> slow to 3–4 sec per rep, extend the leg closer to the floor, and exhale hard to engage your core</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> this is an anti-extension control drill, not a strength move — adding weight recruits the psoas and arches your back. Back arching as you extend the leg → reduce the range</div>
      </div>

      <!-- 5 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">5</div>
            <div class="ex-name">Side<br>Plank</div>
          </div>
          <div class="ex-sets">3 × 20s<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Side plank on your forearm</li>
          <li>Body in a straight line from head to feet</li>
          <li>Hips stacked, not rotated or dropped</li>
          <li>Bottom leg on the floor, top leg stacked on top</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Brace your obliques and core, keep a straight line</li>
          <li>Breathe, don't hold your breath</li>
          <li>Primary work: adductors and lateral stabilizers</li>
          <li>Cut the time short if your hips drop — form &gt; duration</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hips dropping or rotating — cut the time before your form breaks</div>
      </div>

      <!-- 6 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">6</div>
            <div class="ex-name">Step-up +<br>Eccentric Descent</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Low step or bench (knee height or lower to start)</li>
          <li>Whole foot planted on top, not just the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Step up</strong> driving through the heel of the top leg, no push-off from the bottom leg</li>
          <li>Knee tracking over the foot — not caving inward</li>
          <li><strong>Lower in 3 seconds</strong> — the slow, controlled descent is what prepares your quads for trail downhills</li>
          <li><strong>Week 5: bodyweight.</strong> Raise the step height before adding load</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> this preps you for downhills — the value is in the eccentric phase (lowering slowly), not stepping up fast. Knee pain → lower the step height or reduce the range</div>
      </div>

    </div>

    <div class="footer">
      <div class="footer-card expected">
        <div class="footer-title">✓ Expected this week</div>
        <ul class="footer-list">
          <li>Muscle soreness in glutes, adductors, and calves for 2–3 days</li>
          <li>Quads loaded after the step-up — normal as you start downhill-prep work</li>
          <li>Balance trouble in the split squat — completely normal</li>
          <li>Form > load. Master the patterns before adding weight</li>
        </ul>
      </div>
      <div class="footer-card warn">
        <div class="footer-title">⚠ Warning signs · stop and reassess</div>
        <ul class="footer-list">
          <li>Sharp pain (vs. muscle burn) anywhere</li>
          <li>Lower-back pain after dead bugs / bridges → poor activation</li>
          <li>Knee pain in the split squat → front foot or knee position is off</li>
          <li>Achilles discomfort &gt; 48h → reduce calf-raise volume</li>
        </ul>
      </div>
    </div>

    <script>
      function toggleTheme() {
        const html = document.documentElement;
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', html.dataset.theme); } catch (e) { }
      }
    </script>
  </body>

  </html>
  ```

- [ ] **Step 4: Structural verification**

  ```bash
  diff <(git show HEAD:running/gimnasio-semana5.html | grep -o '<[a-zA-Z][a-zA-Z0-9-]*' | sort | uniq -c) \
       <(grep -o '<[a-zA-Z][a-zA-Z0-9-]*' running/gym-week5.html | sort | uniq -c)
  echo "div open=$(grep -o '<div' running/gym-week5.html | wc -l) close=$(grep -o '</div>' running/gym-week5.html | wc -l)"
  ```
  Expected: no diff output; div counts equal.

- [ ] **Step 5: Commit**

  ```bash
  git add running/gimnasio-semana5.html running/gym-week5.html
  git commit -m "feat(coach): translate gym week 5 to English, rename to gym-week5.html"
  ```

---

### Task 5: Rename + translate gym-week 6 (deload)

**Files:**
- Rename: `running/gimnasio-semana6.html` → `running/gym-week6.html`

- [ ] **Step 1: Rename**

  ```bash
  git mv running/gimnasio-semana6.html running/gym-week6.html
  ```

- [ ] **Step 2: Rewrite the head**

  Lines 1–385 verbatim, with:
  - Line 2: `<html lang="es"` → `<html lang="en"`
  - Line 7: `<title>Gimnasio Semana 6 — Descarga</title>` → `<title>Gym Week 6 — Deload</title>`

- [ ] **Step 3: Replace the body with this exact content**

  ```html
  <body>

    <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
    <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>

    <header>
      <div class="title">GYM<br>WEEK <span>6</span></div>
      <div class="subtitle">Deload week · Maintain the pattern, reduce the load · Nico</div>
      <div class="stats-row">
        <div class="stat-pill">Frequency <strong>1× / week</strong></div>
        <div class="stat-pill">Day <strong>Wednesday</strong></div>
        <div class="stat-pill">Duration <strong>~30 min</strong></div>
        <div class="stat-pill hi">Load <strong>~60% (deload)</strong></div>
        <div class="stat-pill">Sets <strong>2 per exercise</strong></div>
        <div class="stat-pill">Rest <strong>90s between sets</strong></div>
      </div>
    </header>

    <div class="warmup-card">
      <div class="warmup-label">⚡ Warm-up · 5 min</div>
      <div class="warmup-body">
        Easy bike or jog 5 min → 10 leg swings each direction per leg → 10 bodyweight squats.
        <strong>Deload week:</strong> 2 sets per exercise, reduced load. The goal is to maintain the patterns
        and leave <strong>fresh</strong>, not fatigued — this week the adaptation consolidates through rest.
      </div>
    </div>

    <div class="section-label">Exercises · Deload</div>

    <div class="exercises">

      <!-- 1 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">1</div>
            <div class="ex-name">Bulgarian<br>Split Squat</div>
          </div>
          <div class="ex-sets">2 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Back foot on the bench, laces down</li>
          <li>Front foot forward — knee doesn't pass the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Lower until the thigh is ≈ parallel to the floor</li>
          <li>Torso slightly leaned forward</li>
          <li>Push through the whole foot, mainly the heel</li>
          <li><strong>Deload: bodyweight, no rush</strong> — clean technique</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> knee caving inward · weight on the back leg · front foot
          too close</div>
      </div>

      <!-- 2 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">2</div>
            <div class="ex-name">Single-Leg<br>Calf Raise</div>
          </div>
          <div class="ex-sets">2 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Ball of the foot on the edge of a step, heel in the air</li>
          <li>Hold something for balance, not to support your weight</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Rise all the way up, squeeze at the top for 1 sec</li>
          <li><strong>Lower in 3 seconds</strong> — slow eccentric</li>
          <li>Heel below the step for full range of motion</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> lowering too fast — brake more than you think you need to</div>
      </div>

      <!-- 3 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">3</div>
            <div class="ex-name">Glute<br>Bridge</div>
          </div>
          <div class="ex-sets">2 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">+
              8 kg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, knees bent, feet hip-width apart</li>
          <li>Heels close to your glutes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Deload: drop to 8 kg</strong> (from the usual 12 kg load)</li>
          <li><strong>Push through your heels</strong>, not your toes</li>
          <li>Rise until shoulders / hips / knees are in one line</li>
          <li>Squeeze your glutes, hold 2 sec at the top</li>
          <li>Ribs down — don't arch your lower back</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> rest the kettlebell over your hip bone, drive up from your glutes without jerking. Hamstring cramps = bring your feet closer to your glutes</div>
      </div>

      <!-- 4 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">4</div>
            <div class="ex-name">Dead<br>Bug</div>
          </div>
          <div class="ex-sets">2 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, arms straight up toward the ceiling</li>
          <li>Knees at 90° over your hips (tabletop)</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Lower back pressed to the floor</strong> — the key point</li>
          <li>Slowly extend the opposite arm + leg</li>
          <li>Without touching the floor, return, switch sides</li>
          <li>Flat back &gt; range of motion</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> this is an anti-extension control drill, not a strength move. Back arching as you extend the leg → reduce the range</div>
      </div>

      <!-- 5 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">5</div>
            <div class="ex-name">Side<br>Plank</div>
          </div>
          <div class="ex-sets">2 × 20s<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Side plank on your forearm</li>
          <li>Body in a straight line from head to feet</li>
          <li>Hips stacked, not rotated or dropped</li>
          <li>Bottom leg on the floor, top leg stacked on top</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Brace your obliques and core, keep a straight line</li>
          <li>Breathe, don't hold your breath</li>
          <li>Primary work: adductors and lateral stabilizers</li>
          <li>Cut the time short if your hips drop — form &gt; duration</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hips dropping or rotating — cut the time before your form breaks</div>
      </div>

      <!-- 6 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">6</div>
            <div class="ex-name">Step-up +<br>Eccentric Descent</div>
          </div>
          <div class="ex-sets">2 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Low step or bench (knee height or lower to start)</li>
          <li>Whole foot planted on top, not just the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Step up</strong> driving through the heel of the top leg, no push-off from the bottom leg</li>
          <li>Knee tracking over the foot — not caving inward</li>
          <li><strong>Lower in 3 seconds</strong> — the slow, controlled descent preps your quads for downhills</li>
          <li><strong>Deload: bodyweight, low step</strong></li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> the value is in the eccentric phase (lowering slowly), not stepping up fast. Knee pain → lower the step height or reduce the range</div>
      </div>

    </div>

    <div class="footer">
      <div class="footer-card expected">
        <div class="footer-title">✓ Expected this week</div>
        <ul class="footer-list">
          <li>Less soreness than previous weeks — that's the deload, normal</li>
          <li>You should finish the session fresh, not drained</li>
          <li>Your legs should feel lighter heading into the next block</li>
          <li>Keep your technique sharp: this week trains the pattern, not the load</li>
        </ul>
      </div>
      <div class="footer-card warn">
        <div class="footer-title">⚠ Warning signs · stop and reassess</div>
        <ul class="footer-list">
          <li>Sharp pain (vs. muscle burn) anywhere</li>
          <li>Lower-back pain after dead bugs / bridges → poor activation</li>
          <li>Knee pain in the split squat → front foot or knee position is off</li>
          <li>Achilles discomfort &gt; 48h → reduce calf-raise volume</li>
        </ul>
      </div>
    </div>

    <script>
      function toggleTheme() {
        const html = document.documentElement;
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', html.dataset.theme); } catch (e) { }
      }
    </script>
  </body>

  </html>
  ```

- [ ] **Step 4: Structural verification**

  ```bash
  diff <(git show HEAD:running/gimnasio-semana6.html | grep -o '<[a-zA-Z][a-zA-Z0-9-]*' | sort | uniq -c) \
       <(grep -o '<[a-zA-Z][a-zA-Z0-9-]*' running/gym-week6.html | sort | uniq -c)
  echo "div open=$(grep -o '<div' running/gym-week6.html | wc -l) close=$(grep -o '</div>' running/gym-week6.html | wc -l)"
  ```
  Expected: no diff output; div counts equal.

- [ ] **Step 5: Commit**

  ```bash
  git add running/gimnasio-semana6.html running/gym-week6.html
  git commit -m "feat(coach): translate gym week 6 to English, rename to gym-week6.html"
  ```

---

### Task 6: Rename + translate gym-week 7

**Files:**
- Rename: `running/gimnasio-semana7.html` → `running/gym-week7.html`

- [ ] **Step 1: Rename**

  ```bash
  git mv running/gimnasio-semana7.html running/gym-week7.html
  ```

- [ ] **Step 2: Rewrite the head**

  Lines 1–385 verbatim, with:
  - Line 2: `<html lang="es"` → `<html lang="en"`
  - Line 7: `<title>Gimnasio Semana 7 — Fuerza + Vert</title>` → `<title>Gym Week 7 — Strength + Vert</title>`

- [ ] **Step 3: Replace the body with this exact content**

  ```html
  <body>

    <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
    <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>

    <header>
      <div class="title">GYM<br>WEEK <span>7</span></div>
      <div class="subtitle">Strength + Vert · Back to 2×/week after the deload · Nico</div>
      <div class="stats-row">
        <div class="stat-pill">Frequency <strong>2× / week</strong></div>
        <div class="stat-pill">Days <strong>Tue + Thu</strong></div>
        <div class="stat-pill">Duration <strong>~45 min</strong></div>
        <div class="stat-pill hi">When <strong>After running</strong></div>
        <div class="stat-pill">Sets <strong>3 per exercise</strong></div>
        <div class="stat-pill">Rest <strong>90s between sets</strong></div>
      </div>
    </header>

    <div class="warmup-card">
      <div class="warmup-label">⚡ Warm-up · 5 min</div>
      <div class="warmup-body">
        Easy bike or jog 5 min → 10 leg swings each direction per leg → 10 bodyweight squats.
        <strong>The strength block begins:</strong> load returns after the deload. Only increase weight if your
        technique stays clean — <strong>stop one rep short of failure</strong> on every set. Today's work is
        climb-specific: hip drive and control on the descent.
      </div>
    </div>

    <div class="section-label">Exercises · Strength + Vert</div>

    <div class="exercises">

      <!-- 1 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">1</div>
            <div class="ex-name">Bulgarian<br>Split Squat</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Back foot on the bench, laces down</li>
          <li>Front foot forward — knee doesn't pass the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Lower until the thigh is ≈ parallel to the floor</li>
          <li>Torso slightly leaned forward</li>
          <li>Push through the whole foot, mainly the heel</li>
          <li><strong>Week 7: add load</strong> — 8 kg kettlebell held at your chest (goblet) or one on each side;
            move up to 12 kg if your form stays clean</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> knee caving inward · weight on the back leg · front foot
          too close. The load shouldn't break your technique — lower the weight before you lose control</div>
      </div>

      <!-- 2 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">2</div>
            <div class="ex-name">Single-Leg<br>Calf Raise</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Ball of the foot on the edge of a step, heel in the air</li>
          <li>Hold something for balance, not to support your weight</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Rise all the way up, squeeze at the top for 1 sec</li>
          <li><strong>Lower in 3 seconds</strong> — slow eccentric</li>
          <li>Heel below the step for full range of motion</li>
          <li><strong>Week 7: 8 kg kettlebell in the hand on the working side</strong> if 12 reps feel easy</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> lowering too fast — brake more than you think you need to. It preps the Achilles for long climbs</div>
      </div>

      <!-- 3 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">3</div>
            <div class="ex-name">Single-Leg<br>Glute Bridge</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, one knee bent, heel close to your glutes</li>
          <li>The other leg straight or with the knee pulled to your chest</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Progression:</strong> the two-leg bridge with 12 kg was already easy → move to <strong>single
            leg, bodyweight</strong></li>
          <li>Drive through the heel of the supporting leg, raise your hip</li>
          <li>Hips level — don't let the free side drop</li>
          <li>Squeeze the glute, hold 2 sec at the top</li>
          <li>Ribs down — don't arch your lower back</li>
          <li>Once you own 10 clean reps, <strong>add 8 kg</strong> over the supporting hip</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> the free-side hip drops or rotates → shorten the range and
          level out before continuing. Drive from the glute, never the lower back</div>
      </div>

      <!-- 4 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">4</div>
            <div class="ex-name">Dead<br>Bug</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, arms straight up toward the ceiling</li>
          <li>Knees at 90° over your hips (tabletop)</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Lower back pressed to the floor</strong> — the key point</li>
          <li>Slowly extend the opposite arm + leg</li>
          <li>Without touching the floor, return, switch sides</li>
          <li>Flat back &gt; range of motion</li>
          <li><strong>Still no added weight:</strong> progress with a 3–4 sec tempo per rep and a hard exhale, not with load</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> this is anti-extension control, not strength — adding weight recruits the psoas and arches your back. Back arching as you extend the leg → reduce the range</div>
      </div>

      <!-- 5 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">5</div>
            <div class="ex-name">Side<br>Plank</div>
          </div>
          <div class="ex-sets">3 × 30s<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Side plank on your forearm</li>
          <li>Body in a straight line from head to feet</li>
          <li>Hips stacked, not rotated or dropped</li>
          <li>Bottom leg on the floor, top leg stacked on top</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Contract your obliques and core, keep a straight line</li>
          <li>Breathe, don't hold your breath</li>
          <li><strong>Week 7: build from 20 to 30 sec</strong> if your hips stay steady</li>
          <li>Cut the time short if your hips drop — form &gt; duration</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hips dropping or rotating — cut the time before your form breaks</div>
      </div>

      <!-- 6 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">6</div>
            <div class="ex-name">High Step-up<br>+ Eccentric Descent</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Use the jump box — height at mid-shin / knee</li>
          <li>Whole foot planted on top, not just the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Step up</strong> driving through the heel of the top leg, no push-off from the bottom leg</li>
          <li><strong>Drive the knee up</strong> — mimics the power-hike motion on a climb</li>
          <li>Knee tracking over the foot — not caving inward</li>
          <li><strong>Lower in 3 seconds</strong> — the slow eccentric preps your quads for trail descents</li>
          <li><strong>Week 7: raise the box height before adding load</strong></li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> the value is in the slow descent and the higher box, not stepping up fast. Knee pain → lower the height or reduce the range</div>
      </div>

    </div>

    <div class="footer">
      <div class="footer-card expected">
        <div class="footer-title">✓ Expected this week</div>
        <ul class="footer-list">
          <li>Soreness returns after the deload — that's a load week, normal</li>
          <li>Supporting-side glute heavily loaded from the single-leg bridge</li>
          <li>Quads worked after the high step-up — prep for descents</li>
          <li>Some instability as you start the loaded split squat — settles in 1–2 sessions</li>
        </ul>
      </div>
      <div class="footer-card warn">
        <div class="footer-title">⚠ Warning signs · stop and reassess</div>
        <ul class="footer-list">
          <li>Sharp pain (vs. muscle burn) anywhere</li>
          <li>Lower-back pain after dead bugs / bridges → poor activation, don't add load</li>
          <li>Knee pain in the split squat or step-up → check alignment or lower height/load</li>
          <li>Achilles discomfort &gt; 48h → reduce calf-raise volume</li>
        </ul>
      </div>
    </div>

    <script>
      function toggleTheme() {
        const html = document.documentElement;
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', html.dataset.theme); } catch (e) { }
      }
    </script>
  </body>

  </html>
  ```

- [ ] **Step 4: Structural verification**

  ```bash
  diff <(git show HEAD:running/gimnasio-semana7.html | grep -o '<[a-zA-Z][a-zA-Z0-9-]*' | sort | uniq -c) \
       <(grep -o '<[a-zA-Z][a-zA-Z0-9-]*' running/gym-week7.html | sort | uniq -c)
  echo "div open=$(grep -o '<div' running/gym-week7.html | wc -l) close=$(grep -o '</div>' running/gym-week7.html | wc -l)"
  ```
  Expected: no diff output; div counts equal.

- [ ] **Step 5: Commit**

  ```bash
  git add running/gimnasio-semana7.html running/gym-week7.html
  git commit -m "feat(coach): translate gym week 7 to English, rename to gym-week7.html"
  ```

---

### Task 7: Rename + translate gym-week 8

**Files:**
- Rename: `running/gimnasio-semana8.html` → `running/gym-week8.html`

- [ ] **Step 1: Rename**

  ```bash
  git mv running/gimnasio-semana8.html running/gym-week8.html
  ```

- [ ] **Step 2: Rewrite the head**

  Lines 1–385 verbatim, with:
  - Line 2: `<html lang="es"` → `<html lang="en"`
  - Line 7: `<title>Gimnasio Semana 8 — Fuerza + Vert</title>` → `<title>Gym Week 8 — Strength + Vert</title>`

- [ ] **Step 3: Replace the body with this exact content**

  ```html
  <body>

    <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
    <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>

    <header>
      <div class="title">GYM<br>WEEK <span>8</span></div>
      <div class="subtitle">Strength + Vert · Load progression + first back-to-back · Nico</div>
      <div class="stats-row">
        <div class="stat-pill">Frequency <strong>2× / week</strong></div>
        <div class="stat-pill">Days <strong>Tue + Thu</strong></div>
        <div class="stat-pill">Duration <strong>~45 min</strong></div>
        <div class="stat-pill hi">When <strong>After running</strong></div>
        <div class="stat-pill">Sets <strong>3 per exercise</strong></div>
        <div class="stat-pill">Rest <strong>90s between sets</strong></div>
      </div>
    </header>

    <div class="warmup-card">
      <div class="warmup-label">⚡ Warm-up · 5 min</div>
      <div class="warmup-body">
        Easy bike or jog 5 min → 10 leg swings each direction per leg → 10 bodyweight squats.
        <strong>Consolidate the block's load:</strong> week 7 landed clean, this week settles the weights and only
        increases where technique holds — <strong>stop one rep short of failure</strong> in each set. The
        <strong>first back-to-back</strong> arrives this week (long Saturday + short Sunday): the focus is on
        descent control, which is what protects your legs through the weekend's downhill meters.
      </div>
    </div>

    <div class="section-label">Exercises · Strength + Vert</div>

    <div class="exercises">

      <!-- 1 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">1</div>
            <div class="ex-name">Bulgarian<br>Split Squat</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Back foot on the bench, laces down</li>
          <li>Front foot forward — knee doesn't pass the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Lower until the thigh is ≈ parallel to the floor</li>
          <li>Torso slightly leaned forward</li>
          <li>Push with the whole foot, mainly the heel</li>
          <li><strong>Week 8: hold 12 kg firm</strong> — consolidates the block's goblet load; keep control on the
            descent, don't chase more weight this week</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> knee caving inward · weight on the back leg · front foot too close.
          The load shouldn't break your technique — lower the weight before you lose control</div>
      </div>

      <!-- 2 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">2</div>
            <div class="ex-name">Single-Leg<br>Calf Raise</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Ball of the foot on the edge of a step, heel in the air</li>
          <li>Hold something for balance, not to support your weight</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Rise all the way up, squeeze at the top for 1 sec</li>
          <li><strong>Lower in 3 seconds</strong> — slow eccentric</li>
          <li>Heel below the step for full range of motion</li>
          <li><strong>Week 8: hold 8 kg, strict 3s eccentric</strong> — this week adds descent meters, the Achilles needs the slow work</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> lowering too fast — brake more than you think you need to. Preps
          the Achilles for long climbs</div>
      </div>

      <!-- 3 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">3</div>
            <div class="ex-name">Single-Leg<br>Glute Bridge</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, one knee bent, heel close to your glutes</li>
          <li>The other leg straight or with the knee pulled to your chest</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Week 8:</strong> the single-leg bodyweight version is clean now → <strong>add 8 kg</strong> over
            the supporting hip (the scheduled progression)</li>
          <li>Drive through the heel of the supporting leg, raise your hip</li>
          <li>Hips level — don't let the free side drop</li>
          <li>Squeeze the glute, hold 2 sec at the top</li>
          <li>Ribs down — don't arch your lower back</li>
          <li>If the weight breaks hip level, drop back to bodyweight — form rules</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> the free-side hip drops or rotates → shorten the range and level
          out before continuing. Drive from the glute, never the lower back</div>
      </div>

      <!-- 4 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">4</div>
            <div class="ex-name">Dead<br>Bug</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, arms straight up toward the ceiling</li>
          <li>Knees at 90° over your hips (tabletop)</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Lower back pressed to the floor</strong> — the key point</li>
          <li>Slowly extend the opposite arm + leg</li>
          <li>Without touching the floor, return, switch sides</li>
          <li>Flat back &gt; range of motion</li>
          <li><strong>Still no added weight:</strong> progress with a 3–4 sec tempo per rep and a hard exhale, not with load</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> this is anti-extension control, not strength — adding weight
          recruits the psoas and arches your back. Back arching as you extend the leg → reduce the range</div>
      </div>

      <!-- 5 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">5</div>
            <div class="ex-name">Side<br>Plank</div>
          </div>
          <div class="ex-sets">3 × 30s<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Side plank on your forearm</li>
          <li>Body in a straight line from head to feet</li>
          <li>Hips stacked, not rotated or dropped</li>
          <li>Bottom leg on the floor, top leg stacked on top</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Contract your obliques and core, keep a straight line</li>
          <li>Breathe, don't hold your breath</li>
          <li><strong>Week 8: hold 30 sec steady</strong> if your hips stay level</li>
          <li>Cut the time short if your hips drop — form &gt; duration</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hips dropping or rotating — cut the time before your form breaks</div>
      </div>

      <!-- 6 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">6</div>
            <div class="ex-name">High Step-up<br>+ Eccentric Descent</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Use the jump box — height at mid-shin / knee</li>
          <li>Whole foot planted on top, not just the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Step up</strong> driving through the heel of the top leg, no push-off from the bottom leg</li>
          <li><strong>Drive the knee up</strong> — mimics the power-hike motion on a climb</li>
          <li>Knee tracking over the foot — not caving inward</li>
          <li><strong>Lower in 3 seconds</strong> — the slow eccentric preps your quads for trail descents</li>
          <li><strong>Week 8: keep the box high, focus fully on the 3–4s descent</strong> — the first back-to-back
            arrives, more accumulated downhill over the weekend</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> the value is in the slow descent and the higher box, not stepping
          up fast. Knee pain → lower the height or reduce the range</div>
      </div>

    </div>

    <div class="footer">
      <div class="footer-card expected">
        <div class="footer-title">✓ Expected this week</div>
        <ul class="footer-list">
          <li>Supporting-side glute heavily loaded once you add the 8 kg to the single-leg bridge</li>
          <li>Quads worked after the high step-up — they're what brakes on the descents</li>
          <li>Legs somewhat loaded heading into Saturday — that's why gym days are Tue/Thu, with a buffer before the weekend</li>
          <li>Sunday's back-to-back run happens on tired legs — that's by design, don't force it</li>
        </ul>
      </div>
      <div class="footer-card warn">
        <div class="footer-title">⚠ Warning signs · stop and reassess</div>
        <ul class="footer-list">
          <li>Sharp pain (vs. muscle burn) anywhere</li>
          <li>Lower-back pain after dead bugs / bridges → poor activation, don't add load</li>
          <li>Knee pain in the split squat or step-up → check alignment or lower height/load</li>
          <li>Achilles discomfort &gt; 48h → reduce calf-raise volume</li>
        </ul>
      </div>
    </div>

    <script>
      function toggleTheme() {
        const html = document.documentElement;
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', html.dataset.theme); } catch (e) { }
      }
    </script>
  </body>

  </html>
  ```

- [ ] **Step 4: Structural verification**

  ```bash
  diff <(git show HEAD:running/gimnasio-semana8.html | grep -o '<[a-zA-Z][a-zA-Z0-9-]*' | sort | uniq -c) \
       <(grep -o '<[a-zA-Z][a-zA-Z0-9-]*' running/gym-week8.html | sort | uniq -c)
  echo "div open=$(grep -o '<div' running/gym-week8.html | wc -l) close=$(grep -o '</div>' running/gym-week8.html | wc -l)"
  ```
  Expected: no diff output; div counts equal.

- [ ] **Step 5: Commit**

  ```bash
  git add running/gimnasio-semana8.html running/gym-week8.html
  git commit -m "feat(coach): translate gym week 8 to English, rename to gym-week8.html"
  ```

---

### Task 8: Rename + translate gym-week 9

**Files:**
- Rename: `running/gimnasio-semana9.html` → `running/gym-week9.html`

- [ ] **Step 1: Rename**

  ```bash
  git mv running/gimnasio-semana9.html running/gym-week9.html
  ```

- [ ] **Step 2: Rewrite the head**

  Lines 1–385 verbatim, with:
  - Line 2: `<html lang="es"` → `<html lang="en"`
  - Line 7: `<title>Gimnasio Semana 9 — Fuerza + Vert</title>` → `<title>Gym Week 9 — Strength + Vert</title>`

- [ ] **Step 3: Replace the body with this exact content**

  ```html
  <body>

    <a href="index.html" style="display:inline-block;margin-bottom:1rem;font-size:.7rem;letter-spacing:.1em;color:var(--muted);text-decoration:none">‹ Running</a>
    <button class="theme-toggle" onclick="toggleTheme()"><span class="sun">☀</span><span class="moon">☾</span></button>

    <header>
      <div class="title">GYM<br>WEEK <span>9</span></div>
      <div class="subtitle">Strength + Vert · Base-block peak · Nico</div>
      <div class="stats-row">
        <div class="stat-pill">Frequency <strong>2× / week</strong></div>
        <div class="stat-pill">Days <strong>Tue + Thu</strong></div>
        <div class="stat-pill">Duration <strong>~45 min</strong></div>
        <div class="stat-pill hi">When <strong>After running</strong></div>
        <div class="stat-pill">Sets <strong>3 per exercise</strong></div>
        <div class="stat-pill">Rest <strong>90s between sets</strong></div>
      </div>
    </header>

    <div class="warmup-card">
      <div class="warmup-label">⚡ Warm-up · 5 min</div>
      <div class="warmup-body">
        Easy bike or jog 5 min → 10 leg swings each direction per leg → 10 bodyweight squats.
        <strong>Peak week of the base block</strong> — the long run climbs to 15 km / 1000 m and week 10 is the
        deload. <strong>Don't increase loads this week:</strong> hold week 8's weights and let the run be the
        priority. The gym here <strong>maintains</strong>, it doesn't progress — the full focus is the slow
        descent, which is what protects your quads and Achilles through the weekend's 1000 m of downhill.
      </div>
    </div>

    <div class="section-label">Exercises · Strength + Vert</div>

    <div class="exercises">

      <!-- 1 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">1</div>
            <div class="ex-name">Bulgarian<br>Split Squat</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Back foot on the bench, laces down</li>
          <li>Front foot forward — knee doesn't pass the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Lower until the thigh is ≈ parallel to the floor</li>
          <li>Torso slightly leaned forward</li>
          <li>Push through the whole foot, mainly the heel</li>
          <li><strong>Week 9: hold 12 kg</strong> — peak week, don't increase load; prioritize flawless control with
            the run already demanding</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> knee caving inward · weight on the back leg · front foot too close.
          The load shouldn't break your technique — lower the weight before you lose control</div>
      </div>

      <!-- 2 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">2</div>
            <div class="ex-name">Single-Leg<br>Calf Raise</div>
          </div>
          <div class="ex-sets">3 × 12<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Ball of the foot on the edge of a step, heel in the air</li>
          <li>Hold something for balance, not to support your weight</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Rise all the way up, squeeze at the top for 1 sec</li>
          <li><strong>Lower in 3 seconds</strong> — slow eccentric</li>
          <li>Heel below the step for full range of motion</li>
          <li><strong>Week 9: hold 8 kg, extend the eccentric to 4s</strong> — the 1000 m descent is the biggest of
            the block, the Achilles needs the slow work</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> lowering too fast — brake more than you think you need to. Preps
          the Achilles for long climbs</div>
      </div>

      <!-- 3 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">3</div>
            <div class="ex-name">Single-Leg<br>Glute Bridge</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, one knee bent, heel close to your glutes</li>
          <li>The other leg straight or with the knee pulled to your chest</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Week 9: hold the 8 kg</strong> over the supporting hip — consolidates week 8's load, no
            increase in peak week</li>
          <li>Drive through the heel of the supporting leg, raise your hip</li>
          <li>Hips level — don't let the free side drop</li>
          <li>Squeeze the glute, hold 2 sec at the top</li>
          <li>Ribs down — don't arch your lower back</li>
          <li>If the weight breaks hip level, drop back to bodyweight — form rules</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> the free-side hip drops or rotates → shorten the range and level
          out before continuing. Drive from the glute, never the lower back</div>
      </div>

      <!-- 4 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">4</div>
            <div class="ex-name">Dead<br>Bug</div>
          </div>
          <div class="ex-sets">3 × 10<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Lying on your back, arms straight up toward the ceiling</li>
          <li>Knees at 90° over your hips (tabletop)</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Lower back pressed to the floor</strong> — the key point</li>
          <li>Slowly extend the opposite arm + leg</li>
          <li>Without touching the floor, return, switch sides</li>
          <li>Flat back &gt; range of motion</li>
          <li><strong>Still no added weight:</strong> progress with a 3–4 sec tempo per rep and a hard exhale, not with load</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> this is anti-extension control, not strength — adding weight
          recruits the psoas and arches your back. Back arching as you extend the leg → reduce the range</div>
      </div>

      <!-- 5 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">5</div>
            <div class="ex-name">Side<br>Plank</div>
          </div>
          <div class="ex-sets">3 × 30s<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              side</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Side plank on your forearm</li>
          <li>Body in a straight line from head to feet</li>
          <li>Hips stacked, not rotated or dropped</li>
          <li>Bottom leg on the floor, top leg stacked on top</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li>Contract your obliques and core, keep a straight line</li>
          <li>Breathe, don't hold your breath</li>
          <li><strong>Week 9: hold 30 sec steady</strong> if your hips stay level</li>
          <li>Cut the time short if your hips drop — form &gt; duration</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> hips dropping or rotating — cut the time before your form breaks</div>
      </div>

      <!-- 6 -->
      <div class="exercise">
        <div class="ex-header">
          <div class="ex-num-name">
            <div class="ex-num">6</div>
            <div class="ex-name">High Step-up<br>+ Eccentric Descent</div>
          </div>
          <div class="ex-sets">3 × 8<br><span
              style="font-size:.6rem;letter-spacing:.08em;font-family:'DM Mono',monospace;color:var(--muted);">/
              leg</span></div>
        </div>

        <div class="ex-label">Position</div>
        <ul class="cues">
          <li>Use the jump box — height at mid-shin / knee</li>
          <li>Whole foot planted on top, not just the toes</li>
        </ul>

        <div class="ex-label">Execution</div>
        <ul class="cues">
          <li><strong>Step up</strong> driving through the heel of the top leg, no push-off from the bottom leg</li>
          <li><strong>Drive the knee up</strong> — mimics the power-hike motion on a climb</li>
          <li>Knee tracking over the foot — not caving inward</li>
          <li><strong>Lower in 3 seconds</strong> — the slow eccentric preps your quads for trail descents</li>
          <li><strong>Week 9: high box, controlled 4s descent</strong> — the biggest descent week of the block; the
            slow eccentric is the knees' insurance policy</li>
        </ul>

        <div class="ex-watch"><strong>Watch:</strong> the value is in the slow descent and the higher box, not stepping
          up fast. Knee pain → lower the height or reduce the range</div>
      </div>

    </div>

    <div class="footer">
      <div class="footer-card expected">
        <div class="footer-title">✓ Expected this week</div>
        <ul class="footer-list">
          <li>Quads worked after the step-up — they're what brakes on Saturday's 1000 m descent</li>
          <li>Legs somewhat loaded heading into Saturday — that's why gym days are Tue/Thu, with a buffer before the long run</li>
          <li>It's peak week: prioritize arriving fresh for the 15 km / 1000 m long run over any gym personal best</li>
          <li>Week 10 is the deload — if anything feels tight, this week is about holding steady, not pushing</li>
        </ul>
      </div>
      <div class="footer-card warn">
        <div class="footer-title">⚠ Warning signs · stop and reassess</div>
        <ul class="footer-list">
          <li>Sharp pain (vs. muscle burn) anywhere</li>
          <li>Lower-back pain after dead bugs / bridges → poor activation, don't add load</li>
          <li>Knee pain in the split squat or step-up → check alignment or lower height/load</li>
          <li>Achilles discomfort &gt; 48h → reduce calf-raise volume</li>
        </ul>
      </div>
    </div>

    <script>
      function toggleTheme() {
        const html = document.documentElement;
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', html.dataset.theme); } catch (e) { }
      }
    </script>
  </body>

  </html>
  ```

- [ ] **Step 4: Structural verification**

  ```bash
  diff <(git show HEAD:running/gimnasio-semana9.html | grep -o '<[a-zA-Z][a-zA-Z0-9-]*' | sort | uniq -c) \
       <(grep -o '<[a-zA-Z][a-zA-Z0-9-]*' running/gym-week9.html | sort | uniq -c)
  echo "div open=$(grep -o '<div' running/gym-week9.html | wc -l) close=$(grep -o '</div>' running/gym-week9.html | wc -l)"
  ```
  Expected: no diff output; div counts equal.

- [ ] **Step 5: Commit**

  ```bash
  git add running/gimnasio-semana9.html running/gym-week9.html
  git commit -m "feat(coach): translate gym week 9 to English, rename to gym-week9.html"
  ```

---

### Task 9: Wire up the new prefix — profile, index, engine, SKILL.md examples

**Files:**
- Modify: `running/data/user.md`
- Modify: `running/index.html`
- Modify: `running/dements-2026-plan.html` (engine-owned region only)
- Modify: `.claude/skills/coach/SKILL.md`

**Interfaces:**
- Consumes: `parse_gym_files(running_dir, gym_prefix)` and `render_gym_links_js(gym_files)` from `.claude/skills/coach/parse-log.py` (unchanged signatures — confirmed prefix-agnostic).

- [ ] **Step 1: Update `gym_prefix` in the profile**

  In `running/data/user.md`:

  old_string:
  ```
  - gym_prefix: gimnasio-semana
  ```

  new_string:
  ```
  - gym_prefix: gym-week
  ```

- [ ] **Step 2: Update `index.html`'s gym card**

  old_string:
  ```
    <a class="link-card" href="gimnasio-semana8.html">
      <div class="link-icon">🏋️</div>
      <div class="link-info">
        <div class="link-name">Gimnasio — Semana 8</div>
        <div class="link-desc">Gym strength training programme, current block</div>
      </div>
      <div class="link-arrow">›</div>
    </a>
  ```

  new_string:
  ```
    <a class="link-card" href="gym-week8.html">
      <div class="link-icon">🏋️</div>
      <div class="link-info">
        <div class="link-name">Gym — Week 8</div>
        <div class="link-desc">Gym strength training programme, current block</div>
      </div>
      <div class="link-arrow">›</div>
    </a>
  ```

- [ ] **Step 3: Re-run the engine and confirm it maps the new filenames**

  ```bash
  python3 .claude/skills/coach/parse-log.py | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['gym_files']); print(d['current_gym_file'])"
  ```
  Expected: `gym_files` maps weeks 3–9 to `gym-week3.html` … `gym-week9.html` (or a range file, if any two adjacent weeks are byte-identical after translation — they are not, since content differs by week); `current_gym_file` is `gym-week8.html`.

- [ ] **Step 4: Re-apply the `// sync:gymlinks` block in the plan file**

  Get the engine's `gym_links_js` value:
  ```bash
  python3 .claude/skills/coach/parse-log.py | python3 -c "import json,sys; print(json.load(sys.stdin)['gym_links_js'])"
  ```
  In `running/dements-2026-plan.html`, find the block between `// sync:gymlinks` and `// /sync:gymlinks` markers and replace its contents with this output (this is the same engine-owned region SKILL.md step C1/"Linking" already governs — only the mapped filenames change, per the existing rename/split contract).

- [ ] **Step 5: Verify the plan file's zero-diff contract**

  ```bash
  python3 .claude/skills/coach/parse-log.py > /tmp/second-pass.json
  git diff --stat running/dements-2026-plan.html
  ```
  Expected: `git diff --stat` shows only the `// sync:gymlinks` region changed (the gym filenames); re-running the engine a second time and re-applying the same block produces no further diff.

- [ ] **Step 6: Update the SKILL.md Gym programming examples**

  old_string:
  ```
  - **Template:** copy the structure and CSS of the current foundation table
    (`<gym_prefix>3-5.html` (e.g. `gimnasio-semana3-5.html`)): theme bootstrap, `GIMNASIO SEMANA N` title, phase
    subtitle, stat pills, warmup card, exercise grid (`.exercise` with `.cues` and
    `.ex-watch`), and the expected/warning footer. Include the back-to-index link
    (`<a href="index.html">‹ Running</a>` right after `<body>`).
  ```

  new_string:
  ```
  - **Template:** copy the structure and CSS of the current foundation table
    (`<gym_prefix>3-5.html`, e.g. `gym-week3-5.html`): theme bootstrap, a stacked
    two-line title in the profile's language (e.g. `GYM<br>WEEK N` in English,
    `GIMNASIO<br>SEMANA N` in Spanish), phase subtitle, stat pills, warmup card,
    exercise grid (`.exercise` with `.cues` and `.ex-watch`), and the
    expected/warning footer. Include the back-to-index link
    (`<a href="index.html">‹ Running</a>` right after `<body>`).
  ```

  old_string:
  ```
  - **Dedup → ranges:** if a week's programme is identical to the previous week's, do **not**
    create a new file. Name the shared file `<gym_prefix><N-M>.html` (e.g.
    `<gym_prefix>3-5.html` (e.g. `gimnasio-semana3-5.html`) covers weeks 3–5). When a later week diverges, split: shrink the
    range and create the new file. The files must tile the gym weeks without overlap.
  ```

  new_string:
  ```
  - **Dedup → ranges:** if a week's programme is identical to the previous week's, do **not**
    create a new file. Name the shared file `<gym_prefix><N-M>.html` (e.g.
    `<gym_prefix>3-5.html`, e.g. `gym-week3-5.html`, covers weeks 3–5). When a later week diverges, split: shrink the
    range and create the new file. The files must tile the gym weeks without overlap.
  ```

- [ ] **Step 7: Full verification pass**

  ```bash
  # No leftover Spanish gym filenames or the old prefix anywhere live (excluding dist/,
  # historical docs, and SKILL.md's own intentional "GIMNASIO SEMANA N" example of what
  # the Spanish-language option looks like, added in Task 9 Step 6)
  grep -rniI "gimnasio\|semana" --include="*.html" --include="*.md" . \
    | grep -v "^./docs/superpowers/" | grep -v "^./dist/" | grep -v "^./running/coach-log.md" \
    | grep -v "^./.claude/skills/coach/SKILL.md"
  # Expected: no output

  # Every gym file is well-formed (div tags balanced)
  for f in running/gym-week3.html running/gym-week4.html running/gym-week5.html \
           running/gym-week6.html running/gym-week7.html running/gym-week8.html \
           running/gym-week9.html; do
    o=$(grep -o '<div' "$f" | wc -l); c=$(grep -o '</div>' "$f" | wc -l)
    echo "$f: open=$o close=$c"
  done
  # Expected: open == close for every file

  # Existing coach test suite still green (no engine code changed, but confirm)
  python3 .claude/skills/coach/test-parse-log.py
  python3 .claude/skills/coach/test-user-profile.py
  ```
  Expected: the grep returns nothing; every file's div counts match; both test scripts report success (no assertion errors / exit 0).

- [ ] **Step 8: Commit**

  ```bash
  git add running/data/user.md running/index.html running/dements-2026-plan.html .claude/skills/coach/SKILL.md
  git commit -m "feat(coach): point gym_prefix + index + plan links at the new gym-week files"
  ```
