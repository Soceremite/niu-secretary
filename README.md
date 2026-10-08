# 牛秘书

牛秘书是一个私人 AI 管家 Web 服务矩阵，当前包含品牌主页、新闻社、塑形馆、时务局、闲趣集和 AIResearch 研知库。v2.0 起，项目新增统一 Action Protocol：主页 AI 助手、子网页和未来语音助手都通过同一组 API 读写能力，避免每个页面各自维护一套业务逻辑。

AIResearch 研知库已经从规划项推进到 MVP 可发布状态：本地论文库、候选发现、可审计 ingest、研究事实抽取、知识图谱、跨论文关系、研究报告、静态站点发布、健康检查、备份、刷新脚本和外部静态站点回滚脚本都已具备。

平台化 schema、actions、CLI、cron 和 Web API 参考见
[`docs/airesearch-api.md`](docs/airesearch-api.md)、
[`airesearch/DEVELOPMENT.md`](airesearch/DEVELOPMENT.md) 和
[`airesearch/SKILL.md`](airesearch/SKILL.md)。

## 当前版本

- 当前标签：`v2.1-dev`
- 前端形态：Vue 3 + Vite 主应用，同时保留可独立部署的模块静态资源
- 后端形态：Python 标准库 HTTP API + SQLite
- AIResearch：Python package + SQLite + paperpipe / papi + 静态研究报告站点
- 部署入口：`/niu-secretary/`
- 远程仓库：`git@github.com:Soceremite/niu-secretary.git`

## 功能矩阵

| 模块 | 路径 | 说明 |
|------|------|------|
| 品牌主页 | `/niu-secretary/` | 牛秘书入口、品牌展示、AI 助手 |
| 新闻社 | `/niu-secretary/news/` | 每日新闻简报，按国内、国际、财经、科技、AI 分类 |
| 塑形馆 | `/niu-secretary/fitness/` | 训练、营养、恢复、评估、咨询一体化管理 |
| 时务局 | `/niu-secretary/schedule/` | 日程、提醒、事务抽屉、目标追踪 |
| 闲趣集 | `/niu-secretary/leisure/` | 影视、音乐、播客、小说等休闲推荐 |
| AIResearch 研知库 | `/niu-secretary/airesearch/` | 本地自动科研 RAG、论文知识图谱、事实溯源、研究地图、静态报告站点 |

## v2.0 设计

牛秘书 AI 助手不是单页聊天框，而是统一调度入口：

1. 模型先判断用户意图属于 `fitness`、`schedule`、`news`、`leisure`、`airesearch`、`chat` 或 `unknown`。
2. 服务端按模块选择专用 prompt，生成候选 action。
3. 前端展示可编辑 JSON 参数，用户确认后执行。
4. `/niu-secretary/api/actions/execute` 统一落库。
5. 子网页从统一 API 读取数据，并与本地 IndexedDB 合并展示。

这个内部 Action Protocol 不是 MCP，但按 MCP 思路设计：能力可发现、输入可校验、执行可审计，未来可以再包一层 MCP Server。

## 统一 API

服务文件位于 `server/`：

