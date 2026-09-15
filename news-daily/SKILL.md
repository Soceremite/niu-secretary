---
name: news-daily
description: "每日新闻头条生成与推送——搜新闻、更新 HTML 页面、部署到 nginx、推送链接"
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron,sessions_send
user-invocable: true
last_updated: "2026-06-04"
---

# 牛秘书新闻社 · 每日新闻推送

> **品牌规范与视觉体系请参考 [主 SKILL.md](../SKILL.md)**

生成每日新闻头条 HTML 页面，部署到 nginx，推送到 QQ。

## 团队分工

- **🐋 DeepSeek V4 Pro** — 一线记者：搜新闻、写摘要、贴链接
- **🧪 Claude Opus 4.6** — 首席码农：改 UI、调样式、性能优化
- **🐄 牛秘书** — 总编辑：质量控制、品牌管理、内容把关

**日常新闻生成用 DeepSeek，UI 改动切 Claude。**

---

## 架构设计（v3.1 模块化）

### 设计理念

单体 HTML 拆分为**模块化多文件架构**：
- CSS 样式独立为单文件，所有页面共享
- 每个新闻板块为独立 HTML 片段，通过主页 `fetch()` 动态加载
- 更新时只需修改对应板块文件，无需触碰主框架
- **v3.1**：新闻配图本地化托管，自适应图片比例；卡片摘要增至3行

### 目录结构

```
/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/
├── SKILL.md                    # 本文件
├── dist/                       # 构建产物（部署到 nginx）
│   ├── index.html              # 主框架页（壳子 + JS loader）
│   ├── style.css               # 全局样式
│   ├── logo.png                # 品牌 Logo（圆形展示）
│   ├── assets/
│   │   └── images/             # 本地新闻配图（news_img_N.jpg）
│   └── sections/               # 各板块 HTML 片段
│       ├── domestic.html       # 🇨🇳 国内要闻
│       ├── international.html  # 🌍 国际焦点
│       ├── finance.html        # 💹 财经快讯
│       ├── tech.html           # 🚀 科技动态
│       └── ai.html             # 🤖 人工智能
└── tools/                      # 辅助脚本
    ├── crawl_images.py         # 爬取新闻配图到本地
    └── update_sections.py      # 根据爬取结果更新 section HTML
```

### 部署目标

```
/var/www/html/niu-secretary/news/
├── index.html
├── style.css
├── logo.png
├── assets/
│   └── images/
│       └── news_img_N.jpg
└── sections/
    ├── domestic.html
    ├── international.html
    ├── finance.html
    ├── tech.html
    └── ai.html
```

**访问地址：** `http://124.222.22.171/niu-secretary/news/`

### Nginx 配置

已在 `/etc/nginx/sites-enabled/control-center` 中配置：

```nginx
location /niu-secretary/news/ {
    alias /var/www/html/niu-secretary/news/;
    index index.html;
    try_files $uri $uri/ =404;
}
```

---

## 文件职责

### `index.html` — 主框架

只包含：
- `<head>` 引用 `style.css`
- 顶栏（品牌 + 导航标签）
- Hero 区域（标题 + 日期）
- 公告栏 + 统计栏
- **空的 section 容器**（由 JS 填充）
- Detail overlay 弹窗容器
- Footer
- JS：`fetch()` 加载各 section HTML 片段并注入 DOM

**主框架极少变动**，除非改版。

### `style.css` — 全局样式

所有视觉样式集中管理：
- 顶栏、Hero、公告栏、统计栏
- 新闻卡片（`.news-card`）
- Detail 弹窗面板
- 响应式断点
- 标签颜色体系

**改样式只改这一个文件。**

### `sections/*.html` — 板块片段

每个文件是一个**纯 HTML 片段**（无 `<html>`/`<head>`），结构：

