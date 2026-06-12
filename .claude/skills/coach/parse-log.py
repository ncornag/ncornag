#!/usr/bin/env python3
"""parse-log.py - Aggregate logged TCX activities against the Dements 2026 plan.

Part of the sync-training-plan skill. This script does the deterministic work so
Claude does not have to: it refreshes the monthly activity CSVs, maps every
logged activity onto a plan week, classifies average heart rate into a
lab-calibrated training zone, aggregates per week, and prints a JSON summary on
stdout for the skill to act on. All progress/errors go to stderr.

Steps:
  1. Refresh CSVs by running running/download-garmin.py (downloads new Garmin
     .fit activities from the plan start onward and rebuilds the monthly CSVs
     with the Garmin FIT SDK). Failures (e.g. Drive offline, or a Garmin login
     is needed) are recorded and the script falls back to existing CSVs.
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
    """Download new Garmin .fit activities and rebuild the monthly CSVs.

    Delegates to running/download-garmin.py, which downloads any new .fit files
    from the plan start onward and (re)writes running/data/tcx-*.csv from them
    via the Garmin FIT SDK. A non-empty log here (e.g. Drive offline, or a
    Garmin login is needed) is fine — the engine then falls back to the CSVs
    already on disk."""
    script = os.path.join(repo, "running", "download-garmin.py")
    if not os.path.exists(script):
        log.append(f"download-garmin.py not found at {script}; skipped refresh")
        return
    try:
        r = subprocess.run([sys.executable, script,
                            "--start", PLAN_START.isoformat(), "--no-prompt"],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            log.append(r.stderr.strip() or "garmin refresh failed")
    except Exception as exc:  # noqa: BLE001 - report any refresh failure
        log.append(str(exc))


def pace_from_speed(speed_mps):
    """Average speed (m/s, raw SDK enhanced_avg_speed) -> 'm:ss' pace per km."""
    v = parse_float(speed_mps)
    if v <= 0:
        return ""
    sec_per_km = round(1000.0 / v)
    return f"{sec_per_km // 60}:{sec_per_km % 60:02d}"


def hms_from_seconds(seconds):
    """Seconds (raw SDK total_timer_time) -> 'm:ss' or 'h:mm:ss'."""
    v = parse_float(seconds)
    if v <= 0:
        return ""
    s = round(v)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def hre_value(avg_hr, pace_str):
    """Heart Rate Efficiency = avg HR (bpm) × pace (min/km), i.e. beats per km.

    Lower is better. Needs both a heart rate and a pace, so it is None for
    strength sessions (no pace) or any activity missing HR. pace_str is the
    'm:ss' string from pace_from_speed()."""
    if not avg_hr or not pace_str:
        return None
    try:
        mm, ss = pace_str.split(":")
        pace_min = int(mm) + int(ss) / 60.0
    except ValueError:
        return None
    return round(avg_hr * pace_min)


def build_activity(row, csvname, errors):
    """Turn one CSV row into a normalised activity dict, or None to skip it.

    Columns are the raw Garmin FIT SDK session field names written by
    running/download-garmin.py (total_distance in metres, enhanced_avg_speed in
    m/s, etc.). The full set of SDK fields is present in the row; we read the
    ones the coach reports on by name and derive pace/time from raw values."""
    src = (row.get("source_file") or "").strip()
    aid = (row.get("start_time") or "").strip()
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
    atype = (row.get("activity_type") or row.get("sport") or "Activity").strip()
    avg_hr = parse_int(row.get("avg_heart_rate"))
    return {
        "date": d.isoformat(),
        "weekday": d.strftime("%a"),
        "day_label": f"{d:%a} {d.day}",
        "week": wk,
        "type": atype,
        "icon": ICONS.get(atype, "•"),
        "km": round(parse_float(row.get("total_distance")) / 1000.0, 2),
        "elev": parse_int(row.get("total_ascent")) or 0,
        "avg_hr": avg_hr,
        "max_hr": parse_int(row.get("max_heart_rate")),
        "zone": hr_zone(avg_hr),
        "pace": pace_from_speed(row.get("enhanced_avg_speed")),
        "hre": hre_value(avg_hr, pace_from_speed(row.get("enhanced_avg_speed"))),
        "time": hms_from_seconds(row.get("total_timer_time")),
        "calories": parse_int(row.get("total_calories")),
        # Running-dynamics fields from the FIT SDK (blank for non-run activities).
        "run_cadence": parse_int(row.get("avg_running_cadence")),
        "step_length": parse_float(row.get("avg_step_length")),       # mm
        "vert_ratio": parse_float(row.get("avg_vertical_ratio")),     # %
        "vert_osc": parse_float(row.get("avg_vertical_oscillation")), # mm
        "ground_contact": parse_float(row.get("avg_stance_time")),    # ms
        "avg_temp": parse_int(row.get("avg_temperature")),            # °C
    }


def read_activities(data_dir, errors):
    acts = []
    for path in sorted(glob.glob(os.path.join(data_dir, "[0-9][0-9][0-9][0-9]-[0-9][0-9].csv"))):
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


# Garmin running-form color zones (fenix 7 / FR945 owner's manual). Each entry
# is (upper_bound_exclusive, css_class); the last catch-all uses inf. Lower is
# better for ground contact / vertical oscillation / vertical ratio; higher is
# better for cadence (handled by its own ascending table). Classes map to the
# panel palette: purple/blue/green = good→better, orange/red = needs work.
GZ_CADENCE = [   # total steps/min (the SDK per-leg value is doubled first)
    (153, "gz-red"), (164, "gz-orange"), (174, "gz-green"),
    (184, "gz-blue"), (float("inf"), "gz-purple")]
GZ_GCT = [       # ground contact time, ms
    (218, "gz-purple"), (249, "gz-blue"), (278, "gz-green"),
    (309, "gz-orange"), (float("inf"), "gz-red")]
GZ_VOSC = [      # vertical oscillation, mm (chest scale)
    (64, "gz-purple"), (82, "gz-blue"), (98, "gz-green"),
    (116, "gz-orange"), (float("inf"), "gz-red")]
GZ_VRATIO = [    # vertical ratio, % (chest scale)
    (6.1, "gz-purple"), (7.5, "gz-blue"), (8.7, "gz-green"),
    (10.2, "gz-orange"), (float("inf"), "gz-red")]


def garmin_form_zone(value, table):
    """Return the CSS color class for a running-form value, or '' if no value."""
    if not value:
        return ""
    for upper, cls in table:
        if value < upper:
            return cls
    return table[-1][1]


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

    # Column titles row — same 15-cell grid as the data rows.
    head = (
        '        <div class="act-row act-head">'
        '<span class="act-when">Day</span>'
        '<span class="act-ico"></span>'
        '<span class="act-km">Dist</span>'
        '<span class="act-vert">Asc</span>'
        '<span class="act-hr">HR</span>'
        '<span class="act-zone">Zone</span>'
        '<span class="act-pace">Pace</span>'
        '<span class="act-cal">Cal</span>'
        '<span class="act-maxhr">Max</span>'
        '<span class="act-cad">Cad</span>'
        '<span class="act-stride">Stride</span>'
        '<span class="act-vratio">V.Ratio</span>'
        '<span class="act-vosc">V.Osc</span>'
        '<span class="act-gct">GCT</span>'
        '<span class="act-temp">Temp</span>'
        '</div>')

    rows = [head]
    for a in acts:
        zone = a["zone"] or ""
        zcls = f" {zone.lower()}" if zone else ""
        km_txt = "gym" if a["type"] == "StrengthTraining" else f'{a["km"]:.1f} km'
        elev_txt = f'{a["elev"]} m' if a["elev"] else "—"
        hr_txt = str(a["avg_hr"]) if a["avg_hr"] else "—"
        pace_txt = f'{a["pace"]}/km' if a["pace"] else "—"
        # New SDK metrics; "—" when absent (parse_int->None, parse_float->0.0)
        # or not applicable (running dynamics are blank on non-run activities).
        cal_txt = str(a["calories"]) if a["calories"] else "—"
        maxhr_txt = str(a["max_hr"]) if a["max_hr"] else "—"
        # Cadence: the SDK stores it per leg; double to total steps/min so it
        # matches Garmin's scale (and its color zones) and the watch display.
        cad_total = a["run_cadence"] * 2 if a["run_cadence"] else 0
        cad_txt = f'{cad_total} spm' if cad_total else "—"
        stride_txt = f'{round(a["step_length"])} mm' if a["step_length"] else "—"
        vratio_txt = f'{a["vert_ratio"]:.1f}%' if a["vert_ratio"] else "—"
        vosc_txt = f'{a["vert_osc"]:.1f} mm' if a["vert_osc"] else "—"
        gct_txt = f'{round(a["ground_contact"])} ms' if a["ground_contact"] else "—"
        temp_txt = f'{a["avg_temp"]}°' if a["avg_temp"] is not None else "—"
        # Garmin running-form color zones (blank cells stay uncolored).
        cad_cls = garmin_form_zone(cad_total, GZ_CADENCE)
        vratio_cls = garmin_form_zone(a["vert_ratio"], GZ_VRATIO)
        vosc_cls = garmin_form_zone(a["vert_osc"], GZ_VOSC)
        gct_cls = garmin_form_zone(a["ground_contact"], GZ_GCT)
        rows.append(
            '        <div class="act-row">'
            f'<span class="act-when">{a["day_label"]}</span>'
            f'<span class="act-ico">{a["icon"]}</span>'
            f'<span class="act-km">{km_txt}</span>'
            f'<span class="act-vert">{elev_txt}</span>'
            f'<span class="act-hr">{hr_txt}</span>'
            f'<span class="act-zone{zcls}">{zone or "—"}</span>'
            f'<span class="act-pace">{pace_txt}</span>'
            f'<span class="act-cal">{cal_txt}</span>'
            f'<span class="act-maxhr">{maxhr_txt}</span>'
            f'<span class="act-cad {cad_cls}">{cad_txt}</span>'
            f'<span class="act-stride">{stride_txt}</span>'
            f'<span class="act-vratio {vratio_cls}">{vratio_txt}</span>'
            f'<span class="act-vosc {vosc_cls}">{vosc_txt}</span>'
            f'<span class="act-gct {gct_cls}">{gct_txt}</span>'
            f'<span class="act-temp">{temp_txt}</span>'
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


_GYM_FILE_RE = re.compile(r"gimnasio-semana(\d+)(?:-(\d+))?\.html$")


def parse_gym_files(running_dir):
    """Map each plan week to its gym HTML file.

    Scans running/gimnasio-semana*.html. A single-week file
    (gimnasio-semana3.html) maps week 3; a range file (gimnasio-semana3-5.html)
    maps weeks 3, 4 and 5. Files are processed in sorted order so overlaps
    resolve deterministically (later filename wins).
    """
    mapping = {}
    for path in sorted(glob.glob(os.path.join(running_dir, "gimnasio-semana*.html"))):
        m = _GYM_FILE_RE.search(os.path.basename(path))
        if not m:
            continue
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if hi < lo:
            lo, hi = hi, lo
        for wk in range(lo, hi + 1):
            mapping[wk] = os.path.basename(path)
    return mapping


def render_gym_links_js(gym_files):
    """JS that links each week's gym day-chip to its mapped gym file.

    Emitted between the `// sync:gymlinks` markers in the plan HTML. Iterates
    every .week[id="wN"] so it covers future weeks too, not only those with
    logged data. Deterministic — identical input yields identical output.
    """
    if gym_files:
        entries = ", ".join(f"{wk}: {json.dumps(name)}"
                            for wk, name in sorted(gym_files.items()))
        obj = "{ " + entries + " }"
    else:
        obj = "{}"
    return (
        f"    const gymFiles = {obj};\n"
        "    document.querySelectorAll('.week[id]').forEach(wk => {\n"
        "      const n = parseInt(wk.id.slice(1), 10);\n"
        "      const file = gymFiles[n];\n"
        "      if (!file) return;\n"
        "      wk.querySelectorAll('.day.gym .day-km').forEach(el => {\n"
        "        el.innerHTML = `<a href=\"${file}\">${el.textContent}</a>`;\n"
        "      });\n"
        "    });"
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


# Runs at/above this D+ are flagged on the HRE chart and excluded from the
# trend fit: hills raise HR for the same pace independently of fitness, so they
# make HRE look worse without meaning a fitness loss, and the plan's vert grows
# steadily. Heat is NOT flagged — this athlete trains consistently at 28–32 °C,
# so it is the baseline condition, not a confound; temp stays in the tooltip
# for context only.
HRE_HILLY_ELEV = 30   # m D+ — matches the plan's "flat" cutoff

# Zone color palette, mirrors the .act-zone.zN classes in the plan CSS.
HRE_ZONE_COLOR = {
    "Z1": "#3a7bd5", "Z2": "#2ecc8a", "Z3": "#f0c040",
    "Z4": "#f07030", "Z5": "#d03050",
}

# SVG scatter + trend for Heart Rate Efficiency (avg HR × pace = beats/km;
# lower is better). One dot per run, colored by HR zone; runs that are hilly
# or hot get a ring marker and are dropped from the least-squares trend so the
# fitness signal stays readable as the plan adds vert. Emitted whole between
# the `// sync:hre` delimiters for deterministic, zero-diff re-runs. The data
# array is the only part that changes run to run; the render code is constant.
HRE_RENDER = r"""
    (() => {
      const host = document.getElementById('hre-chart');
      if (!host || !hreRuns.length) return;
      const W = 720, H = 200, padL = 44, padR = 12, padT = 14, padB = 30;
      const xs = hreRuns.map((_, i) => i);
      const ys = hreRuns.map(r => r.hre);
      const yMin = Math.min(...ys), yMax = Math.max(...ys);
      const yLo = Math.floor((yMin - 20) / 20) * 20;
      const yHi = Math.ceil((yMax + 20) / 20) * 20;
      const n = hreRuns.length;
      const px = i => padL + (n <= 1 ? (W - padL - padR) / 2 : (i / (n - 1)) * (W - padL - padR));
      const py = v => padT + (1 - (v - yLo) / (yHi - yLo)) * (H - padT - padB);

      // Least-squares trend over flat + cool runs only (fitness signal).
      const fit = hreRuns.map((r, i) => ({ i, r })).filter(o => !o.r.flagged);
      let trend = '';
      if (fit.length >= 2) {
        const mx = fit.reduce((s, o) => s + o.i, 0) / fit.length;
        const my = fit.reduce((s, o) => s + o.r.hre, 0) / fit.length;
        let num = 0, den = 0;
        fit.forEach(o => { num += (o.i - mx) * (o.r.hre - my); den += (o.i - mx) ** 2; });
        const slope = den ? num / den : 0;
        const b = my - slope * mx;
        const x1 = 0, x2 = n - 1;
        trend = `<line x1="${px(x1).toFixed(1)}" y1="${py(slope * x1 + b).toFixed(1)}" x2="${px(x2).toFixed(1)}" y2="${py(slope * x2 + b).toFixed(1)}" stroke="#9b6dff" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.85"/>`;
      }

      // Y gridlines + labels.
      let grid = '';
      for (let v = yLo; v <= yHi; v += 20) {
        const y = py(v).toFixed(1);
        grid += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="var(--border)" stroke-width="0.5"/>`;
        grid += `<text x="${padL - 6}" y="${(+y + 3).toFixed(1)}" text-anchor="end" font-size="8" fill="var(--muted)">${v}</text>`;
      }

      // Connecting polyline (faint) + per-run dots.
      const path = hreRuns.map((r, i) => `${px(i).toFixed(1)},${py(r.hre).toFixed(1)}`).join(' ');
      const line = `<polyline points="${path}" fill="none" stroke="var(--border)" stroke-width="1"/>`;
      const dots = hreRuns.map((r, i) => {
        const cx = px(i).toFixed(1), cy = py(r.hre).toFixed(1);
        const ring = r.flagged
          ? `<circle cx="${cx}" cy="${cy}" r="5.5" fill="none" stroke="${r.color}" stroke-width="1" opacity="0.6"/>`
          : '';
        const tip = `<title>${r.label}: ${r.hre} bpm·km${r.flag ? ' · ' + r.flag : ''}${r.flagged ? ' (hilly — off trend)' : ''}</title>`;
        return `<g>${ring}<circle cx="${cx}" cy="${cy}" r="3" fill="${r.color}">${tip}</circle></g>`;
      }).join('');

      // X labels: week boundaries only, to avoid clutter.
      let xlab = '';
      let lastWk = null;
      hreRuns.forEach((r, i) => {
        if (r.week !== lastWk) {
          xlab += `<text x="${px(i).toFixed(1)}" y="${H - 8}" text-anchor="middle" font-size="8" fill="var(--muted)">W${r.week}</text>`;
          lastWk = r.week;
        }
      });

      host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" preserveAspectRatio="xMidYMid meet">${grid}${line}${trend}${dots}${xlab}</svg>`;
    })();"""


def render_hre_js(weeks):
    """Build the per-run HRE data array + render code for the plan's HRE chart.

    Runs only (strength has no pace); flat-and-cool runs feed the trend line,
    hilly/hot runs are flagged and excluded from it. Deterministic — identical
    activities yield byte-identical output."""
    runs = []
    for w in weeks:
        for a in w["activities"]:
            if a["type"] == "StrengthTraining" or a.get("hre") is None:
                continue
            hilly = a["elev"] >= HRE_HILLY_ELEV
            # Tooltip context: always show D+ and temp; the chart flags only
            # hilly runs (heat is this athlete's baseline, see HRE_HILLY_ELEV).
            temp = f"{a['avg_temp']}°" if a["avg_temp"] is not None else ""
            ctx = " · ".join(c for c in (f"{a['elev']} m D+", temp) if c)
            runs.append({
                "label": a["day_label"],
                "week": a["week"],
                "hre": a["hre"],
                "color": HRE_ZONE_COLOR.get(a["zone"], "#888"),
                "flagged": hilly,
                "flag": ctx,
            })
    data = ",\n".join(
        "      " + json.dumps(r, ensure_ascii=False) for r in runs)
    arr = "[]" if not runs else "[\n" + data + "\n    ]"
    return f"    const hreRuns = {arr};\n{HRE_RENDER}"


def main():
    ap = argparse.ArgumentParser(description="Aggregate TCX logs vs the Dements plan.")
    ap.add_argument("--no-refresh", action="store_true",
                    help="skip running download-garmin.py; use existing CSVs only")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
    ap.add_argument("--data-dir", help="directory holding the monthly YYYY-MM.csv files (default: <repo>/running/data)")
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

    running_dir = os.path.join(repo, "running")
    html_path = os.path.join(running_dir, "dements-2026-plan.html")
    plan_days_by_week = parse_plan_days(html_path)
    gym_files = parse_gym_files(running_dir)
    weeks = aggregate(activities, today, plan_days_by_week)
    for w in weeks:
        w["gym_file"] = gym_files.get(w["week"])
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
        "gym_files": gym_files,
        "current_gym_file": gym_files.get(cw),
        "weeks": weeks,
        "chart_js": render_chart_js(weeks),
        "hre_js": render_hre_js(weeks),
        "gym_links_js": render_gym_links_js(gym_files),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
