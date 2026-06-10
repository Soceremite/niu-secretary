---
name: airesearch
description: "牛秘书 AIResearch 研知库。Use when the user wants to build, audit, or operate a local research-paper system on top of paperpipe/papi, including paper ingestion, grounded paper context, scheduled discovery, knowledge graph extraction, provenance, and research reports."
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron
user-invocable: true
last_updated: "2026-06-08-v5"
---

# 牛秘书 AIResearch · 研知库

> 品牌规范与视觉体系参考 [主 SKILL.md](../SKILL.md)。

## 定位

研知库是一个基于 `paperpipe` / `papi` 的本地科研知识系统：

- `paperpipe` 负责论文单体工作流：入库、PDF/LaTeX 获取、公式与摘要产物、全文/排序检索、RAG 问答、agent skill 和 MCP 集成。
- `airesearch` 负责增量层：自动发现、候选预筛、运行台账、跨论文知识图谱、provenance、研究简报和研究地图。

不要把 `paperpipe` 当成完整科研情报平台。它的强项是让 coding agent 用真实论文内容 grounding 实现、公式和方法；它不负责定时发现、OpenAlex 引用图、Method/Dataset/Claim 知识图谱或 gap analysis。

## 已核对的 paperpipe 能力边界

### 稳定作为底座复用

- `papi add <id-or-url-or-title>...`：支持 arXiv ID、arXiv URL、Semantic Scholar URL/ID、标题搜索、PDF、本地文件、批量文件和 BibTeX 导入。
- 本地 paper DB：默认 `~/.paperpipe/`，可用 `PAPER_DB_PATH` 覆盖；每篇论文目录通常包含 `paper.pdf`、`source.tex`、`equations.md`、`summary.md`、`tldr.md`、`meta.json`、`notes.md`，安装 `figures` extra 后可有 `figures/`。
- `papi show <paper> --level eq|tex|summary|tldr`：给 agent 提供公式、原始 LaTeX、摘要或 TL;DR。
- `papi search`：跨标题、标签、摘要、公式等搜索；`papi index --backend search` 可建立 SQLite FTS5/BM25 排序索引；也支持 rg/scan/hybrid 类搜索。
- `papi export`：把论文上下文导出到项目目录，适合 agent 不能读取 `~/.paperpipe/` 时使用。
- `papi notes`、`papi tags`、`papi regenerate`、`papi rebuild-index`：维护本地论文库。
- Agent 集成：`papi install skill|mcp` 可为 Claude Code、Codex CLI、Gemini CLI 安装 skill/MCP 配置。
- 自带技能包括 `/papi`、`/papi-init`、`/verify-with-paper`、`/ground-with-paper`、`/compare-papers`、`/curate-paper-note`。

### 条件能力，使用前要验证环境

- LLM summary / equation extraction / tagging 需要可用 LLM key；无 LLM 时会降级到规则抽取和元数据摘要，质量会下降。
- `papi ask` 需要 RAG backend：PaperQA2 (`paperpipe[paperqa]`) 或 LEANN (`paperpipe[leann]`)。
- PaperQA2 可用云 LLM 和云 embedding，例如 `--pqa-llm ... --pqa-embedding text-embedding-3-small`；第一次查询会构建缓存索引。
- LEANN 是本地 RAG 选项，通常配 Ollama；本服务器无 GPU，所以不作为默认方案，但不能写成 paperpipe 不支持。
- MCP 是 extra 能力 (`paperpipe[mcp]`)，不是基础安装必然可用。
- `figures/` 需要 `paperpipe[figures]` 或 `paperpipe[all]`。

### paperpipe 不覆盖，必须由 airesearch 自建

- 定时自动发现论文。
- OpenAlex topic/author/institution/citation metadata 补全。
- Semantic Scholar seed expansion、推荐队列、限流和缓存策略。
- 候选排序、预筛、跳过原因和 run 审计。
- 跨论文 citation/method/dataset/metric/claim/equation 知识图谱。
- Claim 级 provenance 和置信度评分。
- Research Digest、Research Map、Gap Analysis、跨论文趋势报告。

## 环境原则