```html
<!-- domestic.html 示例 -->
<div class="section domestic" id="section-domestic">
  <div class="section-title">🇨🇳 国内要闻</div>
  <div class="news-grid">
    <!-- 卡片 × N（最多6条） -->
    <a class="card-link" onclick="openDetail('detail-1'); return false;" href="#">
      <div class="news-card">
        <span class="tag tag-red">时政</span>
        <div class="emoji-icon">🇺🇳</div>
        <h3>标题</h3>
        <p class="card-summary">一句话摘要</p>
        <div class="expand-hint">点击查看详情 →</div>
      </div>
    </a>
    <!-- ... -->
  </div>
</div>

<!-- Detail 模板 -->
<template class="detail-tpl" data-id="detail-1">
  <span class="detail-tag tag-red">时政 · 外交</span>
  <h2>完整标题</h2>
  <div class="detail-meta">📅 日期 &nbsp;|&nbsp; 📍 地点 &nbsp;|&nbsp; 📡 来源</div>
  <!-- 图片由 crawl_images.py + update_sections.py 自动处理，写模板时不需要手动加 -->
  <p>正文段落...</p>
  <div class="highlight-box">...</div>
  <a class="external-btn" href="新闻原文URL" target="_blank" rel="noopener">🔗 阅读原文</a>
</template>
```

**配图流程（写完 section 后自动执行）：**
1. `PYTHONPATH=tools python3 tools/validate_news.py` — 部署前先校验结构和真实原文链接
2. `PYTHONPATH=tools python3 tools/crawl_images.py` — 从每条新闻的 `external-btn` 原文 URL 提取候选配图，禁止使用搜索引擎图片结果
3. `python3 tools/review_images.py`（或 AI 手动审核）— 视觉模型判断图片是否与新闻内容相关
4. `PYTHONPATH=tools python3 tools/update_sections.py` — 根据审核结果插入/移除 `detail-visual`
5. `PYTHONPATH=tools python3 tools/validate_news.py` — 图片回写后再次校验
6. `PYTHONPATH=tools python3 tools/archive_news.py` — 保存当天快照并写入 SQLite，保留最近 15 天
7. 爬取失败或审核不通过的新闻不显示图片区域

**detail-visual 规则：**
- 图片来源：新闻原文页面正文图优先；36kr 等文章页优先 `p.image-wrapper img[data-img-size-val]` 这类置顶正文图，其次 `og:image` / `twitter:image`
- 过滤：logo / icon / avatar / qrcode / 通用占位图
- 审核通过 → 保留图片并插入 `detail-visual`
- 审核不通过 / 爬取失败 → **删除图片 + 移除 `detail-visual` div**
- 图片显示：`object-fit: contain` 按原比例完整展示，`max-height: 460px`（移动端 320px），不裁剪
- `onerror` 兜底：运行时图片加载失败隐藏 visual 区域

**⚠️ 每条新闻的 `<template>` 必须包含 `detail-visual` 占位 div：**
```html
<div class="detail-visual"><img src="" alt="" onerror="this.parentElement.style.display='none'"></div>
```
放在 `detail-meta` 之后、正文 `<p>` 之前。

**⚠️ 每条新闻的 `<template>` 必须包含 `detail-keypoints` 关键速览：**
```html
<div class="detail-keypoints">
  <div class="keypoint-card"><span>事件</span><strong>一句话说明发生了什么</strong></div>
  <div class="keypoint-card"><span>影响</span><strong>一句话说明影响谁或影响什么</strong></div>
  <div class="keypoint-card"><span>数据</span><strong>一句话列出关键数字或规模</strong></div>
  <div class="keypoint-card"><span>后续</span><strong>一句话说明接下来关注什么</strong></div>
</div>
```
- 放在 `detail-meta` 之后、`detail-visual` 之前。
- 每条新闻 3-4 个小卡片，不少于 3 个。
- 每个 `<strong>` 控制在 28 个中文字符以内。
- 如果某条新闻没有明确数据，第三张卡可以写「背景」或「看点」。

**每日更新只需重写对应的 section 文件，但必须通过 `validate_news.py` 后才允许部署。**

---

## 内容规范

### ⏰ 时效性要求（重要！）

- **新闻必须为最近 7 天内发生的事件**，最差不超过 14 天
- 搜新闻时使用 `freshness` 参数限制时间范围：`web_search` 的 `freshness` 设为 `"week"`
- 超过 14 天的旧闻不得入选，宁缺毋滥
- 每条新闻的 `detail-meta` 中必须标注具体日期

