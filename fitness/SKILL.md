---
name: fitness
description: "牛秘书塑形馆——AI驱动的身体重组私教系统：Web数据看板 + QQ教练对话，覆盖评估、训练、饮食、恢复、咨询、报告全闭环。"
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron,sessions_send,image
user-invocable: true
last_updated: "2026-05-30"
---

# 牛秘书塑形馆

> **品牌规范与视觉体系请参考 [主 SKILL.md](../SKILL.md)**

AI 驱动的身体重组私教系统。Web 端做数据看板和结构化录入，QQ 教练做日常对话、计划调整和行为陪伴。围绕评估→训练→饮食→恢复→咨询→复测形成长期闭环。

## 团队分工

- **🐋 DeepSeek V4 Pro** — 日常教练对话、饮食识别、周报生成
- **🧪 Claude Opus 4.6** — UI 开发、架构优化、复杂计算逻辑
- **🐄 牛秘书** — 产品总监

## 架构概览

```
用户入口
├── 📱 QQ对话 → OpenClaw Agent → 大模型（饮食识别/教练问答/计划调整）
└── 🖥️ Web页面 → 纯静态 HTML + JS Islands（看板/录入/趋势）

数据流
├── 营养日志 → 后端 Action API（fitness.nutrition.list/create/delete）为唯一数据源
├── 后端 SQLite ← 牛秘书 AI / QQ 教练 / 图片识别 写入 → 看板直接读到
└── IndexedDB/localStorage → 离线缓存兜底；未建模的训练/评估数据仍留本地
```

## 核心约束

| 约束 | 说明 |
|------|------|
| 静态 HTML + Islands | 无 SPA 框架、无前端路由、无独立后端进程 |
| 营养后端为数据源 | 营养日志后端 SQLite 为主（默认拉 180 天 list），IndexedDB/localStorage 退为离线缓存 |
| 纯静态部署 | `npm run build` → `dist/` → Nginx 静态服务 |
| AI 走 Agent | 饮食识别、教练对话、周报生成全部通过 OpenClaw Agent |
| 视觉继承主页 | 暗红黑体系 + 健康管理工作台风格 |
| Feature-first | 按业务模块聚合代码 |

## 文件路径

| 文件 | 路径 |
|------|------|
| 项目根目录 | `/home/ubuntu/.openclaw/workspace/niu-secretary/fitness/` |
| 源码 | `src/` |
| 构建产物 | `dist/` |
| 数据文件 | `data/` |
| 部署目标 | `/var/www/html/niu-secretary/fitness/` |
| 访问地址 | `http://124.222.22.171/niu-secretary/fitness/` |

