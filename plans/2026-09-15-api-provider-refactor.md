# 牛秘书 API 供应商框架重构 · 设计方案

日期：2026-09-15
状态：待帅锅过目

## 1. 调研结论（参考对象）

我们调研了三个成熟的 provider 框架，各自的招值得抄，但都不直接照搬：

| 框架 | 核心设计 | 值得抄的 | 不抄的 |
|------|---------|---------|--------|
| **OpenCode** | AI SDK + models.dev 目录（75+ provider）， provider 只分「openai-compatible 客户端 + 天然协议客户端」两类 | 把 provider 收敛为极少数客户端类型；`provider/model` 二级命名 | 不需要 75+ 目录，我们只有自有网关 |
| **Hermes** | `ProviderRegistry`（全局 + per-scope 双层注册表）+ models.dev 缓存 + `credential_pool`（多 key 轮转、冷却、exhausted TTL） | 注册表作用域思想；key 池的 rotating/cooldown 状态机 | 过度复杂，几万行；单机自用不需要 ETag 缓存守护线程 |
| **LiteLLM** | Router：model_group（同一逻辑名 → 多个 deployment）+ 三类 fallback（普通/上下文超限/内容策略）+ cooldown | **逻辑模型名 → 具体部署** 的间接层，这是整个方案的灵魂 | 不需要它的代理服务器形态，我们要的是库不是 API 服务 |

## 2. 核心抽象（抄 LiteLLM Router 的模型分组思想 + Hermes 的注册表）

### 2.1 「逻辑模型」一级命名

应用代码只说 **用途**，永远不说具体厂商：

```
NiuLLM.for("content")        # 新闻社/闲趣集内容生成
NiuLLM.for("vision")         # 图片审核 / 公式 OCR
NiuLLM.for("blog")           # 研知库博客生成
NiuLLM.for("translate")      # 翻译
NiuLLM.for("embed")          # 向量
NiuLLM.for("assistant")      # 牛秘书 server 对话
```

具体落到哪个 endpoint + 哪个 model，全部由 **config/models.yaml** 决定，应用面零 if-else。

### 2.2 逻辑模型的 YAML 定义（LiteLLM model_group 思想的轻量版）

```yaml
# config/models.yaml
default_endpoint: sub2api          # 未显式指定 endpoint 时用它（本地统一网关）

endpoints:
  sub2api:
    base_url: http://127.0.0.1:8317/v1
    api_key_env: SUB2API_API_KEY
    style: chat_completions        # 或 responses（兼容两类 API 风格）
    timeout: 120
    proxy_env: null                # 需要出墙时填代理 env key，本地网关留空

  opencode_go:
    base_url: https://opencode.ai/zen/go/v1
    api_key_env: OPENCODE_GO_API_KEY
    style: chat_completions

logic_models:
  content:
    endpoint: sub2api
    model: deepseek-v4-pro-260425
    max_retries: 3
    fallback: [ {endpoint: sub2api, model: glm-5.3-flash} ]
  vision:
    endpoint: sub2api
    model: doubao-seed-2.0-pro
  embed:
    endpoint: sub2api
    model: text-embedding-3-large
  ...
```

要点：
- 一个 `logic_model` = 一个用途名，映射到一个 endpoint + 真实 model + 可选 fallback 链
- fallback 是 LiteLLM 思想的轻量版：同一逻辑名下按顺序重试备选部署
- `style: chat_completions | responses` —— 研知库现在有 API 风格分支（AIRESEARCH_BLOG_API_STYLE=responses），统一层里把它做成 endpoint 属性而不是散在调用点

### 2.3 「端点」二级命名（provider 收敛思想）

像 OpenCode 一样只认两类端点：
- **openai-compatible**（chat/completions 风格）—— 全部本地网关、OpenCode、DeepSeek、MiniMax 等都是这一类
- **openai-responses 风格** —— 需要时用，也走同一个 HTTP 客户端，只是 body/reponse 解析不同

不做 Anthropic/Gemini 原生协议适配 —— 您现在所有链路已经收敛到本地网关，付不起也不值得付那种复杂度。

### 2.4 Key 管理（Hermes credential_pool 的迷你版）

