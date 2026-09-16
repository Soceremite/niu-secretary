# niu_core/llm — 牛秘书统一 LLM 网关层

> 2026-09-15 落地；**2026-09-16 深化**：`config/models.yaml` 成为**唯一路由源**，并加上**全链路调用记录**。
> 设计文档：`plans/2026-09-15-api-provider-refactor.md`；执行计划：`plans/2026-09-15-api-unification-execution.md`（已实施）

## 快速使用

```python
from niu_core.llm_client import NiuLLM

llm = NiuLLM.load()                     # 读 config/models.yaml + env
rsp = llm.chat("content", messages)     # 用途名，路由到 endpoint + 真实 model
vecs = llm.embed("embed", ["文本"])
r = llm.vision("vision", image_url, prompt)   # 图片理解
```

命令行探活与用量：

```bash
AIR=/home/ubuntu/vibe_proj/niu-secretary/airesearch/.venv/bin/python
set -a; source config/.env; set +a
$AIR -m niu_core.llm_client doctor          # 探所有 endpoint
$AIR -m niu_core.llm_client doctor flash    # + 真实 ping 某逻辑模型
$AIR -m niu_core.llm_client report --days 7 # 调用记录汇总
```

## 逻辑模型一览（config/models.yaml，2026-09-16 全量切 opencode 订阅）

| 逻辑名 | 用途 | 主选 | fallback |
|--------|------|------|----------|
| content | 新闻社/闲趣集内容生成 | **opencode_go deepseek-v4-pro** | sub2api gpt-5.6-luna → deepseek 官方 deepseek-v4-pro |
| vision | 图片审核（新闻配图/海报）、fitness 拍照识别 | **opencode_go deepseek-v4.1-flash** | sub2api gpt-5.6-luna → opencode deepseek-v4-flash-vision-exp |
| fact / blog / formula_ocr | 研知库事实抽取 / 论文博客 / 公式 OCR | **opencode_go deepseek-v4.1-flash** | sub2api gpt-5.6-luna |
| translate | 研知库中文翻译（两个手工脚本调用） | **opencode_go mimo-v2.5** | opencode deepseek-v4.1-flash → sub2api gpt-5.6-luna |
| embed | 向量（1024 维） | DashScope text-embedding-v4 | — |
| assistant | 牛秘书 server 对话/意图分类 | **opencode_go glm-5.3-flash**（4/4 分类全对、1.7s、订阅内 0 成本） | sub2api gpt-5.6-sol |
| flash | 快速小任务 | **opencode_go mimo-v2.5** | — |

## 渠道（endpoint）

| endpoint | 说明 | key env |
|----------|------|---------|
| opencode_go | OpenCode Go $10/月订阅，官方端点 https://opencode.ai/zen/go/v1 | OPENCODE_SUBSCRIPTION_KEY（config/.env） |
| sub2api | 本地聚合网关 http://124.222.22.171:8080/v1 | NIU_GATEWAY_API_KEY（config/.env） |
| deepseek | DeepSeek 官方按量付费 | DEEPSEEK_API_KEY（~/.hermes/.env） |
| dashscope | 阿里 embedding | AIRESEARCH_EMBEDDING_API_KEY（airesearch/.env） |

## 路由优先级（2026-09-16 起：「yaml 说了算」）

```
显式调用参数
  → 路由专属 env（AIRESEARCH_FACT_* / BLOG_* / FORMULA_OCR_*，保留为逃生舱）
  → config/models.yaml          ← 唯一路由源
  → 历史通用 env（OPENCODE_GO_* / OPENAI_* / TRANSLATE_* / NIU_ASSISTANT_* / FITNESS_VISION_*）
  → 硬编码默认
```

- 管理台「AI 渠道」页改的就是 `config/models.yaml`，`llm_admin._write_config` 调 `compat.reload()` 即时生效
- **坑**：`.env` 里若还留着 `TRANSLATE_BASE_URL` / `AIRESEARCH_FACT_MODEL` 这类显式变量，会**压过 yaml** —— 这是「改了 yaml 不生效」的根因；改路由要**同时看两层**（`airesearch/.env` + `config/.env`）

## 调用记录（llm_calls）

`niu_core/llm_client/call_log.py` → SQLite `data/llm_calls.sqlite3`（WAL）。

