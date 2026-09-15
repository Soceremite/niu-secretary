# 牛秘书 API 统一框架 · 执行计划

日期：2026-09-15
状态：**已实施完成**（阶段 1-4 全部落地，阶段 5 收尾于 README 与 env 清理）
设计文档：plans/2026-09-15-api-provider-refactor.md
目标：niu_core/llm 薄统一层，全域 API 调用收敛到「逻辑模型名」+ 本地网关

## 落地结果摘要

- 阶段1：niu_core/llm_client（config/client/errors/doctor CLI）+ 10 单测全绿；四渠道接入
- 阶段2：研知库 8 调用点迁移 + conftest hermetic fixture；653/653 全绿；真实链路 fact=10 条
- 阶段3：cron 七件套收编——新闻社与闲趣集全 no_agent 管线（RSS/豆瓣真实抓取→统一 LLM→vision 审核→QQ briefing），4 个 agent 会话 job 退役
- 阶段4：niu-secretary-api assistant.py 走 NiuLLM("assistant")=opencode glm-5.3-flash（11 模型横评冠军）；prompt 强化为 fitness 含饮食/运动/健康 + 5 few-shot 例句；niu-fitness-api ExecStart 修正到新仓库，vision 走统一网关；fitness js 版 deprecated 标注
- 最终 README：niu_core/llm_client/README.md（渠道表、逻辑模型表、服务接线现状、坑位记录）

## 已确认的现状

- 统一网关：http://124.222.22.171:8080/v1（sub2api，支持 chat/completions 和 responses 双风格）
- 全部 LLM 端点（FACT/BLOG/DEEPSEEK/LUNA/TRANSLATE/OCR/ASSISTANT/OPENCODE_GO）都已指向该网关，模型统一 gpt-5.6-luna
- 唯一异类：embedding 走 DashScope（text-embedding-v4）
- cron 内容生成用 deepseek-v4-pro / 审核用 doubao-seed-2.0-pro（经 volcengine）

## 阶段划分（每阶段测试通过才停口报告）

### 阶段 1 · niu_core/llm 框架 + 单测（本阶段产出可独立使用）

- [ ] 1.1 config/models.yaml：endpoints（sub2api chat_completions / sub2api responses / dashscope-embedding）+ logic_models（content / vision / blog / fact / translate / formula_ocr / embed / assistant / flash）
- [ ] 1.2 niu_core/llm/client.py + config.py + keypool.py + errors.py
- [ ] 1.3 doctor 子命令：python -m niu_core.llm 检查所有逻辑模型可达性
- [ ] 1.4 pytest 单测：mock HTTP，覆盖 chat / fallback / key 冷却 / style=responses / config 解析
- [ ] **验收**：单测全绿 + doctor 命令对各 endpoint 直连探活成功

### 阶段 2 · 研知库（airesearch）试点迁移

- [ ] 2.1 niu_core 加入 airesearch/.venv（pip install -e 或 sys.path）
- [ ] 2.2 provider_config.py 退役：fact / blog(luna) / translate / formula_ocr / embedding 全走 NiuLLM
- [ ] 2.3 .env 收敛：AIRESEARCH_* 系列 10 套变量删除，仅留 NIU_LLM_ 网关与 key
- [ ] 2.4 回归：跑 airesearch/tests/ + 一条真实链路（fact 或 blog 小样）
- [ ] **验收**：tests 全绿 + 一条真实调用成功

### 阶段 3 · 新闻社 + 闲趣集内容生成收编

- [ ] 3.1 news-daily 生成走 NiuLLM("content")：generate_current.py 改造
- [ ] 3.2 leisure 生成走 NiuLLM("content") + NiuLLM("vision")（海报审核）
- [ ] 3.3 cron 七件套改造为 no_agent 脚本触发（ débơior 输出非零即失败）
- [ ] **验收**：手动触发一条 cron 全链路跑通（不部署 qqbot 推送）

### 阶段 4 · niu_secretary server 切换

- [ ] 4.1 assistant.py / action_handlers.py 走 NiuLLM("assistant")
- [ ] 4.2 重启 niu-secretary-api 服务验证对话正常
- [ ] **验收**：curl 对话接口 200 + 内容合理

### 阶段 5 · fitness + 收尾清理

- [ ] 5.1 fitness py 版走 NiuLLM
- [ ] 5.2 各板块 .env / .env.example 精简清理
- [ ] 5.3 文档：niu_core/llm README + 设计文档状态更新为「已实施」
- [ ] **验收**：git status 干净（除本次新增）+ doctor 全绿

## 测试策略

- 阶段 1 起 pytest（mock httpx/requests），每阶段至少一条真实回归
- cron 收编用「手动触发定时器」先验证，不直接改活产线 job
- 现金牛最重的 news-daily：改造前的 generate_current.py 留 git tag 作为回滚点
