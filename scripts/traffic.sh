#!/usr/bin/env bash
# Generate steady traffic against medanon so dashboards and alerts have data.
# Usage: scripts/traffic.sh [base_url] [requests] [sleep_seconds]
# Example: scripts/traffic.sh http://127.0.0.1:8080 300 0.5
set -euo pipefail

BASE="${1:-http://127.0.0.1:8080}"
COUNT="${2:-200}"
PAUSE="${3:-0.5}"
SAMPLE="${SAMPLE:-samples/synthetic_ct.dcm}"

[ -f "$SAMPLE" ] || { echo "missing $SAMPLE, run: python scripts/make_sample.py"; exit 1; }

garbage="$(mktemp)"
trap 'rm -f "$garbage"' EXIT
echo "not a dicom file" > "$garbage"

for i in $(seq 1 "$COUNT"); do
  case $((i % 10)) in
    0) code=$(curl -s -o /dev/null -w '%{http_code}' -F "file=@${garbage}" "$BASE/v1/deidentify") ;;
    1|2) code=$(curl -s -o /dev/null -w '%{http_code}' -F "file=@${SAMPLE}" "$BASE/v1/inspect") ;;
    *) code=$(curl -s -o /dev/null -w '%{http_code}' -F "file=@${SAMPLE}" "$BASE/v1/deidentify") ;;
  esac
  printf '%s request %d -> %s\n' "$(date +%T)" "$i" "$code"
  sleep "$PAUSE"
done
