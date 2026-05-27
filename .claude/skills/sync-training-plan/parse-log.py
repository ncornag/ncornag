#!/usr/bin/env python3
"""parse-log.py - Aggregate logged TCX activities against the Dements 2026 plan.

Part of the sync-training-plan skill. This script does the deterministic work so
Claude does not have to: it refreshes the monthly activity CSVs, maps every
logged activity onto a plan week, classifies average heart rate into a
lab-calibrated training zone, aggregates per week, and prints a JSON summary on
stdout for the skill to act on. All progress/errors go to stderr.

Steps:
  1. Refresh CSVs by running running/tcx-to-csv.sh for every month from the plan
     start (2026-05) to today. Failures (e.g. Drive offline) are recorded and
     the script falls back to whatever CSVs already exist.
  2. Read every running/data/tcx-*.csv.
  3. Map each activity to a plan week (week 1 = Mon 2026-05-11; week N spans
     [start+(N-1)*7, +6d]). Activities outside the plan range are ignored.
  4. Classify average HR into Z1-Z5 from the VT1/VT2 zones in running-zones.html.
  5. Aggregate per week and emit JSON.

Usage:
  parse-log.py [--no-refresh] [--today YYYY-MM-DD] [--data-dir DIR] [--repo DIR]

The JSON output is the contract with SKILL.md - keep them in sync if you change
the shape here.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta

PLAN_START = date(2026, 5, 11)   # Monday of plan week 1
TOTAL_WEEKS = 26

# Planned weekly volume (km) and elevation (m D+). Canonical baseline - mirrors
# the weeks[] array in dements-2026-plan.html. Index 0 == week 1.
PLAN = [
    (25, 0), (25, 0), (21, 0), (22, 0), (23, 80), (17, 30),
    (28, 300), (33, 500), (38, 700), (25, 350), (45, 1000), (50, 1200),
    (52, 1400), (56, 1600), (32, 500), (45, 1500), (35, 700), (60, 2000),
    (38, 800), (68, 2600), (75, 2900), (65, 2200), (48, 1400), (28, 600),
    (22, 300), (42.5, 3808),
]

ICONS = {"Running": "\U0001F3C3", "Hiking": "\U0001F97E",
         "StrengthTraining": "\U0001F4AA"}
TYPE_NOUN = {"Running": "run", "Hiking": "hike", "StrengthTraining": "gym"}
ZONES = ("Z1", "Z2", "Z3", "Z4", "Z5")

# Canonical icon and zone-class for each plan day type (used when regenerating the days grid)
DAY_ICON = {
    "z2": "\U0001F3C3", "trail-z2": "⛰", "trail-hike": "⛰",
    "z4": "\U0001F525", "strides": "⚡", "rec": "\U0001F3C3",
    "gym": "\U0001F4AA", "rest": "\U0001F4A4",
}
DAY_ELEV_TYPES = {"trail-z2", "trail-hike"}


def hr_zone(hr):
    """Map an average HR to a lab-calibrated zone (VT1 151, VT2 173)."""
    if hr is None:
        return None
    if hr < 135:
        return "Z1"
    if hr < 152:
        return "Z2"
    if hr < 163:
        return "Z3"
    if hr < 174:
        return "Z4"
    return "Z5"


def parse_float(s):
    try:
        return float((s or "").strip())
    except ValueError:
        return 0.0


def parse_int(s):
    try:
        return int(float((s or "").strip()))
    except ValueError:
        return None


def norm_pace(s):
    """Normalise tcx-ls pace to m:ss.

    tcx-ls prints pace un-padded ('6:0') and sometimes with the seconds field
    overflowing 60 ('7:62'); carry the overflow so '7:62' becomes '8:02'.
    """
    s = (s or "").strip()
    if not s or ":" not in s or "Inf" in s or "NaN" in s:
        return ""
    m, _, sec = s.partition(":")
    try:
        total = int(m) * 60 + int(sec)
    except ValueError:
        return ""
    return f"{total // 60}:{total % 60:02d}"


def week_range(n):
    start = PLAN_START + timedelta(days=(n - 1) * 7)
    return start, start + timedelta(days=6)


def week_of(d):
    if d < PLAN_START:
        return None
    n = (d - PLAN_START).days // 7 + 1
    return n if 1 <= n <= TOTAL_WEEKS else None


def week_label(start, end):
    if start.month == end.month:
        return f"{start:%b} {start.day}–{end.day}"
    return f"{start:%b} {start.day}–{end:%b} {end.day}"


def week_status(start, end, today):
    if end < today:
        return "done"
    if start <= today <= end:
        return "current"
    return "upcoming"


def refresh_csvs(repo, today, log):
    """Run running/tcx-to-csv.sh for every month from the plan start to today."""
    script = os.path.join(repo, "running", "tcx-to-csv.sh")
    if not os.path.exists(script):
        log.append(f"tcx-to-csv.sh not found at {script}; skipped refresh")
        return
    y, m = PLAN_START.year, PLAN_START.month
    while (y, m) <= (today.year, today.month):
        try:
            r = subprocess.run(["bash", script, str(y), str(m)],
                               capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                log.append(f"{y}-{m:02d}: {r.stderr.strip() or 'refresh failed'}")
        except Exception as exc:  # noqa: BLE001 - report any refresh failure
            log.append(f"{y}-{m:02d}: {exc}")
        m += 1
        if m > 12:
            m, y = 1, y + 1


def build_activity(row, csvname, errors):
    """Turn one CSV row into a normalised activity dict, or None to skip it."""
    src = (row.get("source_file") or "").strip()
    aid = (row.get("Activity ID") or "").strip()
    d = None
    for cand in (src[:10], aid[:10]):
        try:
            d = datetime.strptime(cand, "%Y-%m-%d").date()
            break
        except ValueError:
            continue
    if d is None:
        errors.append(f"{csvname}: cannot read date from '{src or aid}'")
        return None
    wk = week_of(d)
    if wk is None:
        return None  # activity falls outside the 26-week plan window
    atype = (row.get("activity_type") or row.get("Sport") or "Activity").strip()
    avg_hr = parse_int(row.get("Average Heartrate [bpm]"))
    return {
        "date": d.isoformat(),
        "weekday": d.strftime("%a"),
        "day_label": f"{d:%a} {d.day}",
        "week": wk,
        "type": atype,
        "icon": ICONS.get(atype, "•"),
        "km": round(parse_float(row.get("Accumulated Distance [km]")), 2),
        "elev": parse_int(row.get("Altitude Ascent [m]")) or 0,
        "avg_hr": avg_hr,
        "max_hr": parse_int(row.get("Maximum Heartrate [bpm]")),
        "zone": hr_zone(avg_hr),
        "pace": norm_pace(row.get("Average Pace")),
        "time": (row.get("Accumulated Time") or "").strip(),
        "calories": parse_int(row.get("Accumulated Calories")),
    }


def read_activities(data_dir, errors):
    acts = []
    for path in sorted(glob.glob(os.path.join(data_dir, "tcx-*.csv"))):
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    a = build_activity(row, os.path.basename(path), errors)
                    if a:
                        acts.append(a)
        except OSError as exc:
            errors.append(f"{os.path.basename(path)}: {exc}")
    return acts


def week_hash(acts):
    """Stable fingerprint of a week's data, so the skill can skip unchanged weeks."""
    key = json.dumps(
        [[a["date"], a["type"], a["km"], a["elev"], a["avg_hr"],
          a["max_hr"], a["pace"]] for a in acts],
        sort_keys=True)
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def render_actuals_html(acts):
    """Render the deterministic 'Logged' panel for a week (zero-diff on re-run)."""
    counts = {}
    for a in acts:
        counts[a["type"]] = counts.get(a["type"], 0) + 1
    seg = []
    for t in ("Running", "Hiking", "StrengthTraining"):
        c = counts.get(t, 0)
        if c:
            noun = TYPE_NOUN[t]
            seg.append(f"{c} {noun}{'s' if c > 1 else ''}")
    km = sum(a["km"] for a in acts)
    elev = sum(a["elev"] for a in acts)
    summary = " · ".join(seg + [f"{km:.1f} km", f"{elev} m D+"])

    rows = []
    for a in acts:
        zone = a["zone"] or ""
        zcls = f" {zone.lower()}" if zone else ""
        km_txt = "gym" if a["type"] == "StrengthTraining" else f'{a["km"]:.1f} km'
        elev_txt = f'{a["elev"]} m' if a["elev"] else "—"
        hr_txt = str(a["avg_hr"]) if a["avg_hr"] else "—"
        pace_txt = f'{a["pace"]}/km' if a["pace"] else "—"
        rows.append(
            '        <div class="act-row">'
            f'<span class="act-when">{a["day_label"]}</span>'
            f'<span class="act-ico">{a["icon"]}</span>'
            f'<span class="act-km">{km_txt}</span>'
            f'<span class="act-vert">{elev_txt}</span>'
            f'<span class="act-hr">{hr_txt}</span>'
            f'<span class="act-zone{zcls}">{zone or "—"}</span>'
            f'<span class="act-pace">{pace_txt}</span>'
            '</div>')
    return (
        '      <div class="actuals">\n'
        '        <div class="actuals-head">'
        '<span class="actuals-title">Logged</span>'
        f'<span class="actuals-sum">{summary}</span></div>\n'
        + "\n".join(rows) + "\n"
        '      </div>')


