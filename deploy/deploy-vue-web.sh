#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
WEB_DIST="${WEB_DIST:-$PROJECT_ROOT/web/dist}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/var/www/html/niu-secretary}"
SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-/var/www/html/.niu-secretary-vue-snapshots}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SNAPSHOT_DIR="$SNAPSHOT_ROOT/$STAMP"

if [[ ! -f "$WEB_DIST/index.html" ]]; then
  echo "web_dist_missing path=$WEB_DIST/index.html" >&2
  exit 1
fi

mkdir -p "$DEPLOY_ROOT" "$SNAPSHOT_DIR"

for path in index.html assets; do
  if [[ -e "$DEPLOY_ROOT/$path" ]]; then
    cp -a "$DEPLOY_ROOT/$path" "$SNAPSHOT_DIR/"
  fi
done

# No deletion flag: legacy static module directories stay available as direct-file rollback paths.
rsync -av "$WEB_DIST"/ "$DEPLOY_ROOT"/

cat > "$DEPLOY_ROOT/vue-deploy-manifest.json" <<EOF
{"snapshot":"$SNAPSHOT_DIR","web_dist":"$WEB_DIST","deploy_root":"$DEPLOY_ROOT","deployed_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

echo "vue_web_deployed deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"
