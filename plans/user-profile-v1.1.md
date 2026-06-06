# 牛秘书 AI · 用户画像系统 v1.1（新闻社 + 闲趣集落地方案）

> 状态：待帅锅拍板 · 起草：2026-05-30 · 作者：🐄 牛秘书
> 前置：v1 已完成 fitness/schedule 的画像+推荐闭环（见 user-profile-v1.md）

## 0. 一句话目标

把新闻社、闲趣集也接进牛秘书 AI 的「画像驱动」链路：聊天调画像 → 画像驱动 recommend → 板块页面展示个性化推荐。

## 1. 现状盘点（已就绪 vs 待补）

**后端已就绪（v1 顺手做了）：**
- `store.DEFAULT_PROFILES` 已含 `news` / `leisure` 画像字段
- `user_profiles` / `profile_changes` 表通用，已支持四板块
- `profile.get/update/reset/changes` 通用动作已上线
- `assistant.py`：intent 分类、`PROFILE_FIELD_HINTS`、`local_extract_preference` 都已覆盖 news/leisure
- 也就是说：**「聊天 → 更新新闻社/闲趣集画像」这条路其实已经能跑**，只差前端展示和 recommend

**待补（v1.1 范围）：**
| 项 | 文件 | 说明 |
|----|------|------|
| `news.recommend` handler | action_handlers.py | 读画像 + 新闻内容，按关注话题筛选/排序 |
| `leisure.recommend` handler | action_handlers.py | 读画像 + 影视库，按类型/心情筛选 |
| 注册两个动作 | capabilities.py | confirmByDefault=False |
| 单测 | test_niu_secretary_api.py | 两个 recommend + news/leisure 偏好抽取 |
| 新闻社画像面板 | news-daily/dist | 「我的关注 · 今日精选」面板 |
| 闲趣集画像面板 | leisure/dist | 复用现有 taste-card，接后端画像 |

## 2. 待拍板决策（4 个）

### 决策 1：news.recommend 的数据源（新闻无 JSON）
新闻内容直接嵌在 `news-daily/dist/sections/*.html`，没有结构化 JSON。两个方案：

- **方案 A（推荐，零侵入）**：后端读 `sections/*.html`，正则抽出每条新闻的「标签 + 标题 + 摘要 + 板块」，按画像 `topics`/`excludeTopics` 关键词打分，返回 top N 条匹配的今日新闻。立即可用，不动现有新闻 cron。
- 方案 B（更干净，但要改 cron）：给每日新闻 cron 加一步导出 `news.json`，后端读 JSON。结构更稳，但要改 cron prompt + 等明天 10:00 才有数据。

> 我的建议：**A 起步**（今天就能验证），B 列入 v1.2。

### 决策 2：闲趣集画像「两套」如何统一
闲趣集自己已有 `leisure/dist/data/preferences.json`（cron 每日生成的口味档案），现在又有后端 `user_profiles.leisure`。两套并存会乱。方案：

- **方案 A（推荐）**：后端 `user_profiles.leisure` 为**权威画像**（你聊天调的长期偏好）；`preferences.json` 降为「内容库自带的兜底标签」。`leisure.recommend` 优先用后端画像，画像空字段再回落 preferences.json。
- 方案 B：让 `profile.update` 同时回写 preferences.json，保持单一文件。耦合更紧，cron 覆盖风险高，不推荐。

> 我的建议：**A**。后端画像赢，preferences.json 当兜底。

### 决策 3：要不要做「主动推送」
v1 推送是「拉」（你问才生成）。v1.1 是否加 cron 定时把 recommend 主动推到 QQ？
- 选项：① 暂不做，仍走「拉」；② 加一条 cron 早报，把四板块 recommend 汇总推一次。
> 我的建议：v1.1 先把面板+recommend 打通（拉），**主动推单独排期**，避免一次摊太大。

### 决策 4：推荐文案用规则还是模型
v1 是规则生成文案。v1.1 是否上模型润色？
> 我的建议：**先规则**（稳、快、零成本），跑通后再考虑模型。和 v1 保持一致。

## 3. 实施步骤（拍板后执行）

### 阶段 A：后端 recommend（纯本地可逆，先做并验证）
1. `action_handlers.py`：实现 `news.recommend`（解析 sections + 画像打分）+ `leisure.recommend`（读 data/*.json + 画像打分）
2. `capabilities.py`：注册两个动作
3. `test_niu_secretary_api.py`：加单测（recommend 返回结构、画像筛选生效、news/leisure 偏好抽取已有可补）
4. 验证：`python3 -m pytest` 全过 + 本地起 API e2e

### 阶段 B：前端画像面板
5. 新闻社 `news-daily/dist/index.html`：加「我的关注 · 今日精选」面板，调 `profile.get`(news) + `news.recommend`
6. 闲趣集 `leisure/dist/index.html`：把现有 `taste-card`（写死的「轻松/不烧脑」标签）接到后端 `profile.get`(leisure)，候选区融合 `leisure.recommend` 结果
7. 注意闲趣集是 src→dist 还是直接 dist：本模块直接改 dist（无 build.js，确认中）

### 阶段 C：部署 + 线上验证
8. 后端：`sudo -n systemctl restart niu-secretary-api.service`
9. 前端：`sudo -n cp` 到 nginx，经公网路径验证
10. e2e：首页和 AI 聊「我爱看科幻/别推娱乐新闻」→ 确认 → 新闻社/闲趣集面板读到画像 + recommend 生效

### 阶段 D：收尾
11. 更新 news-daily/SKILL.md + leisure/SKILL.md（新动作、画像数据流）
12. 更新 MEMORY.md，勾掉 v1.1 待办

## 4. 风险与约定
- 后端读 `sections/*.html` 用只读正则，解析失败要兜底返回空列表（不抛错）
- `leisure.recommend` 读 JSON 失败兜底空列表，不阻塞页面
- API key 仍硬编码（独立待办，不在本次范围，但新代码不再新增硬编码）
- systemd 重启用 `sudo -n`；静态部署用 `sudo -n cp` + chown www-data
- 闲趣集 cron 当前因 model allowlist 报错（`opencodego/qwen3.7-max` 不在白名单），顺手记一笔，但属独立问题，不在本方案范围

## 5. 顺带发现的小问题（不在范围，仅记录）
- 闲趣集每日 cron（Job `0fc99702`）上次运行失败：`payload.model 'opencodego/qwen3.7-max' rejected by allowlist`。白名单里是 `opencodegoa/qwen3.7-max`（多个 a）。要修的话改 cron 的 model 即可，等你说一声。
