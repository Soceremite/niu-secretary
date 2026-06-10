#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT='/var/www/html/niu-secretary/airesearch'
SNAPSHOT_ROOT='/var/www/html/niu-secretary/.airesearch-deploy-snapshots'
SNAPSHOT="${1:-latest}"

if [[ "$SNAPSHOT" == "latest" ]]; then
  SNAPSHOT_DIR="$(find "$SNAPSHOT_ROOT" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
else
  SNAPSHOT_DIR="$SNAPSHOT_ROOT/$SNAPSHOT"
fi

if [[ -z "${SNAPSHOT_DIR:-}" || ! -d "$SNAPSHOT_DIR" ]]; then
  echo "snapshot_not_found=$SNAPSHOT" >&2
  exit 2
fi

mkdir -p "$DEPLOY_ROOT"
rsync -a --delete "$SNAPSHOT_DIR"/ "$DEPLOY_ROOT"/
cat > "$DEPLOY_ROOT/rollback-manifest.json" <<EOF
{"snapshot":"$SNAPSHOT_DIR","deploy_root":"$DEPLOY_ROOT","rolled_back_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

echo "static_site_rolled_back deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"
