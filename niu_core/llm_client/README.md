# niu_core/llm — 牛秘书统一 LLM 网关层

> 2026-09-15 落地。所有板块的 LLM 调用收敛到「逻辑模型名」+ `config/models.yaml` 单一路由表。
> 设计文档：`plans/2026-09-15-api-provider-refactor.md`；执行计划：`plans/2026-09-15-api-unification-execution.md`（已实施）

## 快速使用

```python
from niu_core.llm_client import NiuLLM

llm = NiuLLM.load()                     # 读 config/models.yaml + env
rsp = llm.chat("content", messages)     # 用途名，路由到 endpoint + 真实 model
vecs = llm.embed("embed", ["文本"])
r = llm.vision("vision", image_url, prompt)   # 图片理解
```

命令行探活：

```bash
AIR=/home/ubuntu/vibe_proj/niu-secretary/airesearch/.venv/bin/python
set -a; source config/.env; set +a
$AIR -m niu_core.llm_client doctor          # 探所有 endpoint
$AIR -m niu_core.llm_client doctor flash    # + 真实 ping 某逻辑模型
```

## 逻辑模型一览（config/models.yaml）

| 逻辑名 | 用途 | 主选 | fallback |
|--------|------|------|----------|
| content | 新闻社/闲趣集内容生成 | deepseek 官方 deepseek-v4-pro | opencode_go 同模型 → sub2api gpt-5.6-luna |
| vision | 图片审核（新闻配图/海报）、fitness 拍照识别 | sub2api gpt-5.6-luna | opencode deepseek-v4-flash-vision-exp |
| fact / blog / translate / formula_ocr | 研知库四兄弟 | sub2api gpt-5.6-luna（fact/blog responses 风格） | — |
| embed | 向量 | DashScope text-embedding-v4 | — |
| assistant | 牛秘书 server 对话/意图分类 | **opencode_go glm-5.3-flash**（4/4 分类全对、1.7s、订阅内 0 成本） | sub2api gpt-5.6-sol |
| flash | 快速小任务 | sub2api gpt-5.6-luna | — |

## 渠道（endpoint）

| endpoint | 说明 | key env |
|----------|------|---------|
| sub2api | 本地聚合网关 http://124.222.22.171:8080/v1 | NIU_GATEWAY_API_KEY（config/.env） |
| opencode_go | OpenCode Go $10/月订阅，官方端点 | OPENCODE_SUBSCRIPTION_KEY（config/.env） |
| deepseek | DeepSeek 官方按量付费 | DEEPSEEK_API_KEY（~/.hermes/.env） |
| dashscope | 阿里 embedding | AIRESEARCH_EMBEDDING_API_KEY（airesearch/.env） |

## 服务接线现状（统一后）

| 服务 | systemd / cron | 状态 |
|------|---------------|------|
|niu-secretary-api(对话) | niu-secretary-api.service | assistant.py `_post_openai` → NiuLLM("assistant")，prompt 强化(fitness 含饮食/运动/健康)+few-shot 5 例，temperature=0 |
| niu-fitness-api(拍照识别) | niu-fitness-api.service **ExecStart 已指向 vibe_proj 新仓库** | nutrition_api.py → NiuLLM("vision")，legacy 直连路径保留作 grisaille fallback |
| 新闻社 cron 10:00/10:45 | no_agent 脚本 run_pipeline.sh | candidate(RSS)→summary(NiuLLM content)→vision 审核→QQ briefing |
| 闲趣集 cron 11:00/11:30 | no_agent 脚本 | candidates(豆瓣/网易)→recommend(NiuLLM content)→poster(NiuLLM vision)→部署只输出 briefing |
| 研知库调用链 | 8 个调用点走 compat.resolve | 653/653 测试全绿 |

## 客户端规则（重要）

- **显式 env 永远 > 统一 config 默认**：`AIRESEARCH_*` / `NIU_LLM_<NAME>_*` 覆盖 models.yaml
- key 一律走 env 变量名（yaml 只写 `api_key_env`），失败冷却 3 次触发
- fallback 链：主选失败(429/5xx/超时)按序尝试备选，全挂才抛错
- `python -m niu_core.llm_client doctor` 探活所有 endpoint，cron 脚本接入前先 doctor

## 已知坑位记录

1. sub2api 用户 key 分组决定可用模型（sk-7a3… 只有 gpt 系）——换 key/加分组需在网关后台操作
2. OpenCode 官方端点需 `User-Agent`（CF 拦 curl 默认 UA）+ `x-opencode-session` 头，client.py 已内置
3. fitness vision 用了餐盘图，模型诚实说「图片显示为影视海报，未提供可识别的餐食内容」——质量验证通过
4. assistant.py 里 models 元组的 model_id 只是**显示名**，真实模型走 models.yaml
