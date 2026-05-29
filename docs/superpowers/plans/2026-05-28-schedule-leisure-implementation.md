# Schedule And Leisure Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh `niu-secretary/schedule` and `niu-secretary/leisure` into the approved private-secretary visual system and deploy them under `/niu-secretary/schedule/` and `/niu-secretary/leisure/`.

**Architecture:** Keep the existing pure static architecture. Replace only the two homepage documents, preserve existing `logo.png`, `js/store.js`, `js/recommend.js`, and JSON data files, and keep relative links so static nginx deployment works without a backend.

**Tech Stack:** HTML5, CSS Grid/Flexbox, vanilla JavaScript, localStorage, static nginx hosting.

---

## File Structure

- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/schedule/dist/index.html`
  - Owns the complete schedule homepage UI, current-date rendering, localStorage summary counts, and sample schedule composition.
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/leisure/dist/index.html`
  - Owns the complete leisure homepage UI, recommendation JSON loading, fallback content, and taste profile summary.
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/SKILL.md`
  - Corrects function matrix paths and notes that schedule/leisure are deployed under `/niu-secretary/`.
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/schedule/SKILL.md`
  - Replaces the obsolete dark-luxury visual requirement with the approved modern secretary folder palette.
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/leisure/SKILL.md`
  - Replaces the obsolete dark-luxury visual requirement with the approved warm leisure folder palette.
- Deploy target: `/var/www/html/niu-secretary/schedule/`
- Deploy target: `/var/www/html/niu-secretary/leisure/`

## Task 1: Refresh Schedule Homepage

**Files:**
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/schedule/dist/index.html`

- [ ] **Step 1: Replace the dark control-panel shell**

Replace the current black/gold CSS variables with the approved schedule palette:

```css
:root {
  --page: #e8ece6;
  --paper: #fffefa;
  --paper-soft: #f5f7f2;
  --ink: #243039;
  --muted: #59676b;
  --faint: #7c8889;
  --sage: #6f857a;
  --navy: #243746;
  --copper: #d0b37c;
  --line: #ccd5ce;
  --line-soft: #e0e4dd;
  --shadow: 0 24px 80px rgba(34, 48, 54, .13);
  --radius: 18px;
  --ease: cubic-bezier(.2, .8, .2, 1);
}
```

Expected result: the page no longer uses a dark background or gold text as the dominant visual system.

- [ ] **Step 2: Build the approved schedule layout**

Implement these sections in order:

```html
<main class="schedule-shell">
  <section class="bureau-hero">
    <div>
      <p class="kicker">Niu Secretary Schedule Bureau</p>
      <h1>牛秘书时务局</h1>
      <p class="lead">排班、提醒、代办和目标收进同一个事务夹。先看轻重缓急，再看时间。</p>
    </div>
    <div class="date-card">
      <span>今日</span>
      <strong id="today-day">28</strong>
      <span id="today-weekday">星期四</span>
    </div>
  </section>

  <section class="workbench">
    <section class="panel schedule-panel">
      <div class="panel-title">
        <h2>今日排班</h2>
        <span id="today-count">0 项</span>
      </div>
      <div class="timeline" id="timeline"></div>
    </section>

    <aside class="side-stack">
      <section class="panel">
        <h2>秘书提醒</h2>
        <div class="priority-list" id="priority-list"></div>
      </section>
      <section class="panel">
        <h2>事务抽屉</h2>
        <nav class="drawer-grid" aria-label="时务局模块"></nav>
      </section>
    </aside>
  </section>

  <section class="briefing-note">
    <div>
      <p class="note-label">今日批注</p>
      <p><strong>上午处理要务，下午清杂事，晚上收档。</strong> 日程不需要排满，需要排准；今天完成三件关键事即可。</p>
    </div>
    <div class="note-actions">
      <button type="button">生成明日预排</button>
      <button type="button">收进复盘</button>
    </div>
  </section>
</main>
```

Expected result: desktop first screen shows identity, today schedule, secretary reminders, module drawer, and the approved note component.

- [ ] **Step 3: Preserve useful localStorage behavior**

Use the existing storage keys and provide graceful sample rows when no data exists:

