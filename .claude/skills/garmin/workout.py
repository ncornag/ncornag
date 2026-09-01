"""Turn a gym week's HTML table into a Garmin strength-workout payload.

The coach skill writes each gym week as `running/<gym_prefix><N>.html`. That
file is the source of truth: this module reads its exercise cards and builds
the matching Garmin workout, so the watch shows the same sets, reps, holds and
loads the athlete reads on the page.

Kept separate from upload-workout.py, like config.py is from
download-garmin.py, so the parser is importable by tests without triggering
that script's venv bootstrap. Pure stdlib.

Shape of the generated workout, copied from the athlete's own hand-built ones:
a single strength segment holding one repeat group (the circuit) of every
exercise in page order, REST_BETWEEN_S between them, REST_AFTER_LAST_S after
the last, then REST_TAIL_S outside the group.

Two conventions the HTML leaves implicit, both taken from those workouts:
  - A rep count is already per side ("3 x 8 / leg" is 8 reps), so it is used
    as written.
  - A timed hold is not ("3 x 40s / side" is one 80s step covering both), so
    per-side holds are doubled.
"""
import glob
import html as html_mod
import os
import re
from pathlib import Path

from config import read_gym_prefix

# Circuit timing, in seconds — matches the athlete's existing workouts.
REST_BETWEEN_S = 30.0
REST_AFTER_LAST_S = 90.0
REST_TAIL_S = 20.0

# Garmin caps a step description at 200 characters.
DESC_MAX = 200

# The gym page's exercise name (lowercased) -> Garmin's (category, exerciseName).
# Garmin only accepts names from its own catalogue, so a new exercise on a gym
# page must be added here before that week can be pushed; build_workout stops
# and names anything it cannot map rather than guessing a near-miss.
EXERCISES = {
    "banded lateral walk":              ("BANDED_EXERCISES", "LATERAL_BAND_WALKS"),
    "bulgarian split squat":            ("LUNGE", "DUMBBELL_BULGARIAN_SPLIT_SQUAT"),
    "single-leg calf raise":            ("CALF_RAISE", "SINGLE_LEG_STANDING_CALF_RAISE"),
    "single-leg glute bridge":          ("HIP_RAISE", "BRIDGE_WITH_LEG_EXTENSION"),
    "dead bug":                         ("HIP_STABILITY", "DEAD_BUG"),
    "side plank":                       ("PLANK", "SIDE_PLANK"),
    "high step-up + eccentric descent": ("SQUAT", "STEP_UP"),
    "one-arm bent-over row":            ("ROW", "ONE_ARM_BENT_OVER_ROW"),
    "calf raise bent-knee":             ("CALF_RAISE", "SEATED_CALF_RAISE"),
}

STRENGTH = {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 4}
KILOGRAM = {"unitId": 8, "unitKey": "kilogram", "factor": 1000.0}
NO_TARGET = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target",
             "displayOrder": 1}
COND_TIME = {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2,
             "displayable": True}
COND_REPS = {"conditionTypeId": 10, "conditionTypeKey": "reps", "displayOrder": 10,
             "displayable": True}
COND_ITER = {"conditionTypeId": 7, "conditionTypeKey": "iterations",
             "displayOrder": 7, "displayable": False}
TYPE_INTERVAL = {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3}
TYPE_REST = {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5}
TYPE_REPEAT = {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6}


# --- parse the gym page -----------------------------------------------------

def text_of(fragment):
    """Visible text of an HTML fragment: tags dropped, entities decoded."""
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html_mod.unescape(fragment).split())


def gym_file_for(week, running_dir, config_path):
    """The gym page covering `week`, honouring range names like gym-week3-5.html.

    Mirrors parse_gym_files() in the coach engine: sorted order, later wins."""
    prefix = read_gym_prefix(config_path)
    name_re = re.compile(re.escape(prefix) + r"(\d+)(?:-(\d+))?\.html$")
    found = None
    for path in sorted(glob.glob(os.path.join(running_dir, prefix + "*.html"))):
        m = name_re.search(os.path.basename(path))
        if not m:
            continue
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if hi < lo:
            lo, hi = hi, lo
        if lo <= week <= hi:
            found = Path(path)
    if found is None:
        raise SystemExit(f"no {prefix}*.html file covers week {week}")
    return found


def parse_gym_page(path):
    """One dict per exercise card, in page order, straight from the HTML."""
    path = Path(path)
    page = path.read_text(encoding="utf-8")
    cards = []
    for chunk in page.split('<div class="exercise">')[1:]:
        name_m = re.search(r'<div class="ex-name">(.*?)</div>', chunk, re.S)
        sets_m = re.search(r'<div class="ex-sets">(.*?)</div>', chunk, re.S)
        if not name_m or not sets_m:
            continue
        name_html = name_m.group(1)

        load_m = re.search(r'<span class="ex-load[^"]*">(.*?)</span>', name_html, re.S)
        load_text = text_of(load_m.group(1)) if load_m else ""
        name = text_of(re.sub(r'<span class="ex-load.*?</span>', "", name_html,
                              flags=re.S))

        sets_text = text_of(sets_m.group(1))
        m = re.match(r"(\d+)\s*[×x]\s*(\d+)(s?)\b", sets_text)
        if not m:
            raise SystemExit(f"{path.name}: cannot read sets/reps from {sets_text!r} "
                             f"for {name!r}")
        qual_m = re.search(r"/\s*(leg|side|arm)\b", sets_text)

        cues = []
        for block in re.findall(r'<ul class="cues">(.*?)</ul>', chunk, re.S):
            cues += [text_of(li) for li in re.findall(r"<li>(.*?)</li>", block, re.S)]

        kg_m = re.match(r"([\d.]+)\s*kg\b", load_text)
        cards.append({
            "name": name,
            "sets": int(m.group(1)),
            "count": int(m.group(2)),
            "timed": m.group(3) == "s",
            "per_side": qual_m.group(1) if qual_m else None,
            "load_text": load_text,
            "weight_kg": float(kg_m.group(1)) if kg_m else None,
            "cues": cues,
        })
    if not cards:
        raise SystemExit(f"{path.name}: no .exercise cards found")
    return cards