| 接口 | 说明 |
|------|------|
| `GET /niu-secretary/api/health` | 健康检查 |
| `GET /niu-secretary/api/capabilities` | 能力注册表 |
| `GET /niu-secretary/api/platform/runs` | 读取模块运行记录，支持 `module`、`limit` |
| `GET /niu-secretary/api/platform/ops` | 平台运行中心聚合摘要，支持 `module`、`status`、`requiresReview`、`limit` |
| `GET /niu-secretary/api/platform/events` | 读取模块事件记录，支持 `module`、`eventType`、`requiresReview`、`limit` |
| `GET /niu-secretary/api/platform/today` | 今日跨模块上下文，支持 `date`、`limit`；未传 `date` 时默认当天 |
| `GET /niu-secretary/api/platform/modules` | 模块状态总览，支持 `limit` |
| `GET /niu-secretary/api/platform/cron` | Cron jobs/groups 注册表，不执行任务 |
| `GET /niu-secretary/api/profile` | 读取单个或全部画像，支持 `module` |
| `GET /niu-secretary/api/profile/changes` | 读取画像变更历史，支持 `module`、`limit` |
| `GET /niu-secretary/api/news/search` | 新闻社历史搜索/列表，支持 `q`、`date`、`from`、`to`、`section`、`tag`、`source`、`limit` |
| `GET /niu-secretary/api/news/recommend` | 新闻社今日推荐，支持 `limit` |
| `GET /niu-secretary/api/fitness/summary/today` | 塑形馆今日营养汇总，支持 `date` |
| `GET /niu-secretary/api/fitness/summary/weekly` | 塑形馆七日汇总，支持 `date` |
| `GET /niu-secretary/api/fitness/nutrition` | 塑形馆营养历史，支持 `from`、`to`、`limit` |
| `GET /niu-secretary/api/fitness/workouts` | 塑形馆训练历史，支持 `from`、`to`、`limit` |
| `GET /niu-secretary/api/fitness/body-metrics` | 塑形馆身体指标历史，支持 `from`、`to`、`limit` |
| `GET /niu-secretary/api/fitness/daily-summary` | 塑形馆已保存日汇总，支持 `date` |
| `GET /niu-secretary/api/fitness/recommendations` | 塑形馆推荐历史，支持 `date`、`type`、`limit` |
| `GET /niu-secretary/api/schedule/summary/today` | 时务局当日汇总，支持 `date` |
| `GET /niu-secretary/api/schedule/events` | 时务局日程历史，支持 `from`、`to`、`limit` |
| `GET /niu-secretary/api/schedule/todos` | 时务局待办历史，支持 `from`、`to`、`includeDone`、`limit` |
| `GET /niu-secretary/api/schedule/day-plan` | 时务局已保存日计划，支持 `date` |
| `GET /niu-secretary/api/schedule/day-review` | 时务局已保存日复盘，支持 `date` |
| `GET /niu-secretary/api/schedule/conflicts` | 时务局冲突检测，支持 `date` |
| `GET /niu-secretary/api/schedule/recommend` | 时务局今日建议，支持 `date` |
| `GET /niu-secretary/api/schedule/task-history` | 时务局任务历史，支持 `todoId`、`limit` |
| `GET /niu-secretary/api/leisure/recommend` | 闲趣集推荐，支持 `limit`、`availableMinutes`、`scheduleLoad` |
| `GET /niu-secretary/api/leisure/recommendations` | 闲趣集推荐历史，支持 `date`、`limit` |
| `GET /niu-secretary/api/leisure/items` | 闲趣集条目列表，支持 `category`、`limit` |
| `GET /niu-secretary/api/leisure/history` | 闲趣互动历史，支持 `q`、`category`、`itemId`、`limit` |
| `GET /niu-secretary/api/leisure/profile/suggestions` | 闲趣画像待审核建议，支持 `limit` |
| `GET /niu-secretary/api/airesearch/overview` | 研知库数据库、候选评审、聚类、digest 和发布站点概览，支持 `limit` |
| `GET /niu-secretary/api/airesearch/papers/search` | 研知库论文搜索，支持 `q`、`limit` |
| `POST /niu-secretary/api/assistant/message` | 自然语言转候选动作 |
| `POST /niu-secretary/api/actions/execute` | 执行统一动作 |

第一阶段已实现动作：

- `fitness.nutrition.create`
- `fitness.nutrition.today_summary`
- `fitness.nutrition.list`
- `fitness.nutrition.delete`
- `fitness.nutrition.update`
- `fitness.nutrition.recognize_photo`
- `fitness.workout.create`
- `fitness.workout.list`
- `fitness.workout.update`
- `fitness.workout.delete`
- `fitness.body_metric.create`
- `fitness.body_metric.list`
- `fitness.body_metric.update`
- `fitness.body_metric.delete`
- `fitness.summary.today`
- `fitness.summary.weekly`
- `fitness.daily_summary.get`
- `fitness.recommend.meal`
- `fitness.recommend.workout`
- `fitness.recommendations.list`
- `schedule.event.create`
- `schedule.event.list`
- `schedule.event.delete`
- `schedule.event.update`
- `schedule.todo.create`
- `schedule.todo.list`
- `schedule.todo.toggle`
- `schedule.todo.complete`
- `schedule.todo.reschedule`
- `schedule.todo.delete`
- `schedule.todo.update`
- `schedule.today_summary`
- `schedule.conflicts.detect`
- `schedule.day.plan`
- `schedule.day.review`
- `schedule.day_plan.get`
- `schedule.day_review.get`
- `schedule.task_history.list`
- `profile.get`
- `profile.update`
- `profile.reset`
- `profile.changes`
- `fitness.recommend`
- `schedule.recommend`
- `news.search`
- `news.recommend`
- `news.validate-sources`
- `news.validate-keypoints`
- `news.audit-images`
- `news.topic.queue-research`
- `leisure.profile.update`
- `leisure.item.save`
- `leisure.item.dismiss`
- `leisure.item.rate`
- `leisure.item.update`
- `leisure.item.delete`
- `leisure.history.search`
- `leisure.recommendations.list`
- `leisure.items.list`
- `leisure.profile.suggestions`
- `leisure.profile.apply_suggestion`
- `airesearch.overview`
- `airesearch.paper.search`
- `airesearch.candidate.discover`
- `airesearch.paper.ingest`
- `airesearch.paper.review`
- `airesearch.cluster.generate`
- `airesearch.digest.generate`
- `airesearch.site.publish`
- `airesearch.queue.add`
- `platform.runs.list`
- `platform.events.list`
- `platform.today.context`
- `platform.modules.status`
- `platform.ops.center`
- `platform.review.mark`
- `platform.cron.registry`

