#!/usr/bin/env python3
"""Download Garmin Connect activities as .fit and build the coach's monthly CSVs.

This is the data source for the running coach (it replaces the old tcx-ls /
tcx-to-csv.sh pipeline). It does two things in one run:

  1. Download every Garmin Connect activity from a start date (default
     2026-01-01) to today as its native .fit file, into the per-year log
     folder, skipping activities already on disk.
  2. Decode each .fit with the official Garmin FIT SDK and (re)write the coach's
     monthly summary CSVs (running/data/tcx-YYYY-MM.csv) with every named SDK
     session field, raw, one row per activity. The header is the union of fields
     seen that month (lead columns the coach keys on first, then the rest
     alphabetical); parse-log.py reads the fields it needs by name.

Dependencies (garminconnect, garmin-fit-sdk, curl_cffi) are installed into a
local venv (.claude/skills/garmin/.venv) automatically on first run; the script re-executes
itself inside that venv, so plain `python3 download-garmin.py` just works.

Usage:
  python3 .claude/skills/garmin/download-garmin.py                    # 2026-01-01 to today
  python3 .claude/skills/garmin/download-garmin.py --start 2026-05-01 # custom start date
  python3 .claude/skills/garmin/download-garmin.py --end 2026-06-30   # custom end date
  python3 .claude/skills/garmin/download-garmin.py --no-download      # only rebuild CSVs
  python3 .claude/skills/garmin/download-garmin.py --no-csv           # only download

Credentials: set GARMIN_EMAIL / GARMIN_PASSWORD in the environment, or you will
be prompted. Tokens are cached in ~/.garminconnect so later runs need no login.
MFA codes are prompted for interactively when Garmin requires one.
"""

import os
import sys
import subprocess
from pathlib import Path

# --- venv bootstrap ---------------------------------------------------------
# Re-exec inside the skill-local .venv with the required third-party deps installed.
# system Python is PEP 668-managed, so we never install into it.

SKILL_DIR = Path(__file__).resolve().parent            # .../.claude/skills/garmin
REPO = Path(__file__).resolve().parents[3]             # .../profile
VENV_DIR = SKILL_DIR / ".venv"
VENV_PY = VENV_DIR / "bin" / "python"
REQUIRED = ["garminconnect", "garmin-fit-sdk", "curl_cffi"]


def _ensure_venv_and_reexec():
    """Create the venv + install deps if needed, then re-exec this script in it."""
    if os.environ.get("GARMIN_DL_IN_VENV") == "1":
        return  # already running inside the venv
    if not VENV_PY.exists():
        print(f"Creating venv at {VENV_DIR} ...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q",
                        "--upgrade", "pip"], check=True)
    # Install any missing deps (cheap no-op when already present).
    check = subprocess.run(
        [str(VENV_PY), "-c",
         "import garminconnect, garmin_fit_sdk, curl_cffi"],
        capture_output=True)
    if check.returncode != 0:
        print(f"Installing dependencies into venv: {', '.join(REQUIRED)} ...")
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q",
                        "--upgrade", *REQUIRED], check=True)
    env = dict(os.environ, GARMIN_DL_IN_VENV="1")
    os.execve(str(VENV_PY), [str(VENV_PY), __file__, *sys.argv[1:]], env)


_ensure_venv_and_reexec()

# --- everything below runs inside the venv ----------------------------------

import argparse
import csv
import io
import math
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone

from garminconnect import Garmin
from garmin_fit_sdk import Decoder, Stream

from config import read_log_dir

# The download-format enum is nested on the Garmin class in this version.
ActivityDownloadFormat = Garmin.ActivityDownloadFormat

DATA_DIR = REPO / "running" / "data"
LOG_DIR = Path(read_log_dir(DATA_DIR / "user.md"))
TOKEN_STORE = os.path.expanduser("~/.garminconnect")

# Map Garmin typeKey -> the filename suffix / activity_type the coach expects.
TYPE_SUFFIX = {
    "running": "Running",
    "trail_running": "Running",
    "treadmill_running": "Running",
    "hiking": "Hiking",
    "walking": "Walking",
    "strength_training": "StrengthTraining",
    "indoor_cardio": "StrengthTraining",
    "cycling": "Biking",
    "road_biking": "Biking",
}

