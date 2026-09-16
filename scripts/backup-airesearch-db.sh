#!/usr/bin/env bash
# 研知库数据库备份（2026-09-16）
#
# 节奏：本地每日（cron 每天跑）；远端每周（默认周日，或 --remote 强制）
# 目的地：WebDAV（USTC Seafile）→ rclone 远端 niu:webdav/airesearch/
#
# 用法：
#   ./backup-airesearch-db.sh              # 本地备份；周日自动上传
#   ./backup-airesearch-db.sh --remote     # 本次强制上传
#   ./backup-airesearch-db.sh --no-remote  # 本次只做本地
#   ./backup-airesearch-db.sh --verify-remote  # 额外把远端文件读回来比对哈希（慢但最硬）
#
# 可覆盖的环境变量：
#   NIU_BACKUP_DB                 默认 /data/disk/niu-secretary/airesearch/data/airesearch.sqlite3
#   NIU_BACKUP_DIR                默认 /data/disk/niu-secretary/backups/airesearch
#   NIU_BACKUP_KEEP               本地保留份数，默认 30
#   NIU_BACKUP_REMOTE             默认 niu
#   NIU_BACKUP_REMOTE_PATH        默认 webdav/airesearch
#   NIU_BACKUP_REMOTE_KEEP_DAYS   远端保留天数，默认 56（8 周）
#   NIU_BACKUP_REMOTE_DAY         默认 7（%u：7=周日）
set -euo pipefail

DB="${NIU_BACKUP_DB:-/data/disk/niu-secretary/airesearch/data/airesearch.sqlite3}"
DEST="${NIU_BACKUP_DIR:-/data/disk/niu-secretary/backups/airesearch}"
KEEP="${NIU_BACKUP_KEEP:-30}"
REMOTE="${NIU_BACKUP_REMOTE:-niu}"
REMOTE_PATH="${NIU_BACKUP_REMOTE_PATH:-webdav/airesearch}"
REMOTE_KEEP_DAYS="${NIU_BACKUP_REMOTE_KEEP_DAYS:-56}"
REMOTE_DAY="${NIU_BACKUP_REMOTE_DAY:-7}"

DO_REMOTE="auto"
DO_VERIFY_REMOTE=0
for arg in "$@"; do
  case "$arg" in
    --remote) DO_REMOTE=yes ;;
    --no-remote) DO_REMOTE=no ;;
    --verify-remote) DO_VERIFY_REMOTE=1 ;;
    *) echo "未知参数: $arg" >&2; exit 2 ;;
  esac
done

STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEST" "$DEST/logs"
LOG="$DEST/logs/backup-airesearch.log"
TS="$(date '+%F %T')"
TMP_DB="$DEST/.tmp-$STAMP.sqlite3"
ARCHIVE="$DEST/airesearch-$STAMP.sqlite3.zst"
SUMS="$ARCHIVE.sha256"

say() { echo "$*" | tee -a "$LOG"; }
fail() { say "[$TS] ❌ $*"; exit 1; }

cleanup() { rm -f "$TMP_DB" 2>/dev/null || true; }
trap cleanup EXIT

# ---------- 1) 快照（SQLite 在线备份 API：并发写安全） ----------
[ -f "$DB" ] || fail "源库不存在: $DB"
SIZE_IN="$(du -h "$DB" | cut -f1)"
say "[$TS] ── 开始 ── 源库 $SIZE_IN"

python3 - "$DB" "$TMP_DB" <<'PY' || fail "SQLite 在线备份失败"
import sqlite3, sys
src_path, dst_path = sys.argv[1], sys.argv[2]
src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True, timeout=60)
dst = sqlite3.connect(dst_path)
src.backup(dst)          # 在线备份：与并发写入安全共存
dst.close(); src.close()
print("  快照完成")
PY

