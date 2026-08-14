#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT="${DEPLOY_ROOT:-/var/www/html/niu-secretary}"
SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-/var/www/html/.niu-secretary-vue-snapshots}"
TARGET="${1:-latest}"

if [[ "$TARGET" == "latest" ]]; then
  SNAPSHOT_DIR="$(find "$SNAPSHOT_ROOT" -mindepth 1 -maxdepth 1 -type d | sort | tail -1)"
else
  SNAPSHOT_DIR="$SNAPSHOT_ROOT/$TARGET"
fi

if [[ -z "${SNAPSHOT_DIR:-}" || ! -d "$SNAPSHOT_DIR" ]]; then
  echo "vue_snapshot_missing snapshot=$TARGET root=$SNAPSHOT_ROOT" >&2
  exit 1
fi

for path in index.html assets; do
  rm -rf "$DEPLOY_ROOT/$path"
  if [[ -e "$SNAPSHOT_DIR/$path" ]]; then
    cp -a "$SNAPSHOT_DIR/$path" "$DEPLOY_ROOT/"
  fi
done

cat > "$DEPLOY_ROOT/vue-deploy-manifest.json" <<EOF
{"snapshot":"$SNAPSHOT_DIR","deploy_root":"$DEPLOY_ROOT","rolled_back_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

echo "vue_web_rolled_back deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"