### 📰 新闻来源（优先从官方媒体爬取）

**国内新闻源：**
| 媒体 | 网址 | 适用板块 |
|------|------|----------|
| 今日头条 | https://www.toutiao.com/ | 国内/财经/科技 |
| 央视网 | https://news.cctv.com/ | 国内/时政 |
| 腾讯网 | https://news.qq.com/ | 国内/财经/科技 |
| 新浪网 | https://news.sina.com.cn/ | 国内/国际/财经 |
| 新华网 | https://www.news.cn/ | 国内/时政 |
| 人民网 | https://www.people.com.cn/ | 国内/时政 |
| 中国新闻网 | https://www.chinanews.com.cn/ | 国内/国际/财经 |
| 澎湃新闻 | https://www.thepaper.cn/ | 国内/财经/科技 |
| 财联社 | https://www.cls.cn/ | 财经/科技 |
| 证券时报 | https://www.stcn.com/ | 财经 |

**国际新闻源：**
| 媒体 | 网址 | 适用板块 |
|------|------|----------|
| Reuters | https://www.reuters.com/ | 国际/财经 |
| AP News | https://apnews.com/ | 国际 |
| BBC News | https://www.bbc.com/news | 国际 |
| CNN | https://www.cnn.com/ | 国际 |
| Euronews | https://www.euronews.com/ | 国际/欧洲 |
| Al Jazeera | https://www.aljazeera.com/ | 国际/中东 |

**科技/AI 新闻源：**
| 媒体 | 网址 | 适用板块 |
|------|------|----------|
| TechCrunch | https://techcrunch.com/ | 科技/AI |
| The Verge | https://www.theverge.com/ | 科技/AI |
| Ars Technica | https://arstechnica.com/ | 科技 |
| MIT Technology Review | https://www.technologyreview.com/ | 科技/AI |
| VentureBeat | https://venturebeat.com/ | AI/科技 |
| 36氪 | https://36kr.com/ | 科技/AI/财经 |
| IT之家 | https://www.ithome.com/ | 科技/AI |
| 量子位 | https://www.qbitai.com/ | AI |
| 雷峰网 | https://www.leiphone.com/ | AI/科技 |
| 晚点 LatePost | https://www.latepost.com/ | 科技/财经 |
| 机器之心 | https://www.jiqizhixin.com/ | AI |
| Hugging Face Blog | https://huggingface.co/blog | AI/开源 |
| arXiv | https://arxiv.org/ | AI/论文 |
| Papers with Code | https://paperswithcode.com/ | AI/论文 |
| CNBC | https://www.cnbc.com/ | 财经/科技 |

> **重要：** `external-btn` 的 href 必须指向实际新闻原文页面（不是首页），因为爬图脚本会从这个 URL 提取配图。禁止使用百度/Bing/Google 等搜索结果页、媒体首页、`#` 或 `javascript:` 作为原文链接。找不到真实原文链接的新闻必须替换，不得上线。

### 跨板块去重（必须执行）

- 五个板块不得复用同一个新闻事件，即使标题不同、来源不同，也只能保留在一个最合适的板块。
- 科技/AI 最容易重复：同一模型发布、同一公司 AI 基建、同一开源项目，只保留一条。
- 板块归属优先级：
  - 纯模型、Agent、论文、开源项目、AI 产品发布 → 人工智能
  - 航天、芯片、通信、新能源、硬件、基础科研突破 → 科技动态
  - AI 公司财报、股价、融资、裁员、产业链订单 → 财经快讯
  - 国家政策、监管、公共安全、国内民生事件 → 国内要闻
  - 国际冲突、外交、海外选举、全球公共事件 → 国际焦点
- 发布前必须运行 `PYTHONPATH=tools python3 tools/audit_news_sources.py --dist dist --no-network`；若出现 `cross-section similar event`，必须替换低优先级板块里的新闻。

### 各板块条数（弹性，每板块 ≤ 6 条）

