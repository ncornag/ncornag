"""Read per-machine config for the garmin skill from running/data/user.md.

Kept separate from download-garmin.py so the parser is importable by tests
without triggering that script's venv bootstrap. Pure stdlib."""
import re
from pathlib import Path

_LOG_DIR_RE = re.compile(r"^\s*[-*]?\s*log_dir\s*:\s*(.+?)\s*$", re.MULTILINE)


def parse_log_dir(text):
    """Return the log_dir value from user.md contents, or None if absent."""
    m = _LOG_DIR_RE.search(text)
    return m.group(1).strip() if m else None


def read_log_dir(config_path):
    """Read the log_dir path from the user.md at config_path.

    Raises SystemExit with a clear message if the file or the key is missing."""
    path = Path(config_path)
    if not path.exists():
        raise SystemExit(
            f"missing {path} — create it with a line:\n"
            f"  log_dir: /path/to/your/activity/log")
    value = parse_log_dir(path.read_text(encoding="utf-8"))
    if not value:
        raise SystemExit(
            f"no 'log_dir:' line in {path} — add e.g.\n"
            f"  log_dir: /path/to/your/activity/log")
    return value