# Regex helpers for extracting the planned day grid from the HTML.
_WEEK_ID_RE = re.compile(r'<div[^>]+id="(w\d+)"')
_DAY_CELL_RE = re.compile(
    r'<div class="day ([^"]+)">\s*'
    r'<div class="day-label">([^<]+)</div>\s*'
    r'(?:<div class="day-done-dot">[^<]*</div>\s*)?'  # optional logged indicator
    r'<div class="day-icon">[^<]*</div>\s*'
    r'<div class="day-km">([^<]+)</div>\s*'
    r'(?:<div class="day-elev">([^<]*)</div>\s*)?'
    r'<div class="day-type">([^<]+)</div>',
    re.MULTILINE,
)


def parse_plan_days(html_path):
    """Extract the planned day grid for each week from dements-2026-plan.html.

    Returns a dict mapping week number (int) to a list of day dicts:
      [{"day": "Mon", "type": "z2", "km": "5km", "elev": "50m", "label": "Z2"}, ...]
    """
    try:
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
    except OSError:
        return {}

    positions = [(m.start(), int(m.group(1)[1:])) for m in _WEEK_ID_RE.finditer(html)]
    result = {}
    for i, (pos, wnum) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(html)
        block = html[pos:end]
        days = [
            {
                "day": m.group(2).strip(),
                # Strip the "logged" marker class if present — it's injected by
                # the sync engine and must not be treated as a plan day type.
                "type": m.group(1).strip().replace(" logged", ""),
                "km": m.group(3).strip(),
                "elev": (m.group(4) or "").strip(),
                "label": m.group(5).strip(),
            }
            for m in _DAY_CELL_RE.finditer(block)
        ]
        if days:
            result[wnum] = days
    return result