| 板块 | 建议条数 | 选题方向 |
|------|----------|----------|
| 国内要闻 | 4-6 | 时政/经济/民生/外交/司法/安全 |
| 国际焦点 | 3-5 | 中东/半岛/欧美/气候/地缘 |
| 财经快讯 | 3-5 | A股/IPO/政策/能源/资源 |
| 科技动态 | 2-4 | 航天/半导体/新能源/通信 |
| 人工智能 | 3-6 | 大模型/Agent/国产/开源/论文 |

> 条数不固定，按当日新闻热度灵活调整，但单板块不超过 6 条。

### AI 板块滚动选题池
- 大模型更新：Claude/GPT/Gemini/DeepSeek
- 国产模型：Kimi/智谱GLM/MiniMax/豆包/通义/百川
- Agent 框架：AutoGPT/CrewAI/LangGraph/Computer Use
- 有趣 Skill：GitHub 热门 AI 工具
- 顶会论文：NeurIPS/ICML/CVPR/ACL/AAAI
- 期刊论文：Nature/Science AI/JMLR/TPAMI
- 开源项目：HuggingFace 热点
- 行业趋势：监管/算力/AI+行业

### 每条新闻结构

**卡片（列表态）：**
- `tag`（彩色标签）+ `emoji-icon` + 标题 + 一句话摘要

**详情（弹窗态）：**
- `detail-tag` + `h2` 标题
- `detail-meta`（日期 | 地点 | 来源）
- `detail-visual`（大 emoji 视觉区）
- 正文段落（1-3 段）
- `highlight-box` 或 `key-points` 或 `detail-stats`（数据卡）
- 可选：`detail-quote`（引用）
- `external-btn`（外链按钮）

> 详情内容丰富度可灵活调整：重大新闻写详细，一般新闻简洁即可。

### 标签颜色体系

| 颜色 | 适用场景 |
|------|----------|
| `tag-red` | 时政/事故/军事/Anthropic |
| `tag-blue` | 教育/朝韩/市场/航天/Google |
| `tag-green` | 民生/交通/能源/AI医疗/OpenAI |
| `tag-orange` | 救灾/安全/气候/政策/国产模型 |
| `tag-purple` | 外交/娱乐/IPO/DeepSeek |

---

## 部署流程

### 日常更新（只改内容）

```bash
# 1. 修改对应板块文件
#    /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist/sections/domestic.html
#    ...

# 2. 部署前校验：真实原文链接、卡片/详情结构、新闻数量
PYTHONPATH=/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools \
python3 /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools/validate_news.py

# 3. 从新闻原文爬取配图（优先正文大图，fallback og:image/json-ld）
PYTHONPATH=/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools \
python3 /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools/crawl_images.py

# 4. AI 审核图片相关性（视觉模型判断图片是否与新闻内容匹配，不匹配的删除）
python3 tools/review_images.py

# 5. 根据审核结果更新 section HTML（有图加 img，无图移除 visual）
PYTHONPATH=/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools \
python3 /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools/update_sections.py

# 6. 图片回写后再次校验
PYTHONPATH=/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools \
python3 /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools/validate_news.py

# 7. 保存当天归档（news.json + sections + images + SQLite），保留最近 15 天
PYTHONPATH=/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools \
python3 /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/tools/archive_news.py

# 8. 同步到 nginx
sudo rsync -av --delete /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist/ /var/www/html/niu-secretary/news/

# 9. 验证
curl -s http://124.222.22.171/niu-secretary/news/ | head -20
```

### AI 图片审核机制

- **工具：** `tools/review_images.py`
- **原理：** 读取每条新闻的标题和正文摘要，用视觉模型判断爬取的图片是否与新闻内容相关
- **审核标准：** 相关人物/场景/事件/数据图表 → 通过；通用图库照/logo/广告/无关内容 → 不通过
- **不合格处理：** 直接删除图片文件，`update_sections.py` 会自动移除对应的 `detail-visual` 区域
- **模型配置：** 通过环境变量 `IMAGE_REVIEW_MODEL` / `IMAGE_REVIEW_API_BASE` / `IMAGE_REVIEW_API_KEY` 控制（默认 localhost:9900）
- **审核方式：** 两种可选
  1. Python 脚本（`python3 tools/review_images.py`）— 需配置可用的 OpenAI 兼容视觉 API
  2. Agent 手动审核 — cron 子会话中直接用 `image` 工具逐张审核（当前默认方式）

