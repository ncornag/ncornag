#!/usr/bin/env python3
"""Push a gym week's HTML table to Garmin Connect as a strength workout.

The workout is named `week <N>`. If one with that name already exists it is
updated in place (same workoutId, so anything scheduled on the calendar keeps
pointing at it); otherwise a new one is created. Nothing is ever deleted.

The payload itself is built by workout.py from `running/<gym_prefix><N>.html` —
see that module for the HTML it reads and the circuit it produces.

Usage:
  python3 .claude/skills/garmin/upload-workout.py --week 17
  python3 .claude/skills/garmin/upload-workout.py --week 17 --dry-run

Credentials: same as download-garmin.py — a cached token in ~/.garminconnect,
or GARMIN_EMAIL / GARMIN_PASSWORD in the environment. MFA codes are prompted
for interactively when Garmin requires one.
"""

import os
import sys
import subprocess
from pathlib import Path

# --- venv bootstrap ---------------------------------------------------------
# Same venv as download-garmin.py; system Python is PEP 668-managed.

SKILL_DIR = Path(__file__).resolve().parent            # .../.claude/skills/garmin
REPO = Path(__file__).resolve().parents[3]             # .../profile
VENV_DIR = SKILL_DIR / ".venv"
VENV_PY = VENV_DIR / "bin" / "python"
REQUIRED = ["garminconnect", "curl_cffi"]


def _ensure_venv_and_reexec():
    """Create the venv + install deps if needed, then re-exec this script in it."""
    if os.environ.get("GARMIN_DL_IN_VENV") == "1":
        return  # already running inside the venv
    if not VENV_PY.exists():
        print(f"Creating venv at {VENV_DIR} ...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q",
                        "--upgrade", "pip"], check=True)
    check = subprocess.run(
        [str(VENV_PY), "-c", "import garminconnect, curl_cffi"],
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
import json

from garminconnect import Garmin

from workout import build_workout, gym_file_for, parse_gym_page, summary_lines

RUNNING_DIR = REPO / "running"
USER_MD = RUNNING_DIR / "data" / "user.md"
TOKEN_STORE = os.path.expanduser("~/.garminconnect")


def login() -> Garmin:
    """Reuse the cached token, else GARMIN_EMAIL/GARMIN_PASSWORD, else prompt."""
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    def mfa():
        return input("MFA code: ")

    client = Garmin(email, password, prompt_mfa=mfa)
    try:
        client.login(TOKEN_STORE)             # reuse cached tokens if present
        return client
    except Exception:                         # noqa: BLE001 - need fresh credentials
        pass
    if not email or not password:
        email = email or input("Garmin email: ")
        password = password or __import__("getpass").getpass("Garmin password: ")
    client = Garmin(email, password, prompt_mfa=mfa)
    client.login(TOKEN_STORE)
    return client


def push(workout: dict) -> None:
    """Create the workout, or update the existing one of the same name in place."""
    client = login()
    name = workout["workoutName"]
    existing = [w for w in client.get_workouts() if w.get("workoutName") == name]
    if len(existing) > 1:
        ids = ", ".join(str(w["workoutId"]) for w in existing)
        raise SystemExit(f"{len(existing)} workouts are named {name!r} ({ids}) — "
                         f"delete the duplicates in Garmin Connect first")
    if existing:
        workout_id = existing[0]["workoutId"]
        client.client.put("connectapi",
                          f"{client.garmin_workouts}/workout/{workout_id}",
                          json=workout, api=True)
        action = "updated"
    else:
        workout_id = client.upload_workout(workout)["workoutId"]
        action = "created"
    print(f"{action} {name!r} — "
          f"https://connect.garmin.com/modern/workout/{workout_id}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--week", type=int, required=True,
                    help="plan week number to push")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the workout that would be sent, contact nobody")
    ap.add_argument("--json", metavar="PATH",
                    help="also write the generated workout JSON here")
    args = ap.parse_args()

    path = gym_file_for(args.week, str(RUNNING_DIR), USER_MD)
    cards = parse_gym_page(path)
    workout = build_workout(args.week, cards)

    print(f"week {args.week} from {path.name} — {len(cards)} exercises")
    for line in summary_lines(workout):
        print("  " + line)
    if args.json:
        Path(args.json).write_text(json.dumps(workout, indent=2, ensure_ascii=False),
                                   encoding="utf-8")
        print(f"wrote {args.json}")
    if args.dry_run:
        print("dry run — nothing sent to Garmin")
        return
    push(workout)


if __name__ == "__main__":
    main()