# Lead columns, in this fixed order, at the front of every monthly CSV. The
# first two are filename-derived (not session fields); the rest are the raw SDK
# session field names the coach reads. All remaining session fields follow,
# alphabetically. Header is the union of fields seen across a month's
# activities, so different activity types stay column-aligned.
LEAD_COLUMNS = [
    "source_file",          # filename (also carries the date the coach keys on)
    "activity_type",        # filename suffix: Running / StrengthTraining / ...
    "start_time",           # SDK session start (ISO, UTC)
    "sport",                # SDK sport
    "total_timer_time",     # seconds
    "total_distance",       # metres
    "total_calories",
    "total_ascent",         # metres
    "altitude_min",         # derived from the record stream (metres)
    "altitude_max",         # derived from the record stream (metres)
    "enhanced_avg_speed",   # m/s (coach derives pace from this)
    "avg_heart_rate",
    "max_heart_rate",
    "num_laps",
]


# --- helpers ----------------------------------------------------------------

def suffix_for(type_key: str) -> str:
    return TYPE_SUFFIX.get((type_key or "").lower(), "Other")


def parse_start(a: dict) -> datetime:
    """Local start time of an activity dict, as a naive datetime."""
    s = a.get("startTimeLocal") or a.get("startTimeGMT")
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def activity_basename(a: dict) -> str:
    """Coach-convention stem WITHOUT extension: YYYY-MM-DD-HH-MM_<Type>."""
    dt = parse_start(a)
    type_key = (a.get("activityType") or {}).get("typeKey", "")
    return f"{dt:%Y-%m-%d-%H-%M}_{suffix_for(type_key)}"


# --- download ---------------------------------------------------------------

class LoginUnavailable(Exception):
    """No cached token and no credentials, with prompting disabled."""


def login(no_prompt: bool = False) -> Garmin:
    """Log in to Garmin, reusing cached tokens when possible.

    With no_prompt=True (how the coach engine calls this), never block on input:
    reuse a cached token, else use GARMIN_EMAIL/GARMIN_PASSWORD from the env,
    else raise LoginUnavailable so the caller can skip the download cleanly."""
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    def mfa():
        if no_prompt:
            raise LoginUnavailable("Garmin MFA required but prompting is disabled")
        return input("MFA code: ")

    client = Garmin(email, password, prompt_mfa=mfa)
    try:
        client.login(TOKEN_STORE)             # reuse cached tokens if present
        return client
    except Exception:                         # noqa: BLE001 - need fresh credentials
        pass
    if not email or not password:
        if no_prompt:
            raise LoginUnavailable(
                "no cached Garmin token and no GARMIN_EMAIL/GARMIN_PASSWORD set")
        email = email or input("Garmin email: ")
        password = password or __import__("getpass").getpass("Garmin password: ")
    client = Garmin(email, password, prompt_mfa=mfa)
    client.login(TOKEN_STORE)
    return client


def extract_fit(blob: bytes) -> bytes:
    """ORIGINAL downloads are a zip containing the .fit; return the .fit bytes."""
    if blob[:2] == b"PK":                     # zip magic
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            fits = [n for n in zf.namelist() if n.lower().endswith(".fit")]
            if not fits:
                raise ValueError("zip contained no .fit file")
            return zf.read(fits[0])
    return blob                               # already raw .fit


def download_all(start: date, end: date, no_prompt: bool = False) -> int:
    client = login(no_prompt=no_prompt)
    activities = client.get_activities_by_date(start.isoformat(), end.isoformat())
    print(f"Garmin returned {len(activities)} activities "
          f"in {start}..{end}")
    # (extension, Garmin format, post-processor). ORIGINAL ships a zip holding
    # the .fit; TCX is returned as raw XML, so it is written through unchanged.
    formats = [
        (".fit", ActivityDownloadFormat.ORIGINAL, extract_fit),
        (".tcx", ActivityDownloadFormat.TCX, lambda b: b),
    ]
    new = 0
    for a in activities:
        try:
            base = activity_basename(a)
        except Exception as exc:              # noqa: BLE001 - skip unparseable
            print(f"  skip activity {a.get('activityId')}: {exc}")
            continue
        year_dir = LOG_DIR / f"{parse_start(a):%Y}"
        year_dir.mkdir(parents=True, exist_ok=True)
        for ext, fmt, post in formats:
            dest = year_dir / f"{base}{ext}"
            if dest.exists():
                continue                      # already downloaded
            blob = client.download_activity(a["activityId"], dl_fmt=fmt)
            dest.write_bytes(post(blob))
            print(f"  downloaded {dest.name}")
            new += 1
    print(f"Downloaded {new} new file(s)")
    return new


# --- FIT -> CSV row ---------------------------------------------------------

