---
name: leisure
description: "牛秘书闲趣集——三维上下文感知休闲推荐中心：影视、音乐、播客、小说，结合用户偏好+日程状态+运动数据，每日 AI 生成个性化推荐。"
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron,sessions_send
user-invocable: true
last_updated: "2026-05-29"
---

# 牛秘书闲趣集 · 三维上下文感知推荐引擎

> **品牌规范与视觉体系请参考 [主 SKILL.md](../SKILL.md)**

**核心理念**：不靠算法投喂，不刷无尽榜单。AI 每天读取你的**口味偏好 + 日程密度 + 运动状态**，三个维度交叉匹配，给你精心筛选的少量精选内容——像一位了解你的私人策展人。

## 团队分工

- **🐋 DeepSeek V4 Pro** — 日常推荐生成：搜索热点、分析上下文、写入 JSON
- **🧪 Claude Opus 4.6** — UI 打磨：视觉优化、动效设计
- **🐄 牛秘书** — 产品总监 + 策展人

## 三维推荐引擎（v2.2）

```
AI cron (每天 12:00)
  ├── 维度一：口味偏好
  │   └── 读取 data/preferences.json（类型/心情/场景/语种等）
  ├── 维度二：日程密度
  │   └── 读取 时务局数据 → 今日任务数量、忙碌程度
  ├── 维度三：运动状态
  │   └── 读取 塑形馆数据 → 训练强度、恢复状态
  ├── 三维交叉匹配
  │   ├── 影视推荐 → 偏好类型 ∩ 日程适配 ∩ 运动调性
  │   ├── 音乐推荐 → 偏好场景 ∩ 运动适配 ∩ 心情匹配
  │   ├── 播客推荐 → 偏好类型 ∩ 日程时长适配
  │   └── 小说推荐 → 偏好类型 ∩ 日程阅读时长适配
  ├── 搜索最新热门内容（豆瓣/网易云/喜马拉雅/起点）
  ├── 生成个性化推荐理由（必须提到为什么适合"今天的你"）
  ├── 写入 data/*.json + context.json + preferences.json
  └── 部署到 nginx
```

### 推荐策略矩阵

| 日程密度 | 运动状态 | 推荐调性 | 影视偏好 | 音乐偏好 |
|----------|----------|----------|----------|----------|
| 🟢 轻松(≤2) | 无运动 | 烧脑沉浸 | 悬疑/科幻长片 | 专注音乐 + 深度播客 |
| 🟢 轻松(≤2) | 有运动 | 活力放松 | 动作/热血片 | 运动歌单 + 轻喜剧 |
| 🟡 适中(3-4) | 无运动 | 平衡舒缓 | 文艺/剧情片 | 治愈音乐 + 人文播客 |
| 🟡 适中(3-4) | 有运动 | 节奏切换 | 动画/喜剧 | 多元歌单 + 科技播客 |
| 🔴 繁忙(≥5) | 无运动 | 轻量放松 | 短片/轻喜剧 | 纯音乐 + 短播客 |
| 🔴 繁忙(≥5) | 有运动 | 解压治愈 | 治愈系 | 自然白噪音 + 搞笑播客 |

## 文件路径

| 文件 | 路径 |
|------|------|
| 项目根 | `/home/ubuntu/.openclaw/workspace/niu-secretary/leisure/` |
| 构建产物 | `dist/` |
| 部署目标 | `/var/www/html/niu-secretary/leisure/` |
| 访问地址 | `http://124.222.22.171/niu-secretary/leisure/` |

## 目录结构

```
niu-secretary/leisure/
├── SKILL.md                  # 本文件
└── dist/
    ├── index.html            # 主入口：今晚首推 + 今日候选(4项)
    ├── logo.png              # 品牌 logo (圆形展示)
    └── data/
        ├── context.json      # 每日上下文快照（日程/运动/mood）
        ├── preferences.json  # 用户口味偏好
        ├── movies.json       # 影视推荐
        ├── music.json        # 音乐推荐
        ├── podcasts.json     # 播客推荐
        └── novels.json       # 小说推荐
```

## 入口页设计

`index.html` — 单文件包含完整功能：