v2.1-dev 新增公共审计底座：

| 表 | 说明 |
|------|------|
| `module_runs` | 记录 CLI、cron、API、assistant、web 触发的模块运行 |
| `module_events` | 记录跨模块事件、校验结果、归档和搜索等可追溯事件 |
| `assistant_actions` | 记录 AI 或 API 触发的 action 输入、状态、结果和错误 |
| `model_calls` | 记录模型调用摘要、用途、模型、状态和延迟 |

v2.1-dev 同时补齐了模块业务表：

| 表 | 说明 |
|------|------|
| `fitness_nutrition_logs` | 塑形馆饮食日志 |
| `fitness_workout_logs` | 塑形馆训练日志 |
| `fitness_body_metrics` | 塑形馆体重、体脂、腰围等指标 |
| `fitness_daily_summaries` | 塑形馆每日/每周可重跑汇总快照 |
| `fitness_food_candidates` | 塑形馆餐食候选扩展表 |
| `fitness_recommendations` | 塑形馆餐食和训练推荐历史 |
| `schedule_events` | 时务局日程事件 |
| `schedule_todos` | 时务局待办事项 |
| `schedule_day_plans` | 时务局日计划派生结果 |
| `schedule_day_reviews` | 时务局日复盘 |
| `schedule_focus_blocks` | 时务局专注块扩展表 |
| `schedule_reminders` | 时务局提醒扩展表 |
| `schedule_task_history` | 时务局待办完成、重开、改期历史 |
| `leisure_items` | 闲趣集候选和反馈条目索引 |
| `leisure_interactions` | 闲趣集收藏、忽略、评分和历史反馈 |
| `leisure_sessions` | 闲趣集观看/收听会话扩展表 |
| `leisure_mood_logs` | 闲趣集心情日志扩展表 |
| `leisure_recommendations` | 闲趣集推荐历史和上下文 |
| `leisure_sources` | 闲趣集候选来源扩展表 |

公共 Python 层位于 `niu_core/`：

| 文件 | 说明 |
|------|------|
| `db.py` | SQLite 连接、迁移和事务包装 |
| `audit.py` | module run、event、assistant action、model call 审计包装 |
| `cli.py` | CLI 公共 runner，自动写 `module_runs` |
| `pipeline.py` | ingest/normalize/validate/store/export/publish 风格的轻量步骤编排 |
| `validators.py` | 通用日期、时间、文本、枚举和数值校验 |
| `profiles.py` | 用户画像读写包装 |
| `exporters.py` | JSON 读写导出工具 |
| `cron.py` | 定时任务入口包装，自动写 `module_runs` |
| `llm.py` | 模型调用摘要审计入口 |

成功的 Action 响应会在原有字段外附加 `actionId`、`auditId`、`warnings`，旧调用方可以继续读取原字段。
`confirmByDefault: true` 的高风险 action 在 web/assistant/API 显式入口中需要
`context.confirmed: true` 才会执行；未确认时会返回 `confirmation_required`，并把
`assistant_actions` 与 `module_runs` 标记为 `blocked`。CLI/cron 是显式运维入口，
默认视为已授权。

## 目录结构

```text
.
├── config/                 # 本地环境变量模板，不含真实密钥
├── dist/                   # 牛秘书品牌主页静态文件
├── docs/                   # 设计文档和实施计划
├── airesearch/             # 牛秘书 AIResearch 研知库（本地自动科研 RAG + 知识图谱）
├── fitness/                # 牛秘书塑形馆
├── leisure/                # 牛秘书闲趣集
├── news-daily/             # 牛秘书新闻社
├── niu_core/               # 统一数据库、审计、CLI、pipeline、校验、导出和 cron 公共层
├── niu_secretary/          # 统一模块 CLI
├── schedule/               # 牛秘书时务局
├── server/                 # v2.0 Action Protocol Python API
└── SKILL.md                # 品牌、设计语言、协议理念说明
```

## GitHub 源码与本地数据边界

GitHub 的 `main` 分支发布源码、测试、文档、部署模板和前端源代码。论文库、生成站点和个人运行数据留在部署机器，不作为源码依赖提交：

