#!/usr/bin/env python3
"""Plain-assert tests for workout.py. Run: python3 test-workout.py"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                       # workout.py imports config.py
_spec = importlib.util.spec_from_file_location(
    "garmin_workout", os.path.join(HERE, "workout.py"))
wo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wo)


def card_html(name, load, sets, qualifier=None, cues=()):
    load_span = f'<span class="ex-load">{load}</span>' if load else ""
    qual = (f'<br><span style="font-size:.6rem;">/ {qualifier}</span>'
            if qualifier else "")
    cue_lis = "".join(f"<li>{c}</li>" for c in cues)
    return f"""<div class="exercise">
      <div class="ex-header">
        <div class="ex-num-name">
          <div class="ex-name">{name}{load_span}</div>
        </div>
        <div class="ex-sets">{sets}{qual}</div>
      </div>
      <ul class="cues">{cue_lis}</ul>
    </div>"""


def page(*cards):
    return "<html><body>" + "".join(cards) + "</body></html>"


def write(tmp, text, name="gym-week9.html"):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


# --- parsing ----------------------------------------------------------------

def test_parses_name_load_sets_and_cues():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, page(card_html(
            "Bulgarian<br>Split Squat", "12 kg", "3 × 10", "leg",
            cues=["Back foot on the bench", "Thigh &asymp; parallel"])))
        c, = wo.parse_gym_page(p)
        assert c["name"] == "Bulgarian Split Squat", c["name"]
        assert (c["sets"], c["count"]) == (3, 10)
        assert c["timed"] is False
        assert c["per_side"] == "leg"
        assert c["weight_kg"] == 12.0
        assert c["cues"] == ["Back foot on the bench", "Thigh ≈ parallel"], c["cues"]


def test_bodyweight_and_band_carry_no_weight():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, page(card_html("Dead<br>Bug", "bodyweight", "3 × 8", "side"),
                          card_html("Banded<br>Lateral Walk", "band · ankles",
                                    "3 × 15")))
        bug, band = wo.parse_gym_page(p)
        assert bug["weight_kg"] is None
        assert band["weight_kg"] is None
        assert band["per_side"] is None


def test_timed_hold_is_flagged():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, page(card_html("Side<br>Plank", "bodyweight", "3 × 40s", "side")))
        c, = wo.parse_gym_page(p)
        assert c["timed"] is True
        assert (c["count"], c["per_side"]) == (40, "side")


def test_page_with_no_cards_exits():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "<html><body><p>nothing here</p></body></html>")
        try:
            wo.parse_gym_page(p)
            assert False, "expected SystemExit for a page with no exercise cards"
        except SystemExit:
            pass


def test_unreadable_sets_exits():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, page(card_html("Dead<br>Bug", "bodyweight", "as many as you like")))
        try:
            wo.parse_gym_page(p)
            assert False, "expected SystemExit for an unparseable sets field"
        except SystemExit:
            pass


# --- building ---------------------------------------------------------------

def bug_card(**over):
    card = {"name": "Dead Bug", "sets": 3, "count": 8, "timed": False,
            "per_side": "side", "load_text": "bodyweight", "weight_kg": None,
            "cues": ["Lower back pressed to the floor"]}
    card.update(over)
    return card


def steps_of(workout):
    group = workout["workoutSegments"][0]["workoutSteps"][0]
    return [s for s in group["workoutSteps"]
            if s["stepType"]["stepTypeKey"] != "rest"]


def test_reps_are_used_as_written():
    w = wo.build_workout(9, [bug_card()])
    step, = steps_of(w)
    assert step["endCondition"]["conditionTypeKey"] == "reps"
    assert step["endConditionValue"] == 8.0
    assert step["exerciseName"] == "DEAD_BUG"
    assert step["category"] == "HIP_STABILITY"


def test_per_side_hold_is_doubled():
    w = wo.build_workout(9, [bug_card(name="Side Plank", timed=True, count=40)])
    step, = steps_of(w)
    assert step["endCondition"]["conditionTypeKey"] == "time"
    assert step["endConditionValue"] == 80.0, step["endConditionValue"]


def test_hold_without_a_side_is_not_doubled():
    w = wo.build_workout(9, [bug_card(name="Side Plank", timed=True, count=40,
                                      per_side=None)])
    step, = steps_of(w)
    assert step["endConditionValue"] == 40.0


def test_weight_becomes_kilograms():
    w = wo.build_workout(9, [bug_card(name="One-Arm Bent-Over Row", count=12,
                                      load_text="12 kg", weight_kg=12.0)])
    step, = steps_of(w)
    assert step["weightValue"] == 12.0
    assert step["weightUnit"]["unitKey"] == "kilogram"


def test_bodyweight_step_is_zero_kilograms():
    w = wo.build_workout(9, [bug_card()])
    step, = steps_of(w)
    assert step["weightValue"] == 0.0
    assert step["weightUnit"]["unitKey"] == "kilogram"


def test_circuit_shape_rests_and_order():
    cards = [bug_card(), bug_card(name="Side Plank", timed=True, count=40)]
    w = wo.build_workout(9, cards)
    seg_steps = w["workoutSegments"][0]["workoutSteps"]
    group, tail = seg_steps
    assert group["numberOfIterations"] == 3
    assert group["skipLastRestStep"] is True
    rests = [s["endConditionValue"] for s in group["workoutSteps"]
             if s["stepType"]["stepTypeKey"] == "rest"]
    assert rests == [wo.REST_BETWEEN_S, wo.REST_AFTER_LAST_S], rests
    assert tail["endConditionValue"] == wo.REST_TAIL_S
    orders = [s["stepOrder"] for s in group["workoutSteps"]]
    assert orders == [2, 3, 4, 5], orders
    assert w["workoutName"] == "week 9"


def test_description_leads_with_the_prescription_then_cues():
    w = wo.build_workout(9, [bug_card()])
    step, = steps_of(w)
    assert step["description"].splitlines()[0] == "3 × 8 / side · bodyweight"
    assert "Lower back pressed to the floor" in step["description"]


def test_description_is_capped_at_the_garmin_limit():
    w = wo.build_workout(9, [bug_card(cues=["x" * 400])])
    step, = steps_of(w)
    assert len(step["description"]) == wo.DESC_MAX


def test_mixed_set_counts_exit():
    try:
        wo.build_workout(9, [bug_card(sets=3), bug_card(name="Side Plank", sets=2)])
        assert False, "expected SystemExit when the page mixes set counts"
    except SystemExit as e:
        assert "mixes set counts" in str(e)


def test_unmapped_exercise_exits_naming_it():
    try:
        wo.build_workout(9, [bug_card(name="Kettlebell Juggling")])
        assert False, "expected SystemExit for an unmapped exercise"
    except SystemExit as e:
        assert "Kettlebell Juggling" in str(e)


# --- file lookup ------------------------------------------------------------

def user_md(tmp, prefix="gym-week"):
    p = os.path.join(tmp, "user.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"- gym_prefix: {prefix}\n")
    return p


def test_gym_file_lookup_single_week():
    with tempfile.TemporaryDirectory() as d:
        write(d, page(card_html("Dead<br>Bug", "bodyweight", "3 × 8")),
              "gym-week9.html")
        got = wo.gym_file_for(9, d, user_md(d))
        assert os.path.basename(got) == "gym-week9.html"


def test_gym_file_lookup_range_covers_every_week():
    with tempfile.TemporaryDirectory() as d:
        write(d, "x", "gym-week3-5.html")
        cfg = user_md(d)
        for week in (3, 4, 5):
            got = wo.gym_file_for(week, d, cfg)
            assert os.path.basename(got) == "gym-week3-5.html", (week, got)


def test_gym_file_lookup_uncovered_week_exits():
    with tempfile.TemporaryDirectory() as d:
        write(d, "x", "gym-week3-5.html")
        try:
            wo.gym_file_for(9, d, user_md(d))
            assert False, "expected SystemExit for a week with no gym file"
        except SystemExit:
            pass


if __name__ == "__main__":
    test_parses_name_load_sets_and_cues()
    test_bodyweight_and_band_carry_no_weight()
    test_timed_hold_is_flagged()
    test_page_with_no_cards_exits()
    test_unreadable_sets_exits()
    test_reps_are_used_as_written()
    test_per_side_hold_is_doubled()
    test_hold_without_a_side_is_not_doubled()
    test_weight_becomes_kilograms()
    test_bodyweight_step_is_zero_kilograms()
    test_circuit_shape_rests_and_order()
    test_description_leads_with_the_prescription_then_cues()
    test_description_is_capped_at_the_garmin_limit()
    test_mixed_set_counts_exit()
    test_unmapped_exercise_exits_naming_it()
    test_gym_file_lookup_single_week()
    test_gym_file_lookup_range_covers_every_week()
    test_gym_file_lookup_uncovered_week_exits()
    print("OK")