# ---------- 2) 完整性验证（副本必须自身可开、可查、表数对得上） ----------
python3 - "$TMP_DB" <<'PY' || fail "副本完整性校验未通过（本次不产出备份）"
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])
ok = conn.execute("pragma integrity_check").fetchone()[0]
assert ok == "ok", f"integrity_check={ok}"
tables = conn.execute("select count(*) from sqlite_master where type='table'").fetchone()[0]
papers = conn.execute("select count(*) from papers").fetchone()[0]
facts = conn.execute("select count(*) from research_facts").fetchone()[0]
assert tables > 0 and papers > 0, "关键表为空，疑似坏库"
print(f"  校验通过: integrity=ok, 表数={tables}, papers={papers}, facts={facts}")
conn.close()
PY

# ---------- 3) 压缩 + 校验和 ----------
zstd -q -3 -f "$TMP_DB" -o "$ARCHIVE" || fail "zstd 压缩失败"
rm -f "$TMP_DB"
( cd "$DEST" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$SUMS")" ) || fail "生成校验和失败"
SIZE_OUT="$(du -h "$ARCHIVE" | cut -f1)"
say "[$TS] ✅ 本地备份完成: $(basename "$ARCHIVE") ($SIZE_IN → $SIZE_OUT)"

# ---------- 4) 本地保留 N 份 ----------
ls -1t "$DEST"/airesearch-*.sqlite3.zst 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f "$old" "$old.sha256"
  say "[$TS]   本地清理: $(basename "$old")"
done

# ---------- 5) 远端（每周 / 强制） ----------
WEEKDAY="$(date +%u)"
if [ "$DO_REMOTE" = "auto" ]; then
  if [ "$WEEKDAY" = "$REMOTE_DAY" ]; then DO_REMOTE=yes; else DO_REMOTE=no; fi
fi

if [ "$DO_REMOTE" = "yes" ]; then
  if ! rclone listremotes 2>/dev/null | grep -qx "$REMOTE:"; then
    say "[$TS] ⚠️  远端 $REMOTE: 不存在，跳过上传（本地备份已完成）"
    exit 0
  fi
  say "[$TS] ── 上传远端 $REMOTE:$REMOTE_PATH ──"
  rclone mkdir "$REMOTE:$REMOTE_PATH" 2>/dev/null || true
  if rclone copy "$ARCHIVE" "$REMOTE:$REMOTE_PATH/" --retries 3 --low-level-retries 5 2>>"$LOG" \
     && rclone copy "$SUMS" "$REMOTE:$REMOTE_PATH/" --retries 3 2>>"$LOG"; then
    # 校验：先比大小，必要时把远端文件读回来算哈希（--verify-remote）
    REMOTE_SIZE="$(rclone size --json "$REMOTE:$REMOTE_PATH/$(basename "$ARCHIVE")" 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("bytes",0))' 2>/dev/null || echo 0)"
    LOCAL_SIZE="$(stat -c %s "$ARCHIVE")"
    if [ "$REMOTE_SIZE" = "$LOCAL_SIZE" ]; then
      say "[$TS] ✅ 上传校验通过（大小一致 $LOCAL_SIZE 字节）"
    else
      fail "上传后大小不一致（本地 $LOCAL_SIZE / 远端 $REMOTE_SIZE）"
    fi
    if [ "$DO_VERIFY_REMOTE" = "1" ]; then
      say "[$TS]    回读远端文件算哈希（最硬的校验，稍慢）…"
      REMOTE_HASH="$(rclone cat "$REMOTE:$REMOTE_PATH/$(basename "$ARCHIVE")" 2>/dev/null | sha256sum | cut -d' ' -f1)"
      LOCAL_HASH="$(cut -d' ' -f1 "$SUMS")"
      [ "$REMOTE_HASH" = "$LOCAL_HASH" ] || fail "回读哈希不一致！远端内容与本地不同"
      say "[$TS] ✅ 回读哈希一致: ${LOCAL_HASH:0:16}…"
    fi
    # 远端保留：删掉超过 N 天的（限定在本目录内）
    rclone delete "$REMOTE:$REMOTE_PATH" --min-age "${REMOTE_KEEP_DAYS}d" --include "airesearch-*.sqlite3.zst*" 2>>"$LOG" || true
  else
    fail "远端上传失败（本地备份仍在，未被破坏）"
  fi
else
  say "[$TS]   远端：今天不是周$REMOTE_DAY（%u=$WEEKDAY），按周节流跳过"
fi

say "[$TS] ── 结束 ──"
