#!/usr/bin/env bash
set -euo pipefail
# schedule=daily
ROOT_DIR=/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
LOG_DIR=logs
HISTORY_DIR=exports/run-history
STAMP="$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$ROOT_DIR/$LOG_DIR" "$ROOT_DIR/$HISTORY_DIR" "$ROOT_DIR/backups"
cd "$ROOT_DIR"
if [ -f ./activate.sh ]; then source ./activate.sh; fi
LOG_PATH="$LOG_DIR/launch-refresh-$STAMP.log"
RUN_MANIFEST="$HISTORY_DIR/launch-refresh-$STAMP.json"
{
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python -m airesearch.cli backup-db --out-dir backups --label "before-launch-refresh-$STAMP"
  python -m airesearch.cli health-check --site-dir exports/site-current || echo "preflight_health_check_failed_continue=true"
  python -m airesearch.cli run-launch-refresh --limit-per-profile 50 --select-limit 10 --min-score 0.60 --out-dir exports/mvp-current --site-dir exports/site-current --progress --run-manifest "$RUN_MANIFEST"
  python -m airesearch.cli health-check --site-dir exports/site-current
  echo "finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$LOG_PATH"
