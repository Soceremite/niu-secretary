# 牛秘书 2.0 统一 Action Protocol 设计

## 背景

牛秘书当前由品牌主页和四个子网页组成：新闻社、塑形馆、时务局、闲趣集。各子网页已经具备独立能力，但能力入口和数据层不统一：

- 塑形馆已有 Python API、图片识别能力和 IndexedDB 数据层。
- 时务局主要通过浏览器 localStorage 保存日程、待办、目标等数据。
- 新闻社和闲趣集主要是静态内容与本地数据展示。
- 品牌主页目前只是入口页，没有可执行的 AI 助手。

牛秘书 2.0 的目标是让主页 AI 助手、语音助手、各子网页和未来 App 调用同一组能力，而不是每个页面各写一套业务逻辑。

## 目标

第一阶段建设“牛秘书内部 Action Protocol”，并为未来 MCP Server 留出适配层。

用户可以在主页 AI 助手里输入或说出自然语言，例如“我今天吃了牛肉面”“明天下午三点提醒我开会”“这张饭图帮我记到塑形馆”，系统会解析为统一动作并写入对应模块。

同一个动作也必须可被具体网页调用。例如塑形馆网页保存餐食、主页 AI 记录餐食、图片识别后确认餐食，都调用 `fitness.nutrition.create`。

## 非目标

- 第一阶段不做完整移动 App。
- 第一阶段不强制实现标准 MCP 协议服务，只设计可被 MCP 包装的内部协议。
- 第一阶段不把所有历史浏览器本地数据自动迁移到服务器；只为新动作建立统一数据入口，并提供后续迁移路径。
- 第一阶段不实现长期记忆、主动推送、复杂权限体系。

## 推荐架构

采用三层结构：

```text
主页 AI 助手 / 语音助手 / 子网页 / 未来 App
  ↓
牛秘书统一 HTTP API
  ↓
Action Registry + Domain Services
  ↓
统一服务器数据层 + 必要时同步到浏览器本地缓存
```

未来 MCP 适配层位于统一 HTTP API 之上：

```text
MCP Client / 外部 Agent
  ↓
牛秘书 MCP Server
  ↓
牛秘书统一 HTTP API
```

这样可以先满足网页和主页助手使用，同时避免被 MCP 绑定；后续只需要把同一批 action 暴露为 MCP tools。

## 公共接口

### 1. 能力注册表

`GET /niu-secretary/api/capabilities`

返回当前可用能力、输入字段、输出字段、权限级别和调用示例。

示例：

```json
{
  "version": "2026-05-29",
  "capabilities": [
    {
      "name": "fitness.nutrition.create",
      "title": "记录一餐",
      "module": "fitness",
      "description": "写入塑形馆营养日志",
      "inputSchema": {
        "type": "object",
        "required": ["food", "date"],
        "properties": {
          "food": { "type": "string" },
          "date": { "type": "string", "format": "date" },
          "calories": { "type": "number" },
          "proteinG": { "type": "number" },
          "carbsG": { "type": "number" },
          "fatG": { "type": "number" },
          "source": { "type": "string" }
        }
      }
    }
  ]
}
```

### 2. 统一动作执行

`POST /niu-secretary/api/actions/execute`

请求：

```json
{
  "action": "fitness.nutrition.create",
  "input": {
    "food": "牛肉面",
    "date": "2026-05-29",
    "calories": 650,
    "proteinG": 28,
    "carbsG": 82,
    "fatG": 20,
    "source": "assistant"
  },
  "context": {
    "client": "home-assistant",
    "timezone": "Asia/Shanghai"
  }
}
```

响应：

```json
{
  "ok": true,
  "action": "fitness.nutrition.create",
  "record": {
    "id": "nut_20260529_000001",
    "createdAt": "2026-05-29T14:30:00+08:00",
    "syncStatus": "synced"
  },
  "message": "已记录到塑形馆营养。"
}
```

### 3. 主页 AI 助手消息

`POST /niu-secretary/api/assistant/message`

请求：

```json
{
  "text": "我今天吃了牛肉面",
  "attachments": [],
  "context": {
    "client": "home",
    "timezone": "Asia/Shanghai"
  }
}
```

响应包含自然语言回复、解析出的动作、是否需要用户确认。

```json
{
  "reply": "我估算这碗牛肉面约 650 千卡。要记到今天的营养日志吗？",
  "intent": "record_meal",
  "proposedActions": [
    {
      "action": "fitness.nutrition.create",
      "input": {
        "food": "牛肉面",
        "date": "2026-05-29",
        "calories": 650,
        "proteinG": 28,
        "carbsG": 82,
        "fatG": 20,
        "source": "assistant-estimate"
      },
      "requiresConfirmation": true
    }
  ]
}
```

### 4. 图片识别能力

保留现有塑形馆图片识别接口，但挂到统一动作中：

- 现有接口：`POST /niu-secretary/fitness/api/agent/nutrition-recognize`
- 统一动作：`fitness.nutrition.recognize_photo`

