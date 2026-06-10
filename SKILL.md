---
name: niu-secretary
description: "牛秘书品牌体系——品牌定位、视觉规范、技术架构与功能矩阵。用于统一品牌调性，指导各子产品（新闻社、塑形馆、时务局、闲趣集、AIResearch 研知库）的设计与开发。"
risk: safe
date_added: "2026-05-28"
last_updated: "2026-06-10"
---

# 牛秘书品牌体系

> **核心理念**：不只是一个助手，而是一位懂你节奏、替你操心的虚拟私人管家。

## 品牌定位

**牛秘书** — 你的私人 AI 管家

- **人格**：御姐型 AI 管家
- **气质**：清冷中带着温柔，干练且体贴
- **口吻**：专业、可靠、有温度，偶尔调皮但不失分寸
- **对标**：不是冰冷的工具，也不是撒娇的宠物，而是一位值得信赖的秘书

### 品牌关键词

专业 · 干练 · 可靠 · 有温度 · 主动服务 · 私人定制

### 品牌宣言

> 在这个信息过载的时代，
> 你不需要另一个 App，
> 你需要的是一位真正了解你的管家。

### 品牌愿景

让每个人都能拥有自己的 AI 私人管家。

- **现阶段**：以 Web 服务矩阵形式提供新闻简报、健身管理等核心功能
- **中期目标**：整合为统一入口的「牛秘书」个人管理中心
- **终极形态**：「牛秘书 App」— 面向所有人的私人 AI 管家平台，支持个性化配置、多模态交互、主动服务

---

## 视觉规范

### Logo

- **文件**：`/home/ubuntu/Pictures/image-2.png`（2048×2048）
- **风格**：黑金配色、御姐动漫头像
- **展示形式**：**圆形裁剪**，可带金色渐变边框
- **使用范围**：所有牛秘书子品牌站点

### 配色方案

品牌主页采用 **dark luxury** 风格：

| 色彩 | 色值 | 用途 |
|------|------|------|
| 深底 | `#0a0a0a` | 页面背景 |
| 卡片底 | `#1a1a1a` | 卡片、面板 |
| 主金色 | `#c8a45c` | 强调色、标题、边框 |
| 亮金 | `#e4c97c` | 渐变高光 |
| 暗金 | `#8b6914` | 渐变阴影 |
| 主文字 | `#e8e4dc` | 正文标题 |
| 副文字 | `#a8a49c` | 描述文字 |
| 弱文字 | `#6a6660` | 提示、标注 |

### 字体

- **标题/品牌名**：Noto Serif SC（思源宋体）— 优雅、有分量
- **正文**：Noto Sans SC（思源黑体）— 清晰、现代
- **装饰/英文**：Playfair Display — 杂志感、高端

### 设计语言

- **基调**：暗色底 + 金色点缀，营造高端管家服务的质感
- **氛围**：噪声纹理叠加，径向渐变光晕，杂志排版感
- **动效**：滚动渐现（reveal）、卡片悬浮光效、Logo 浮动动画

---

## 技术栈

| 层 | 选型 |
|----|------|
| 前端 | 纯 HTML/CSS/JS（无框架依赖），响应式设计 |
| 后端 | Python HTTP API + SQLite（Action Protocol） |
| 部署 | nginx `/niu-secretary/` → `/var/www/html/niu-secretary/` |
| 部署权限 | 目标目录属于 root，需 sudo cp / rsync |
| AI 助手 | Python 标准库 HTTP API + SQLite Action Protocol |
| AIResearch | Python package + SQLite + paperpipe / papi + 静态研究报告站点 |
| AI 驱动 | OpenClaw + DeepSeek V4 Pro / Claude Opus 4.6 / OpenAI-compatible providers |
| Logo 托管 | `logo.png` 放在各子目录下 |

---

## 功能矩阵

### 已上线