# --- build the Garmin workout ----------------------------------------------

def describe(card):
    """Step description: the page's own prescription line, then its cues."""
    unit = "s" if card["timed"] else ""
    head = f"{card['sets']} × {card['count']}{unit}"
    if card["per_side"]:
        head += f" / {card['per_side']}"
    if card["load_text"]:
        head += f" · {card['load_text']}"
    return "\n".join([head, *card["cues"]])[:DESC_MAX]


def rest_step(order, seconds, child=1):
    return {
        "type": "ExecutableStepDTO", "stepOrder": order, "stepType": TYPE_REST,
        "childStepId": child, "description": None,
        "endCondition": COND_TIME, "endConditionValue": seconds,
        "targetType": NO_TARGET,
    }


def exercise_step(order, card):
    category, exercise_name = EXERCISES[card["name"].lower()]

    if card["timed"]:
        # A timed hold is written per side but runs as one step covering both.
        seconds = card["count"] * (2 if card["per_side"] else 1)
        end_condition, end_value = COND_TIME, float(seconds)
    else:
        end_condition, end_value = COND_REPS, float(card["count"])

    step = {
        "type": "ExecutableStepDTO", "stepOrder": order, "stepType": TYPE_INTERVAL,
        "childStepId": 1, "description": describe(card),
        "endCondition": end_condition, "endConditionValue": end_value,
        "endConditionCompare": "", "targetType": NO_TARGET,
        "category": category, "exerciseName": exercise_name,
        # Garmin has no "bodyweight" value: a step is a number plus a unit, so
        # an unloaded exercise is sent as 0 kg.
        "weightValue": card["weight_kg"] or 0.0, "weightUnit": KILOGRAM,
    }
    return step


def build_workout(week, cards):
    """One circuit of every card, repeated `sets` times."""
    rounds = {c["sets"] for c in cards}
    if len(rounds) > 1:
        detail = ", ".join(f"{c['name']}: {c['sets']}" for c in cards)
        raise SystemExit(
            f"week {week}: the page mixes set counts ({detail}). A circuit is one "
            f"repeat group, so every exercise must share the same number of sets.")
    unmapped = [c["name"] for c in cards if c["name"].lower() not in EXERCISES]
    if unmapped:
        raise SystemExit(
            "no Garmin exercise mapped for: " + ", ".join(repr(u) for u in unmapped) +
            "\nAdd each to EXERCISES in workout.py, as "
            "'<page name lowercased>': ('<CATEGORY>', '<EXERCISE_NAME>').")

    steps, order = [], 2                       # 1 is the repeat group itself
    for i, card in enumerate(cards):
        steps.append(exercise_step(order, card))
        order += 1
        last = i == len(cards) - 1
        steps.append(rest_step(order, REST_AFTER_LAST_S if last else REST_BETWEEN_S))
        order += 1

    group = {
        "type": "RepeatGroupDTO", "stepOrder": 1, "stepType": TYPE_REPEAT,
        "childStepId": 1, "numberOfIterations": cards[0]["sets"],
        "endCondition": COND_ITER, "endConditionValue": float(cards[0]["sets"]),
        "skipLastRestStep": True, "smartRepeat": False,
        "workoutSteps": steps,
    }
    return {
        "workoutName": f"week {week}",
        "description": "",
        "sportType": STRENGTH,
        "subSportType": None,
        "estimatedDurationInSecs": 0,
        "estimatedDistanceInMeters": 0.0,
        "avgTrainingSpeed": 0.0,
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": STRENGTH,
            "workoutSteps": [group, rest_step(order, REST_TAIL_S, child=None)],
        }],
    }


def summary_lines(workout):
    """Human-readable one line per exercise, for the CLI and the coach's summary."""
    group = workout["workoutSegments"][0]["workoutSteps"][0]
    lines = [f"circuit × {group['numberOfIterations']}"]
    for step in group["workoutSteps"]:
        if step["stepType"]["stepTypeKey"] == "rest":
            continue
        unit = "s" if step["endCondition"]["conditionTypeKey"] == "time" else " reps"
        weight = f" @ {step['weightValue']:g} kg" if step["weightValue"] else ""
        lines.append(f"  {step['exerciseName']:32s} "
                     f"{step['endConditionValue']:g}{unit}{weight}"
                     f"   | {step['description'].splitlines()[0]}")
    return lines