def render_days_html(plan_days, logged_days):
    """Regenerate the full .days grid from plan_days[], marking logged chips.

    logged_days is a set of weekday abbreviations (e.g. {"Mon", "Tue"}) for
    days where at least one activity was recorded that week.
    Returns the full <div class="days">...</div> block as a string.
    """
    chips = []
    for d in plan_days:
        day_name = d["day"]
        css_type = d["type"]
        extra_cls = " logged" if day_name in logged_days else ""
        icon = DAY_ICON.get(css_type, "•")
        done_dot = ('          <div class="day-done-dot">✓</div>\n'
                    if day_name in logged_days else "")
        elev_line = ""
        if d.get("elev") and d["elev"] not in ("", "—"):
            elev_line = f'          <div class="day-elev">{d["elev"]}</div>\n'
        chips.append(
            f'        <div class="day {css_type}{extra_cls}">\n'
            f'          <div class="day-label">{day_name}</div>\n'
            f'{done_dot}'
            f'          <div class="day-icon">{icon}</div>\n'
            f'          <div class="day-km">{d["km"]}</div>\n'
            f'{elev_line}'
            f'          <div class="day-type">{d["label"]}</div>\n'
            f'        </div>'
        )
    return (
        '      <div class="days">\n'
        + "\n".join(chips) + "\n"
        '      </div>'
    )


def aggregate(activities, today, plan_days_by_week=None):
    by_week = {}
    for a in activities:
        by_week.setdefault(a["week"], []).append(a)

    weeks = []
    for n in range(1, TOTAL_WEEKS + 1):
        start, end = week_range(n)
        plan_km, plan_elev = PLAN[n - 1]
        acts = sorted(by_week.get(n, []), key=lambda a: a["date"])
        runs = [a for a in acts if a["type"] != "StrengthTraining"]

        actual_km = round(sum(a["km"] for a in acts), 1)
        actual_elev = sum(a["elev"] for a in acts)
        zone_km = {z: 0.0 for z in ZONES}
        for a in runs:
            if a["zone"]:
                zone_km[a["zone"]] += a["km"]
        run_km = sum(zone_km.values())
        polarized = {"easy_pct": 0, "tempo_pct": 0, "hard_pct": 0}
        if run_km > 0:
            polarized = {
                "easy_pct": round((zone_km["Z1"] + zone_km["Z2"]) / run_km * 100),
                "tempo_pct": round(zone_km["Z3"] / run_km * 100),
                "hard_pct": round((zone_km["Z4"] + zone_km["Z5"]) / run_km * 100),
            }
        hrs = [a["avg_hr"] for a in runs if a["avg_hr"]]
        counts = {}
        for a in acts:
            counts[a["type"]] = counts.get(a["type"], 0) + 1

        weeks.append({
            "week": n,
            "label": week_label(start, end),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "status": week_status(start, end, today),
            "is_race": n == TOTAL_WEEKS,
            "plan_km": plan_km,
            "plan_elev": plan_elev,
            "actual_km": actual_km,
            "actual_elev": actual_elev,
            "km_pct": round(actual_km / plan_km * 100) if plan_km else None,
            "has_data": bool(acts),
            "counts": counts,
            "zone_km": {z: round(v, 1) for z, v in zone_km.items()},
            "polarized": polarized,
            "avg_hr": round(sum(hrs) / len(hrs)) if hrs else None,
            "activities": acts,
            "data_hash": week_hash(acts) if acts else None,
            "actuals_html": render_actuals_html(acts) if acts else None,
            "plan_days": (plan_days_by_week or {}).get(n, []),
            "logged_days": sorted({a["weekday"] for a in acts}),
            "days_html": render_days_html(
                (plan_days_by_week or {}).get(n, []),
                {a["weekday"] for a in acts},
            ) if (plan_days_by_week or {}).get(n) else None,
        })
    return weeks