- **收口点**在 `NiuLLM.chat()/embed()` 的主选+备选循环里，**只记元信息、不记正文**：时间 / 调用方 / 逻辑路由 / 端点 / 真实模型 / is_fallback / status / 耗时 / tokens / 错误摘要
- 查看：`python3 -m niu_core.llm_client report --days 7`；管理台 **「AI 渠道 → API 用量」**（action `llm.usage.report`，页面 `AdminLLMUsagePage.vue`）
- 自建 HTTP 客户端用装饰器埋点：`@call_log.tracked("<路由名>", endpoint_param="base_url", model_param="model", prompt_param="messages")`（`fact_extraction.py` / `paper_blog.py` / 两个翻译脚本已接）
- **papi（paperpipe）内部直接用 litellm、不经过本层** → 由 `airesearch/papi_hooks/sitecustomize.py`（activate.sh 放进 PYTHONPATH）把 `airesearch/tools/papi_litellm_log.py` 的回调挂到 `litellm.success_callback/failure_callback`，记录里显示 `caller=papi(litellm)`、`logic_model=blog`
- 环境开关：`NIU_LLM_LOG=0` 关闭；`NIU_LLM_LOG_DB` 换库路径
- **测试必须隔离**：两处 `tests/conftest.py` 把 `NIU_LLM_LOG_DB` 指向临时库，否则测试会污染真实记录库

## 服务接线现状（统一后）

| 服务 | systemd / cron | 状态 |
|------|---------------|------|
| niu-secretary-api（对话） | niu-secretary-api.service | assistant.py → `NiuLLM("assistant")`，prompt 强化（fitness 含饮食/运动/健康）+ few-shot 5 例，temperature=0 |
| niu-fitness-api（拍照识别） | niu-fitness-api.service（ExecStart 已指向 vibe_proj 新仓库） | nutrition_api.py → `NiuLLM("vision")`，legacy 直连保留作 fallback |
| 新闻社 cron 10:00/10:45 | no_agent 脚本 `niu-news-pipeline.sh` / `niu-news-deploy.sh` | candidate(RSS) → summary(content) → vision 审核 → QQ briefing |
| 闲趣集 cron 11:00/11:30 | no_agent 脚本 `niu-leisure-pipeline.sh` / `niu-leisure-deploy.sh` | candidates(豆瓣/网易) → recommend(content) → poster(vision) → 部署只输出 briefing |
| 研知库调用链 | 8 个调用点走 `compat.resolve` | **663 passed**（2026-09-16 全量 3:42） |
| 研知库翻译脚本 ×2 | 手工 / cron | translate 路由 + call_log 埋点，已补 OpenCode 两个必需头 |
| papi（paperpipe） | `airesearch/activate.sh` 环境 | litellm 直连 + sitecustomize 回调节点 |

## 客户端规则（重要）

- 优先级见上节；key 一律走 env 变量名（yaml 只写 `api_key_env`），失败冷却 3 次触发
- fallback 链：主选失败（429/5xx/超时）按序尝试备选，全挂才抛错
- `python -m niu_core.llm_client doctor` 探活所有 endpoint，cron 脚本接入前先 doctor
- **自建 HTTP 客户端必须带两个头**：正常 `User-Agent`（Cloudflare 会拦 urllib/curl 默认 UA → `403 error code: 1010`）+ `x-opencode-session`（缺失 → `400 MissingSessionID`）

## 已知坑位记录

1. sub2api 用户 key 分组决定可用模型（`sk-7a3…` 只有 gpt 系）—— 换 key/加分组需在网关后台操作
2. OpenCode 官方端点需 `User-Agent` + `x-opencode-session`，`client.py` 已内置；**自建 urllib 客户端容易漏**（事实抽取「2 秒失败、`llm_calls=0`」就是这个）
3. `.env` 显式变量压过 `models.yaml` —— 改路由要同时看两层
4. `assistant.py` 里 models 元组的 `model_id` 只是**显示名**，真实模型走 models.yaml
5. 测试会写进真实调用记录库 → 用 conftest 隔离（`NIU_LLM_LOG_DB` 指临时库）
6. WebDAV/Web 类端口探活：无凭据 `401` 只证明「地址对、服务在」，不证明账号能登
