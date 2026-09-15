#!/bin/bash
# 牛秘书新闻社 · 全自动 no-agent 日报管线
# 阶段: 候选抓取(RSS) → LLM摘要+写section → 校验 → 爬图 → vision审核 → 更新section → 归档
# 部署与 QQ 推送由独立的 niu-news-deploy / QQ 通道负责，不在本脚本内
set -e
WORKDIR=/home/ubuntu/vibe_proj/niu-secretary/news-daily
ENVFILES="/home/ubuntu/vibe_proj/niu-secretary/config/.env /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env"
PY=/home/ubuntu/vibe_proj/niu-secretary/airesearch/.venv/bin/python

cd "$WORKDIR"
set -a
for f in $ENVFILES; do [ -f "$f" ] && . "$f"; done
set +a

echo "=== [1/6] fetch_news_candidates (RSS 抓取, 无 LLM) ==="
$PY tools/fetch_news_candidates.py

echo "=== [2/6] summarize_news_llm (统一网关 content 模型写摘要+section) ==="
$PY tools/summarize_news_llm.py

echo "=== [3/6] validate_news ==="
PYTHONPATH=tools $PY tools/validate_news.py

echo "=== [4/6] crawl_images (从原文页抓配图) ==="
PYTHONPATH=tools $PY tools/crawl_images.py

echo "=== [5/6] review_images (统一网关 vision 审核) ==="
PYTHONPATH=tools $PY tools/review_images.py

echo "=== [6/6] update_sections (回写图片引用) ==="
PYTHONPATH=tools $PY tools/update_sections.py || echo "update_sections skipped: $?"

echo "=== [7/7] build_qq_digest (briefing 写入 dist/qq_digest.txt, 部署 job 负责推送) ==="
$PY tools/build_qq_digest.py > dist/qq_digest.txt 2>/dev/null || echo "briefing 生成失败"
echo "briefing bytes: $(wc -c < dist/qq_digest.txt 2>/dev/null || echo 0)"

echo "=== DONE: news pipeline (pre-deploy) ==="
# 本 job 静默完成：工程日志进 cron 存档；QQ 推送由 10:45 部署 job 读取 dist/qq_digest.txt 后输出
echo '{"wakeAgent": false}'
