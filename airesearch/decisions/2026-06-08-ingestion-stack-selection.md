# AIResearch 选型修正：PaperPipe/papi 能力评估与研知库优化

> 日期：2026-06-08（v2，按 GitHub/PyPI 能力边界复核后修正）
> 背景：PaperPipe（`pip install paperpipe`，CLI `papi`）是真实存在的 PyPI 包，GitHub: hummat/paperpipe。之前的选型文档误判其不存在，现做修正。

## 一、PaperPipe 实际能力盘点

### papi 已经覆盖的能力

| 研知库需求层 | papi 覆盖度 | 具体实现 |
|-------------|-------------|----------|
| **源解析** | ✅ 完整 | arXiv ID / DOI / URL / Semantic Scholar / 本地 PDF / title 搜索 / BibTeX 导入 |
| **PDF + LaTeX 获取** | ✅ 完整 | 自动下载 PDF + arXiv LaTeX 源码 |
| **公式提取** | ✅ 核心能力 | `equations.md` — 公式 + 变量定义 + 上下文 |
| **摘要/TL;DR** | ✅ | `summary.md`（实现导向）+ `tldr.md` |
| **图片提取** | ✅ `[figures]` extra | LaTeX/PDF 图片抽取到 `figures/` |
| **本地论文 DB** | ✅ | `~/.paperpipe/` 目录结构 + `index.json` |
| **FTS/BM25 搜索** | ✅ | `papi index --backend search` → SQLite FTS5 |
| **RAG 问答** | ✅ 条件能力 | `papi ask` 需要 `paperpipe[paperqa]` 或 `paperpipe[leann]` backend、模型和索引配置 |
| **Agent Skill** | ✅ | `/papi`、`/verify-with-paper`、`/ground-with-paper`、`/compare-papers` |
| **MCP Server** | ✅ extra | `paperpipe[mcp]` 安装后可用；具体工具以当前版本为准 |
| **论文比较** | ✅ | `/compare-papers` skill |
| **代码核对** | ✅ 核心设计目标 | `/verify-with-paper` — 逐符号比对公式和代码 |
| **批量导入** | ✅ | `--from-file` JSON/TXT/BibTeX |
| **标签管理** | ✅ | `papi tags`、`--tag` 过滤 |
| **导出** | ✅ | `papi export` 到项目目录 |

### papi 没覆盖 / 研知库仍需自建的层

| 研知库需求层 | papi 覆盖度 | 差距 |
|-------------|-------------|------|
| **引用关系图** | ❌ | papi 不维护 citation graph（谁引用谁） |
| **元数据补全** | 🔶 部分 | papi 从 S2/arXiv 获取基础 metadata，但不拉 OpenAlex 的 topics/institutions/citation counts |
| **知识图谱** | ❌ | 无 Method/Dataset/Metric/Claim/Task 实体抽取 |
| **定时自动调研** | ❌ | papi 是按需 CLI，不负责 scheduled discovery |
| **run 审计** | ❌ | 无 research_run / candidates / skip_reason 概念 |
| **向量检索（Qdrant）** | 🔶 | 用 PaperQA2 内置 Numpy 向量，不是 Qdrant |
| **GraphRAG** | ❌ | 无跨论文图数据库、community summary 或 gap analysis |
| **研究地图/gap analysis** | ❌ | 无此功能 |

## 二、关键认知更新

**PaperPipe 不是"PDF 解析工具"，而是一个完整的论文-Agent grounding 系统。** 它在研知库 pipeline 中的位置不是替代 GROBID，而是覆盖了"源解析 + 入库 + 公式提取 + 搜索 + RAG + agent skill"整条链路的中段。

研知库原方案把 papi 定位为"入库引擎"是低估了它——它覆盖 Phase 1 的核心底座，并能支撑 RAG/search；Phase 2 自动发现和 Phase 3 知识图谱仍需自建。

## 三、优化后的架构分层

