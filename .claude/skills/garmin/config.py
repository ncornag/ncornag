"""Read per-machine config for the garmin skill from running/data/user.md.

Kept separate from download-garmin.py so the parser is importable by tests
without triggering that script's venv bootstrap. Pure stdlib."""
import re
from pathlib import Path


def parse_key(text, key):
    """Return the value of `key` from user.md contents, or None if absent."""
    m = re.search(rf"^\s*[-*]?\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def read_key(config_path, key, example):
    """Read `key` from the user.md at config_path.

    Raises SystemExit with a clear message if the file or the key is missing."""
    path = Path(config_path)
    if not path.exists():
        raise SystemExit(
            f"missing {path} — create it with a line:\n"
            f"  {key}: {example}")
    value = parse_key(path.read_text(encoding="utf-8"), key)
    if not value:
        raise SystemExit(
            f"no '{key}:' line in {path} — add e.g.\n"
            f"  {key}: {example}")
    return value


def parse_log_dir(text):
    """Return the log_dir value from user.md contents, or None if absent."""
    return parse_key(text, "log_dir")


def read_log_dir(config_path):
    """Read the log_dir path from the user.md at config_path."""
    return read_key(config_path, "log_dir", "/path/to/your/activity/log")


def read_gym_prefix(config_path):
    """Read the gym-file prefix (e.g. `gym-week`) from the user.md at config_path."""
    return read_key(config_path, "gym_prefix", "gym-week")
