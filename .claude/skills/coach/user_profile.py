"""Parse the athlete + training profile from running/data/user.md.

Pure stdlib so it is importable by tests and by parse-log.py without any
dependency. The coach skill reads the whole file as prose context; this parser
extracts only the structured values the engine computes with. Named
`user_profile` (not `profile`) to avoid shadowing the stdlib `profile` module."""
import re
from datetime import datetime
from pathlib import Path

_ZONE_ROW = re.compile(r"^\s*\|\s*(Z[1-5])\s*\|\s*(\d+)\s*\|\s*$", re.MULTILINE)
_PLAN_ROW = re.compile(
    r"^\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)\s*\|\s*$", re.MULTILINE)


def _num(s):
    """'25' -> int 25, '42.5' -> float 42.5 (preserves the old PLAN's types)."""
    s = s.strip()
    return float(s) if "." in s else int(s)


def _value(text, key):
    """Read a `key: value` line (optionally bulleted), or None if absent."""
    m = re.search(rf"^\s*[-*]?\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def parse_zone_cutoffs(text):
    """Z2..Z5 lower bounds (the hr_zone cutoffs) from the HR-zones table."""
    zones = {z: int(v) for z, v in _ZONE_ROW.findall(text)}
    return [zones[z] for z in ("Z2", "Z3", "Z4", "Z5") if z in zones]


def parse_plan(text):
    """List of (km, elev) ordered by week from the Training-plan table."""
    rows = [(int(w), _num(km), int(elev)) for w, km, elev in _PLAN_ROW.findall(text)]
    rows.sort(key=lambda r: r[0])
    return [(km, elev) for _, km, elev in rows]


def read_profile(config_path):
    """Read the structured engine values from the user.md at config_path.

    Raises SystemExit with a clear message if the file or a required
    field/table is missing or malformed."""
    path = Path(config_path)
    if not path.exists():
        raise SystemExit(
            f"missing {path} — create the athlete profile (see the coach skill).")
    text = path.read_text(encoding="utf-8")

    def need(key):
        v = _value(text, key)
        if v is None:
            raise SystemExit(f"{path}: missing required '{key}:' line")
        return v

    plan = parse_plan(text)
    cutoffs = parse_zone_cutoffs(text)
    if not plan:
        raise SystemExit(f"{path}: no Training plan table rows found")
    if len(cutoffs) != 4:
        raise SystemExit(f"{path}: HR zones table must define Z2..Z5 lower bounds")
    try:
        plan_start = datetime.strptime(need("plan_start"), "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"{path}: plan_start must be YYYY-MM-DD")
    closed_through = _value(text, "closed_through")
    if closed_through is not None:
        try:
            closed_through = int(closed_through)
        except ValueError:
            raise SystemExit(f"{path}: closed_through must be a week number")
    return {
        "plan_file": need("plan_file"),
        "gym_prefix": need("gym_prefix"),
        "plan_start": plan_start,
        "hilly_elev": int(need("hilly_elev")),
        "zone_cutoffs": cutoffs,
        "plan": plan,
        "closed_through": closed_through,
    }
