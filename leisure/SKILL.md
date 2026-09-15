---
name: leisure
description: "牛秘书闲趣集 · 休闲推荐策展"
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron,sessions_send
user-invocable: true
---

# 牛秘书闲趣集 🎬

根据日程密度和运动状态，自动生成个性化影视/音乐/播客/小说推荐。

> 品牌规范请参考 [主 SKILL.md](../SKILL.md)

## 目录结构

```
/home/ubuntu/.openclaw/workspace/niu-secretary/leisure/
├── SKILL.md                        # 本文件
├── dist/                           # 构建产物（部署到 nginx）
│   ├── index.html                  # 主页：Hero + 今晚首推 + 今日候选 + 闲趣批注
│   ├── movies.html                 # 🎬 影视推荐子页面
│   ├── music.html                  # 🎵 音乐推荐子页面
│   ├── podcasts.html               # 🎙️ 播客推荐子页面
│   ├── novels.html                 # 📖 小说推荐子页面
│   ├── style.css                   # 共享样式（所有页面共用）
│   ├── logo.png                    # 品牌 Logo
│   ├── data/                       # JSON 数据文件
│   │   ├── movies.json             # 影视推荐数据（数组或 {items:[]}）
│   │   ├── music.json              # 音乐推荐数据
│   │   ├── podcasts.json           # 播客推荐数据
│   │   ├── novels.json             # 小说推荐数据（可选）
│   │   ├── context.json            # 上下文（日程/运动/策略）
│   │   └── preferences.json        # 偏好（可选）
│   └── js/
│       └── nav.js                  # 导航栏 + 公共逻辑（detail弹窗、数据加载、卡片渲染）
└── plans/                          # (预留) 实施方案文档
```

## 部署目标

```
/var/www/html/niu-secretary/leisure/
├── index.html
├── movies.html
├── music.html
├── podcasts.html
├── novels.html
├── style.css
├── logo.png
├── data/
│   ├── movies.json
│   ├── music.json
│   ├── podcasts.json
│   ├── novels.json
│   ├── context.json
│   └── preferences.json
└── js/
    └── nav.js
```

**访问地址：**
- 主页：`http://124.222.22.171/niu-secretary/leisure/`
- 影视：`http://124.222.22.171/niu-secretary/leisure/movies.html`
- 音乐：`http://124.222.22.171/niu-secretary/leisure/music.html`
- 播客：`http://124.222.22.171/niu-secretary/leisure/podcasts.html`
- 小说：`http://124.222.22.171/niu-secretary/leisure/novels.html`

## 页面架构（v2.0 多页面）

### 主页 (`index.html`)

包含：
- **Hero**：品牌标语 + 口味档案
- **导航菜单**：🏠首页 / 🎬影视 / 🎵音乐 / 🎙️播客 / 📖小说（菜单栏切换子页面）
- **今晚首推**：最高匹配度的推荐（卡片样式，含海报/导演/主演/标签）
- **今日候选**：四类各取1-2条的紧凑列表
- **闲趣批注**：显示日程状态、运动状态、推荐策略

### 子页面（movies/music/podcasts/novels.html）

每个子页面结构一致：
- Topbar + 导航菜单（当前页高亮）
- 区标题
- 卡片网格（显示该分类所有推荐）
- 点击卡片弹出 detail 弹窗

### 共享资源

- **style.css**：所有页面共用的完整样式
- **nav.js**：导航高亮 + `showDetail()` 弹窗 + `renderCardGrid()` 渲染 + `loadSectionData()` 数据加载 + scroll reveal

## 数据格式

### movies.json
```json
[
  {
    "id": "mov_001",
    "title": "沙丘第二部",
    "titleOriginal": "Dune: Part Two",
    "type": "电影",
    "year": 2024,
    "genres": ["科幻", "史诗"],
    "region": "美国",
    "duration": "166分钟",
    "doubanRating": 8.2,
    "matchScore": 88,
    "reason": "与你的科幻偏好匹配",
    "mood": "沉浸",
    "coverUrl": "海报URL",
    "doubanUrl": "豆瓣链接",
    "director": "导演",
    "actors": "主演"
  }
]
```

### music.json
```json
[
  {
    "id": "mus_001",
    "title": "歌单/专辑名",
    "type": "歌单",
    "genre": "治愈民谣",
    "language": "国语",
    "trackCount": 30,
    "matchScore": 85,
    "reason": "适合晚间放松",
    "mood": "安静",
    "scene": "睡前",
    "platformUrl": "平台链接"
  }
]
```

### podcasts.json
```json
[
  {
    "id": "pod_001",
    "title": "单集标题",
    "podcast": "播客节目名",
    "episode": "集数",
    "genres": ["科技"],
    "duration": "45分钟",
    "matchScore": 82,
    "reason": "轻松了解前沿科技",
    "platformUrl": "喜马拉雅链接"
  }
]
```

### context.json
```json
{
  "generated": "2026-05-30T00:00:00+08:00",
  "schedule": { "taskCount": 2, "busyLevel": "轻松", "note": "..." },
  "fitness": { "hasWorkout": false, "intensity": "低", "note": "..." },
  "moodProfile": { "primary": "文艺", "secondary": "放松", "label": "文艺放松型" },
  "dailyNote": "今天适合文艺放松型内容...",
  "recommendationStrategy": {
    "movies": ["文艺", "剧情"],
    "music": ["治愈", "民谣"],
    "podcasts": ["人文", "科技"]
  }
}
```