- `airesearch/.env`、`airesearch/data/`、`airesearch/exports/`、`airesearch/blog-assets/`
- `airesearch/logs/`、`airesearch/manifests/`、`backups/`、`.runtime-logs/`
- `fitness/data/`、`leisure/dist/data/` 以及本地生成的图片审核文件
- 根目录 `data/`、`logs/`、`manifests/` 和所有真实 `.env`、SQLite 数据库

这些目录被 `.gitignore` 忽略，服务器上的现有文件不会因源码同步被删除。新机器克隆后，需要先准备 `airesearch/.env`，再从论文 PDF 重新生成 layout、公式、表格、博客和 `exports/` 发布目录；需要恢复个人数据时使用独立备份，不要把备份直接加入 Git。

## 本地配置

真实 API Key 不进入 Git 仓库。仓库只保存模板；AIResearch 的模型、代理和 OCR 配置统一从被忽略的 `airesearch/.env` 读取：

| 模板 | 真实配置路径 | 用途 |
|------|------|------|
| `config/niu-secretary-api.env.example` | `/etc/niu-secretary-api.env` | 首页 AI 助手、Action Protocol、SQLite |
| `config/niu-fitness-api.env.example` | `/etc/niu-fitness-api.env` | 塑形馆图片识别、多模态模型 |

迁移到新机器时：

```bash
sudo cp config/niu-secretary-api.env.example /etc/niu-secretary-api.env
sudo cp config/niu-fitness-api.env.example /etc/niu-fitness-api.env
sudo chmod 600 /etc/niu-secretary-api.env /etc/niu-fitness-api.env
```

然后编辑 `/etc/*.env`，填入本机真实 API Key。

准备 AIResearch 环境：

```bash
cd airesearch
cp .env.example .env
chmod 600 .env
# 研知库专属变量放 airesearch/.env（AIRESEARCH_EMBEDDING_API_KEY / SERPAPI_API_KEY 等）
# 共享渠道 key 放仓库根 config/.env（OPENCODE_SUBSCRIPTION_KEY / NIU_GATEWAY_API_KEY / DEEPSEEK_API_KEY）
# ⚠️ 路由（模型/端点）不要写进 env —— 唯一来源是 config/models.yaml，
#    在管理台「AI 渠道」页改即时生效；env 里残留的显式路由变量会压过 yaml（改 yaml 不生效的根因）
source ./activate.sh
```

公式 OCR 走 `config/models.yaml` 的 `formula_ocr` 路由（当前 `opencode_go/deepseek-v4.1-flash`），不再是写死的 `gpt-5.6-luna`。

生产 API 启动脚本会在启动 Python 服务前加载同一个 `airesearch/.env`，管理员账号、密码和会话密钥仍以 `/etc/niu-secretary-api.env` 为准。

## 本地运行

启动牛秘书统一 API：

```bash
NIU_SECRETARY_API_PORT=5188 bash scripts/run-niu-secretary-api.sh
```

启动塑形馆图片识别 API：

```bash
cd fitness
FITNESS_API_PORT=5177 python3 server/nutrition_api.py
```

构建塑形馆静态文件：

```bash
cd fitness
npm run build
```

启动 AIResearch 本地环境：

```bash
cd airesearch
source ./activate.sh
python -m airesearch.cli health-check --site-dir exports/site-current
python -m airesearch.cli serve-report-site --dir exports/site-current --host 127.0.0.1 --port 8765
```

统一模块 CLI：