### 改版（改样式/结构）

```bash
# 修改 dist/style.css 或 dist/index.html
# 然后同样 rsync 部署（含 assets/images/）
sudo rsync -av /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist/ /var/www/html/niu-secretary/news/
```

---

## Cron 约定（2026-09-15 已收编为 no_agent 统一管线）

- 每天 **10:00 Asia/Shanghai** 自动更新
- Job `94f85806c890`（新闻社·内容生成）— **no_agent 模式**，脚本 `bash run_pipeline.sh`：
  1. `tools/fetch_news_candidates.py` — RSS 直抓官方媒体（无 LLM）
  2. `tools/summarize_news_llm.py` — NiuLLM("content") 写摘要 → 渲染 section HTML
  3. `tools/validate_news.py` → `crawl_images.py` → `tools/review_images.py`（NiuLLM("vision") 真实审核）
  4. `tools/update_sections.py` 回写图片引用
  5. `tools/build_qq_digest.py` 生成 QQ briefing → `dist/qq_digest.txt`
  6. 末行输出 `{"wakeAgent": false}` — 本 job **静默完成**，stdout 不打扰 QQ
- Job `7939a11e048c`（10:45 新闻社部署，deliver=qqbot）— stdout 只含最终 briefing 正文：
  终检 validate → archive → rsync → HTTP 验证 → `cat dist/qq_digest.txt`
- 暂停的 job：`222fdc42c679` 后处理（并入管线）、`fb57b11ea956` 图片管线（审核并入管线）
- 校验失败时必须停止，不得 rsync 覆盖线上页面。
- 配图只能从原文 URL 抓取，不得使用搜索引擎图片结果。
- 每天文件归档到 `news-daily/archive/YYYY-MM-DD/`，同时写入 `news-daily/news_daily.db`。
- SQLite 表：`news_days`、`news_items`、`news_tags`、`image_candidates`。
- 文件归档和 SQLite 都只保留最近 15 天。
- **LLM 调用**：全部走 `niu_core/llm_client`（逻辑模型 content / vision），路由见 `config/models.yaml`，禁止在脚本里硬编码 key 或 base_url。

---

## 样式原则（性能优先）

- 浅色背景 + 静态彩色柔光球体（无动画）
- 卡片：`background: rgba(255,255,255,0.42)` + `backdrop-filter: blur(16px)`
- 仅主容器使用 blur（顶栏/统计栏/卡片/modal），内部组件不加 blur
- transition 用具体属性名，避免 `all`
- 无 SVG 噪点、无背景动画、无 saturate
- CSS 变量统一管理颜色/间距，方便主题切换

---

## JS 加载逻辑（index.html 内嵌）

```javascript
const SECTIONS = ['domestic', 'international', 'finance', 'tech', 'ai'];

async function loadSections() {
  for (const name of SECTIONS) {
    const res = await fetch(`sections/${name}.html?t=${Date.now()}`);
    if (res.ok) {
      const html = await res.text();
      document.getElementById(`slot-${name}`).innerHTML = html;
      // 解析 <template> 注册 detail 数据
      registerDetails(document.getElementById(`slot-${name}`));
    }
  }
  updateStats();
}

function registerDetails(container) {
  container.querySelectorAll('template.detail-tpl').forEach(tpl => {
    const id = tpl.dataset.id;
    detailMap[id] = tpl.innerHTML;
  });
}

function openDetail(id) {
  document.getElementById('detail-body').innerHTML = detailMap[id] || '';
  document.getElementById('detail-overlay').classList.add('active');
}

function closeDetail(e) {
  if (!e || e.target === e.currentTarget)
    document.getElementById('detail-overlay').classList.remove('active');
}

function updateStats() {
  // 动态统计各 section 卡片数量并更新统计栏
  SECTIONS.forEach(name => {
    const cards = document.querySelectorAll(`#section-${name} .news-card`).length;
    const el = document.getElementById(`stat-${name}`);
    if (el) el.textContent = cards;
  });
}

