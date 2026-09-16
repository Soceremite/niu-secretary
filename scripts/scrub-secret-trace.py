#!/usr/bin/env python3
"""从 Hermes 本机状态里抹掉一个泄露的凭据（密码/token）。

背景：凭据一旦进了对话，就同时落在这些地方 —— 少抹一处都还能搜出来：
  1. ~/.hermes/state.db          会话消息（messages.content / tool_calls / reasoning）
  2. ~/.hermes/state.db-wal      未落盘的 WAL 页
  3. messages_fts / messages_fts_trigram   两套「全文检索影子索引」的分词副本
                                 —— 只改 messages 表没用，索引里仍能 match 到
  4. ~/.hermes/logs/agent.log    运行日志
  5. ~/.hermes/.hermes_history   CLI 输入历史
  6. ~/.bash_history             交互式 shell 历史（Hermes 工具调用不进这里，但要查）

用法（推荐第 2 种 —— 明文不出现在命令行/进程表里）：
  scrub-secret-trace.py <字面量>
  scrub-secret-trace.py --rclone <远端名>      # 从 rclone 配置里 reveal 出来
  scrub-secret-trace.py --from-file <路径>     # 取文件第一行

注意：
- 先备份到 --backup-dir（默认 /data/disk 下），弄坏了能回滚；回滚点本身含原文，确认无残留后要删掉
- 文本文件用「同 inode 原地截断重写」，否则正在追加写的进程会写进被删的 inode（日志黑洞）
- 最后必须 wal_checkpoint(TRUNCATE) + VACUUM，否则旧字节留在 WAL/空闲页里
- 这只是本机清理；**凭据已经发给了模型服务方，那部分无法收回 → 该改密码还是要改**
"""
from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
HERMES = HOME / ".hermes"
STATE = HERMES / "state.db"
LOG = HERMES / "logs" / "agent.log"
HIST = HERMES / ".hermes_history"
REDACT = "[REDACTED]"


def resolve_secret(args) -> str:
    if args.rclone:
        conf = (HOME / ".config" / "rclone" / "rclone.conf").read_text()
        block = re.search(rf"^\[{re.escape(args.rclone)}\]$", conf, re.M)
        if not block:
            sys.exit(f"❌ rclone 配置里没有 [{args.rclone}]")
        rest = conf[block.end():]
        m = re.search(r"^pass = (.+)$", rest, re.M)
        if not m:
            sys.exit("❌ 该远端没有 pass 项")
        out = subprocess.run(["rclone", "reveal", m.group(1).strip()], capture_output=True, text=True)
        if not out.stdout.strip():
            sys.exit("❌ rclone reveal 失败")
        return out.stdout.strip()
    if args.from_file:
        return Path(args.from_file).read_text().splitlines()[0].strip()
    if args.literal:
        return args.literal
    sys.exit("❌ 需要 <字面量> 或 --rclone/--from-file")


def scrub_text(path: Path, secret: str) -> int:
    """同 inode 原地截断重写：保住正在追加写的进程的 fd 偏移。"""
    if not path.exists():
        return 0
    text = path.read_text(errors="surrogateescape")
    n = text.count(secret)
    if not n:
        return 0
    with open(path, "r+", errors="surrogateescape") as fh:
        fh.write(text.replace(secret, REDACT))
        fh.truncate()
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("literal", nargs="?")
    ap.add_argument("--rclone", help="从该 rclone 远端的 pass 取（推荐）")
    ap.add_argument("--from-file", help="取文件第一行")
    ap.add_argument("--backup-dir", default="/data/disk/niu-secretary/backups/hermes-trace")
    ap.add_argument("--no-vacuum", action="store_true", help="跳过 VACUUM（磁盘紧张时用）")
    args = ap.parse_args()

    secret = resolve_secret(args)
    print(f"  待抹除字符串长度 {len(secret)}（不回显）")

    bk = Path(args.backup_dir)
    bk.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    if STATE.exists():
        src = sqlite3.connect(f"file:{STATE}?mode=ro", uri=True, timeout=60)
        dst = sqlite3.connect(bk / f"state-{stamp}.db", timeout=60)
        src.backup(dst)
        dst.close()
        src.close()
        print(f"  ✅ 备份 → {bk}/state-{stamp}.db（⚠️ 含原文，确认无残留后删掉）")
    for f in (LOG, HIST):
        if f.exists():
            shutil.copy2(f, bk / f"{f.name}-{stamp}")

    for f in (HIST, LOG):
        n = scrub_text(f, secret)
        if n:
            print(f"  {f.name}: 抹掉 {n} 处")

    if STATE.exists():
        con = sqlite3.connect(STATE, timeout=120)
        cur = con.cursor()
        rows = 0
        for (t,) in cur.execute("select name from sqlite_master where type='table'"):
            if "_fts" in t:  # 影子索引整体 rebuild，不逐列改
                continue
            for name, ctype in [(r[1], r[2]) for r in cur.execute(f'pragma table_info("{t}")')]:
                if ctype and not any(k in ctype.upper() for k in ("TEXT", "CHAR", "CLOB")):
                    continue
                try:
                    hits = cur.execute(
                        f'select count(*) from "{t}" where "{name}" like ?', (f"%{secret}%",)
                    ).fetchone()[0]
                except sqlite3.Error:
                    continue
                if hits:
                    cur.execute(
                        f'update "{t}" set "{name}" = replace("{name}", ?, ?) where "{name}" like ?',
                        (secret, REDACT, f"%{secret}%"),
                    )
                    print(f"  {t}.{name}: 抹掉 {hits} 行")
                    rows += hits
        con.commit()
        print(f"  业务表合计 {rows} 行")

        for idx in ("messages_fts", "messages_fts_trigram"):
            try:
                cur.execute(f"insert into {idx}({idx}) values('rebuild')")
                print(f"  ✅ {idx} 已重建")
            except sqlite3.Error as exc:
                print(f"  ⚠️ {idx} 重建失败: {exc}")
        con.commit()
        try:
            cur.execute("pragma wal_checkpoint(truncate)")
            print("  ✅ WAL 已截断")
        except sqlite3.Error as exc:
            print(f"  ⚠️ checkpoint: {exc}")
        if not args.no_vacuum:
            try:
                cur.execute("vacuum")
                print("  ✅ VACUUM 完成")
            except sqlite3.Error as exc:
                print(f"  ⚠️ VACUUM 失败（空间/锁）: {exc}")
        con.close()

    print("\n  ── 复检（期望 0）──")
    out = subprocess.run(["grep", "-rlF", secret, str(HERMES)], capture_output=True, text=True).stdout.strip()
    print(f"  {HERMES}: {out if out else '无残留 ✅'}")
    print("  ⚠️ 提醒：本机清干净了，但凭据已发给模型服务方 → 请轮换该密码")


if __name__ == "__main__":
    main()
