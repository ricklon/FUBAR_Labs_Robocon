#!/usr/bin/env bash
# Run the presentation full-screen in Chrome kiosk mode, auto-advancing and looping.
# Usage: ./kiosk.sh [seconds-per-slide]   (default 10)
# Exit with Alt+F4.
DIR="$(cd "$(dirname "$0")" && pwd)"
SECS="${1:-10}"
exec google-chrome --kiosk --incognito --noerrdialogs --disable-infobars \
  --disable-session-crashed-bubble --no-first-run \
  --user-data-dir=/tmp/robocon-kiosk-profile \
  "file://$DIR/FUBAR_Labs_Robocon_presentation.html?kiosk&interval=$SECS"