```text
┌─────────────────────────────────────────────────────────┐
│  Layer 0: Scheduled Discovery（研知库自建）              │
│  OpenAlex topic query + S2 seed expansion → candidates  │
│  cron 定时 + run 审计 + skip tracking                    │
└────────────────────────┬────────────────────────────────┘
                         │ candidate papers (arXiv IDs / DOIs / titles)
                         v
┌─────────────────────────────────────────────────────────┐
│  Layer 1-3: PaperPipe/papi（现成基础设施）               │
│  papi add → PDF/LaTeX/equations/summary/figures          │
│  papi index → SQLite FTS5/BM25                          │
│  papi ask → PaperQA2 RAG                                │
│  papi show → agent grounding                            │
│  MCP server → retrieve_chunks                           │
└────────────────────────┬────────────────────────────────┘
                         │ paper artifacts + search index
                         v
┌─────────────────────────────────────────────────────────┐
│  Layer 4-5: 知识图谱 + GraphRAG（研知库自建）            │
│  OpenAlex citation graph → SQLite adjacency tables       │
│  LLM entity extraction → Method/Dataset/Claim nodes      │
│  量大或深图查询时再迁移 Kuzu                              │
│  research maps / gap analysis / claim trace              │
└─────────────────────────────────────────────────────────┘
```

## 四、对原方案各 Phase 的影响

### Phase 1: Unified Paper Ledger + Manual Ingestion
- **大幅简化**：`papi add` 直接实现了手动入库的全部需求
- 自建部分仅剩：
  - 将 papi 的 `index.json` / paper 目录映射到研知库的 SQLite `papers` 表（薄适配层）
  - 或直接复用 papi 的存储作为 source of truth，研知库 SQLite 只存补充字段（status/run_id/provenance）

### Phase 2: Scheduled Discovery
- **完全自建**：papi 不做定时发现，这块维持原方案
- 但发现后的入库直接调 `papi add <arXiv_id>` 即可，不需要自建 PDF 下载/解析逻辑

### Phase 3: RAG Indexing
- **简化但要验证环境**：`paperpipe[paperqa]` 提供 PaperQA2 RAG，`paperpipe[leann]` 提供 LEANN RAG
- 考虑点：
  - papi 用 Numpy 向量（PaperQA2 内置），不是 Qdrant
  - `papi ask` 不是零配置能力，先验证 backend、LLM key、embedding 和索引缓存
  - 本机无 GPU 时默认 PaperQA2 + 云 embedding；LEANN/Ollama 只作为低优先级可选项
  - 后期是否加独立向量库取决于规模和查询延迟，不在 MVP 默认范围

### Phase 4: Knowledge Graph
- **完全自建**：papi 不做 KG，这块维持原方案
- papi 的 `equations.md` + `summary.md` 可作为 KG 实体抽取的高质量输入源

### Phase 5: GraphRAG Research Assistant
- **完全自建**：维持原方案

## 五、推荐实施策略

### 策略：papi 作为基础层，研知库在其上扩展

1. **安装 papi**：`pip install 'paperpipe[all]'`
2. **设置 PAPER_DB_PATH** 指向研知库数据目录：`export PAPER_DB_PATH=~/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe`
3. **Phase 1 直接用 papi CLI**：手动入库 = `papi add`；搜索 = `papi search`；公式 = `papi show --level eq`
4. **Phase 2 自建 scheduler**：cron → OpenAlex/S2 discovery → `papi add <id>` 批量入库
5. **Phase 3 先验证 papi RAG**：`papi ask` 可用后再接入；不够时再评估独立向量库
6. **Phase 4-5 在 papi 产物上建图谱**：读 papi 的 `equations.md`/`summary.md`/`paper.pdf` → LLM 实体抽取 → SQLite 邻接表，量大再评估 Kuzu

### papi 与 GROBID 的关系

- **不冲突，可互补**：papi 用自己的方式解析（LLM summary + LaTeX 源码 + equations 提取）
- GROBID 的优势在**引用解析**（F1 .87-.90）和**TEI 细粒度标注**
- 如果研知库需要精确的 citation graph（Phase 4），可以对 papi 存储的 `paper.pdf` 额外跑 GROBID 做引用抽取
- **建议**：Phase 1-3 纯用 papi；Phase 4 按需引入 GROBID 做引用精修

## 六、SKILL.md 当前状态

已将 SKILL.md 恢复为 papi 作为 L0 底座，GROBID 仅作为按需引用精修补充。同时补充了条件能力边界：`papi ask`、MCP、figures、LEANN/PaperQA2 都需要安装 extras 和验证配置。


## 七、v2 结论

- SKILL.md 已恢复 papi 作为 L0 底座，并已写清楚条件能力边界。
- `papi ask`、MCP、figures、LEANN/PaperQA2 都不是无条件可用能力，需要安装 extras 和验证配置。
- AIResearch 的 MVP 不引入 Neo4j/Qdrant；先用 paperpipe + SQLite，规模或查询需求触发后再评估 Kuzu/独立向量库。
- paperpipe 的 `summary.md` 偏 implementation-oriented，只能作为 evidence input，不能替代跨论文 literature review。
