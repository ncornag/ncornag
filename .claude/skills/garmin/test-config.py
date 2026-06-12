#!/usr/bin/env python3
"""Plain-assert tests for config.py. Run: python3 test-config.py"""
import importlib.util
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "garmin_config", os.path.join(HERE, "config.py"))
cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg)


def test_parse_log_dir_bulleted():
    assert cfg.parse_log_dir("- log_dir: /a/b/c\n") == "/a/b/c"


def test_parse_log_dir_plain():
    assert cfg.parse_log_dir("log_dir: /x/y\n") == "/x/y"


def test_parse_log_dir_path_with_spaces():
    text = "# config\n- log_dir: /Users/me/My Drive/running/log\n"
    assert cfg.parse_log_dir(text) == "/Users/me/My Drive/running/log"


def test_parse_log_dir_missing_key():
    assert cfg.parse_log_dir("# config\nno key here\n") is None


def test_read_log_dir_missing_file_exits():
    with tempfile.TemporaryDirectory() as d:
        try:
            cfg.read_log_dir(os.path.join(d, "user.md"))
            assert False, "expected SystemExit for a missing file"
        except SystemExit:
            pass


def test_read_log_dir_happy_path():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("- log_dir: /tmp/log\n")
        assert cfg.read_log_dir(p) == "/tmp/log"


if __name__ == "__main__":
    test_parse_log_dir_bulleted()
    test_parse_log_dir_plain()
    test_parse_log_dir_path_with_spaces()
    test_parse_log_dir_missing_key()
    test_read_log_dir_missing_file_exits()
    test_read_log_dir_happy_path()
    print("OK")