| 功能 | 地址 | 说明 |
|------|------|------|
| 🏠 品牌主页 | `/niu-secretary/` | 品牌入口，功能导航，品牌宣言与愿景 |
| 📰 新闻社 | `/niu-secretary/news/` | 每日新闻简报，五维分类（国内/国际/财经/科技/AI），AI 精选 |
| 🏋️ 塑形馆 | `/niu-secretary/fitness/` | 科学健身管理，训练/营养/恢复/评估/咨询六大模块 |
| 📅 时务局 | `/niu-secretary/schedule/` | 日程管理：今日排班、秘书提醒、事务抽屉、目标追踪 |
| 🎬 闲趣集 | `/niu-secretary/leisure/` | 休闲推荐：今晚首推、今日候选、口味档案 |
| 🧠 AIResearch 研知库 | `/niu-secretary/airesearch/` | 本地自动科研 RAG、论文知识图谱、事实溯源、研究地图、静态报告站点 |

### 规划中

| 功能 | 地址 | 说明 |
|------|------|------|
| 🤖 AI 对话管家 | — | 7×24h 私人 AI 对话，个性化记忆，主动提醒 |
| 📱 牛秘书 App | — | 统一入口，多端同步，开放平台 |

---

## v2.0 AI 助手与 Action Protocol

v2.0 的核心理念：牛秘书主页 AI、语音助手、四个子网页和未来 App 不再各写一套业务逻辑，而是统一调用同一组 Action Protocol。

### AI 助手设计理念

牛秘书 AI 是总入口，不直接把一句话硬塞进某个页面，而是先理解意图，再调用能力：

1. **意图分流**：先调用模型判断用户属于 `fitness`、`schedule`、`news`、`leisure`、`airesearch`、`chat` 或 `unknown`。
2. **模块 Prompt**：根据板块选择专用 prompt。塑形馆负责营养、训练、恢复、评估；时务局负责日程、提醒、待办；新闻社、闲趣集和 AIResearch 保留后续技能接入。
3. **动作生成**：模型只生成允许的 action 和参数，不直接写库。
4. **用户确认**：主页先展示可编辑 JSON，用户确认后才执行。
5. **统一落库**：确认后调用 `/niu-secretary/api/actions/execute` 写入服务端 SQLite。
6. **多端同步**：子网页直接从统一 API 读取服务端记录（后端 SQLite 为唯一数据源），localStorage 退化为离线缓存/兜底。

> 这个内部 Action Protocol 不是 MCP，但按 MCP 思路设计：能力可发现、输入可校验、执行可审计，未来可以再包一层 MCP Server。

> **数据源原则（2026-05-30 起）**：后端 SQLite 是唯一权威数据源。各板块页面优先调用 `actions/execute` 的 list 类动作读取，请求失败时才回落到 localStorage 缓存。AI 写入的数据因此能被各板块直接读到，并跨设备一致。

> **AIResearch 状态（2026-06-10 起）**：AIResearch 已进入 MVP 可发布状态。当前链路包含 paperpipe 本地论文库、OpenAlex/arXiv/Semantic Scholar/SerpAPI 候选发现、规范化 ingest、论文卡片、代码链接、artifact ledger、研究事实抽取、事实审计、证据修复、研究 digest/map/gap/synthesis/narrative、语义聚类、人审摘要、静态报告站点、刷新命令、健康检查、DB 备份、发布差异和外部静态站点 deploy/rollback 脚本。

### 本地启动

```bash
NIU_SECRETARY_API_PORT=5188 python3 server/niu_secretary_api.py
```

### AIResearch 本地启动

```bash
cd airesearch
source ./activate.sh
python -m airesearch.cli health-check --site-dir exports/site-current
python -m airesearch.cli serve-report-site --dir exports/site-current --host 127.0.0.1 --port 8765
```

### 本地配置

真实 API Key 只保存在服务器本地 `/etc`，不进入 Git 仓库。仓库只保存模板：

| 模板 | 本地真实配置 | 用途 |
|------|------|------|
| `config/niu-secretary-api.env.example` | `/etc/niu-secretary-api.env` | 主页 AI 助手、Action Protocol、SQLite 路径 |
| `config/niu-fitness-api.env.example` | `/etc/niu-fitness-api.env` | 塑形馆图片识别、多模态模型 |

