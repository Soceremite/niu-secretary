---
name: schedule
description: "牛秘书时务局——私人日程管理中心：日程核心、重要日期、生活代办、目标追踪、阅读学习、出行助手六大板块，纯静态 HTML 数据看板。"
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron,sessions_send
user-invocable: true
last_updated: "2026-05-30"
---

# 牛秘书时务局

> **品牌规范与视觉体系请参考 [主 SKILL.md](../SKILL.md)**

时间线上的一切事务管理中心。不是冷冰冰的日历，而是一位帮你记住所有重要事情、替你操心的秘书。

## 品牌命名

**时务局** — 时=时间，务=事务，局=管理机关。与新闻「社」、塑形「馆」、闲趣「集」后缀各异，辨识度高。

## 团队分工

- **🐋 DeepSeek V4 Pro** — 日常开发：页面搭建、数据层实现、交互逻辑
- **🧪 Claude Opus 4.6** — UI 优化：视觉打磨、动效设计
- **🐄 牛秘书** — 产品总监：功能设计、用户体验把关

## 架构概览

```
用户入口
├── 📅 Web页面 → 纯静态 HTML + JS（日历看板/事件管理/倒计时/代办/目标/阅读/出行）
├── 🔔 Cron 提醒 → 每日概览推送 / 重要日期提醒
└── 🔮 未来 → QQ Agent 语音创建日程

数据流
├── 板块页面 → 后端 Action API（schedule.event.list / schedule.todo.list）为主数据源
├── 后端 SQLite ← 牛秘书 AI 写入（event.create / todo.create）→ 板块直接读到
└── localStorage → 离线缓存/兜底（后端不可达时回落）；dates/goals 后端暂未建模，维持本地
```

## 核心约束

| 约束 | 说明 |
|------|------|
| 静态 HTML + 多页面 | 无 SPA 框架、无前端路由 |
| 后端为数据源 | events/todos 后端 SQLite 为主，localStorage 退为离线缓存兜底 |
| AI 打通 | 牛秘书 AI 写入的日程/待办经后端直达板块，跨设备一致 |
| 纯静态部署 | `dist/` 直接 cp 到 Nginx 静态目录 |
| 视觉体系 | 现代私人秘书事务夹，雾灰绿背景、象牙白卡片、墨蓝要务、铜金点缀 |
| 页面结构 | 每个子板块一个独立 HTML 文件 |

## 文件路径

| 文件 | 路径 |
|------|------|
| 项目根目录 | `/home/ubuntu/.openclaw/workspace/niu-secretary/schedule/` |
| 源码/构建产物 | `dist/` |
| 部署目标 | `/var/www/html/niu-secretary/schedule/` |
| 访问地址 | `http://124.222.22.171/niu-secretary/schedule/` |

## 部署

```bash
sudo mkdir -p /var/www/html/niu-secretary/schedule
sudo cp -r /home/ubuntu/.openclaw/workspace/niu-secretary/schedule/dist/* /var/www/html/niu-secretary/schedule/
```

## 目录结构

```
niu-secretary/schedule/
├── SKILL.md              # 本文件
└── dist/
    ├── index.html        # 主入口：六宫格导航 + 今日概览
    ├── calendar.html     # 日程核心：日/周/月视图 + 事件管理
    ├── dates.html        # 重要日期：生日/纪念日 + 倒计时
    ├── todos.html        # 生活代办：清单 + 购物 + 快递
    ├── goals.html        # 目标追踪：习惯打卡 + OKR
    ├── reading.html      # 阅读学习：书单 + 进度 + 笔记
    ├── travel.html       # 出行助手：天气 + 穿搭 + 旅行
    ├── logo.png          # 品牌 Logo（圆形展示）
    └── js/
        ├── store.js      # 统一 localStorage 数据层
        └── calendar.js   # 日历组件逻辑
```

---

## 六大功能模块

### Module 1: 日程核心 `calendar`

入口模块。所有时间事务的中心。

- 日/周/月三视图切换
- 事件创建/编辑/删除
- 时间段 + 标签分类（会议/个人/约会/学习/运动/其他）
- 今日概览摘要
- 提醒时间设置（事件前 N 分钟）

**标签色系**：
- `#8e2d24`（红）— 会议
- `#476d94`（蓝）— 个人
- `#c8a45c`（金）— 约会
- `#3c7a62`（绿）— 学习
- `#7f5d18`（棕）— 运动
- `#756b5b`（灰）— 其他

