#!/usr/bin/env python3
"""Plain-assert tests for user_profile.py. Run: python3 test-user-profile.py"""
import importlib.util
import os
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "user_profile", os.path.join(HERE, "user_profile.py"))
up = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(up)

ZONES = "| Z1 | 0 |\n| Z2 | 135 |\n| Z3 | 152 |\n| Z4 | 163 |\n| Z5 | 174 |\n"
PLAN = "| 1 | 25 | 0 |\n| 2 | 17 | 30 |\n| 3 | 42.5 | 3808 |\n"
FULL = (
    "## Paths\n- plan_file: p.html\n- gym_prefix: gym-week\n\n"
    "## HR zones\n" + ZONES +
    "\n## Training plan\n- plan_start: 2026-05-11\n- hilly_elev: 30\n\n" + PLAN
)


def test_parse_zone_cutoffs():
    assert up.parse_zone_cutoffs(ZONES) == [135, 152, 163, 174]


def test_parse_plan_preserves_int_and_float():
    # "25" stays int, "42.5" stays float (so JSON output matches the old PLAN).
    assert up.parse_plan(PLAN) == [(25, 0), (17, 30), (42.5, 3808)]


def test_parse_plan_sorts_by_week():
    out_of_order = "| 3 | 5 | 0 |\n| 1 | 9 | 0 |\n| 2 | 7 | 0 |\n"
    assert up.parse_plan(out_of_order) == [(9, 0), (7, 0), (5, 0)]


def test_read_profile_happy_path():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write(FULL)
        prof = up.read_profile(p)
        assert prof["plan_file"] == "p.html"
        assert prof["gym_prefix"] == "gym-week"
        assert prof["plan_start"] == date(2026, 5, 11)
        assert prof["hilly_elev"] == 30
        assert prof["zone_cutoffs"] == [135, 152, 163, 174]
        assert prof["plan"] == [(25, 0), (17, 30), (42.5, 3808)]


def test_read_profile_missing_file_exits():
    with tempfile.TemporaryDirectory() as d:
        try:
            up.read_profile(os.path.join(d, "nope.md"))
            assert False, "expected SystemExit"
        except SystemExit:
            pass


def test_read_profile_missing_plan_exits():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("## Paths\n- plan_file: p.html\n- gym_prefix: g\n## HR zones\n" + ZONES
                    + "- plan_start: 2026-05-11\n- hilly_elev: 30\n")  # no plan table
        try:
            up.read_profile(p)
            assert False, "expected SystemExit"
        except SystemExit:
            pass


def test_read_profile_missing_zones_exits():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("## Paths\n- plan_file: p.html\n- gym_prefix: g\n"
                    "## Training plan\n- plan_start: 2026-05-11\n- hilly_elev: 30\n" + PLAN)
        try:
            up.read_profile(p)
            assert False, "expected SystemExit"
        except SystemExit:
            pass


if __name__ == "__main__":
    test_parse_zone_cutoffs()
    test_parse_plan_preserves_int_and_float()
    test_parse_plan_sorts_by_week()
    test_read_profile_happy_path()
    test_read_profile_missing_file_exits()
    test_read_profile_missing_plan_exits()
    test_read_profile_missing_zones_exits()
    print("OK")
