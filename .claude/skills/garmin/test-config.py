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


def test_read_log_dir_empty_value_exits():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("log_dir:   \n")
        try:
            cfg.read_log_dir(p)
            assert False, "expected SystemExit for empty log_dir value"
        except SystemExit:
            pass

def test_parse_key_reads_any_key():
    assert cfg.parse_key("- gym_prefix: gym-week\n", "gym_prefix") == "gym-week"


def test_parse_key_missing_key():
    assert cfg.parse_key("- log_dir: /a/b\n", "gym_prefix") is None


def test_parse_key_picks_the_named_key_only():
    text = "- log_dir: /a/b\n- gym_prefix: strength-week\n- language: English\n"
    assert cfg.parse_key(text, "gym_prefix") == "strength-week"


def test_read_gym_prefix_happy_path():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("- log_dir: /tmp/log\n- gym_prefix: gym-week\n")
        assert cfg.read_gym_prefix(p) == "gym-week"


def test_read_gym_prefix_missing_key_exits():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "user.md")
        with open(p, "w") as f:
            f.write("- log_dir: /tmp/log\n")
        try:
            cfg.read_gym_prefix(p)
            assert False, "expected SystemExit for a missing gym_prefix"
        except SystemExit:
            pass


if __name__ == "__main__":
    test_parse_log_dir_bulleted()
    test_parse_log_dir_plain()
    test_parse_log_dir_path_with_spaces()
    test_parse_log_dir_missing_key()
    test_read_log_dir_missing_file_exits()
    test_read_log_dir_happy_path()
    test_read_log_dir_empty_value_exits()
    test_parse_key_reads_any_key()
    test_parse_key_missing_key()
    test_parse_key_picks_the_named_key_only()
    test_read_gym_prefix_happy_path()
    test_read_gym_prefix_missing_key_exits()
    print("OK")
