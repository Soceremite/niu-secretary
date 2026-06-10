# AIResearch Requirements

> Last updated: 2026-06-08 v3

## Core Goal

构建基于 paperpipe 的本地科研系统，实现：

- 定时自动发现新论文（OpenAlex + Semantic Scholar）
- 手动提交论文（URL / arXiv ID / DOI / PDF / title）→ 直接调 `papi add`
- 从 paperpipe 产出物（summary.md / equations.md / chunks）做深度结构化分析
- 构建跨论文知识图谱（Method / Dataset / Metric / Claim / Equation 关系网）
- 生成研究报告：paper card / research digest / research map / gap analysis
- 全链路 provenance：每条结论可追溯到原文

## paperpipe 能力边界

- `paperpipe` 是 Alpha 阶段工具，适合作为本地论文 grounding 底座；不要把它包装成完整科研情报系统。
- `papi ask`、MCP、figures、LEANN/PaperQA2 都依赖 extras 和环境配置。
- `airesearch` 只把 paperpipe 产物作为证据输入，跨论文发现、图谱、报告和审计都由自建服务完成。

## 环境约束

- **无本地 GPU**
- Embedding 走云 API（OpenAI `text-embedding-3-small`）
- LLM 推理走云 API（Kimi K2.6 / Qwen3.7 Max / GPT 模型池）
- 本地 Ollama/LEANN 不作为默认方案；paperpipe 支持 LEANN extra，但本机无 GPU 时优先云 LLM + 云 embedding
- paperpipe 本身（入库/解析/公式/FTS5）纯 CPU 可运行

## 架构：paperpipe 底座 + 三层增量

### L0: paperpipe（不自研，直接复用）

paperpipe 已覆盖或可作为条件能力复用：

| 能力 | 实现 |
|------|------|
| 论文入库 | `papi add`（arXiv/DOI/URL/S2/PDF/title/BibTeX） |
| PDF + LaTeX 解析 | 自动下载 PDF / arXiv LaTeX，生成 equations.md / summary.md / tldr.md；figures/ 需要 figures extra |
| 公式提取 | `papi show <paper> --level eq`（结构化公式 + 变量定义） |
| BM25/全文检索 | `papi search`；`papi index --backend search` 建 SQLite FTS5/BM25 索引，另有 rg/scan/hybrid 类搜索 |
| RAG 问答 | `papi ask`；需要 PaperQA2 (`paperpipe[paperqa]`) 或 LEANN (`paperpipe[leann]`) backend，不能假定零配置可用 |
| 代码核对 | `/verify-with-paper` skill |
| 论文比较 | `/compare-papers` skill |
| MCP | `paperpipe[mcp]` extra；安装后提供 retrieve/list/search 类工具，具体工具以当前版本为准 |
| Agent skill | `papi install skill` 安装；包括 `/papi`、`/papi-init`、`/verify-with-paper`、`/ground-with-paper`、`/compare-papers`、`/curate-paper-note` |
| 本地存储 | 默认 `~/.paperpipe/`，可用 `PAPER_DB_PATH` 覆盖；每篇论文目录含 PDF/tex/equations/summary/notes 等产物 |

**不重复实现这些能力，但使用前要验证当前安装 extras、LLM key、RAG backend 和索引状态。**

### L1: Scheduler & Discovery（自研）

paperpipe 是被动的（给 ID 才入库），不做主动发现。L1 负责：

- research_topics 管理
- OpenAlex 按 topic/keywords/authors/venues 发现 works
- Semantic Scholar 从 seed papers 做 recommendation 扩展
- 候选预筛（metadata 过滤 + abstract embedding 打分）
- 过阈值自动 `papi add`
- run 台账 + 跳过原因 + 排序信号

### L2: Knowledge Graph（自研）

paperpipe 存 per-paper 平铺文件，没有跨论文实体-关系图。L2 负责：

- 从 paperpipe 产出物提取结构化实体（Method/Dataset/Metric/Claim/Equation/Task）
- 建立跨论文关系图（引用、方法演进、数据集复用、指标对比）
- Provenance 全链路（paper_id / chunk_id / page / section / quote）
- Claim 置信度评分
- 统一 extraction service（云 LLM，batch + 缓存）
- 图存储：Phase 1-3 SQLite 邻接表；> 5000 篇迁移 Kuzu

### L3: Reports（自研）

paperpipe 不生成跨论文研究报告。L3 负责：

- Paper Card：单论文结构化深度分析（超出 summary.md 的粒度）
- Research Digest：某 topic 时间窗口内新增论文简报
- Research Map：方法族 / 关键论文 / 影响力路径 / 未解问题
- Gap Analysis：图谱空白 + 推荐实验方向
- 区分：extracted fact / model summary / speculative hypothesis

## Entry Points

### Scheduled Automatic Research

每个 research_topic：

- `topic_id`, `name`, `description`
- `keywords`, `exclude_keywords`
- `seed_papers`
- `venues`, `authors`
- `update_frequency`: `daily` / `every_2_days` / `weekly`
- `last_run_at`