```bash
python -m niu_secretary.cli news validate
python -m niu_secretary.cli news validate-sources
python -m niu_secretary.cli news validate-keypoints
python -m niu_secretary.cli news audit-images
python -m niu_secretary.cli news search --q "AI Agent" --section ai --tag 大模型 --limit 10
python -m niu_secretary.cli news extract-json
python -m niu_secretary.cli news crawl-images
python -m niu_secretary.cli news review-images
python -m niu_secretary.cli news update-sections
python -m niu_secretary.cli news archive
python -m niu_secretary.cli news publish
python -m niu_secretary.cli news run-daily
python -m niu_secretary.cli news ingest
python -m niu_secretary.cli news derive
python -m niu_secretary.cli news export
python -m niu_secretary.cli fitness validate
python -m niu_secretary.cli fitness ingest
python -m niu_secretary.cli fitness derive
python -m niu_secretary.cli fitness export
python -m niu_secretary.cli fitness publish
python -m niu_secretary.cli fitness run-daily
python -m niu_secretary.cli fitness summarize-day --date today
python -m niu_secretary.cli fitness summarize-week --date 2026-06-14
python -m niu_secretary.cli fitness recommend-meal --date 2026-06-14
python -m niu_secretary.cli fitness recommend-workout --date 2026-06-14
python -m niu_secretary.cli fitness list-nutrition --limit 20
python -m niu_secretary.cli fitness list-workouts --from 2026-06-01 --to 2026-06-14
python -m niu_secretary.cli fitness list-body-metrics --limit 20
python -m niu_secretary.cli fitness daily-summary --date today
python -m niu_secretary.cli fitness list-recommendations --date 2026-06-14 --type meal
python -m niu_secretary.cli schedule validate
python -m niu_secretary.cli schedule ingest
python -m niu_secretary.cli schedule derive
python -m niu_secretary.cli schedule export
python -m niu_secretary.cli schedule publish
python -m niu_secretary.cli schedule run-daily
python -m niu_secretary.cli schedule detect-conflicts --date 2026-06-14
python -m niu_secretary.cli schedule plan-day --date 2026-06-14
python -m niu_secretary.cli schedule review-day --date 2026-06-14 --completed 3 --note "复盘"
python -m niu_secretary.cli schedule list-events --limit 20
python -m niu_secretary.cli schedule list-todos --no-include-done --limit 20
python -m niu_secretary.cli schedule day-plan --date today
python -m niu_secretary.cli schedule day-review --date today
python -m niu_secretary.cli schedule task-history --limit 20
python -m niu_secretary.cli schedule rollover-todos
python -m niu_secretary.cli leisure validate
python -m niu_secretary.cli leisure ingest
python -m niu_secretary.cli leisure derive
python -m niu_secretary.cli leisure publish
python -m niu_secretary.cli leisure run-daily
python -m niu_secretary.cli leisure recommend --mood relaxed --minutes 60 --limit 2
python -m niu_secretary.cli leisure recommend-daily --mood relaxed --minutes 60 --limit 2
python -m niu_secretary.cli leisure history-search --q "科幻" --limit 10
python -m niu_secretary.cli leisure list-items --category movie --limit 20
python -m niu_secretary.cli leisure list-recommendations --limit 20
python -m niu_secretary.cli leisure export
python -m niu_secretary.cli airesearch health-check
python -m niu_secretary.cli airesearch validate
python -m niu_secretary.cli airesearch derive
python -m niu_secretary.cli airesearch export
python -m niu_secretary.cli airesearch run-daily
python -m niu_secretary.cli airesearch paper-search --q "attention" --limit 5
python -m niu_secretary.cli airesearch refresh-weekly
python -m niu_secretary.cli platform health-check
python -m niu_secretary.cli platform derive
python -m niu_secretary.cli platform export
python -m niu_secretary.cli platform publish
python -m niu_secretary.cli platform run-daily
python -m niu_secretary.cli platform today --date today --limit 5
python -m niu_secretary.cli platform modules --limit 1
```

这些命令都会写入 `module_runs`；新闻社校验、搜索和归档，以及新增模块动作产生的关键状态变化会写入 `module_events`。

统一 cron 入口只调用上述 CLI，不绕过模块校验：

```bash
python -m niu_secretary.cron fitness.summarize-day
python -m niu_secretary.cron platform.run-daily
python -m niu_secretary.cron list
python -m niu_secretary.cron daily --keep-going
python -m niu_secretary.cron weekly
```

`cron list` 会输出机器可读的 jobs/groups 注册表，但不执行任务。crontab 示例位于
`config/niu-secretary-crontab.example`。它不会自动安装，需要人工确认路径、Python 和日志位置后再启用。

审计和历史搜索也可以通过统一 Action API 调用：