### Module 2: 重要日期 `dates`

帮你记住每一个不该忘记的日子。

- 生日/纪念日/节日管理
- 倒计时卡片（距今天 X 天 / 已过 X 天）
- 周期性日期（每年/每月/自定义间隔）
- 提前提醒天数设置
- 按时间排序 + 颜色编码（即将到来/近期/远期）

**倒计时状态**：
- 🔴 7 天内 — 紧急
- 🟡 30 天内 — 临近
- 🟢 30 天以上 — 正常

### Module 3: 生活代办 `todos`

生活杂事的可靠接盘侠。

- 待办清单（可勾选、可拖拽排序）
- 分类标签：购物/家政/缴费/快递/其他
- 购物清单（物品/数量/已购）
- 快递追踪（单号/物流状态/预计到达）
- 优先级标记：高/中/低

### Module 4: 目标追踪 `goals`

把"想做的事"变成"做完的事"。

- 习惯打卡：每日签到 + 连续天数火焰动画
- OKR 目标管理：目标 → 关键结果 → 里程碑
- 周/月复盘模板
- 进度可视化：完成率环形图、连续天数趋势
- 目标分类：健康/学习/工作/财务/生活

### Module 5: 阅读学习 `reading`

知识摄入的私人图书馆。

- 书单/书架管理（在读/已读/想读）
- 阅读进度追踪（页数/百分比）
- 学习计划（课程/技能/目标日期）
- 笔记/知识卡片（Markdown 预览）
- 每周阅读时间统计

### Module 6: 出行助手 `travel`

出门在外，有备无患。

- 实时天气（wttr.in API）
- 穿搭建议（基于气温+天气）
- 通勤路况（未来集成）
- 旅行规划看板：目的地/行程/清单/预算
- 行李打包清单模板

---

## 数据模型

### 日程事件
```json
{
  "id": "evt_001",
  "title": "项目评审会",
  "date": "2026-06-01",
  "time": "14:00",
  "duration": 90,
  "type": "meeting",
  "repeat": "none",
  "remindMinutes": 30,
  "notes": "带上 Q2 报告"
}
```

### 重要日期
```json
{
  "id": "date_001",
  "name": "帅锅生日",
  "date": "XXXX-XX-XX",
  "type": "birthday",
  "repeat": "yearly",
  "remindDays": 7
}
```

### 待办
```json
{
  "id": "todo_001",
  "title": "买牛奶",
  "date": "2026-05-30",
  "done": false,
  "priority": "high",
  "source": "home-assistant-ai"
}
```

> 后端 `schedule_todos` 表字段：`id / title / date / priority / done / source / created_at`。无日期待办 `date=""`，list 范围查询时始终纳入。`list / shopping / due` 等为前端扩展字段，后端暂未建模。

### 目标
```json
{
  "id": "goal_001",
  "title": "每天运动30分钟",
  "type": "habit",
  "category": "health",
  "streak": 12,
  "history": ["2026-05-16", "2026-05-17"],
  "targetStreak": 30
}
```

---

## 视觉体系

采用现代私人秘书事务夹风格：

- 雾灰绿背景（`#e8ece6`），避免新闻社泛黄报刊感
- 象牙白卡片（`#fffefa`），保留文件夹和纸张秩序
- 墨蓝要务色（`#243746`），用于关键事项和高优先级
- 铜金点缀（`#d0b37c`），用于日期、批注边线和品牌细节
- 首页以今日排班、秘书提醒、事务抽屉、今日批注为第一屏核心
- 响应式：桌面 1440px / 平板 768px / 手机 375px
- 尊重 `prefers-reduced-motion`
- 日历组件适配移动端滑动手势

## 入口页设计要点

`index.html` — 今日排班 + 秘书提醒 + 事务抽屉：

- 顶部：品牌名「牛秘书时务局」+ Logo（圆形）+ 今日日期牌
- 主区：今日排班时间轴，优先展示当天事项
- 侧栏：秘书提醒 + 事务抽屉模块入口
- 底部：今日批注，使用浅色签批便笺样式
- 底部：返回品牌主页链接

---

## 开发工作流

1. 在 `dist/` 下直接开发各页面
2. `sudo cp -r dist/* /var/www/html/niu-secretary/schedule/` 部署
3. 验证 `http://124.222.22.171/niu-secretary/schedule/`

> 所有资源引用使用相对路径。单个 HTML > 500 行时考虑拆分 JS/CSS。JS 使用 ES Module 组织。
