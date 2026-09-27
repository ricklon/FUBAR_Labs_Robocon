#!/usr/bin/env bash
# Run the presentation full-screen in browser kiosk mode, auto-advancing and looping.
# Usage: ./kiosk.sh [seconds-per-slide]   (default 10)
# Uses Chrome/Chromium if installed, otherwise Firefox. Force one with
# KIOSK_BROWSER=firefox (or chrome). Exit with Alt+F4.
DIR="$(cd "$(dirname "$0")" && pwd)"
SECS="${1:-10}"
URL="file://$DIR/FUBAR_Labs_Robocon_presentation.html?kiosk&interval=$SECS"

chrome=$(command -v google-chrome || command -v chromium || command -v chromium-browser)
case "${KIOSK_BROWSER:-auto}" in
  firefox) chrome= ;;
  chrome) [ -n "$chrome" ] || { echo "Chrome/Chromium not found" >&2; exit 1; } ;;
esac

if [ -n "$chrome" ]; then
  exec "$chrome" --kiosk --incognito --noerrdialogs --disable-infobars \
    --disable-session-crashed-bubble --no-first-run \
    --user-data-dir=/tmp/robocon-kiosk-profile "$URL"
fi

command -v firefox >/dev/null || { echo "Need Chrome, Chromium, or Firefox" >&2; exit 1; }
# Throwaway profile so first-run pages, crash-restore prompts, and the
# fullscreen warning don't cover the slides.
PROFILE=/tmp/robocon-kiosk-firefox
mkdir -p "$PROFILE"
cat > "$PROFILE/user.js" <<'EOF'
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("datareporting.policy.dataSubmissionPolicyBypassNotification", true);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("full-screen-api.warning.timeout", 0);
user_pref("full-screen-api.transition-duration.enter", "0 0");
EOF
exec firefox --no-remote --profile "$PROFILE" --kiosk "$URL"