def csv_value(v):
    """Render one SDK value for CSV, or return None to omit the field.

    datetime -> ISO 8601 (UTC); NaN float -> '' (empty cell); list/tuple -> None
    (skip non-scalar fields); everything else -> as-is."""
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    if isinstance(v, float) and math.isnan(v):
        return ""
    if isinstance(v, (list, tuple)):
        return None
    return v


def fit_to_row(path: Path) -> dict | None:
    """Decode one .fit into a row dict of all named SDK session fields.

    Keys are the raw SDK session field names (e.g. total_distance, avg_heart_rate)
    so the CSV mirrors the SDK exactly. Adds two filename-derived columns the
    coach keys on (source_file, activity_type) plus altitude_min/altitude_max
    derived from the record stream (not present on the session)."""
    try:
        messages, _ = Decoder(Stream.from_file(str(path))).read()
    except Exception as exc:                  # noqa: BLE001 - report and skip
        print(f"  decode failed for {path.name}: {exc}")
        return None
    sessions = messages.get("session_mesgs") or []
    if not sessions:
        print(f"  no session in {path.name}; skipping")
        return None
    s = sessions[0]

    row = {
        # Filename-derived: date source for the coach + authoritative type.
        "source_file": path.name,
        "activity_type": path.stem.split("_")[-1],
    }
    # Every named session field, raw, with non-scalar/NaN handling.
    for k, v in s.items():
        if str(k).isdigit():                  # drop undocumented numeric keys
            continue
        out = csv_value(v)
        if out is not None:                   # None == skip (e.g. list fields)
            row[k] = out

    # Altitude min/max aren't on the session; derive from the record stream.
    alts = [r["enhanced_altitude"] for r in messages.get("record_mesgs", [])
            if r.get("enhanced_altitude") is not None]
    if alts:
        row["altitude_min"] = round(min(alts), 2)
        row["altitude_max"] = round(max(alts), 2)
    return row


def month_header(rows: list[dict]) -> list[str]:
    """Union of all fields across a month's rows: lead columns first (in fixed
    order, only those actually present), then the rest alphabetically."""
    seen = set().union(*(r.keys() for r in rows))
    lead = [c for c in LEAD_COLUMNS if c in seen]
    rest = sorted(seen - set(lead))
    return lead + rest


def build_csvs(start: date, end: date) -> None:
    """Rebuild running/data/tcx-YYYY-MM.csv from .fit files in the log folders."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows_by_month: dict[str, list] = defaultdict(list)
    fname_re = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-\d{2}-\d{2}_.+\.fit$",
                          re.IGNORECASE)

    for year_dir in sorted(LOG_DIR.glob("[0-9][0-9][0-9][0-9]")):
        for fit in sorted(year_dir.glob("*.fit")):
            m = fname_re.match(fit.name)
            if not m:
                continue
            d = date(int(m[1]), int(m[2]), int(m[3]))
            if d < start or d > end:
                continue
            row = fit_to_row(fit)
            if row:
                rows_by_month[f"{m[1]}-{m[2]}"].append((fit.name, row))

    for month, items in sorted(rows_by_month.items()):
        items.sort(key=lambda t: t[0])        # filenames sort chronologically
        rows = [r for _, r in items]
        out = DATA_DIR / f"tcx-{month}.csv"
        with open(out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=month_header(rows), extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"Wrote {len(rows)} activit"
              f"{'y' if len(rows) == 1 else 'ies'} to {out}")


# --- main -------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2026-01-01",
                    help="earliest activity date to download (YYYY-MM-DD, "
                         "default 2026-01-01)")
    ap.add_argument("--end", default=None,
                    help="latest activity date (YYYY-MM-DD, default: today)")
    ap.add_argument("--no-download", action="store_true",
                    help="skip downloading; only rebuild CSVs from existing .fit")
    ap.add_argument("--no-csv", action="store_true",
                    help="only download; skip rebuilding the coach CSVs")
    ap.add_argument("--no-prompt", action="store_true",
                    help="never prompt for login/MFA; skip the download if no "
                         "cached token or GARMIN_EMAIL/GARMIN_PASSWORD is set "
                         "(used by the coach engine's automatic refresh)")
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = (datetime.strptime(args.end, "%Y-%m-%d").date()
           if args.end else date.today())

    if not args.no_download:
        try:
            download_all(start, end, no_prompt=args.no_prompt)
        except LoginUnavailable as exc:
            # Non-fatal: keep going and rebuild CSVs from .fit already on disk.
            print(f"Skipping download ({exc})")
    if not args.no_csv:
        build_csvs(start, end)


if __name__ == "__main__":
    main()