主页 AI 上传餐食图时调用统一动作；塑形馆页面可以继续直接调用现有接口，后续再切到统一动作接口。

## 第一阶段动作清单

### Fitness

- `fitness.nutrition.create`：记录一餐。
- `fitness.nutrition.recognize_photo`：识别图片餐食并返回可编辑估算。
- `fitness.nutrition.today_summary`：读取今日营养汇总。
- `fitness.training.create_log`：记录训练。
- `fitness.recovery.create_log`：记录恢复状态。

### Schedule

- `schedule.event.create`：创建日程事件。
- `schedule.todo.create`：创建待办。
- `schedule.goal.check_in`：目标打卡。
- `schedule.today_summary`：读取今日安排。

### News

- `news.briefing.get`：读取今日简报摘要。
- `news.section.get`：读取指定板块。

### Leisure

- `leisure.recommend.today`：读取今日推荐。
- `leisure.preference.update`：更新口味偏好。

## 数据策略

第一阶段新增服务器统一数据文件或轻量数据库。推荐从 SQLite 开始，因为它比散落 JSON 文件更适合跨模块查询、导出和未来同步。

核心表：

- `action_logs`：记录所有动作调用、输入摘要、结果、错误。
- `fitness_nutrition_logs`：统一餐食记录。
- `fitness_training_logs`：训练记录。
- `fitness_recovery_logs`：恢复记录。
- `schedule_events`：日程事件。
- `schedule_todos`：待办。
- `assistant_messages`：主页 AI 会话记录。

浏览器端仍可保留 IndexedDB/localStorage 作为缓存，但新能力写入以服务器为准。后续再做“导入本地历史数据到服务器”的迁移入口。

## AI 解析策略

主页助手分两步：

1. `assistant/message` 调用模型把自然语言解析成 `proposedActions`。
2. 前端展示确认卡片。用户确认后调用 `actions/execute`。

高风险或不可逆动作必须确认。第一阶段所有写入动作都默认确认；读取动作可以直接执行。

模型输出不直接写数据库，必须经过 action schema 校验和服务端归一化。

## MCP 边界

牛秘书内部 Action Protocol 不是 MCP，但设计上与 MCP 兼容。

后续 MCP Server 的职责只做适配：

- 把 `/capabilities` 映射为 MCP tools。
- 把 MCP tool call 转发到 `/actions/execute`。
- 把必要的只读数据映射为 MCP resources。

内部业务逻辑不写在 MCP Server 里，避免 MCP 客户端、网页和未来 App 各走不同逻辑。

## 错误格式

所有统一 API 返回一致错误：

```json
{
  "ok": false,
  "error": "validation_failed",
  "message": "缺少 food 字段。",
  "details": {
    "field": "food"
  }
}
```

建议错误码：

- `invalid_request`
- `unknown_action`
- `validation_failed`
- `agent_unconfigured`
- `agent_timeout`
- `action_failed`
- `storage_failed`

## 前端体验

主页新增 AI 助手区域：

- 支持文本输入。
- 支持图片附件，先用于餐食识别。
- 支持“建议动作确认卡”。
- 显示动作来源和写入目标，例如“将写入：塑形馆 / 营养日志”。

语音助手第一阶段可以先预留按钮和状态，后续接浏览器 Web Speech API 或服务端语音识别。

各子网页不需要一次性重做界面，只需要把核心写入操作逐步改为统一动作接口。

## 测试策略

- `GET /capabilities` 返回稳定 action 列表。
- 未知 action 返回 `unknown_action`。
- `fitness.nutrition.create` 能写入服务器数据，并被塑形馆今日汇总读取。
- `schedule.event.create` 能写入日程，并被时务局今日安排读取。
- `assistant/message` 能把“我今天吃了牛肉面”解析成 `fitness.nutrition.create` 候选动作。
- 图片上传能走 `fitness.nutrition.recognize_photo` 并返回与塑形馆兼容的营养结构。
- AI 返回脏数据时不会直接写库，必须经过 schema 校验。

## 分阶段实施

### Phase 1：统一协议骨架

新增牛秘书统一 Python API 服务，包含 capabilities、actions/execute、assistant/message 三个入口。先实现 nutrition create、schedule event create、schedule todo create 三个写入动作。

### Phase 2：首页 AI 助手

在品牌主页增加 AI 助手面板，调用 assistant/message，展示候选动作确认卡，确认后执行动作。

### Phase 3：子网页逐步接入

塑形馆营养写入、时务局日程/待办写入改为调用统一 action。保留本地缓存用于页面展示和离线容错。

### Phase 4：MCP Adapter

新增独立 MCP Server 或同服务 MCP 路由，把内部 actions 暴露给外部 Agent。

## 开放问题

第一阶段必须确认服务器数据层位置和部署方式。推荐复用当前 Python systemd 服务风格，新增 `niu-secretary-api.service`，监听本地端口，由 nginx 反代 `/niu-secretary/api/`。

第一阶段还需要决定是否立即迁移历史本地数据。推荐先不迁移，只保证新动作进入统一数据层；迁移作为单独工具处理。
