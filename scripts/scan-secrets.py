#!/usr/bin/env python3
"""提交前扫描隐私数据 / 密钥（niu-secretary 项目）。

三道防线，任一中招就拦下：
  A. 被追踪/待提交的**文件路径**像不像隐私文件（.env / *.key / *.pem / id_rsa / 凭据 / 库文件）
  B. 内容里的**密钥形态**（私钥块、各家 token 前缀、JWT、Bearer、rclone obscure …）
  C. 内容里出现了**当前线上真实的密钥值**（读 config/.env、airesearch/.env）—— 零假阳性，最硬

用法：
  python3 scripts/scan-secrets.py --staged     # 只看暂存区（pre-commit 钩子用）
  python3 scripts/scan-secrets.py --tree       # 看工作区被追踪的文件
  python3 scripts/scan-secrets.py --history    # 遍历全部 git 对象（历史里有没有进过）
  python3 scripts/scan-secrets.py --install-hook   # 装成 .git/hooks/pre-commit

安全：只报「文件:行 类型 脱敏样例(长度)」，**绝不回显完整值**。
放行：行尾写 `secrets-scan:ignore`（要写原因），或用 --allow 指定路径 glob。
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
IGNORE_MARK = "secrets-scan:ignore"

# ── B 防线：密钥形态 ──
PATTERNS: list[tuple[str, re.Pattern[bytes]]] = [
    ("私钥块", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("OpenAI/opencode 风格 sk-", re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}")),
    ("Anthropic sk-ant-", re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("GitHub PAT", re.compile(rb"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}")),
    ("Slack token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("AWS AccessKeyId", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JWT", re.compile(rb"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("Bearer 长凭据", re.compile(rb"[Bb]earer\s+[A-Za-z0-9._\-]{30,}")),
    ("rclone obscure 密码", re.compile(rb"^\s*pass\s*=\s*[A-Za-z0-9_\-+/=]{20,}", re.M)),
    ("校园/服务账号标识", re.compile(rb"\b\d{9,12}@(?:auth\.local|mail\.ustc\.edu\.cn)\b")),
    ("赋值给人看的密钥", re.compile(
        rb"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*[\"']?([A-Za-z0-9_\-+/=]{24,})[\"']?")),
]

# ── A 防线：隐私文件名 ──
SENSITIVE_PATH = re.compile(
    r"(^|/)(\.env($|\.)|[^/]*\.env(\.[^/]*)?$|[^/]*\.(key|pem|p12|pfx|jks)$|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$"
    r"|credentials([^/]*)?$|secrets?([^/]*)?$|rclone\.conf$|[^/]*\.(sqlite3?|db)(-wal|-shm)?$|\.npmrc$|\.netrc$)"
)
PATH_ALLOW: list[str] = ["*.env.example", "*.example", "*crontab.example", "*/deploy/*.conf"]

SKIP_DIRS = (".git/", "node_modules/", ".venv/", "venv/", "dist/", "site-packages/")
SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf",
            ".zip", ".gz", ".zst", ".mp4", ".mp3", ".pdf", ".so", ".o", ".pyc")


def redact(raw: bytes) -> str:
    try:
        s = raw.decode("utf-8", "replace")
    except Exception:
        return f"<{len(raw)}B>"
    if len(s) <= 8:
        return f"<len {len(s)}>"
    return f"{s[:3]}…{s[-3:]} (len {len(s)})"


def live_secrets() -> dict[str, str]:
    """C 防线：从线上 .env 读出真实密钥值（只用于匹配，值不外泄）。"""
    out: dict[str, str] = {}
    for path in (REPO / "config" / ".env", REPO / "airesearch" / ".env",
                 Path("/etc/niu-secretary-api.env")):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, val = line.partition("=")
            name = name.replace("export", "").strip()
            val = val.strip().strip("\"'")
            if not any(k in name.upper() for k in ("KEY", "TOKEN", "SECRET", "PASS")):
                continue
            # 路径/目录/URL/主机名/端口不是凭据（例：NIU_SECRETARY_DB_PATH）
            if name.upper().endswith(("_PATH", "_DIR", "_URL", "_URI", "_HOST", "_PORT",
                                      "_NAME", "_DB", "_MODEL", "_ENDPOINT", "_FILE")):
                continue
            if len(val) < 12 or val.startswith(("$", "${", "/", "http://", "https://")):
                continue
            out[f"{path.name}:{name}"] = val
    return out


def scan_bytes(name: str, data: bytes, secrets: dict[str, str], allow: list[str]) -> list[str]:
    findings: list[str] = []
    if any(fnmatch.fnmatch(name, pat) for pat in allow):
        return findings
    lines = data.split(b"\n")
    for lineno, line in enumerate(lines, 1):
        if IGNORE_MARK.encode() in line:
            continue
        for label, rx in PATTERNS:
            m = rx.search(line)
            if m:
                findings.append(f"{name}:{lineno}  [{label}]  {redact(m.group(0))}")
                break
    for src, val in secrets.items():
        if val.encode() in data:
            findings.append(f"{name}  [真实密钥值命中 ← {src}]  {redact(val.encode())}")
    return findings


def files_staged() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                         cwd=REPO, capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f.strip()]


def blob_of_staged(path: str) -> bytes:
    return subprocess.run(["git", "show", f":{path}"], cwd=REPO, capture_output=True).stdout


def files_tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f.strip()]


def iter_blob_of_workdir(path: str) -> bytes:
    try:
        return (REPO / path).read_bytes()
    except OSError:
        return b""


def iter_history() -> list[tuple[str, bytes]]:
    """遍历所有 ref 可达的对象里的 blob（带大小上限，避免拖垮）。"""
    names = subprocess.run(["git", "rev-list", "--objects", "--all"],
                           cwd=REPO, capture_output=True, text=True).stdout
    seen: set[str] = set()
    blobs: list[tuple[str, str]] = []   # (sha, hint-path)
    for line in names.splitlines():
        sha, _, hint = line.partition(" ")
        if sha in seen:
            continue
        seen.add(sha)
        blobs.append((sha, hint or "<no-path>"))
    # 用 --batch-check 拿类型和大小，只保留 <512KB 的 blob
    payload = "\n".join(sha for sha, _ in blobs).encode()
    chk = subprocess.run(["git", "cat-file", "--batch-check"], cwd=REPO, input=payload,
                         capture_output=True).stdout.decode(errors="replace")
    ok: list[tuple[str, str]] = []
    for line, (sha, hint) in zip(chk.splitlines(), blobs):
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "blob" and parts[2].isdigit() and int(parts[2]) < 512 * 1024:
            ok.append((sha, hint))
    if not ok:
        return []
    payload = "\n".join(sha for sha, _ in ok).encode()
    cat = subprocess.run(["git", "cat-file", "--batch"], cwd=REPO, input=payload, capture_output=True).stdout
    # 解析 --batch 输出：<sha> blob <size>\n<content>\n
    out: list[tuple[str, bytes]] = []
    pos = 0
    for sha, hint in ok:
        nl = cat.find(b"\n", pos)
        if nl < 0:
            break
        header = cat[pos:nl].split()
        pos = nl + 1
        if len(header) < 3 or not header[2].isdigit():
            continue
        size = int(header[2])
        out.append((f"历史 {sha[:10]} ({hint})", cat[pos:pos + size]))
        pos += size + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--staged", action="store_true", help="只扫暂存区（pre-commit）")
    g.add_argument("--tree", action="store_true", help="扫工作区被追踪文件")
    g.add_argument("--history", action="store_true", help="扫全部 git 对象")
    ap.add_argument("--allow", action="append", default=[], help="额外放行的路径 glob")
    ap.add_argument("--install-hook", action="store_true", help="安装 pre-commit 钩子")
    args = ap.parse_args()

    if args.install_hook:
        hooks = REPO / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        tpl = ("#!/usr/bin/env bash\n"
               "# 由 scripts/scan-secrets.py --install-hook 安装\n"
               "exec python3 \"$(git rev-parse --show-toplevel)/scripts/scan-secrets.py\" {mode}\n")
        # pre-commit 扫暂存区；pre-push 扫全部历史（推送后更难收回）
        for name, mode in (("pre-commit", "--staged"), ("pre-push", "--history")):
            hp = hooks / name
            if hp.exists() and "scan-secrets" not in hp.read_text(errors="ignore"):
                print(f"⚠️ {hp} 已存在且不是本工具安装的，跳过（请手动合并）")
                continue
            hp.write_text(tpl.format(mode=mode))
            hp.chmod(0o755)
            print(f"✅ 已安装钩子: {hp}   ({mode})")
        return 0

    allow = list(PATH_ALLOW) + list(args.allow)
    secrets = live_secrets()
    print(f"  C 防线载入 {len(secrets)} 个线上真实密钥值（仅用于匹配，不外显）")

    findings: list[str] = []
    if args.staged:
        files = files_staged()
        print(f"  扫描暂存区 {len(files)} 个文件")
        for f in files:
            if any(d in f for d in SKIP_DIRS) or f.endswith(SKIP_EXT):
                continue
            if SENSITIVE_PATH.search(f) and not any(fnmatch.fnmatch(f, p) for p in allow):
                findings.append(f"{f}  [隐私文件名被暂存]")
            findings += scan_bytes(f, blob_of_staged(f), secrets, allow)
    elif args.history:
        blobs = iter_history()
        print(f"  扫描历史 blob {len(blobs)} 个（<512KB）")
        for name, data in blobs:
            findings += scan_bytes(name, data, secrets, allow)
    else:  # 默认 --tree
        files = files_tracked()
        print(f"  扫描被追踪文件 {len(files)} 个")
        for f in files:
            if any(d in f for d in SKIP_DIRS) or f.endswith(SKIP_EXT):
                continue
            if SENSITIVE_PATH.search(f) and not any(fnmatch.fnmatch(f, p) for p in allow):
                findings.append(f"{f}  [隐私文件名被追踪]")
            findings += scan_bytes(f, iter_blob_of_workdir(f), secrets, allow)

    if findings:
        print(f"\n❌ 发现 {len(findings)} 处可疑：")
        for line in findings[:60]:
            print(f"    {line}")
        if len(findings) > 60:
            print(f"    …还有 {len(findings) - 60} 处")
        print("\n  处理：把密钥改成 env 引用（api_key_env / os.environ），或行尾加 "
              "`secrets-scan:ignore` 并写明原因。")
        return 1
    print("\n✅ 未发现隐私密钥")
    return 0


if __name__ == "__main__":
    sys.exit(main())