## 推荐策略矩阵

| 日程密度 | 运动状态 | 推荐调性 | 内容偏好 |
|----------|----------|----------|----------|
| 🟢 轻松(≤2项) | 无运动 | 烧脑沉浸 | 悬疑/科幻长片 + 深度播客 + 专注音乐 |
| 🟢 轻松(≤2项) | 有运动 | 活力放松 | 动作/热血片 + 运动歌单 + 轻喜剧 |
| 🟡 适中(3-4项) | 无运动 | 平衡舒缓 | 文艺/剧情片 + 治愈音乐 + 人文播客 |
| 🟡 适中(3-4项) | 有运动 | 节奏切换 | 动画/喜剧 + 多元歌单 + 科技播客 |
| 🔴 繁忙(≥5项) | 无运动 | 轻量放松 | 短喜剧/短片 + 纯音乐 + 短播客 |
| 🔴 繁忙(≥5项) | 有运动 | 解压治愈 | 治愈系 + 自然白噪音 + 搞笑播客 |

无法读取塑形馆/时务局数据时，默认使用「平衡舒缓」策略。

## 部署流程

### 日常更新（只更新 JSON 数据）

```bash
# 1. 更新 JSON 数据文件
#    dist/data/movies.json / music.json / podcasts.json / novels.json / context.json

# 2. 部署到 nginx
sudo rsync -av --delete /home/ubuntu/.openclaw/workspace/niu-secretary/leisure/dist/ /var/www/html/niu-secretary/leisure/

# 3. 验证
curl -s http://124.222.22.171/niu-secretary/leisure/data/context.json | head -5
```

### 改版（修改 HTML/CSS/JS）

修改完 `dist/` 下的相关文件后，同样执行 rsync 部署即可。CSS 改一次所有页面生效。

## Nginx 配置

已在 `/etc/nginx/sites-enabled/control-center` 中配置：

```nginx
location /niu-secretary/leisure/ {
    alias /var/www/html/niu-secretary/leisure/;
    index index.html;
    try_files $uri $uri/ =404;
}
```

## 负责模型

- 内容生成：`qwen3.7-max`（搜索、推荐、生成 JSON）
- UI 改版：`Claude Opus 4.6`（HTML/CSS/JS 重构）

## 用户画像 · 个性化精选（v1.1，2026-05-30）

闲趣集接入牛秘书 AI 画像链路：首页「口味档案」标签 + 「今日候选」都由后端 `leisure` 画像驱动。

- **两套画像的关系（重要）**：
  - 后端 `user_profiles.leisure`（你跟 AI 聊出来的长期偏好）= **权威画像**。
  - `dist/data/preferences.json`（cron 每日生成）= 内容库自带的**兑底标签**，画像空字段才回落它。
  - `profile.update` 不回写 preferences.json，避免 cron 覆盖冲突。
- 推荐动作：`leisure.recommend`（confirmByDefault=false）
  - 后端读 `dist/data/{movies,music,podcasts,novels}.json`（movies/music/podcasts 是数组，novels 是 `{items:[]}`），按画像 `genres.{movie,music,podcast,novel}` / `moods` / `avoid` 打分。
  - 类型命中 +3 / mood 命中 +2 / 内容自带 matchScore 做微调；`avoid` 命中则剔除；返回按类目分组。
  - 读文件失败/空画像都有兑底，不阻塞页面。
- 画像编辑入口：**只走主页牛秘书 AI 对话**（如「我爱看科幻、别推恐怖片」），本页面板只读展示。
- `leisure` 画像字段：`genres{movie,music,podcast,novel} / moods[] / avoid[] / notes`，定义在 `server/store.py:DEFAULT_PROFILES`。
- 前端：`dist/index.html` 内联脚本 `loadTasteProfile()` + `leisure.recommend` 融合候选（按 id 回原数据复用 `showDetail`）；本模块无 build，`dist/` 即唯一源。

## Cron 管线（2026-09-15 已收编为 no_agent 统一管线）

- Job `9b50d06ee811`（11:00 闲趣集·每日更新）— **no_agent 模式**，脚本 `bash run_pipeline.sh`：
  1. `tools/fetch_leisure_candidates.py` — 直抓豆瓣新片榜/网易热歌榜 API/豆瓣新书（无 LLM，海报 URL 顺带拿到）
  2. `tools/recommend_leisure_llm.py` — NiuLLM("content") 写推荐理由/matchScore/mood → 写 movies/music/podcasts/novels/context.json + `dist/qq_digest.txt`
  3. `niu_secretary.leisure_validation` 数据校验（errors 非零即失败）
  4. `tools/review_posters.py` — NiuLLM("vision") 真实审核海报 → image_review.json
  5. 末行 `{"wakeAgent": false}` — 静默完成
- Job `c6e3ee3ec66c`（11:30 闲趣集部署，deliver=qqbot）— stdout 只含推荐正文：
  剔除 fail 海报 → quality gate → rsync → HTTP 验证 → `cat dist/qq_digest.txt`
- 暂停的 job：`126551b6494c` 图片审核（提前并入管线）
- **LLM 调用**：全部走 `niu_core/llm_client`（content / vision），路由见 `config/models.yaml`，禁止硬编码 key/base_url。
- 海报拉取注意：豆瓣 CDN 需要 Chrome UA + `Referer: https://movie.douban.com/` 否则 418。

last_updated: 2026-09-15