```json
{"action":"platform.runs.list","input":{"module":"news","limit":20}}
{"action":"platform.events.list","input":{"module":"news","eventType":"search","limit":20}}
{"action":"news.search","input":{"q":"AI","section":"ai","tag":"大模型","limit":10}}
{"action":"news.validate-sources","input":{}}
{"action":"news.validate-keypoints","input":{}}
{"action":"news.audit-images","input":{}}
{"action":"fitness.summary.today","input":{"date":"2026-06-14"}}
{"action":"fitness.summary.weekly","input":{"date":"2026-06-14"}}
{"action":"fitness.recommend.workout","input":{"date":"2026-06-14"}}
{"action":"fitness.nutrition.update","input":{"id":"nut_xxx","calories":360}}
{"action":"fitness.workout.delete","input":{"id":"wrk_xxx"}}
{"action":"schedule.conflicts.detect","input":{"date":"2026-06-14"}}
{"action":"schedule.event.update","input":{"id":"evt_xxx","time":"10:00","note":"延后"}}
{"action":"schedule.todo.update","input":{"id":"todo_xxx","priority":"high"}}
{"action":"schedule.todo.reschedule","input":{"id":"todo_xxx","date":"2026-06-15"}}
{"action":"leisure.recommend","input":{"limit":2}}
{"action":"leisure.history.search","input":{"q":"科幻","limit":10}}
{"action":"leisure.item.update","input":{"itemId":"movie_xxx","title":"修正后的标题"}}
{"action":"leisure.item.delete","input":{"itemId":"movie_xxx"}}
{"action":"airesearch.overview","input":{"limit":3}}
{"action":"airesearch.paper.search","input":{"q":"attention","limit":5}}
{"action":"airesearch.queue.add","input":{"title":"Agent memory paper","note":"follow up"}}
{"action":"news.topic.queue-research","input":{"topic":"Agent memory","note":"from news"}}
{"action":"platform.today.context","input":{"date":"2026-06-14","limit":5}}
{"action":"platform.modules.status","input":{"limit":1}}
{"action":"platform.ops.center","input":{"module":"fitness","status":"passed","limit":12}}
{"action":"platform.review.mark","input":{"eventId":"evtlog_xxx","status":"handled","note":"确认完成"}}
{"action":"profile.change.review","input":{"changeId":"pch_xxx","note":"确认无误"}}
{"action":"profile.change.revert","input":{"changeId":"pch_xxx","note":"恢复到变更前"}}
{"action":"platform.cron.registry","input":{}}
```

Web UI 也可以用只读 GET 路由读取同一套 action 结果：

```bash
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/platform/runs?limit=10'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/platform/today?date=2026-06-14&limit=5'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/platform/today?limit=5'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/platform/modules?limit=1'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/platform/ops?module=fitness&status=passed&limit=12'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/platform/cron'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/news/search?q=AI&limit=2'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/fitness/recommendations?date=2026-06-14&type=meal&limit=2'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/schedule/task-history?limit=5'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/leisure/recommend?limit=1'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/leisure/recommendations?limit=2'
curl --noproxy '*' 'http://127.0.0.1:5188/niu-secretary/api/leisure/profile/suggestions?limit=5'
```

首页 `dist/index.html` 现在包含平台运行区块，直接读取 `platform/ops` 和
`platform/today`。运行中心会聚合模块状态、运行记录、审计事件、统一待办、助手动作、
模型调用和画像变更，并支持按模块、状态和审核状态筛选。`platform.ops.center`
会额外返回 `pendingWorkItems`，把待审核模块事件、闲趣画像建议和待处理画像变更收拢成
一个可操作队列；首页可直接对普通审核项标记处理，对画像变更执行处理/回滚，也可应用闲趣画像建议。
普通审核项通过 `platform.review.mark` 追加处理审计事件后会从待办队列移除。画像变更可通过
`profile.change.review` 标记为已处理，也可通过 `profile.change.revert`
把单个字段恢复到变更前的旧值；两类处理都会写入模块审计事件。
同一区块会并发读取 `airesearch.overview`，展示研知库论文、事实、候选、聚类、digest
和发布站点状态；该读取失败时只影响研知库面板，不阻断其它平台状态。研知库面板还可直接通过
`/niu-secretary/api/airesearch/papers/search` 检索本地论文库，搜索请求保持只读上下文。
`platform.today.context`
会把时务局日程负载转换为闲趣集的 `availableMinutes`，让忙碌日优先推荐短内容。
新闻社、塑形馆、时务局和闲趣集首页同时接入共享状态组件
`/niu-secretary/dist/platform-widget.js`；每个页面只声明自己的
`data-platform-module`，组件用只读 `platform/ops` 展示该模块的待审核、最近运行、
审计事件和模型调用摘要。
同一上下文也会把日程负载传给塑形馆训练建议，忙碌日降级为短训练/恢复建议；
高训练负荷会以 `fitnessLoad`/`recoveryRecommended` 传给闲趣集，优先偏向轻量恢复内容。
闲趣集分类详情页的收藏、忽略和评分优先调用统一 Action API，失败时只写入离线缓存；
成功反馈会生成待审核画像建议。Web 首页通过
`leisure/profile/suggestions` 展示建议，并在用户确认后调用
`leisure.profile.apply_suggestion` 应用到画像，字段变更仍写入 `profile_changes`。
新闻社推荐会合并研知库画像中的 `topics`/`keywords`，近期研究关注会提升相关新闻排序；
新闻主题可以通过 `news.topic.queue-research` 写入研知库候选队列，该写操作默认需要确认。
首页今日上下文会把推荐新闻直接暴露为可确认按钮，确认后进入研知库候选和统一待办队列。
`python -m niu_secretary.cli platform export` 会生成 `exports/niu-secretary/platform.json`，
用于静态 UI 或外部工具读取统一模块状态、今日上下文、运行记录、事件、画像摘要和模块业务快照。
`snapshots` 字段目前包含塑形馆当日总结/推荐、时务局日计划/日复盘/任务历史、闲趣集条目/
反馈历史/推荐历史，以及研知库数据库、候选评审、聚类、digest 和发布站点概览。