每次 run 产出 `research_run` 台账：papers discovered / selected / skipped / skip reasons / ranking signals / errors / digest path。

### Manual Paper Submission

接受：URL / arXiv ID / DOI / 本地 PDF / title。

直接调 `papi add`，绕过候选排序，但仍写入 airesearch SQLite 台账（papers / sources / provenance）。

## Candidate Pre-filtering（候选预筛）

自动发现的候选在进入 `papi add` 前先过预筛：

1. **Metadata 过滤**：citation count / venue tier / author h-index（OpenAlex 提供）
2. **Abstract embedding 相似度**：topic 的 seed papers 平均 embedding vs 候选 abstract embedding，余弦相似度打分
3. **阈值判定**：过阈值 → `papi add` 入库；未过 → `research_candidates` 标记 `status=filtered`，保留可追溯

这样避免自动调研被大量低质量论文淹没 pipeline。

## Paper Analysis Flow（论文分析总结）

paperpipe 产出偏 implementation-oriented 的 summary；airesearch 在此基础上做结构化深度分析。不要把 `summary.md` 当作完整 literature review：

```text
papi add <paper>
    ↓ paperpipe 产出：
    summary.md / equations.md / tldr.md / meta.json / optional figures/
    ↓ airesearch extraction（云 LLM）：
    ├── Section splitter（按 # heading 拆分）
    ├── Per-section extraction:
    │   - Abstract → research problem + one-paragraph summary
    │   - Method → core method + novelty claim + key equations
    │   - Experiments → datasets + metrics + baselines + main results
    │   - Conclusion → limitations + future work
    ├── Claim extraction + evidence pairing（每条 claim 绑 chunk_id）
    ├── Entity extraction: Method / Dataset / Metric / Task
    ├── 公式 grounding: equation_id + 上下文窗口（前后 2 段）
    └── Claim confidence scoring:
        - high: 有实验数据/表格支撑
        - medium: 有定量比较但无原始数据
        - low: 纯文字论述
    ↓ 输出：
    ├── Paper Card（结构化 JSON）
    ├── SQLite: claims / entities / relations / provenance
    └── KG edges
```

### 统一 Extraction Service

所有 LLM 抽取调用统一为一个模块：

```
input:  paper_id + chunk_ids + task_type (extract_claims | extract_entities | summarize | compare)
output: structured JSON + provenance metadata
```

好处：
- 换模型只改一处
- batch 调用省成本
- 同 chunk 结果缓存 7 天
- 可审计每次抽取的 input/output

## Semantic Scholar API 调度

免费 tier 限制：100 requests / 5 minutes。

对策：
- 请求队列 + 速率限制器（令牌桶，100/300s）
- 已查过的 paper metadata 存 SQLite，7 天内不重复请求
- batch endpoint（`/graph/v1/paper/batch`）减少请求数
- 429/Retry-After 自动退避

## Data Model

### SQLite 表

| 表 | 用途 |
|----|------|
| `papers` | 论文主表，映射 paperpipe index.json |
| `paper_sources` | 每篇论文的来源记录（arXiv/DOI/URL/PDF hash） |
| `paper_chunks` | chunk 切分记录（section/page/text_hash） |
| `paper_equations` | 公式 + LaTeX + 上下文窗口 |
| `paper_claims` | 结论 + 置信度 + evidence chunk_id |
| `paper_citations` | 引用关系（OpenAlex 补充） |
| `research_topics` | 自动调研主题配置 |
| `research_runs` | 每次调研运行记录 |
| `research_candidates` | 所有候选论文（含跳过原因 + 排序信号） |
| `graph_entities` | KG 实体 |
| `graph_relations` | KG 关系（含 provenance） |
| `provenance` | 通用溯源表 |
| `jobs` | 任务状态 |
| `api_cache` | Semantic Scholar / OpenAlex 响应缓存 |

### Knowledge Graph Schema

**节点**：Paper / Author / Institution / Topic / Method / Dataset / Metric / Task / Claim / Equation / Chunk / CodeArtifact

**边**：
- `Paper -[:CITES]-> Paper`
- `Paper -[:WRITTEN_BY]-> Author`
- `Author -[:AFFILIATED_WITH]-> Institution`
- `Paper -[:HAS_TOPIC]-> Topic`
- `Paper -[:USES_METHOD]-> Method`
- `Paper -[:INTRODUCES_METHOD]-> Method`
- `Paper -[:EVALUATES_ON]-> Dataset`
- `Paper -[:REPORTS_METRIC]-> Metric`
- `Claim -[:SUPPORTED_BY]-> Chunk`
- `Equation -[:DEFINED_IN]-> Chunk`
- `CodeArtifact -[:IMPLEMENTS]-> Method`

每条边保存 provenance：`paper_id` / `chunk_id` / `page` / `section` / `quote` / `extractor` / `created_at`。

