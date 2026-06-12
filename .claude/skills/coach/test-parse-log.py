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
    test_parse_gym_files_empty()
    test_render_gym_links_js_has_map_and_walker()
    test_render_gym_links_js_empty()
    print("OK")
