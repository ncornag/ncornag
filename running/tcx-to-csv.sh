#!/usr/bin/env bash
#
# tcx-to-csv.sh - Extract activity summaries from a month of TCX files into a CSV.
#
# For the given year and month, finds every .tcx file whose name begins with
# YYYY-MM- inside the matching per-year subfolder of the running log directory
# (log/<YEAR>/), runs `tcx-ls` on each one, and writes a single CSV (one row
# per activity) to running/data/tcx-YYYY-MM.csv.
#
# Usage:
#   ./tcx-to-csv.sh YEAR MONTH
#
#   YEAR    four-digit year, e.g. 2026
#   MONTH   month 1-12, with or without a leading zero, e.g. 5 or 05
#
# Examples:
#   ./tcx-to-csv.sh 2026 5
#   ./tcx-to-csv.sh 2026 11
#
# The log directory defaults to the Google Drive running log. Override it with
# the TCX_LOG_DIR environment variable, e.g.:
#   TCX_LOG_DIR=/path/to/logs ./tcx-to-csv.sh 2026 5
#
# Requires the `tcx-ls` utility on PATH.

set -euo pipefail

readonly DEFAULT_LOG_DIR="/Users/ncornag/Library/CloudStorage/GoogleDrive-ncornag@gmail.com/My Drive/personal/running/log"
readonly DEFAULT_TAPIRIIK_DIR="/Users/ncornag/Dropbox/Apps/tapiriik"

usage() {
  echo "Usage: $(basename "$0") YEAR MONTH" >&2
  echo "  e.g. $(basename "$0") 2026 5" >&2
  exit 1
}

[ $# -eq 2 ] || usage
year="$1"
month_arg="$2"

# Validate the year and month arguments.
[[ "$year" =~ ^[0-9]{4}$ ]] || { echo "Error: YEAR must be four digits: '$year'" >&2; exit 1; }
[[ "$month_arg" =~ ^[0-9]{1,2}$ ]] || { echo "Error: MONTH must be 1-12: '$month_arg'" >&2; exit 1; }
month_num=$((10#$month_arg))
{ [ "$month_num" -ge 1 ] && [ "$month_num" -le 12 ]; } || { echo "Error: MONTH must be 1-12: '$month_arg'" >&2; exit 1; }
printf -v month "%02d" "$month_num"

# Resolve dependencies and paths.
command -v tcx-ls >/dev/null 2>&1 || { echo "Error: 'tcx-ls' not found on PATH" >&2; exit 1; }

log_dir="${TCX_LOG_DIR:-$DEFAULT_LOG_DIR}"
[ -d "$log_dir" ] || { echo "Error: log directory not found: $log_dir" >&2; exit 1; }

# TCX files are organised into a per-year subfolder, e.g. log/2026/.
year_dir="$log_dir/$year"
[ -d "$year_dir" ] || { echo "Error: no log folder for year $year: $year_dir" >&2; exit 1; }

# Copy new TCX files from the tapiriik export folder into the per-year log subfolder.
tapiriik_dir="${TAPIRIIK_DIR:-$DEFAULT_TAPIRIIK_DIR}"
if [ -d "$tapiriik_dir" ]; then
  shopt -s nullglob
  new_count=0
  for src in "$tapiriik_dir/$year-$month-"*.tcx; do
    dest="$year_dir/$(basename "$src")"
    if [ ! -e "$dest" ]; then
      mv "$src" "$dest"
      new_count=$((new_count + 1))
    fi
  done
  shopt -u nullglob
  [ "$new_count" -gt 0 ] && echo "Moved $new_count new .tcx file$([ "$new_count" -eq 1 ] && echo '' || echo s) from tapiriik to $year_dir"
else
  echo "Warning: tapiriik folder not found: $tapiriik_dir — skipping sync" >&2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out_dir="$script_dir/data"
mkdir -p "$out_dir"
out_file="$out_dir/tcx-$year-$month.csv"

# Collect the TCX files for this month, sorted (filenames sort chronologically).
shopt -s nullglob
files=("$year_dir/$year-$month-"*.tcx)
shopt -u nullglob

[ ${#files[@]} -gt 0 ] || echo "Warning: no .tcx files found for $year-$month in $year_dir" >&2

# Build the CSV: a header row followed by one row per activity.
count=0
{
  echo 'source_file,activity_type,Activity ID,Sport,Accumulated Time,Accumulated Distance [km],Accumulated Calories,Altitude Ascent [m],Altitude Min [m],Altitude Max [m],Average Pace,Average Heartrate [bpm],Maximum Heartrate [bpm],Number Laps'

  for file in ${files[@]+"${files[@]}"}; do
    base="$(basename "$file")"
    # Activity type is the filename suffix, e.g. ..._Running.tcx -> Running
    # (also Hiking, StrengthTraining, ...). The TCX Sport field cannot be
    # relied on for this, as the schema only allows Running/Biking/Other.
    activity_type="${base##*_}"
    activity_type="${activity_type%.tcx}"
    if ! output="$(tcx-ls "$file" 2>/dev/null)"; then
      echo "Warning: tcx-ls failed for '$base' - skipping" >&2
      continue
    fi
    printf '%s\n' "$output" | awk -v src="$base" -v atype="$activity_type" '
      # Quote a field for CSV only when it contains a comma, quote or newline.
      function csv(s) {
        if (s ~ /[",\n]/) { gsub(/"/, "\"\"", s); return "\"" s "\"" }
        return s
      }
      {
        # Split each line on its first colon: label before, value after.
        pos = index($0, ":")
        if (pos == 0) next
        key = substr($0, 1, pos - 1)
        val = substr($0, pos + 1)
        gsub(/^[ \t\r]+|[ \t\r]+$/, "", key)
        gsub(/^[ \t\r]+|[ \t\r]+$/, "", val)
        data[key] = val
      }
      END {
        n = split("Activity ID|Sport|Accumulated Time|Accumulated Distance [km]|" \
                  "Accumulated Calories|Altitude Ascent [m]|Altitude Min [m]|" \
                  "Altitude Max [m]|Average Pace|Average Heartrate [bpm]|" \
                  "Maximum Heartrate [bpm]|Number Laps", cols, "|")
        # tcx-ls emits a bogus "Infinity:NaN" pace for zero-distance
        # activities (e.g. StrengthTraining); leave that cell blank.
        if (data["Average Pace"] ~ /Infinity|NaN/) data["Average Pace"] = ""
        row = csv(src) "," csv(atype)
        for (i = 1; i <= n; i++) row = row "," csv(data[cols[i]])
        print row
      }
    '
    count=$((count + 1))
  done
} > "$out_file"

echo "Wrote $count activit$([ "$count" -eq 1 ] && echo y || echo ies) for $year-$month to $out_file"