- **顶部**：品牌名 + 返回主页链接
- **闲趣批注区**：动态显示今日上下文（日程状态/运动状态/mood）和推荐策略说明
- **口味档案区**：从 `preferences.json` 动态加载偏好标签展示
- **今晚首推区**：展示第一条推荐 + 海报图片 + 匹配度 + 个性化理由
- **今日候选区**：4 个可点击卡片（影视/音乐/播客/小说），点击弹出详情弹窗

## 详情弹窗

点击候选卡片弹出底部弹窗（detail-overlay），非跳转页面：

| 板块 | 展示内容 | 主跳转平台 | APP Scheme（移动端） |
|------|---------|-----------|---------------------|
| 🎬 影视 | 海报/导演/主演/类型/年份/地区/时长/豆瓣评分/简介 | 豆瓣 | `douban://douban.com/movie/{id}` |
| 🎵 音乐 | 歌曲列表(5-10首)/类型/语言/场景 | 网易云音乐 | `orpheus://playlist?id={id}` |
| 🎧 播客 | 播客名/单集/类型/时长/简介 | 喜马拉雅 | `xmly://album/{id}` |
| 📖 小说 | 作者/类型/字数/简介 | 起点读书 | 网页版 |
| 🌐 备用 | 所有板块 | 网页版链接（fallback） | — |

**跳转逻辑**：前端判断 `navigator.userAgent` 是否为移动端 → 优先使用 APP scheme → 失败则 fallback 网页版。

## 数据格式

### preferences.json — 用户口味偏好
```json
{
  "movies": {
    "genres": ["科幻", "动画", "悬疑"],
    "moods": ["沉浸", "治愈", "热血"],
    "regions": ["欧美", "日韩", "大陆"],
    "avoidGenres": ["恐怖"],
    "maxDuration": 180
  },
  "music": {
    "genres": ["流行", "民谣", "轻音乐"],
    "scenes": ["放松", "通勤", "运动", "专注"],
    "moods": ["治愈", "活力", "平静"],
    "languages": ["中文", "英文", "纯音乐"]
  },
  "podcasts": {
    "genres": ["科技", "AI", "商业", "人文"],
    "minDuration": 15,
    "maxDuration": 90
  },
  "novels": {
    "genres": ["科幻", "悬疑", "历史"],
    "preferChinese": true,
    "minWordCount": "5万字"
  }
}
```

### context.json — 每日上下文快照
```json
{
  "generated": "ISO-8601",
  "schedule": {"taskCount": 3, "busyLevel": "适中", "note": "..."},
  "fitness": {"hasWorkout": true, "intensity": "中等", "note": "..."},
  "moodProfile": {"primary": "平衡", "secondary": "放松", "label": "节奏切换日"},
  "dailyNote": "今天日程适中、有运动安排，适合节奏切换型内容",
  "recommendationStrategy": {
    "movies": ["动画", "喜剧"],
    "music": ["多元歌单", "运动歌单"],
    "podcasts": ["科技", "人文"]
  }
}
```

### movies.json — 影视推荐
```json
{
  "generated": "ISO-8601",
  "items": [{
    "id": "mov_001",
    "title": "沙丘3",
    "titleOriginal": "Dune: Part Three",
    "type": "电影",
    "year": 2026,
    "genres": ["科幻", "史诗"],
    "region": "美国",
    "duration": 165,
    "doubanRating": 8.6,
    "matchScore": 94,
    "reason": "结合偏好+上下文的推荐理由",
    "director": "丹尼斯·维伦纽瓦",
    "actors": "提莫西·查拉梅、赞达亚",
    "description": "剧情简介",
    "posterUrl": "data/poster-dune.jpg",
    "doubanUrl": "https://movie.douban.com/subject/{id}/",
    "appScheme": "douban://douban.com/movie/{id}"
  }]
}
```

### music.json — 音乐推荐
```json
{
  "items": [{
    "id": "mus_001",
    "title": "歌单名称",
    "genre": ["流行", "民谣"],
    "trackCount": 8,
    "matchScore": 88,
    "reason": "结合上下文的推荐理由",
    "description": "歌单描述",
    "tracks": [
      {"name": "歌曲名", "artist": "艺术家", "duration": "4:24"}
    ],
    "platformUrl": "https://music.163.com/",
    "appScheme": "orpheus://playlist?id={id}"
  }]
}
```

