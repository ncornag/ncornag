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
        m = pl.parse_gym_files(d, "gimnasio-semana")
        assert m == {3: "gimnasio-semana3-5.html",
                     4: "gimnasio-semana3-5.html",
                     5: "gimnasio-semana3-5.html",
                     7: "gimnasio-semana7.html"}, m


def test_parse_gym_files_empty():
    with tempfile.TemporaryDirectory() as d:
        assert pl.parse_gym_files(d, "gimnasio-semana") == {}


def _weeks(logged_by_week):
    """Minimal week dicts: {week_no: (planned_days, logged_days)}.

    TOTAL_WEEKS is a module global main() sets from the profile, so these tests
    set it themselves rather than importing a real user.md."""
    pl.TOTAL_WEEKS = 26
    out = []
    for n in range(1, pl.TOTAL_WEEKS + 1):
        planned, logged = logged_by_week.get(n, ([], []))
        out.append({
            "week": n,
            "plan_days": [{"day": d, "type": "z2"} for d in planned],
            "logged_days": logged,
        })
    return out


def test_resolve_current_week_stays_when_sessions_remain():
    weeks = _weeks({17: (["Tue", "Thu", "Sat", "Sun"], ["Tue", "Thu", "Sat"])})
    assert pl.resolve_current_week(weeks, 17) == 17


def test_resolve_current_week_advances_when_all_logged():
    weeks = _weeks({17: (["Tue", "Thu", "Sat"], ["Tue", "Thu", "Sat"])})
    assert pl.resolve_current_week(weeks, 17) == 18


def test_closed_through_advances_past_a_week_with_a_dropped_session():
    # W17's Sunday was deliberately dropped, so it can never complete on its
    # own — the athlete's declaration is what moves the plan on.
    weeks = _weeks({17: (["Tue", "Thu", "Sat", "Sun"], ["Tue", "Thu", "Sat"])})
    assert pl.resolve_current_week(weeks, 17, closed_through=17) == 18


def test_closed_through_never_rewinds_the_calendar():
    weeks = _weeks({})
    assert pl.resolve_current_week(weeks, 20, closed_through=17) == 20


def test_closed_through_is_capped_at_the_last_week():
    weeks = _weeks({})
    assert pl.resolve_current_week(weeks, 26, closed_through=26) == 26


def test_closed_through_outside_the_plan_is_ignored():
    assert pl.resolve_current_week(_weeks({}), None, closed_through=17) is None


def test_render_gym_links_js_has_map_and_walker():
    js = pl.render_gym_links_js({3: "gimnasio-semana3-5.html",
                                 4: "gimnasio-semana3-5.html"})
    assert '3: "gimnasio-semana3-5.html"' in js, js
    assert "document.querySelectorAll('.week[id]')" in js, js
    assert ".day.gym .day-km" in js, js


def test_render_gym_links_js_empty():
    js = pl.render_gym_links_js({})
    assert "const gymFiles = {}" in js, js


if __name__ == "__main__":
    test_parse_gym_files_single_and_range()
    test_resolve_current_week_stays_when_sessions_remain()
    test_resolve_current_week_advances_when_all_logged()
    test_closed_through_advances_past_a_week_with_a_dropped_session()
    test_closed_through_never_rewinds_the_calendar()
    test_closed_through_is_capped_at_the_last_week()
    test_closed_through_outside_the_plan_is_ignored()
    test_parse_gym_files_empty()
    test_render_gym_links_js_has_map_and_walker()
    test_render_gym_links_js_empty()
    print("OK")