恢复或迁移到新机器时：

```bash
sudo cp config/niu-secretary-api.env.example /etc/niu-secretary-api.env
sudo cp config/niu-fitness-api.env.example /etc/niu-fitness-api.env
sudo chmod 600 /etc/niu-secretary-api.env /etc/niu-fitness-api.env
sudo systemctl restart niu-secretary-api.service niu-fitness-api.service
```

然后编辑两个 `/etc/*.env` 文件，把 `*_API_KEY` 改成本机真实密钥。

### 模型配置分工

| 配置 | 当前用途 |
|------|------|
| `NIU_ASSISTANT_API_BASE` / `NIU_ASSISTANT_MODEL` | 首页 AI 文本理解、意图分流、动作生成 |
| `FITNESS_VISION_API_BASE` / `FITNESS_VISION_MODEL` | 塑形馆图片识别、餐食营养估算 |

两者可以指向同一个模型，例如 `qwen3.6-plus`；也可以以后拆成"文本强模型 + 视觉强模型"。

### 核心接口

| 接口 | 说明 |
|------|------|
| `GET /niu-secretary/api/health` | 服务健康检查 |
| `GET /niu-secretary/api/capabilities` | 当前可调用能力注册表 |
| `POST /niu-secretary/api/assistant/message` | 自然语言解析为候选动作 |
| `POST /niu-secretary/api/actions/execute` | 执行统一动作 |

### 动作清单

**写入类**
- `fitness.nutrition.create`：记录一餐。
- `schedule.event.create`：创建日程。
- `schedule.todo.create`：创建待办。

**读取类**（板块页面从后端拉数据，支持 `from`/`to` 日期范围）
- `fitness.nutrition.today_summary`：读取某日营养汇总。
- `fitness.nutrition.list`：按范围读取营养日志。
- `schedule.today_summary`：读取某日日程与待办。
- `schedule.event.list`：按范围读取日程。
- `schedule.todo.list`：读取待办，支持 `includeDone` 过滤；无日期待办始终纳入。

**修改/删除类**
- `schedule.todo.toggle`：切换待办完成状态（不传 `done` 则翻转当前值）。
- `fitness.nutrition.delete` / `schedule.event.delete` / `schedule.todo.delete`：按 `id` 删除。

**用户画像类（2026-05-30 新增）**
- `profile.get`：读某板块画像；不传 module 返回全部。
- `profile.update`：patch 语义合并画像字段，同时记录变更历史（需确认）。
- `profile.reset`：重置某板块画像为默认。
- `profile.changes`：读画像变更历史。

**画像驱动推送类（2026-05-30 新增）**
- `fitness.recommend`：按塑形馆画像生成今日饮食/训练建议。
- `schedule.recommend`：按时务局画像生成今日时间安排与提醒建议。

> 完整能力注册表以 `GET /api/capabilities` 为准。新增动作需同步更新 `store.py`、`capabilities.py`、`action_handlers.py` 三处，并补单测。

### 用户画像系统（v1，2026-05-30）

牛秘书 AI 不只记录数据，还能通过聊天**自适应调整四大板块的用户画像**，并用画像驱动个性化推送。

- **两层结构**：`user_profiles`（每板块一份结构化 JSON 快照，驱动推送）+ `profile_changes`（每次增量变更记录，可追溯可审计）。
- **意图分类加 intent 维度**：assistant 在分类时同时判断 `record`（记录一次性数据）/ `preference`（调整长期偏好）/ `query`（询问推荐）。
- **preference → profile.update**：模型从聊天抽取偏好生成画像更新动作，同样走「待确认动作卡片」，不让 AI 偿偿改画像。
- **本地降级**：模型不可用时用关键词粗抽取（减脂/增肌、川渝/清淡、悬疑/科幻 等）。
- **v1 范围**：画像 CRUD + 聊天调整 + 塑形馆/时务局推送闭环；新闻社/闲趣集真实内容库对接列为 v1.1。
- 详细方案见 `plans/user-profile-v1.md`。