- 本地无 GPU：默认使用云 LLM 和云 embedding；不要默认规划 Ollama/LEANN 本地推理链路。
- 本地保存 PDF、LaTeX、索引、台账、图谱和报告。
- API key 只放环境变量或未提交 `.env`。
- 发送到云 LLM 的内容要最小化：优先发送必要 chunk、equation context 和 extraction prompt。
- 自动生成的结论必须区分 `extracted fact`、`model summary` 和 `speculative hypothesis`。

## 架构分层

```text
L3 Reports
  research digest / research map / gap analysis / paper card

L2 Knowledge Graph
  entity extraction / relation extraction / claim trace / provenance
  Phase 1-3: SQLite adjacency tables
  Scale trigger: >5000 papers, >3-hop graph queries, or graph analytics -> evaluate Kuzu

L1 Scheduler & Discovery
  research topics / OpenAlex discovery / Semantic Scholar expansion
  candidate ranking / prefilter / run audit / automatic papi add

L0 paperpipe / papi
  add / show / search / index / ask / export / notes / tags
  local paper DB / equations.md / summary.md / tldr.md / source.tex
  optional PaperQA2, LEANN, MCP, figures
```

## 技术选型

| 层 | 选型 | 约束 |
|----|------|------|
| 单论文入库与上下文 | `paperpipe` / `papi` | 直接复用，不重写 PDF/LaTeX/公式/摘要/搜索基础能力 |
| LLM 摘要/抽取 | 云 LLM | `papi add` 的高质量产物和 airesearch KG extraction 都依赖可用 key |
| Embedding/RAG | PaperQA2 + cloud embedding | 默认用云 embedding；LEANN/Ollama 仅作为低优先级可选项 |
| 元数据发现 | OpenAlex | topic、author、institution、citation metadata |
| 推荐扩展 | Semantic Scholar API | seed paper expansion；需要限流和 7 天缓存 |
| 图谱存储 | SQLite -> Kuzu | 先 SQLite 邻接表；满足规模条件再迁移 |
| 引用精修 | GROBID 可选 | 只在需要细粒度 citation parsing 时引入 |
| 版面兜底 | MinerU 可选 | 只在 PDF 复杂版面或扫描件导致 `papi` 产物不足时评估 |

## 命令映射

| airesearch 命令 | 实际实现 | 说明 |
|-----------------|----------|------|
| `/paper-add <input>` | `papi add <input>` | 手动入库，支持多源输入 |
| `/paper-show <paper> <level>` | `papi show <paper> --level <level>` | level: eq/tex/summary/tldr |
| `/paper-search <query>` | `papi search <query>` | 需要时先 `papi index --backend search` |
| `/paper-ask <question>` | `papi ask "<question>"` | 先验证 PaperQA2/LEANN backend |
| `/paper-export <papers>` | `papi export <papers...> --to <dir>` | agent 读不到 paper DB 时使用 |
| `/paper-build <input>` | `papi add` + airesearch sync + extraction | 入库后同步台账并抽取 KG |
| `/paper-compare <a> <b>` | `/compare-papers` 或 `papi show/search` 组合 | 使用 paperpipe skill 进行 grounded comparison |
| `/verify-with-paper` | paperpipe skill | 代码与公式逐项核对 |
| `/research-topic add/list` | airesearch L1 | 自建 topic CRUD |
| `/research-run` | airesearch L1 | 执行发现、预筛、入库和简报 |
| `/kg-search <query>` | airesearch L2 | 查询图谱 |
| `/claim-trace <claim>` | airesearch L2 | 追溯结论证据 |
| `/research-digest` | airesearch L3 | 生成新增论文简报 |
| `/research-map <topic>` | airesearch L3 | 生成领域地图 |
| `/gap-analysis <topic>` | airesearch L3 | 生成研究空白分析 |

## Workflow

### 1. 首次接入 paperpipe

1. 安装：优先 `uv tool install paperpipe --with "paperpipe[all]"`，也可 `pip install 'paperpipe[all]'`。
2. 设置 `PAPER_DB_PATH` 到研知库数据目录，例如 `~/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe`。
3. 配置云 LLM / embedding key，并运行 `papi models` 检查可用模型。
4. 入库 5-20 篇核心论文：`papi add ...`。
5. 验证：`papi show --level eq`、`papi search`、`papi index --backend search`、`papi ask`。
6. 如果 agent 不能直接读 paper DB，用 `papi export` 导出上下文到项目目录。

### 2. 手动论文入库

