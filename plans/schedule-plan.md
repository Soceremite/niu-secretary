# 📅 牛秘书时务局 — 实施方案

> v1.0 | 2026-05-28 | 帅锅出品

## 定位

时间线上的一切事务管理中心。不是冷冰冰的日历，而是一位帮你记住所有重要事情、替你操心的秘书。

## 品牌命名

**牛秘书时务局** — 时=时间，务=事务，局=管理机关。与新闻「社」、塑形「馆」、放映「厅」后缀各异，辨识度高。

## 功能矩阵

### P0 — 首批交付

| 子板块 | 路由 | 核心功能 |
|--------|------|----------|
| 🗓️ 日程核心 | `/schedule/calendar` | 日/周/月三视图、事件创建/编辑、时间轴展示、今日概览 |
| 🎂 重要日期 | `/schedule/dates` | 生日/纪念日/节日管理、倒计时卡片、周期性日期、提醒通知 |

### P1 — 二批交付

| 子板块 | 路由 | 核心功能 |
|--------|------|----------|
| 🛒 生活代办 | `/schedule/todos` | 待办清单（可拖拽排序）、购物清单、快递单号追踪 |
| 🎯 目标追踪 | `/schedule/goals` | 习惯打卡（连续天数）、OKR 目标管理、周/月复盘模板 |

### P2 — 三批交付

| 子板块 | 路由 | 核心功能 |
|--------|------|----------|
| 📚 阅读学习 | `/schedule/reading` | 书单书架、阅读进度追踪、学习计划、笔记/知识卡片 |
| 🌤️ 出行助手 | `/schedule/travel` | 天气+穿搭建议、通勤路况、旅行规划看板 |

## 技术方案

- **源码目录**: `/home/ubuntu/.openclaw/workspace/niu-secretary/schedule/dist/`
- **部署路径**: `/var/www/html/schedule/`
- **访问地址**: `http://124.222.22.171/home/schedule/`
- **技术栈**: 纯 HTML/CSS/JS，无框架，响应式
- **数据存储**: localStorage（MVP 阶段），后期可接 SQLite/API
- **视觉风格**: 品牌 dark luxury 黑金配色，与新闻社、塑形馆统一

## 页面结构

```
schedule/dist/
├── index.html          # 六宫格主入口 + 今日概览卡片
├── calendar.html       # 日程核心（日历视图）
├── dates.html          # 重要日期管理
├── todos.html          # 生活代办清单
├── goals.html          # 目标追踪
├── reading.html        # 阅读学习管理
├── travel.html         # 出行助手
├── logo.png
└── js/
    ├── store.js         # 统一 localStorage 数据层
    └── calendar.js      # 日历组件逻辑
```

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
  "remind": 30,
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
  "remind_days": 7
}
```

### 待办
```json
{
  "id": "todo_001",
  "title": "买牛奶",
  "list": "shopping",
  "done": false,
  "priority": "high",
  "due": "2026-05-30"
}
```

### 目标
```json
{
  "id": "goal_001",
  "title": "每天运动30分钟",
  "type": "habit",
  "category": "health",
  "streak": 12,
  "history": ["2026-05-16", "2026-05-17"],
  "target_streak": 30
}
```

## 交互设计要点

- 日历支持左右滑动手势（移动端）
- 倒计时卡片悬停翻转效果
- 待办列表支持拖拽排序
- 习惯打卡采用连续天数火焰动画
- 所有页面顶部统一导航栏（面包屑 + 返回入口）

## 实施步骤

### Phase 1: 基础框架 + 入口页
1. 创建目录结构，拷贝 logo
2. 搭建 `index.html` 六宫格导航 + 今日概览
3. 实现 `store.js` 数据层

### Phase 2: P0 子板块
4. `calendar.html` — 日历三视图 + 事件管理
5. `dates.html` — 重要日期 + 倒计时

### Phase 3: P1 子板块
6. `todos.html` — 待办/购物/快递
7. `goals.html` — 习惯打卡 + 目标

### Phase 4: P2 子板块
8. `reading.html` — 阅读/学习管理
9. `travel.html` — 出行助手

### Phase 5: 集成
10. 品牌主页更新入口
11. 全线测试 + 部署
