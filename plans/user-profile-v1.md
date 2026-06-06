# 牛秘书 AI · 四大板块用户画像系统 v1（实施方案）

> 状态：待帅锅确认 · 起草：2026-05-30 · 作者：🐄 牛秘书

## 1. 目标

让牛秘书 AI 从「记录员」升级为「懂你的管家」：

1. **四大板块各有一份用户画像**（fitness / schedule / news / leisure）
2. **通过聊天自适应调整画像** —— 用户说一句「我最近想减脂」「我爱看悬疑剧」，AI 理解并更新对应画像
3. **画像驱动个性化推送** —— 每个板块根据画像筛选/生成对应内容
4. 延续现有 Action Protocol：能力可发现、输入可校验、执行可审计

## 2. 数据模型设计

### 2.1 两层结构

| 层 | 说明 | 用途 |
|----|------|------|
| **画像快照 profile** | 每板块一份结构化 JSON，存当前完整偏好 | 推送引擎读取 |
| **偏好变更 preference_log** | AI 每次从聊天抽取的增量更新记录 | 可追溯、可回滚、可审计 |

### 2.2 各板块画像字段（profile schema）

**fitness（塑形馆）**
```json
{
  "goal": "fat_loss | muscle_gain | recomp | maintain",
  "dietStyle": "川渝 | 粤式 | 江浙 | 东北 | 清淡 | 高蛋白 | ...",
  "restrictions": ["乳糖不耐", "不吃牛肉", "海鲜过敏"],
  "trainingLevel": "beginner | intermediate | advanced",
  "targetCalories": 1800,
  "proteinTarget": 140,
  "notes": "自由文本补充"
}
```

**schedule（时务局）**
```json
{
  "workHours": "09:00-18:00",
  "focusBlocks": ["上午深度工作", "晚上不排会"],
  "reminderStyle": "提前30分钟 | 提前1天",
  "priorities": ["科研 rebuttal", "健身打卡"],
  "notes": ""
}
```

**news（新闻社）**
```json
{
  "topics": ["AI", "科技", "财经"],
  "excludeTopics": ["娱乐八卦"],
  "depth": "headline | brief | deep",
  "regions": ["国内", "国际"],
  "notes": ""
}
```

**leisure（闲趣集）**
```json
{
  "genres": {"movie": ["悬疑", "科幻"], "music": ["民谣"], "podcast": ["科技"], "novel": ["硬科幻"]},
  "moods": ["下饭", "解压"],
  "avoid": ["恐怖"],
  "notes": ""
}
```

> 字段是「软约束」：后端只存 JSON，不强校验枚举值，AI 和前端按约定使用。`notes` 永远兜底自由文本。

### 2.3 数据库表

```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    module TEXT PRIMARY KEY,           -- fitness|schedule|news|leisure
    profile_json TEXT NOT NULL,        -- 完整画像快照
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_changes (
    id TEXT PRIMARY KEY,
    module TEXT NOT NULL,
    field TEXT NOT NULL,               -- 改动的字段
    old_value TEXT NOT NULL DEFAULT '',
    new_value TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',  -- AI 给的人话说明
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_profile_changes_module ON profile_changes(module);
```

> 单用户系统，`user_profiles` 用 `module` 做主键即可，无需 user_id。未来多用户再加列。

## 3. 新增动作（Action Protocol）

| 动作 | 类型 | 说明 |
|------|------|------|
| `profile.get` | 读 | 读某板块画像（不传 module 则返回全部）|
| `profile.update` | 写 | 合并更新画像字段（patch 语义），写 profile_changes |
| `profile.reset` | 写 | 重置某板块画像为默认 |
| `profile.changes` | 读 | 读某板块变更历史 |
| `<module>.recommend` | 读 | 按画像生成/筛选推送内容（见 §5）|

`profile.update` 的 input：
```json
{
  "module": "fitness",
  "patch": {"goal": "fat_loss", "targetCalories": 1700},
  "summary": "调整为减脂目标，热量下调到1700",
  "source": "home-assistant-ai"
}
```

## 4. AI 聊天调整画像（assistant.py 升级）

### 4.1 意图分类扩展

现有分类 `fitness|schedule|news|leisure|chat`。新增维度：**判断是「记录一次性数据」还是「调整长期偏好」**。

方案：在分类 prompt 里加 `intent` 字段：
```
{"module":"fitness","intent":"record|preference|query"}
```
- `record` → 走现有 create 动作（吃了什么、几点开会）
- `preference` → 走新的 `profile.update`（我想减脂、我爱看悬疑）
- `query` → 走 recommend 或 summary