1. 调 `papi add <input>`，不要自研 PDF 下载和 LaTeX 解析。
2. 读取 `papi path` 和 `index.json`，同步到 airesearch SQLite `papers` / `paper_sources`。
3. 记录来源：input type、resolved IDs、paper directory、PDF hash、入库时间。
4. 如果需要图谱，读取 `summary.md`、`equations.md`、必要 tex/chunk，进入 L2 extraction。

### 3. 自动发现

1. 从 `research_topics` 读取 keywords、exclude_keywords、seed_papers、authors、venues 和 frequency。
2. OpenAlex 拉候选 works，Semantic Scholar 从 seeds 做扩展。
3. 写入 `research_candidates`，先不要直接入库。
4. 预筛：metadata gate + abstract embedding similarity + duplicate check。
5. 过阈值的候选调用 `papi add`；未过阈值的候选保留 skip reason。
6. 写 `research_runs`：输入、发现数、入库数、跳过数、错误、digest path。

### 4. 知识图谱抽取

从 paperpipe 产物抽取，不直接让模型凭标题或摘要自由发挥。

统一 extraction service 输入：

```json
{
  "paper_id": "",
  "chunk_ids": [],
  "task_type": "extract_claims|extract_entities|summarize|compare",
  "source_files": ["summary.md", "equations.md", "source.tex"],
  "provenance_required": true
}
```

输出必须包含：

- structured JSON
- source file
- section/page/chunk/equation reference
- short quote or local text hash
- extractor model and prompt version
- created_at

Claim confidence:

- `high`: 有实验数据、表格、公式推导或明确证据支撑。
- `medium`: 有定量比较或清晰论述，但证据不完整。
- `low`: 主要来自作者论述或模型综合，缺少强证据。

### 5. 报告生成

Paper Card、Research Digest、Research Map、Gap Analysis 必须分层标注：

- `extracted fact`: 来自论文原文或 paperpipe 产物，可追溯。
- `model summary`: 模型基于证据做的压缩概括。
- `speculative hypothesis`: 研究假设或未来方向，不能写成事实。

报告里每个重要 claim 至少要能追到 paper、section/chunk/equation 或引用片段。

## 数据模型最小集

- `papers`: 映射 paperpipe `index.json` 和每篇 paper directory。
- `paper_sources`: arXiv/DOI/S2/URL/PDF hash/title search 等来源记录。
- `paper_artifacts`: `summary.md`、`equations.md`、`tldr.md`、`source.tex`、figures 的路径和 hash。
- `paper_chunks`: airesearch 自己切分的 section/chunk 台账。
- `paper_equations`: equation id、LaTeX、变量说明、上下文窗口。
- `paper_claims`: claim、confidence、evidence reference。
- `paper_citations`: OpenAlex/S2/GROBID 补充的引用关系。
- `research_topics`: 自动调研主题配置。
- `research_runs`: 每次自动调研 run 台账。
- `research_candidates`: 候选论文、分数、状态和 skip reason。
- `graph_entities`: Method/Dataset/Metric/Task/Claim/Equation 等节点。
- `graph_relations`: 图谱边和 provenance。
- `provenance`: 通用来源记录。
- `api_cache`: OpenAlex/S2/embedding/extraction 缓存。
- `jobs`: 长任务状态。

## 质量与安全约束

- 不把本地 PDF、notes、SQLite DB 上传到未知远程服务。
- 不把 `paperpipe` 的 `summary.md` 当作完整 literature review；它偏 implementation-oriented。
- 不把 `papi ask` 当作零配置能力；先确认 backend、index 和模型配置。
- 不把 LEANN 当默认方案；本机无 GPU时优先 PaperQA2 + 云 embedding。
- KG 抽取结果默认是草稿，必须留证据以便复核。
- 自动调研 run 必须可审计：query、候选、阈值、跳过原因、错误和报告路径都要记录。

## MVP 顺序

1. 跑通 `paperpipe`：`papi add`、`papi show --level eq`、`papi search`、`papi ask`。
2. 建 airesearch SQLite 台账，同步 `index.json` 和 paper artifacts。
3. 做 `/paper-build`：入库后生成 Paper Card 草稿和基础 provenance。
4. 做 L1 自动发现：OpenAlex/S2 candidates -> prefilter -> `papi add`。
5. 做 L2 图谱：claims/entities/relations + `claim-trace`。
6. 做 L3 报告：digest -> map -> gap analysis。