# JavaScript for the volume chart. The actuals object is filled per run; the
# render loop is constant. Emitted whole so the skill drops it between the
# <!-- sync:chart --> delimiters for deterministic, zero-diff re-runs.
CHART_RENDER = """
    weeks.forEach((w, i) => {
      const pct = (w.km / maxKm) * 75;
      const ePct = w.elev > 0 ? Math.max((w.elev / maxEl) * 22, 3) : 0;
      const act = actuals[i + 1];
      const wrap = document.createElement('div');
      wrap.className = 'vol-bar-wrap';
      const glow = w.current ? `box-shadow:0 0 6px ${w.color}66;` : (w.peak ? `box-shadow:0 0 8px ${w.color}88;` : '');
      let op = '0.75';
      if (w.done) op = '0.4';
      else if (w.reco) op = '0.55';
      else if (w.current) op = '1';
      else if (w.peak) op = '1';
      else if (w.race) op = '1';
      const isRace = w.label === 'R';
      const kmBar = act
        ? `<div class="vol-bar vol-bar-track" style="height:${pct}%"><div class="vol-bar-fill" style="height:${Math.min(act.km / w.km * 100, 100)}%;background:${w.color}"></div></div>`
        : `<div class="vol-bar" style="height:${pct}%;background:${w.color};opacity:${op};${glow}"></div>`;
      wrap.innerHTML = `
    <div class="vol-num" style="color:${w.current || w.peak ? w.color : ''}">${act ? act.km + '/' + w.km : w.km}</div>
    ${kmBar}
    ${w.elev > 0 ? `<div class="vol-elev-bar" style="height:${ePct}%;background:#7040d0;"></div>` : '<div style="height:3px"></div>'}
    <div class="vol-wk" style="color:${w.current || w.peak || isRace ? w.color : ''};font-weight:${isRace ? '500' : '400'}">${isRace ? '\U0001F3C1' : 'W' + w.label}</div>
    ${w.elev > 0 ? `<div class="vol-elev-num">${w.elev}</div>` : ''}
  `;
      chart.appendChild(wrap);
    });"""


def render_chart_js(weeks):
    entries = [f'      {w["week"]}: {{ km: {w["actual_km"]}, elev: {w["actual_elev"]} }}'
               for w in weeks if w["has_data"]]
    obj = "{}" if not entries else "{\n" + ",\n".join(entries) + "\n    }"
    return f"    const actuals = {obj};\n{CHART_RENDER}"


def main():
    ap = argparse.ArgumentParser(description="Aggregate TCX logs vs the Dements plan.")
    ap.add_argument("--no-refresh", action="store_true",
                    help="skip running tcx-to-csv.sh; use existing CSVs only")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
    ap.add_argument("--data-dir", help="directory holding tcx-*.csv (default: <repo>/running/data)")
    ap.add_argument("--repo", help="repo root (default: inferred from script location)")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo) if args.repo \
        else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    data_dir = args.data_dir or os.path.join(repo, "running", "data")
    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today \
        else date.today()

    refresh_log, errors = [], []
    if not args.no_refresh:
        refresh_csvs(repo, today, refresh_log)
    for msg in refresh_log:
        print(f"refresh: {msg}", file=sys.stderr)

    activities = read_activities(data_dir, errors)
    for msg in errors:
        print(f"warning: {msg}", file=sys.stderr)

    html_path = os.path.join(repo, "running", "dements-2026-plan.html")
    plan_days_by_week = parse_plan_days(html_path)
    weeks = aggregate(activities, today, plan_days_by_week)
    cw = week_of(today)
    print(json.dumps({
        "generated": datetime.now().isoformat(timespec="seconds"),
        "plan_start": PLAN_START.isoformat(),
        "today": today.isoformat(),
        "current_week": cw,
        "data_dir": data_dir,
        "refresh_errors": refresh_log,
        "csv_errors": errors,
        "activity_count": len(activities),
        "weeks": weeks,
        "chart_js": render_chart_js(weeks),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