document.addEventListener('DOMContentLoaded', loadSections);
```

---

## 推送格式

部署后发到 QQ 私聊：
```
📰 牛秘书新闻速报 · YYYY年M月D日

🔥 今日头条：
1. [标题一]
2. [标题二]
3. [标题三]

👉 完整图文页面：http://124.222.22.171/niu-secretary/news/
```

---

## 用户画像 · 个性化精选（v1.1，2026-05-30）

新闻社接入牛秘书 AI 画像链路：首页「我的关注 · 今日精选」面板根据 `news` 画像从当天新闻里筛选/排序。

- 画像编辑入口：**只走主页牛秘书 AI 对话**（如「我关注 AI 和科技，别给我推娱乐」→ AI 识别 preference → 生成 `profile.update` 动作卡 → 确认落库）。本页面板只读展示。
- 推荐动作：`news.recommend`（confirmByDefault=false）
  - 后端 `server/action_handlers.py` 只读解析 `dist/sections/*.html`（标签/标题/摘要/板块），按画像 `topics`/`excludeTopics`/`regions` 关键词打分排序。
  - `topics` 命中标签 +3 / 标题 +2 / 摘要 +1；`excludeTopics` 命中则剔除；有匹配项时 `personalized=true`。
  - 画像为空时回落「今日要闻」（按板块顺序），不报错。
- `news` 画像字段：`topics[] / excludeTopics[] / depth(headline|brief|deep) / regions[] / notes`，定义在 `server/store.py:DEFAULT_PROFILES`。
- 前端面板：`dist/index.html` 内联脚本 `loadFocus()`，调 `/niu-secretary/api/actions/execute`，精选条目能点开复用现有 `openDetail` 详情。
- ⚠️ 当前推荐仍直接解析 section HTML；每日流程会额外导出 `dist/news.json` 和 `archive/YYYY-MM-DD/news.json` 作为归档与后续迁移基础。若后续切换，可让 `news.recommend` 优先读当天 JSON。

---

## 运维问题记录

### 2026-06-04：手动推送中遇到的三个问题及解决方案

#### 问题 1：web_search provider 不稳定

**现象：** 同一会话中多次调用 `web_search`，provider 在 duckduckgo → kimi → searxng 之间随机切换。kimi 不支持 `freshness` 参数，searxng 未配置直接报错。

**根因：** OpenClaw 的搜索 provider 会动态切换，不同 provider 能力差异大。

**解决方案：**
- 首轮搜索不加 `freshness` 参数，避免非 duckduckgo provider 报错
- 用 `web_fetch` 抓取新闻汇总页面替代多次独立搜索，效率更高
- 关键补充搜索用 `web_fetch` 直接抓具体页面

#### 问题 2：image 视觉模型认证失败

**现象：** AI 配图审核环节，`image` 工具报 `Your authentication token has been invalidated`。`review_images.py` 脚本依赖本地 localhost:9900 视觉 API，也可能不可用。

**解决方案：** 手动审核备选方案——
- 根据爬取来源判断：`court.gov.cn`/`fmprc.gov.cn` 等官网通常返回 logo/icon/qrcode
- 根据文件大小判断：<10KB 大概率是图标/logo/banner，>100KB 通常是大图新闻配图
- 根据爬取日志中的 URL 路径名判断：含 `qrcode`/`logo`/`icon` 关键词的 → FAIL
- 审核标准：相关人物/场景/事件/数据图表 → 通过；通用图库照/logo/二维码/订阅广告 → 不通过

**⚠️ 手动审核不如视觉模型精确，优先级：视觉模型 > 手动推断。**

#### 问题 3：cron 上次执行报错 "Request was aborted"

**现象：** 每日 cron（Job ID `7567c2d1`）上次运行耗时 427 秒后 abort，可能超时。

**根因：** 搜索+写 section+爬图+AI审核全流程耗时较长，900 秒超时可能不够，或者中间某步卡住。

**建议修复（可选）：**
- 增大 `timeoutSeconds` 至 1200
- 或者拆分流程：搜索+写 section 一个 cron，爬图+审核+部署 另一个 cron
- 当前手动推送全流程约 3-4 分钟即可完成
