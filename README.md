# 牛秘书

牛秘书是一个私人 AI 管家 Web 服务矩阵，当前包含品牌主页、新闻社、塑形馆、时务局、闲趣集和 AIResearch 研知库。v2.0 起，项目新增统一 Action Protocol：主页 AI 助手、子网页和未来语音助手都通过同一组 API 读写能力，避免每个页面各自维护一套业务逻辑。

AIResearch 研知库已经从规划项推进到 MVP 可发布状态：本地论文库、候选发现、可审计 ingest、研究事实抽取、知识图谱、跨论文关系、研究报告、静态站点发布、健康检查、备份、刷新脚本和外部静态站点回滚脚本都已具备。

## 当前版本

- 当前标签：`v2.1-dev`
- 前端形态：静态 HTML/CSS/JavaScript
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
| `POST /niu-secretary/api/assistant/message` | 自然语言转候选动作 |
| `POST /niu-secretary/api/actions/execute` | 执行统一动作 |

第一阶段已实现动作：

- `fitness.nutrition.create`
- `fitness.nutrition.today_summary`
- `fitness.nutrition.list`
- `fitness.nutrition.delete`
- `schedule.event.create`
- `schedule.event.list`
- `schedule.event.delete`
- `schedule.todo.create`
- `schedule.todo.list`
- `schedule.todo.toggle`
- `schedule.todo.delete`
- `schedule.today_summary`
- `profile.get`
- `profile.update`
- `profile.reset`
- `profile.changes`
- `fitness.recommend`
- `schedule.recommend`

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
├── schedule/               # 牛秘书时务局
├── server/                 # v2.0 Action Protocol Python API
└── SKILL.md                # 品牌、设计语言、协议理念说明
```

## 本地配置

真实 API Key 不进入 Git 仓库。仓库只保存模板：

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

## 本地运行

启动牛秘书统一 API：

```bash
NIU_SECRETARY_API_PORT=5188 python3 server/niu_secretary_api.py
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

常用 AIResearch 刷新与发布：

```bash
cd airesearch
python -m airesearch.cli run-launch-refresh --limit-per-profile 50 --select-limit 10 --min-score 0.60 --out-dir exports/mvp-current --site-dir exports/site-current --progress
python -m airesearch.cli publish-static-site --source-dir exports/mvp-current/bundle --out-dir exports/site-current
python -m airesearch.cli write-static-host-config --site-dir exports/site-current --out-dir deploy --base-path /niu-secretary/airesearch/ --deploy-root /var/www/html/niu-secretary/airesearch
python -m airesearch.cli write-static-deploy-scripts --site-dir exports/site-current --out-dir deploy --deploy-root /var/www/html/niu-secretary/airesearch
```

## 部署

线上静态目录：

```text
/var/www/html/niu-secretary/
```

部署品牌主页：

```bash
sudo cp dist/index.html dist/assistant.js /var/www/html/niu-secretary/
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
python3 -m py_compile server/actions.py server/assistant.py server/capabilities.py server/niu_secretary_api.py server/store.py
node --check dist/assistant.js
node --check fitness/dist/js/features/nutrition.js
cd airesearch && .venv/bin/python -m pytest -q
curl --noproxy '*' -s http://127.0.0.1/niu-secretary/api/health
```

## 安全约定

- 不提交真实 `.env`、API Key、数据库文件和服务端私有配置。
- `*.env` 默认被 `.gitignore` 忽略，只允许提交 `*.env.example`。
- AI 生成的 action 必须先让用户确认，再写入数据库。
- 服务端执行 action 前会做字段清洗、范围限制和动作白名单校验。
- AIResearch 不提交真实 `.env`、API Key、SQLite 数据库和 `.venv`；可提交源码、测试、文档、静态发布产物和可审计 manifest。
- 外部静态站点部署前先生成快照；需要回滚时使用 `rollback-airesearch.sh latest` 或指定快照名。

## Git 版本

```bash
git log --oneline -5
git tag --list "v*"
```

当前 v2.0 关键提交：

- `63f95ad feat: add niu secretary action protocol`
- `87de6a9 feat: route assistant actions through model`
- `9b0002e docs: document assistant config and protocol`