### podcasts.json — 播客推荐
```json
{
  "items": [{
    "id": "pod_001",
    "title": "单集标题",
    "podcast": "播客频道名",
    "episode": "EP.158",
    "genres": ["科技", "AI"],
    "duration": 45,
    "matchScore": 90,
    "reason": "结合上下文的推荐理由",
    "description": "单集简介",
    "platformUrl": "https://www.ximalaya.com/album/{id}",
    "appScheme": "xmly://album/{id}"
  }]
}
```

### novels.json — 小说推荐
```json
{
  "items": [{
    "id": "novel_001",
    "title": "小说名",
    "author": "作者",
    "genres": ["科幻", "悬疑"],
    "wordCount": "约12万字",
    "matchScore": 90,
    "reason": "结合上下文的推荐理由",
    "description": "简介",
    "platformUrl": "https://www.qidian.com/search?kw={书名}"
  }]
}
```

## 图片爬取策略

海报图片来源优先级：

1. **百度图片搜索** → 搜电影名+海报 → 提取大图 URL → `curl` 下载到 `data/` 目录
2. **豆瓣图片 CDN** (`img9.doubanio.com`) → 已知的豆瓣图片 ID 直接拼接 URL 下载
3. **AI 生成** → 使用 `image_generate` 生成风格匹配的图片（最后手段）
4. **无图 fallback** → 不显示海报，使用 CSS 渐变背景

**下载后处理**：`convert` 压缩到 300×450px，转为 JPG，存为 `data/poster-{name}.jpg`

**爬取流程（cron 任务中执行）**：
```bash
# 1. web_search 搜"电影名 海报"获取海报 URL
# 2. curl 下载图片
curl -sL -o poster-mov_001.jpg "海报URL"
# 3. 压缩（分辨率 300×450）
convert poster-mov_001.jpg -resize 300x450 poster-mov_001.jpg
# 4. 更新 movies.json 中 posterUrl 为相对路径
#    "posterUrl": "data/poster-mov_001.jpg"
```

> 注意：服务器在国内，外网图片源（unsplash/tmdb/wikimedia）基本不可用。仅使用国内可访问的图源。
> movie poster 文件名格式：`data/poster-{movie_id}.jpg`

## Cron 运行完整流程

```
1. 读取 preferences.json → 获取口味偏好
2. 读取 时务局/塑形馆 数据 → 获取日程+运动上下文
3. web_search × 4 → 影视/音乐/播客/小说各搜一次（freshness="month"）
4. 三维交叉匹配 → 从搜索结果筛选最匹配的内容
5. 写个性化推荐理由 → 必须提到为什么适合"今天的你"
6. 搜海报图 → 下载到 data/poster-*.jpg
7. 写入 5 个 JSON 文件
8. sudo cp -r dist/* → 部署到 nginx
```

## 页面数据加载逻辑

前端 JS 加载顺序：

1. `fetch('data/preferences.json')` → 渲染口味标签
2. `fetch('data/context.json')` → 渲染闲趣批注（日程/运动/mood）
3. `Promise.allSettled([movies, music, podcasts, novels])` → 渲染候选列表
4. 第一条数据 → 渲染今晚首推（含海报）
5. 点击候选 → 详情弹窗（含 APP scheme 跳转）

## 部署

```bash
sudo cp -r /home/ubuntu/.openclaw/workspace/niu-secretary/leisure/dist/* /var/www/html/niu-secretary/leisure/
```

## Cron 任务

| 任务 | 频率 | 时间 | 内容 |
|------|------|------|------|
| 智能推荐更新 | 每天 | 12:00 CST | 三维上下文匹配 + 搜索热点 + 生成 JSON + 部署 |

> 当前 Job ID: `0fc99702`，`sessionTarget: "isolated"`，`payload.kind: "agentTurn"`

## 视觉规范

- 品牌色：温暖象牙底 `#f1eee7`，茶金 `#c9975f`，灰蓝 `#66848e`
- 卡片：`#fffdf7`，柔光阴影
- 弹窗：底部 sheet，24px 圆角
- 图标：emoji + 纯色圆底
- 海报：100px 缩略图，12px 圆角
- 时长格式：统一使用"分钟"（非 m/min）
- 响应式三档：桌面 1440 / 平板 768 / 手机 375