## Graph Database Strategy

**Phase 1-3**：SQLite 邻接表 + 递归 CTE。
- 论文量 < 5000、查询深度 ≤ 3 跳时完全够用
- 零运维，和其他台账共享同一个 .sqlite3 文件

**迁移条件**（满足任一）：
- 论文量 > 5000
- 需要 > 3 跳路径查询（方法演进链、引用影响力传播）
- 需要 community detection / graph embedding

**迁移目标**：Kuzu（嵌入式、零运维、Cypher 兼容），不用 Neo4j（JVM 重、运维成本高）。

## GraphRAG 策略

**Phase 3-4**：朴素图查询（SQLite CTE / Kuzu Cypher）+ LLM 总结。够用就不引入重框架。

**Phase 5（按需评估）**：如果需要 field-level 主题趋势（"这个领域的三大研究方向是什么"），才引入 Microsoft GraphRAG 模式的 Leiden community detection + community summary。否则不做。

## Output Standards

### Paper Card

```json
{
  "title": "",
  "authors": [],
  "year": 0,
  "venue": "",
  "ids": { "doi": "", "arxiv": "", "openalex": "", "s2": "" },
  "summary": "one paragraph",
  "research_problem": "",
  "core_method": "",
  "novelty": "",
  "datasets": [{ "name": "", "domain": "" }],
  "metrics": [{ "name": "", "value": "", "baseline": "" }],
  "key_equations": [{ "equation_id": "", "latex": "", "meaning": "" }],
  "claims": [{ "text": "", "confidence": "high|medium|low", "evidence_chunk_id": "" }],
  "limitations": [],
  "implementation_relevance": "",
  "kg_entities_added": [],
  "kg_relations_added": []
}
```

### Research Digest

- run_id / topic / time_window / source_queries
- top new papers + why each matters
- relation to existing local library
- new methods / datasets / metrics / claims
- suggested reading order
- skipped papers with reasons

### Research Map

- main research branches
- representative papers per branch
- method families + evolution
- datasets and benchmarks
- citation/influence paths
- unresolved problems

## Agent Commands

| 命令 | 层 | 作用 |
|------|-----|------|
| `/paper-add <input>` | L0 | `papi add` |
| `/paper-build <id>` | L0+L2 | 入库 + KG extraction |
| `/paper-search <query>` | L0 | `papi search`；需要排序检索时先建 search index |
| `/paper-compare <a> <b>` | L0 | `/compare-papers` 或 `papi show/search` 组合 |
| `/verify-with-paper` | L0 | paperpipe skill |
| `/research-topic add <topic>` | L1 | 添加调研主题 |
| `/research-topic list` | L1 | 查看主题 |
| `/research-run --topic <t>` | L1 | 执行自动调研 |
| `/kg-search <query>` | L2 | 图谱查询 |
| `/claim-trace <claim>` | L2 | 结论溯源 |
| `/research-digest --topic <t> --since 7d` | L3 | 调研简报 |
| `/research-map <topic>` | L3 | 领域地图 |
| `/gap-analysis <topic>` | L3 | 研究空白 |

## MVP Phases

### Phase 1: paperpipe 集成 + 论文台账

- 安装配置 paperpipe（优先 `uv tool install paperpipe --with "paperpipe[all]"`，也可 `pip install 'paperpipe[all]'`）
- 配置云 embedding + 云 LLM，并用 `papi models` / `papi ask` 小样本验证
- 建 SQLite 台账 schema
- 薄适配层：papi index.json ↔ SQLite papers 同步
- 验证：`papi add` → `papi show --level eq` → `papi search` → `papi index --backend search` → `papi ask` 闭环

### Phase 2: 定时自动发现

- research_topics CRUD
- OpenAlex 发现 + S2 扩展
- 请求调度 + 7 天缓存
- 候选预筛（metadata + embedding 打分）
- 过阈值自动 `papi add` + run 台账

### Phase 3: 知识图谱

- 统一 extraction service
- 实体/关系抽取 + provenance
- Claim 置信度评分
- SQLite 邻接表 + 递归 CTE
- `kg-search` / `claim-trace`

### Phase 4: 研究报告

- Paper Card 生成
- Research Digest
- Research Map
- Gap Analysis
- 评估 community detection 需求

### Phase 5: 扩展（按需）

- Kuzu 迁移（如 > 5000 篇）
- GROBID 引用精修
- GraphRAG community summarization
- 自动假设生成 + 实验规划

## Quality and Safety Constraints

- API key 只存本机 `.env`（gitignored）
- 不上传本地 PDF/数据库/笔记到未知远程服务
- 云 LLM 只发送 chunk text + extraction prompt，不发完整论文
- RAG 回答必须 cite evidence；若 backend/index 未就绪，先退回 `papi show/search/export` grounding
- KG 抽取默认不可信，保留 source quote 允许复核
- 自动生成的 hypothesis 标记为"研究假设"
- 自动 run 全链路可审计
