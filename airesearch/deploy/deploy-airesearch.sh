#!/usr/bin/env bash
set -euo pipefail

SITE_DIR='/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/exports/site-current'
DEPLOY_ROOT='/var/www/html/niu-secretary/airesearch'
SNAPSHOT_ROOT='/var/www/html/niu-secretary/.airesearch-deploy-snapshots'
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
SNAPSHOT_DIR="$SNAPSHOT_ROOT/$STAMP"

if [[ ! -f "$SITE_DIR/index.html" || ! -f "$SITE_DIR/manifest.json" ]]; then
  echo "site_dir_missing_required_files=$SITE_DIR" >&2
  exit 2
fi

mkdir -p "$SNAPSHOT_ROOT"
if [[ -d "$DEPLOY_ROOT" ]]; then
  mkdir -p "$SNAPSHOT_DIR"
  rsync -a --delete "$DEPLOY_ROOT"/ "$SNAPSHOT_DIR"/
else
  mkdir -p "$SNAPSHOT_DIR"
fi

mkdir -p "$DEPLOY_ROOT"
rsync -a --delete "$SITE_DIR"/ "$DEPLOY_ROOT"/
cat > "$DEPLOY_ROOT/deploy-manifest.json" <<EOF
{"snapshot":"$SNAPSHOT_DIR","site_dir":"$SITE_DIR","deploy_root":"$DEPLOY_ROOT","deployed_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

echo "static_site_deployed deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"