### 4.2 偏好抽取

`intent=preference` 时，调模型生成 `profile.update` 动作：
```
用户："我最近想多吃点蛋白，少油腻"
→ {"action":"profile.update","input":{"module":"fitness",
     "patch":{"proteinTarget":150,"dietStyle":"高蛋白","restrictions":["少油"]},
     "summary":"提高蛋白摄入目标，偏好清淡少油"}}
```

同样走「待确认动作卡片」——画像变更也要用户确认后才落库，保持可控。

### 4.3 本地降级

模型不可用时，本地规则引擎用关键词粗抽取（如「减脂/增肌」「川菜/清淡」「悬疑/科幻」），保证基本可用。

## 5. 画像驱动推送

每板块新增 `recommend` 动作，读画像生成内容：

| 板块 | recommend 行为 |
|------|---------------|
| 🏋️ fitness | 按 goal/restrictions 推荐今日饮食建议、训练重点 |
| 📅 schedule | 按 workHours/priorities 推荐今日时间安排、提醒优化 |
| 📰 news | 按 topics/excludeTopics 筛选/排序新闻（与新闻社 cron 数据结合）|
| 🎬 leisure | 按 genres/moods 推荐影视音乐（与闲趣集现有内容结合）|

> v1 先做「基于画像的规则筛选 + 模型生成建议文本」。新闻社/闲趣集的真实内容库对接放 v1.1。

## 6. 前端改动

### 6.1 首页 AI 对话框
- 动作卡片支持 `profile.update` 类型（标题「更新画像：塑形馆」，展示 patch JSON 可编辑）
- 进度可视化增加「更新画像」步骤文案

### 6.2 各板块页面
- 新增「我的画像」入口/面板：展示当前画像，可查看 AI 调整历史
- 推送区：调用 `<module>.recommend` 展示个性化内容
- 数据源仍走后端优先 + localStorage 兜底（延续上次改造）

## 7. 实施步骤（分阶段，每阶段可独立验证）

### 阶段 A：后端画像基础设施
1. `store.py`：建表 user_profiles / profile_changes + CRUD 函数 + 默认画像常量
2. `capabilities.py`：注册 profile.get/update/reset/changes
3. `action_handlers.py`：实现 4 个 handler（patch 合并、变更记录）
4. 单测：画像增删改查、patch 合并、变更历史
5. 验证：单测全过

### 阶段 B：AI 聊天调整画像
6. `assistant.py`：分类 prompt 加 intent 字段；新增 preference 抽取 prompt + 模型调用
7. 本地降级：关键词粗抽取
8. 单测：preference 意图生成 profile.update 动作
9. 验证：本地起 API，聊天 → 画像更新闭环

### 阶段 C：画像驱动推送
10. 各板块 `recommend` 动作（先 fitness + leisure，规则 + 模型生成）
11. 单测 + 验证

### 阶段 D：前端
12. 首页 assistant.js：支持 profile.update 动作卡片
13. 塑形馆 + 时务局：画像面板 + recommend 推送区（先做这两个验证闭环）
14. 新闻社 + 闲趣集画像面板（v1.1 可延后）
15. build + 部署到 nginx + 线上验证

### 阶段 E：收尾
16. 更新 5 个 SKILL.md（新动作、画像数据模型、数据流）
17. 更新 MEMORY.md

## 8. 风险与约定

- **画像变更需用户确认**：和现有动作一样走确认卡片，不让 AI 偷偷改画像
- **生产 DB 自动建表**：store.initialize 已有 `CREATE TABLE IF NOT EXISTS`，新表自动创建，无破坏性迁移
- **API key 仍硬编码**：本次不处理（独立待办），但新代码不要再硬编码
- **systemd 重启**：阶段 B 起需 `sudo -n systemctl restart niu-secretary-api.service`
- **范围控制**：v1 聚焦「画像 CRUD + 聊天调整 + 塑形馆/时务局推送」打通闭环；新闻社/闲趣集真实内容库对接列为 v1.1

## 9. 工作量预估

| 阶段 | 文件 | 规模 |
|------|------|------|
| A 后端基础 | store/capabilities/action_handlers/test | 中 |
| B AI 聊天 | assistant/test | 中 |
| C 推送 | action_handlers/test | 小-中 |
| D 前端 | assistant.js + 2~4 个板块页面 | 中-大 |
| E 文档 | 5×SKILL + MEMORY | 小 |

建议：**A→B→C 后端三阶段一次做完并验证**（这是核心价值，纯本地可逆），再做 D 前端 + 部署。
