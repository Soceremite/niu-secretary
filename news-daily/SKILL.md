---
name: news-daily
description: "每日新闻头条生成与推送——搜新闻、更新 HTML 页面、部署到 nginx、推送链接"
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron,sessions_send
user-invocable: true
last_updated: "2026-05-29"
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
1. `python3 tools/crawl_images.py` — 从每条新闻的 `external-btn` URL 爬取 `og:image` 配图
2. `python3 tools/review_images.py`（或 AI 手动审核）— 视觉模型判断图片是否与新闻内容相关
3. `python3 tools/update_sections.py` — 根据审核结果插入/移除 `detail-visual`
4. 爬取失败或审核不通过的新闻不显示图片区域

**detail-visual 规则：**
- 图片来源：新闻原文页面的 `og:image` / `twitter:image`
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

**每日更新只需重写对应的 section 文件。**

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
| 36氪 | https://36kr.com/ | 科技/AI/财经 |
| 机器之心 | https://www.jiqizhixin.com/ | AI |
| CNBC | https://www.cnbc.com/ | 财经/科技 |

> **重要：** `external-btn` 的 href 必须指向实际新闻原文页面（不是首页），因为爬图脚本会从这个 URL 提取配图。

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

# 2. 从新闻原文爬取配图（优先正文大图，fallback og:image）
python3 tools/crawl_images.py

# 3. AI 审核图片相关性（视觉模型判断图片是否与新闻内容匹配，不匹配的删除）
python3 tools/review_images.py

# 4. 根据审核结果更新 section HTML（有图加 img，无图移除 visual）
python3 tools/update_sections.py

# 5. 同步到 nginx
sudo rsync -av --delete /home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist/ /var/www/html/niu-secretary/news/

# 6. 验证
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

## Cron 约定

- 每天 **10:00 Asia/Shanghai** 自动更新
- Job ID: `7567c2d1-9fa9-4d79-a881-a53402d0ba2c`
- 更新流程：搜新闻 → 写各 section HTML → 爬图 → AI 审核图片 → rsync 部署 → 推送 QQ

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
