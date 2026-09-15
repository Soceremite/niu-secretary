#!/bin/bash
# 牛秘书闲趣集 · 全自动 no-agent 日报管线
# 候选抓取(豆瓣/网易) → LLM 推荐 JSON + QQ 摘要 → 数据校验 → 海报 vision 审核 → 部署校验
# QQ 推送由 11:30 部署 job 读 dist/qq_digest.txt 后输出（工程日志不进 QQ）
set -e
WORKDIR=/home/ubuntu/vibe_proj/niu-secretary/leisure
ENVFILES="/home/ubuntu/vibe_proj/niu-secretary/config/.env /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env"
PY=/home/ubuntu/vibe_proj/niu-secretary/airesearch/.venv/bin/python

cd "$WORKDIR"
set -a
for f in $ENVFILES; do [ -f "$f" ] && . "$f"; done
set +a

echo "=== [1/4] fetch_leisure_candidates (豆瓣/网易, 无 LLM) ==="
$PY tools/fetch_leisure_candidates.py

echo "=== [2/4] recommend_leisure_llm (统一网关 content → 推荐JSON+摘要) ==="
$PY tools/recommend_leisure_llm.py

echo "=== [3/4] validate_leisure_data ==="
PYTHONPATH=/home/ubuntu/vibe_proj/niu-secretary $PY -c "
import sys; sys.path.insert(0, '/home/ubuntu/vibe_proj/niu-secretary')
from niu_secretary.leisure_validation import validate_leisure_data_dir
from pathlib import Path
r = validate_leisure_data_dir(Path('dist/data'))
errs = r['errors']
print('validation errors:', errs if errs else 'none')
import sys as s
s.exit(2 if errs else 0)
"

echo "=== [4/4] review_posters (统一网关 vision) ==="
$PY tools/review_posters.py

echo "=== DONE: leisure pipeline (pre-deploy) ==="
echo '{"wakeAgent": false}'