常用 AIResearch 刷新与发布：

```bash
python -m niu_secretary.cli airesearch overview --limit 5
cd airesearch
python -m airesearch.cli run-launch-refresh --limit-per-profile 50 --select-limit 10 --min-score 0.60 --out-dir exports/mvp-current --site-dir exports/site-current --progress
python -m airesearch.cli publish-static-site --source-dir exports/mvp-current/bundle --out-dir exports/site-current
python -m airesearch.cli write-static-host-config --site-dir exports/site-current --out-dir deploy --base-path /niu-secretary/airesearch/ --deploy-root /var/www/html/niu-secretary/airesearch
python -m airesearch.cli write-static-deploy-scripts --site-dir exports/site-current --out-dir deploy --deploy-root /var/www/html/niu-secretary/airesearch
```

统一 Action 入口会为 AIResearch 桥接命令补齐必填参数：候选发现默认使用
`multimodal_foundation_models` 和 `limit=20`，候选评审、聚类和 digest 默认写入
`airesearch/exports/mvp-current`，供概览 API 和静态发布继续读取。

## 部署

线上静态目录：

```text
/var/www/html/niu-secretary/
```

部署品牌主页：

```bash
sudo cp dist/index.html dist/assistant.js /var/www/html/niu-secretary/
```

部署 Vue 版牛秘书主应用：

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary
npm --prefix web run build
sudo deploy/deploy-vue-web.sh
```

nginx 需要把 Vue history 深链接回退到主入口。可将
`deploy/niu-secretary-vue.nginx.conf` 放入现有 `niu-secretary` server block，并移除旧的
`/niu-secretary/fitness/`、`/schedule/`、`/leisure/`、`/news/`、`/airesearch/`
模块目录 location；否则这些旧 location 会优先命中，Vue 模块页不会上线。

```nginx
location /niu-secretary/airesearch/admin/ {
    proxy_pass http://127.0.0.1:8791/niu-secretary/airesearch/admin/;
}

location ^~ /niu-secretary/assets/ {
    alias /var/www/html/niu-secretary/assets/;
    try_files $uri =404;
}

location ^~ /niu-secretary/ {
    root /var/www/html;
    try_files $uri /niu-secretary/index.html;
}
```

注意：API 代理、`/niu-secretary/fitness/api/` 和 `/niu-secretary/airesearch/admin/` 必须放在
上述 SPA fallback 之前。Vue 部署脚本不会 `--delete` 旧的 `fitness/`、`schedule/`、
`leisure/`、`news/`、`airesearch/` 静态目录；这些目录保留为直接文件路径回退，例如
`/niu-secretary/fitness/index.html`。Vue 回滚：

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary
sudo deploy/rollback-vue-web.sh latest
```

部署塑形馆：

```bash
cd fitness
npm run build
sudo cp -r dist/. /var/www/html/niu-secretary/fitness/
```

部署 AIResearch 静态站点：

```bash
cd airesearch
python -m airesearch.cli write-static-deploy-scripts --site-dir exports/site-current --out-dir deploy --deploy-root /var/www/html/niu-secretary/airesearch
sudo deploy/deploy-airesearch.sh
```

回滚 AIResearch 外部静态站点：

```bash
cd airesearch
sudo deploy/rollback-airesearch.sh latest
```

重启服务：

```bash
sudo systemctl restart niu-secretary-api.service
sudo systemctl restart niu-fitness-api.service
```

## 验证