```js
const store = {
  events: JSON.parse(localStorage.getItem('niu_schedule_events') || '[]'),
  todos: JSON.parse(localStorage.getItem('niu_schedule_todos') || '[]'),
  dates: JSON.parse(localStorage.getItem('niu_schedule_dates') || '[]'),
  goals: JSON.parse(localStorage.getItem('niu_schedule_goals') || '[]')
};
```

Render today's events first. If there are no events, render the sample timeline from the approved visual direction: 晨间梳理、项目推进、生活代办、复盘收档.

Expected result: first load is visually complete, and existing local data still affects counts and schedule rows.

- [ ] **Step 4: Validate schedule markup**

Run:

```bash
node --check /home/ubuntu/.openclaw/workspace/niu-secretary/schedule/dist/index.html
```

Expected result: this command may fail because HTML is not JavaScript. If it fails with an HTML parsing error, run a browser/curl smoke test after deployment instead. Do not treat this as a blocker for static HTML.

## Task 2: Refresh Leisure Homepage

**Files:**
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/leisure/dist/index.html`

- [ ] **Step 1: Replace the dark leisure shell**

Use the approved warm leisure palette:

```css
:root {
  --page: #f1eee7;
  --paper: #fffdf7;
  --paper-soft: #f7f2e9;
  --ink: #2d2a25;
  --muted: #676157;
  --faint: #8a8174;
  --tea: #c9975f;
  --blue: #66848e;
  --navy: #243746;
  --olive: #7f8a6a;
  --line: #d7d0c1;
  --line-soft: #e3dbce;
  --shadow: 0 24px 80px rgba(48, 42, 32, .13);
  --radius: 18px;
  --ease: cubic-bezier(.2, .8, .2, 1);
}
```

Expected result: the leisure page feels warm and relaxed, not black/gold and not newspaper-like.

- [ ] **Step 2: Build the approved leisure layout**

Implement these sections in order:

```html
<main class="leisure-shell">
  <section class="leisure-hero">
    <div>
      <p class="kicker">Niu Secretary Leisure Collection</p>
      <h1>牛秘书闲趣集</h1>
      <p class="lead">按时间、心情和口味给少量精选。今晚看什么、听什么、读什么，不用刷长榜。</p>
    </div>
    <aside class="taste-card">
      <h2>口味档案</h2>
      <div class="taste-meter"><span></span></div>
      <div class="taste-tags" id="taste-tags"></div>
    </aside>
  </section>

  <section class="recommend-workbench">
    <section class="panel featured-panel">
      <h2>今晚首推</h2>
      <div class="featured-choice" id="featured-choice"></div>
    </section>

    <aside class="panel">
      <h2>今日候选</h2>
      <div class="candidate-list" id="candidate-list"></div>
    </aside>
  </section>

  <section class="leisure-note">
    <div>
      <p class="note-label">闲趣批注</p>
      <p><strong>今天适合低负担内容。</strong> 不追热点，不刷长榜，按你的时间、心情和口味给出少量精选。</p>
    </div>
    <div class="note-actions">
      <button type="button">换一组</button>
      <button type="button">加入今晚</button>
    </div>
  </section>
</main>
```

Expected result: first screen presents one main recommendation, taste profile, candidate list, and the approved leisure note.

- [ ] **Step 3: Preserve JSON recommendation loading**

Continue loading:

```js
fetch('data/movies.json')
fetch('data/music.json')
fetch('data/podcasts.json')
```

Normalize loaded items into:

```js
{
  type: '影视',
  title: item.title,
  reason: item.reason || '适合今晚低负担放松。',
  score: item.matchScore || 88,
  href: 'movies.html',
  duration: item.duration ? `${item.duration}m` : '45m'
}
```

When no JSON data loads, render four fallback candidates: 影视、音乐、播客、阅读.

Expected result: existing data files still enhance the page, but the page looks complete without them.

- [ ] **Step 4: Validate leisure data loading path**

Run after deployment:

```bash
curl -I http://127.0.0.1/niu-secretary/leisure/data/movies.json
curl -I http://127.0.0.1/niu-secretary/leisure/data/music.json
curl -I http://127.0.0.1/niu-secretary/leisure/data/podcasts.json
```

Expected result: each returns HTTP 200.

## Task 3: Update Brand And Subproject Documentation

**Files:**
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/SKILL.md`
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/schedule/SKILL.md`
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/leisure/SKILL.md`