- key **永远不进 config yaml**，yaml 里只写 `api_key_env`（env 变量名）
- 每个端点支持 key 列表（多个 env 变量名），当前单 key 但留轮转位
- 失败计数 + 冷却：429/5xx 连续 N 次 → 冷却 X 分钟，有备选 key 时轮转，无则抛清晰错误
- 实现约 100 行，够用且可测

### 2.5 统一客户端 `niu_core/llm/`

```
niu_core/llm/
├── client.py          # NiuLLM 客户端：chat / chat_stream / embed / vision_url
├── config.py          # yaml 解析 + env 解析 + 逻辑模型解析
├── keypool.py         # key 轮转 + 冷却
├── errors.py          # 分类错误：rate_limit / timeout / bad_key / content_filter
└── defaults.py        # config 默认路径（project config/ + 允许 profile 覆盖）
```

对外 API 就四个方法，签名稳定：

```python
from niu_core.llm import NiuLLM

llm = NiuLLM.load()                      # 读 config/models.yaml + env
rsp = llm.chat("content", messages)      # 逻辑名 + 消息
vec = llm.embed("embed", texts)
img_rsp = llm.vision("vision", image_url, prompt)
```

## 3. 迁移范围（一步到位路线）

| 板块 | 现状 | 迁移后 |
|------|------|--------|
| **airesearch** | 10+ 套 AIRESEARCH_*_BASE_URL/KEY/MODEL 散落 env | config/models.yaml 里定义 FACT / BLOG / DEEPSEEK / LUNA / TRANSLATE / FORMULA_OCR / EMBED 逻辑模型，代码全走 NiuLLM |
| **news-daily / leisure cron** | Hermes LLM agent 模式，key 在 Hermes 那边 | 收编为 no_agent 脚本 + NiuLLM("content"/"vision")，Hermes 只做定时触发 |
| **niu_secretary server** | action_handlers / assistant.py 自带调用 | NiuLLM("assistant") |
| **fitness** | 双实现（py + js） | 先对齐 py 版走 NiuLLM，js 版后续并入（避免一次改两语言引入新 bug） |
| **web 前端 → 后台 API** | 各板块各自管鉴权 | server 统一鉴权中间件（单独 PR，跟 LLM 层解耦） |

## 4. 环境与部署

- config/models.yaml 进 git（无敏感信息），key 走 config/.env（本地不进 git）
- `NiuLLM.load()` 失败时报「哪个 endpoint 的哪个 env 变量缺失」，一眼定位
- cron 脚本启动时先跑 `python -m niu_core.llm doctor`（快速检查所有逻辑模型可达），失败即退出非零，Hermes 侧能看到失败信号

## 5. 实施步骤（PR 顺序）

1. **niu_core/llm 落地**：config.py + client.py + keypool.py + doctor 子命令 + pytest 单测（mock HTTP）
2. **airesearch 切换**：provider_config.py 退役，10+ env 收敛到 models.yaml；跑一轮 fact/blog/translate/公式 OCR 回归
3. **news-daily / leisure 收编 crons**：generate_current.py / 后处理 / 图片审核全部走 NiuLLM；Hermes cron 改 no_agent + script
4. **niu_secretary server 切换**：assistant.py / action_handlers.py 走 NiuLLM；先只动客户端层，不动路由
5. **fitness py 版切换**（对齐 js 版语义）
6. **旧 env 变量清理 + 文档更新**（airesearch/.env.example 精简为 NIU_LLM 系列少量变量）

## 6. 已知的取舍

- 本地网关（sub2api）是 SPOF，但已有部署有既成事实，重构范围是「统一打它」，不是「给它做 HA」——HA 属于后续运维项
- js 版 fitness / web 前端直连_LOCAL 网关部分不在本 PR 里，划到收尾单独处理
- 冷却策略按简单计数器实现，不做 LiteLLM 那种带 TTL+置信度的完整池子（加复杂度大于价值）

---

## 待帅锅确认的点

1. 端点是否**全部**默认走本地 sub2api，包括 Hermes cron 收编后的内容生成？
2. `content` 逻辑模型的主选是 deepseek-v4-pro-260425（现在的 cron 默认）对吗，fallback 用 glm-5.3-flash？
3. OCR/公式识别的模型现在是 gpt-5.6-luna（airesearch env 里 OCR 相关指向 gpt-5.6），这次也一起收进 models.yaml 一起切，还是先保持原样？