## 构建与部署

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/fitness
npm run build
sudo cp -r dist/* /var/www/html/niu-secretary/fitness/
```

构建脚本 `build.js` 将 `src/` 组装到 `dist/`，同时复制 `data/` 目录。

## 目录结构

```
fitness/
├── SKILL.md              # 本文件
├── build.js              # 构建脚本
├── package.json          # 极简依赖
├── src/
│   ├── index.html        # 应用壳（导航 + 内容区）
│   ├── style.css         # 全局样式
│   ├── theme.css         # 主题变量
│   ├── sw.js             # Service Worker
│   ├── manifest.json     # PWA manifest
│   ├── logo.png          # 品牌 Logo（圆形展示）
│   ├── sections/         # 各模块 HTML 片段
│   │   ├── dashboard.html
│   │   ├── assessment.html
│   │   ├── training.html
│   │   ├── nutrition.html
│   │   ├── recovery.html
│   │   └── consult.html
│   └── js/
│       ├── app.js        # 导航切换 + section 懒加载
│       ├── lib/          # 同构工具库（纯函数）
│       └── features/     # 各模块交互逻辑
├── data/                 # 持久化 JSON（Agent 可直写）
└── dist/                 # 构建产物（部署用）
```

## 七大功能模块

### Module 1: 身体评估 `assessment`

入口模块。所有计划的基础。

- 基础体测：身高、体重、体脂、围度（8部位）
- 人种感知 BMI：亚太标准（超重 23、肥胖 25）vs WHO 标准
- 体型判定：内胚/中胚/外胚，影响训练和饮食策略
- FMS 功能筛查：7 项动作评分，决定动作限制
- 体态检测：圆肩、头前引、骨盆前倾等 11 种问题
- 阶段复测：每 2-4 周对比，决定是否调整计划

> **评估结果必须影响后续模块**（FMS 低分限制大重量、体态问题增加矫正动作）。

### Module 2: 运动训练 `training`

基于 ACSM 2026 抗阻训练指南。

- 周期化编排：力量/肌肥大/耐力/减脂/体态改善分期（4-6 周中周期）
- 个性化计划：体型 + 训练水平 + 目标 + 器械 + FMS 结果
- 动作库：100+ 动作，含要领、常见错误、替代动作、禁忌症
- 渐进负荷：RPE/RIR/1RM 百分比/训练容量追踪
- 有氧方案：HIIT/LISS/MICT 混合策略
- 训练记录：组×次×重量×RPE

**关键原则**：接近力竭即可（RPE 7-9），不需绝对力竭；每周 ≥10 组/肌群；全幅度动作。

### Module 3: 智能营养 `nutrition`

不是简单记卡路里，而是根据目标、训练日类型、地域饮食做动态处方。

- AI 饮食识别：文字/图片 → 热量和营养素估算（通过 QQ Agent）
- BMR/TDEE：Mifflin-St Jeor + 活动系数 + 训练日校正
- 宏量营养分配：蛋白优先恒定，碳水/脂肪随训练日变化
- 营养周期化：训练日高碳，休息日低碳
- 地域饮食适配：亚洲 8 区（川渝/湖南/广东/江浙沪/东北/西北/华北/日韩）+ 国际模型

> **蛋白质恒定不变，只调整碳水和脂肪。**

### Module 4: 恢复管理 `recovery`

决定计划能否长期执行。

- 睡眠评估：时长 + 质量 → 当日训练强度建议
- 压力/情绪：主观评分 → 影响训练建议
- 肌肉酸痛：按肌群记录
- 疲劳监控：训练量 40% + RPE 30% + 睡眠 15% + 压力 15% → 绿/黄/红
- Deload 建议：连续高强度 → 自动建议减载周

**疲劳状态直接影响训练**：绿色按计划；黄色降 10-30%；红色 deload 或主动恢复。

### Module 5: 身体咨询 `consult`

健身范围内的建议，第一步永远是风险识别。

- 体态矫正：11 种体态问题 → 拉伸 + 强化 + 行为提醒
- 久坐改善：髋屈肌紧张、胸椎僵硬、臀肌失活
- 关节不适：动作降级和替代
- 特殊人群：三高、腰椎/膝关节问题、孕产、术后
- **红线提示**：胸闷、晕厥、急性疼痛、肿胀、麻木放射痛 → 停止训练并就医

> **红线规则**：出现严重信号时不生成训练方案，只给停止训练和就医建议。

### Module 6: 数据仪表盘 `dashboard`

把复杂数据压缩成可行动的判断。

- 今日决策面板：能量缺口、恢复就绪度、最新体重/趋势、同步状态
- 营养环形图：热量/蛋白/碳水/脂肪进度
- 体重/体脂/围度曲线：7 日均线、阶段对比
- 训练容量趋势：肌群、动作、周训练量
- 目标达成率：预计完成时间

**核心判断**：体重不变但围度下降、力量提升 → 判定为"身体重组有效"。

### Module 7: 智能教练 `coach`（QQ Agent）

前 6 个模块的入口层、决策层和习惯运营层。

- QQ 对话式交互：自然语言意图识别
- 动态计划调整：读取近期数据 → 调整热量/训练量/有氧
- 激励与习惯养成：连续记录、缺卡提醒、目标反馈
- 知识科普：健身谣言识别，证据分级回答
- 工具调用路由：判断应调用哪个模块

**对话流程**：意图识别 → 红线检查 → 读取档案和近期数据 → 调用模块 → 写入数据 → 回复用户。

---

## 人种差异引擎

系统核心差异化能力。相同 BMI 下不同人种体脂率、肌肉分布、代谢风险完全不同。

| 人种 | BMI 超重起点 | 特点 | 策略要点 |
|------|-------------|------|----------|
| 东亚 | 23 | 同 BMI 体脂高 3-5%，内脏脂肪倾向强，乳糖不耐 70-90% | 碳水循环不戒主食，监控内脏脂肪，植物蛋白/分离乳清 |
| 南亚 | 23 | 最易代谢综合征，腹型肥胖极强 | 更严格控制精制碳水 |
| 高加索 | 25 | 快肌纤维多，力量训练响应好 | 地中海/DASH 饮食，关注心血管 |
| 非裔 | 25 | 骨骼肌量最高，骨密度高 | 高血压高发，DASH 优先，关注维生素 D |
| 拉美 | 介于两者之间 | 传统饮食碳水偏高 | 保留豆谷组合，减油炸和含糖饮料 |

---

## AI 饮食识别 Prompt 模板

```
你是一个持有NSCA-CSCS认证的运动营养师。
分析以下食物内容，返回JSON格式的营养估算。

用户信息：
- 地区：{region}（考虑当地烹饪习惯对热量的影响）
- 人种：{ethnicity}
- 目标：{goal}
- 乳糖不耐：{lactoseIntolerant}

注意：
1. 中式烹饪油量估算（炒菜约8-15g油/份，红烧更多）
2. 川渝/湖南地区麻辣锅底/红油热量不可低估
3. 东亚人种米饭分量需准确
4. 标注含乳制品的食物

输出格式：
{
  "items": [{ "name", "weightG", "calories", "proteinG", "carbsG", "fatG", "fiberG", "cookingMethod" }],
  "totalCalories", "totalProteinG", "totalCarbsG", "totalFatG",
  "confidence": "high|medium|low",
  "notes": "评估备注"
}
```

---

## 安全边界

- 系统只提供运动、营养和生活方式建议，不替代医生/营养师/康复治疗师的诊断
- **红线信号**（胸闷、晕厥、急性剧痛、关节肿胀、神经放射痛、术后未获医生许可、血压/血糖未控制）→ 不生成训练方案，只建议就医
- **参考依据**：WHO 身体活动建议、ACSM 2026 抗阻训练指南、ISSN 蛋白与运动立场声明、WHO 亚洲 BMI 专家咨询

---

## 开发工作流

1. 修改 `src/` 下的源文件
2. `npm run build` 生成 `dist/`
3. `sudo cp -r dist/* /var/www/html/niu-secretary/fitness/` 部署
4. 验证 `http://124.222.22.171/niu-secretary/fitness/`

> 所有资源引用使用相对路径。单个文件不超过 300 行，超过则拆分子模块。JS 使用 ES Module。
