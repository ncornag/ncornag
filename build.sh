#!/usr/bin/env bash
#
# Stage only the public site for nicolas.cornaglia.xyz into ./dist.
#
# Cloudflare Pages settings:
#   Build command:            bash build.sh
#   Build output directory:   dist
#
# This is an allowlist: only the paths copied below are published. Anything else
# in the repo root (README.md for the GitHub profile, .claude/, docs/, this
# script, .gitignore, ...) is intentionally left out of the public deploy.
#
# /running is published but gated by Cloudflare Access (Google auth) on the
# /running* path — that policy lives in the Cloudflare dashboard, not here.
# Only the running/ *pages* ship; raw data (running/data/*.csv) and coach-log.md
# stay in the repo but are never uploaded. The garmin skill (and its
# download-garmin.py) lives under .claude/ and is never part of the build.
#
# When you add a new public top-level file or folder, add it to ROOT below.
set -euo pipefail

# Public top-level entries published at the site root.
ROOT=(
  index.html
  assets
)

rm -rf dist
mkdir -p dist/running
cp -R "${ROOT[@]}" dist/
# /running: ship only the rendered pages, their stylesheet, and vendored assets.
cp running/*.html running/theme.css dist/running/
cp -R running/assets dist/running/

echo "Staged public site into dist/:"
find dist -mindepth 1 | sort