- [ ] **Step 1: Correct access paths in root brand skill**

Set planned/active paths to:

```markdown
| 📅 牛秘书时务局 | `/niu-secretary/schedule/` | 日程管理：今日排班、秘书提醒、事务抽屉、目标追踪 |
| 🎬 牛秘书闲趣集 | `/niu-secretary/leisure/` | 休闲推荐：今晚首推、今日候选、口味档案 |
```

Expected result: root brand docs match the deployed `/niu-secretary/` namespace.

- [ ] **Step 2: Correct schedule visual requirement**

Replace schedule's obsolete visual paragraph with:

```markdown
## 视觉体系

采用现代私人秘书事务夹风格：

- 雾灰绿背景（`#e8ece6`），避免新闻社泛黄报刊感
- 象牙白卡片（`#fffefa`），保留文件夹和纸张秩序
- 墨蓝要务色（`#243746`），用于关键事项和高优先级
- 铜金点缀（`#d0b37c`），用于日期、批注边线和品牌细节
- 首页以今日排班、秘书提醒、事务抽屉、今日批注为第一屏核心
```

- [ ] **Step 3: Correct leisure visual requirement**

Replace leisure's obsolete visual paragraph with:

```markdown
## 视觉体系

采用私人秘书休闲推荐夹风格：

- 温暖象牙背景（`#f1eee7`），区别于时务局的办公感
- 推荐卡片使用 `#fffdf7`，保持轻松、干净、可读
- 茶金（`#c9975f`）表达休闲温度
- 灰蓝（`#66848e`）用于候选、批注和轻按钮
- 首页以今晚首推、今日候选、口味档案、闲趣批注为第一屏核心
```

Expected result: docs no longer instruct future work to return to black/gold.

## Task 4: Deploy And Verify

**Files:**
- Deploy from: `/home/ubuntu/.openclaw/workspace/niu-secretary/schedule/dist/`
- Deploy from: `/home/ubuntu/.openclaw/workspace/niu-secretary/leisure/dist/`
- Deploy to: `/var/www/html/niu-secretary/schedule/`
- Deploy to: `/var/www/html/niu-secretary/leisure/`

- [ ] **Step 1: Copy schedule dist**

Run:

```bash
sudo mkdir -p /var/www/html/niu-secretary/schedule
sudo cp -r /home/ubuntu/.openclaw/workspace/niu-secretary/schedule/dist/* /var/www/html/niu-secretary/schedule/
```

Expected result: `/var/www/html/niu-secretary/schedule/index.html` is updated.

- [ ] **Step 2: Copy leisure dist**

Run:

```bash
sudo mkdir -p /var/www/html/niu-secretary/leisure
sudo cp -r /home/ubuntu/.openclaw/workspace/niu-secretary/leisure/dist/* /var/www/html/niu-secretary/leisure/
```

Expected result: `/var/www/html/niu-secretary/leisure/index.html` is updated.

- [ ] **Step 3: Set ownership**

Run:

```bash
sudo chown -R www-data:www-data /var/www/html/niu-secretary/schedule /var/www/html/niu-secretary/leisure
```

Expected result: nginx can serve all copied files.

- [ ] **Step 4: Smoke-test routes**

Run:

```bash
curl -I http://127.0.0.1/niu-secretary/schedule/
curl -I http://127.0.0.1/niu-secretary/leisure/
curl -s http://127.0.0.1/niu-secretary/schedule/ | rg "牛秘书时务局|今日批注"
curl -s http://127.0.0.1/niu-secretary/leisure/ | rg "牛秘书闲趣集|闲趣批注"
```

Expected result: both routes return HTTP 200 and contain the approved page text.

## Self-Review

- Spec coverage: schedule palette, schedule layout, leisure palette, leisure layout, docs, and deployment are all mapped to tasks.
- Placeholder scan: no TBD/TODO/fill-in-later language remains.
- Type consistency: storage keys match existing pages; leisure JSON paths match current `dist/data/*.json`.