---

## AIResearch 研知库运行边界

AIResearch 是牛秘书当前最重的子系统。根项目文档只记录入口和运维边界，详细实现以 `airesearch/SKILL.md`、`airesearch/PLAN.md` 和 `airesearch/DEVELOPMENT.md` 为准。

### 核心能力

- 论文 ingest 必须优先通过 `papi add`，不要绕过 paperpipe 直接写论文库。
- SQLite 是 MVP 账本，记录论文、候选、来源、provenance、facts、reports、run history。
- 报告必须基于可追溯 evidence，不把 `summary.md` 当作完整 literature review。
- 生成性内容必须区分事实、证据和假设；假设要明确标注。
- 外部静态站点部署前必须有快照，回滚使用 `deploy/rollback-airesearch.sh latest` 或指定快照名。

### 常用命令

```bash
cd airesearch
python -m airesearch.cli run-launch-refresh --limit-per-profile 50 --select-limit 10 --min-score 0.60 --out-dir exports/mvp-current --site-dir exports/site-current --progress
python -m airesearch.cli health-check --site-dir exports/site-current --require-fact-provider
python -m airesearch.cli backup-db --out-dir backups --label before-launch-refresh
python -m airesearch.cli write-static-host-config --site-dir exports/site-current --out-dir deploy --base-path /niu-secretary/airesearch/ --deploy-root /var/www/html/niu-secretary/airesearch
python -m airesearch.cli write-static-deploy-scripts --site-dir exports/site-current --out-dir deploy --deploy-root /var/www/html/niu-secretary/airesearch
```


```bash
# 备份
sudo cp /var/www/html/index.html /var/www/html/index.html.bak.YYYYMMDD

# 部署品牌主页
sudo mkdir -p /var/www/html/niu-secretary
sudo cp /home/ubuntu/.openclaw/workspace/niu-secretary/dist/index.html /var/www/html/niu-secretary/index.html
sudo cp /home/ubuntu/.openclaw/workspace/niu-secretary/dist/logo.png /var/www/html/niu-secretary/logo.png

# 部署子模块（示例：塑形馆）
cd /home/ubuntu/.openclaw/workspace/niu-secretary/fitness
npm run build
sudo cp -r dist/* /var/www/html/niu-secretary/fitness/

# 部署 AIResearch 静态站点
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
python -m airesearch.cli write-static-deploy-scripts --site-dir exports/site-current --out-dir deploy --deploy-root /var/www/html/niu-secretary/airesearch
sudo deploy/deploy-airesearch.sh

# 回滚 AIResearch 静态站点
sudo deploy/rollback-airesearch.sh latest
```

---

## 品牌资产清单

| 资产 | 路径 |
|------|------|
| 品牌 SKILL | `/home/ubuntu/.openclaw/workspace/niu-secretary/SKILL.md` |
| 品牌主页源码 | `/home/ubuntu/.openclaw/workspace/niu-secretary/dist/index.html` |
| Logo 原始文件 | `/home/ubuntu/Pictures/image-2.png` |
| 品牌主页 Logo | `/home/ubuntu/.openclaw/workspace/niu-secretary/dist/logo.png` |

---

## 子模块文档

各子模块的详细技术文档请参考对应目录下的 SKILL.md：

- 📰 [新闻社 SKILL.md](news-daily/SKILL.md)
- 🏋️ [塑形馆 SKILL.md](fitness/SKILL.md)
- 📅 [时务局 SKILL.md](schedule/SKILL.md)
- 🎬 [闲趣集 SKILL.md](leisure/SKILL.md)
- 🧠 [AIResearch 研知库 SKILL.md](airesearch/SKILL.md)

---

## 出品信息

- **出品人**：帅锅（三更力争）
- **品牌设计**：牛秘书团队
- **技术协作**：DeepSeek V4 Pro / Claude Opus 4.6
- **基础设施**：OpenClaw
- **科研底座**：paperpipe / papi + AIResearch SQLite ledger