```bash
python3 -m unittest server.test_niu_secretary_api
python3 -m unittest server.test_platform_audit
cd web && npm run build && npm run verify:routes && npm run verify:admin-smoke && npm run verify:fitness-smoke && npm run verify:schedule-smoke && npm run verify:leisure-smoke && npm run verify:news-smoke && npm run verify:airesearch-smoke
python3 -m py_compile server/actions.py server/assistant.py server/capabilities.py server/niu_secretary_api.py server/store.py
python3 -m py_compile niu_core/*.py niu_secretary/*.py server/action_handlers.py
python3 -m niu_secretary.cli news validate
python3 -m niu_secretary.cli news validate-sources
python3 -m niu_secretary.cli news validate-keypoints
python3 -m niu_secretary.cli news audit-images
python3 -m niu_secretary.cli news search --q AI --limit 2
python3 -m niu_secretary.cli fitness validate
python3 -m niu_secretary.cli fitness summarize-day --date today
python3 -m niu_secretary.cli fitness summarize-week --date 2026-06-14
python3 -m niu_secretary.cli fitness recommend-workout --date 2026-06-14
python3 -m niu_secretary.cli schedule validate
python3 -m niu_secretary.cli schedule detect-conflicts --date 2026-06-14
python3 -m niu_secretary.cli schedule rollover-todos
python3 -m niu_secretary.cli leisure validate
python3 -m niu_secretary.cli leisure recommend --mood relaxed --minutes 60 --limit 1
python3 -m niu_secretary.cli leisure recommend-daily --mood relaxed --minutes 60 --limit 1
python3 -m niu_secretary.cli leisure history-search --q AI --limit 2
python3 -m niu_secretary.cli leisure export
python3 -m niu_secretary.cli airesearch health-check
python3 -m niu_secretary.cli airesearch paper-search --q attention --limit 2
python3 -m niu_secretary.cli airesearch refresh-weekly
python3 -m niu_secretary.cli platform health-check
python3 -m niu_secretary.cli platform export
python3 -m niu_secretary.cli platform run-daily
python3 -m niu_secretary.cli platform today --date today --limit 1
python3 -m niu_secretary.cli platform modules --limit 1
python3 -m niu_secretary.cron fitness.summarize-day
python3 - <<'PY'
from server.actions import execute_action
print(execute_action("platform.runs.list", {"limit": 2})["count"])
print(execute_action("news.search", {"q": "AI", "limit": 2})["count"])
print(execute_action("airesearch.paper.search", {"q": "attention", "limit": 2})["count"])
PY
NIU_SECRETARY_API_PORT=5199 python3 -m server.niu_secretary_api &
API_PID=$!
curl --noproxy '*' -s 'http://127.0.0.1:5199/niu-secretary/api/news/search?q=AI&limit=1'
kill "$API_PID"
node --check dist/assistant.js
node --check fitness/dist/js/features/nutrition.js
cd airesearch && .venv/bin/python -m pytest -q
curl --noproxy '*' -s http://127.0.0.1/niu-secretary/api/health
```

## 安全约定

- 不提交真实 `.env`、API Key、数据库文件和服务端私有配置。
- `*.env` 默认被 `.gitignore` 忽略，只允许提交 `*.env.example`。
- **提交闸门（2026-09-16）**：`scripts/scan-secrets.py` 三道防线 —— ①隐私文件名 ②密钥形态 ③**线上真实密钥值反查**（从 `config/.env` / `airesearch/.env` / `/etc/niu-secretary-api.env` 读当前有效值比对，零假阳性）。已装成 git 钩子：`pre-commit` 扫暂存区、`pre-push` 扫全历史。被拦时改成 env 引用，或在行尾写 `secrets-scan:ignore` 并注明原因。
- ⚠️ 换机器 / 重新 clone 后要跑一次：`python3 scripts/scan-secrets.py --install-hook`（钩子存在 `.git/hooks/`，不进版本库）。
- ⚠️ **不要用 `git -c core.hooksPath=/dev/null` 提交** —— 它会把这道闸门（以及任何别人的钩子）静默关掉。
- **凭据已经进了对话/仓库怎么办**：本机用 `scripts/scrub-secret-trace.py --rclone <远端名>` 抹落点（Hermes 消息库含 `reasoning` 列 / 两套 FTS 影子索引 / WAL / `agent.log` / `.hermes_history`）；但**轮换密钥才是唯一真修复** —— 提示词那条副本收不回来。方法论见 skill `credential-hygiene`。
- **数据备份**：研知库库（650MB）曾长期单副本 → `scripts/backup-airesearch-db.sh`，ubuntu crontab 每日 03:20 本地 + 周日 WebDAV，恢复演练已验证（38 张表计数与线上库一致）。方法论见 skill `service-data-backup`。
- AI 生成的 action 必须先让用户确认，再写入数据库。
- 服务端执行 action 前会做字段清洗、范围限制和动作白名单校验。
- AIResearch 不提交真实 `.env`、API Key、SQLite 数据库、论文数据、生成站点、图片产物、日志或 manifest；这些内容必须在本地生成或从独立备份恢复。
- 外部静态站点部署前先生成快照；需要回滚时使用 `rollback-airesearch.sh latest` 或指定快照名。回滚快照只保留最新 1 份（`SNAPSHOT_KEEP` 默认 1，可用 env 覆盖）。

## Git 版本

```bash
git log --oneline -5
git tag --list "v*"
```

当前 v2.0 关键提交：

- `63f95ad feat: add niu secretary action protocol`
- `87de6a9 feat: route assistant actions through model`
- `9b0002e docs: document assistant config and protocol`
