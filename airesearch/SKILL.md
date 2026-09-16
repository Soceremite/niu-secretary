---
name: airesearch
description: "牛秘书 AIResearch 研知库。Use when the user wants to build, audit, or operate a local research-paper system on top of paperpipe/papi, including paper ingestion, grounded paper context, scheduled discovery, knowledge graph extraction, provenance, and research reports."
allowed-tools: read,write,edit,exec,web_search,web_fetch,cron
user-invocable: true
last_updated: "2026-08-11-v13"
---

# 牛秘书 AIResearch · 研知库

> 品牌规范与视觉体系参考 [主 SKILL.md](../SKILL.md)。

## 定位

研知库是一个基于 `paperpipe` / `papi` 的本地科研知识系统：

- `paperpipe` 负责论文单体工作流：入库、PDF/LaTeX 获取、公式与摘要产物、全文/排序检索、RAG 问答、agent skill 和 MCP 集成。
- `airesearch` 负责增量层：自动发现、候选预筛、运行台账、跨论文知识图谱、provenance、研究简报、研究地图和 native layout v2 版面结构化。
- native layout v2 负责 MinerU-inspired 的 PDF 结构化产物：页面块、坐标、Markdown/content list/layout JSON、图注配对、表格/公式/证据块、代表图候选、公开详情页 layout evidence 面板、管理台 Layout Evidence Inspector 和深度解读证据预检。

不要把 `paperpipe` 当成完整科研情报平台。它的强项是让 coding agent 用真实论文内容 grounding 实现、公式和方法；它不负责定时发现、OpenAlex 引用图、Method/Dataset/Claim 知识图谱或 gap analysis。

不要把研知库写成已经完整复刻 MinerU。当前生产可用范围是 native layout v2 的结构化解析、扫描/混合 PDF 类型检测、Tesseract 中英文 OCR 回退、公式图片裁剪与 OpenCode Go `gpt-5.6-luna` LaTeX 重建链路、几何阅读顺序重建、基于词坐标和 PDF 横线的复杂表格行列/稀疏单元格/跨列/Booktabs/堆叠子表重建、代表图选择、证据块、确定性事实到版面证据图谱和管理台集成；尚未实现本地公式模型、高级低清晰度/旋转文本 OCR、任意复杂浮动版面语义顺序恢复、任意 row-span 可靠恢复、向量化版面块搜索或独立图数据库。

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
| 版面结构化 | native layout v2 | 借鉴 MinerU 的文档结构化思想，自研 PyMuPDF parser，不安装 MinerU |
| 版面兜底 | MinerU 可选 | 只在 PDF 复杂版面或扫描件导致 native layout v2 / `papi` 产物不足时评估 |

## 命令映射

| airesearch 命令 | 实际实现 | 说明 |
|-----------------|----------|------|
| `/paper-add <input>` | `papi add <input>` | 手动入库，支持多源输入 |
| `airesearch.paper.ingest_single` | `papi add` + sync + `paper_layout_parse` job | 管理台单篇入库，成功后自动排队 layout v2 |
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
4. 管理台 action `airesearch.paper.ingest_single` 在同步成功并识别 `paper_key` 后，会自动创建 `paper_layout_parse` 后台任务。
5. 自动排队有去重：已有 completed/skipped layout run 时不重跑；已有 queued/running layout job 时复用现有 job。
6. 如果需要图谱，读取 `summary.md`、`equations.md`、必要 tex/chunk，进入 L2 extraction。

### 2B. Native Layout V2

当前 layout v2 是研知库自研的 PDF 版面理解能力，借鉴 MinerU 的“结构化文档产物”方向，但不是安装 MinerU。

核心模块：

- `layout_parser.py`: PyMuPDF PDF parser，输出 Markdown、content list、layout JSON、debug JSON、summary JSON 和 assets。
- `table_reconstruction.py`: 词级 bbox 行列聚类、稀疏单元格、表头、跨列和重建置信度；不依赖 MinerU 或 GPU 模型。
- `layout_parse.py`: DB run/artifact/block 记录、CLI、admin detail contract。
- `layout_service.py`: 代表图候选、PDF figure crop fallback、caption-window 整图截图、cover fallback 排序。
- `layout_evidence_graph.py`: 将 research facts 与高质量图、表、公式确定性关联，写入现有 `kg_nodes` / `kg_edges` / `kg_provenance`。

主要数据表：

- `paper_layout_runs`: 每次解析 run、provider/version/status、input/output、stats。
- `paper_layout_blocks`: page/block/type/bbox/text/asset/metadata。
- `paper_artifacts`: layout markdown/content list/structure/debug/summary/assets 路径和 hash。

主要能力：

- 产物版本：`api_version = "layout-v2"`，`provider = "airesearch_layout"`。
- 清理规则：重复页眉/页脚和纯页码从 Markdown/content list/layout JSON 中移除，summary 记录 `removed_margin_blocks`。
- PDF 类型与 OCR：逐页判定 `digital`、`scanned`、`mixed`；`ocr_mode=auto` 时只对缺少文本层的扫描/混合页运行 Tesseract，默认语言 `eng+chi_sim`、DPI 220。
- OCR provenance：OCR block 写入 `metadata.ocr`、`ocr_engine`、`ocr_languages`、`ocr_confidence`；summary 写入 `document_type`、`page_types` 和 OCR 页/块统计。
- 公式 OCR：数字 PDF 先用本地规则过滤公式候选；扫描公式 block 才会按 bbox 裁剪为 PNG，并由视觉 provider 返回和校验 LaTeX。成功结果保留原 OCR 文本、模型、置信度、crop asset 和来源坐标。生产通过 OpenCode Go Responses API `/v1/responses` 使用 `gpt-5.6-luna`，请求仅经 `AIRESEARCH_FORMULA_OCR_PROXY` 指定的本机 `7890` 代理；支持 `off`、`auto`、`force`，低置信度结果不会覆盖原文。
- Canonical 公式优先级：`equations.md` / 论文 TeX 的完整公式高于 PDF layout 文本和图片 OCR。artifact ledger 将 fenced LaTeX 按完整多行块写入、按论文规范化去重，并从误包整段 TeX 文档的污染围栏中只抢救完整 display-math 环境；“No LaTeX source available” 不会写成公式。公开 `paper-layout-evidence.json` 优先输出 `source_kind=paperpipe_equations`，layout 公式仅在没有有效 canonical 公式时兜底。
- Luna 使用边界：当前生产只在 `auto` 模式下为扫描/OCR 公式图生成 LaTeX，不会无差别重写已有源码，也尚未对所有表格调用模型。复杂/低置信度表格的推荐后续流程是原图 + OCR token + bbox 进入审核队列，由 Luna 返回严格 `headers/rows/merged_cells/confidence/issues`，再经过 JSON Schema 和逐格数值校验；模型候选不得覆盖原始证据。
- 阅读顺序：`geometry_columns_v2` 先移除页眉页脚，再识别左/右栏和跨栏锚点，用跨栏标题/图表/公式切分页面区段，并把图表与 caption 作为相邻视觉组排序。每个 block 写入 `metadata.reading_order_index`、`reading_order_region`、`reading_order_confidence` 和原因；summary 写入多栏页、跨栏块、caption 组和低置信读序计数。
- block 类型：title/text/image/chart/table/interline_equation 等。
- 表格结构：无框表使用 `word_geometry_v2`；有框表先用 PyMuPDF 线框确定整表区域再以 `pymupdf_table_lines` 重建；Booktabs 彩色/无竖线表使用 `booktabs_geometry_v1` 聚合横线、整表长边界和堆叠子表边界。解析器会拒绝正文折叠进首列、图片/图注混入表格以及与完整 Booktabs 表重叠的候选；输出 `table_rows`、`table_cells`、cell bbox/row/column/span/confidence、表头行数、列锚点/边界、重建置信度和原因。
- 线框安全门槛：`pymupdf_table_lines` 要求 `PyMuPDF>=1.27.0` 且运行时存在 `page.find_tables()`；更旧版本只关闭线框区域检测，继续使用 `word_geometry_v2`，避免原生库差异影响 API 服务。
- 表格降级：几何信息不足时保留 `text_spacing_v1`，仍生成 `table_markdown`/`table_html`，但管理台和 API 会显示文本降级计数；不要将它描述成与几何重建同等可靠。
- evidence blocks：图、表、公式、标题、关键文本块，供深度解读和公开详情页证据面板使用。
- public evidence：`export_report_bundle()` 生成 `paper-layout-evidence.json` 和 `layout-evidence-graph.json`，`research_site.py` 合并到 `/airesearch/api/papers/<paper_key>.json` 的 `layout_evidence` 与 `evidence_graph` 字段，并在公开论文详情页展示“实验与评测 / 证据关系 / 公式 / 表格 / OCR / Layout”。表格以转义后的语义 HTML 显示，公开预览最多 12 行、12 列、单元格 160 字符；`display_quality=good|review|fallback` 显示为“结构化预览 / 需要复核 / 文本降级”。公式通过 MathJax 排版，畸形 LaTeX 或非公式标签会被过滤，不会伪装成高可信公式。
- `layout-evidence-graph.json` 是完整 report bundle 的数据产物；公开站点通过逐论文 API 分片展示 `evidence_graph`，不会要求浏览器下载整库图谱。
- admin evidence inspector：统一管理台 `/niu-secretary/admin/airesearch/papers` 的论文详情区提供“证据检查器”，复用 `airesearch.admin.paper.layout.detail`，展示 `事实关联 / 证据块 / 公式 OCR / 表格结构 / OCR / 读序 / 视觉候选`，用于复核事实到证据的匹配方法/分数/provenance、公式 LaTeX、表格 markdown/cell 结构、OCR 错误、读序风险和代表图候选。
- evidence 质量：每个 evidence block 写入 `metadata.quality_score` 和 `metadata.quality_reasons`；当前 `quality_score >= 0.72` 视为高质量证据。
- capabilities：除结构/图注/公式/证据质量外，表格新增 `has_geometry_tables`、`has_spanning_table_cells`、`has_text_fallback_tables`；阅读顺序新增 `has_reading_order`、`has_multi_column_reading_order`、`has_caption_paired_reading_order`、`needs_reading_order_attention`。
- representative visual：优先 `pdf_figure_crop` 和 `layout_block`，再退回 source figures / cover。
- PDF 整图截图：对 Figure 1/2 caption 生成 `pdf_figure_crop` 候选；图注识别要求严格的 caption 前缀，拒绝 `Figure 2 presents ...` 这类正文引用，并兼容 PDF 图注换行。同页多个 Figure 会按 caption 附近的图块组分配裁剪框，随后吸收相邻的无 caption 图层和图内短标签，以保留完整复合图；足够完整的图块使用 tight 裁剪，碎片图层或缺图时从 PDF 重渲染整图，避免把局部素材、纯文字块或栏间正文误当代表图。裁剪摘要版本变化时必须生成新资源，不能复用旧图。

Layout evidence graph 规则：

- 稳定键：`research_fact:<paper_key>:<fact_id>`、`layout_evidence:<paper_key>:<run_id>:<block_id>`；关系为 `has_research_fact`、`has_layout_evidence`、`supported_by`。
- 所有权：只重建 `extractor_name=layout_evidence_graph` 的事实/证据节点与边；共享 `paper:<paper_key>` 节点只做 `insert or ignore`，不覆盖、不删除。
- 数据来源：事实与 `research_fact_provenance`，以及最新 completed/reused layout run 的 image/chart/table/interline_equation block。
- 门槛：入图质量至少 `0.55`；文本匹配质量至少 `0.72`。优先 `paper_layout_blocks:<id>` 显式引用，其次至少 24 字符的规范化包含，最后要求至少 4 个共享词元、source coverage `>=0.72`、Jaccard `>=0.30` 的严格词元匹配。
- 类型兼容：dataset/benchmark 只匹配图或表；method/claim 可匹配图、表、公式；limitation 只匹配图或表。每条事实最多 3 条证据，排序稳定；同页、同证据类型、标准化内容相同的 layout fragment 只保留一个关系目标。
- 公开上限：24 facts、48 evidence、72 relations、每条事实 3 links、preview 240 字；移除本地路径、raw HTML、完整 metadata 和 admin provenance。
- 自动刷新：CLI 事实提取、CLI/admin layout parse、admin fact create/update/delete、MVP pipeline 和 report bundle export 都会重建受影响图谱。

常用 API：

- `airesearch.paper.ingest_single`: 单论文入库并自动排队 layout。
- `airesearch.admin.paper.layout.generate`: 手动解析或强制重跑。
- `airesearch.admin.paper.layout.detail`: 读取完整 layout v2 detail。
- `airesearch.admin.state`: 读取论文列表的 layout compact status。
- `/niu-secretary/admin/airesearch/papers`: 管理台论文页，显示 layout badge、版面解析摘要、产物列表和 Layout Evidence Inspector。
- `/niu-secretary/airesearch/api/papers/<paper_key>.json`: 公开静态论文 API，包含 `layout_evidence` 以及脱敏的 `evidence_graph`，供详情页和前端只读展示。
- `extract-layout-evidence-graph [--paper-key <key>] [--limit N]`: 重建事实到版面证据图谱。
- `export-layout-evidence-graph --out <path>`: 导出稳定、脱敏、按论文排序的 `evidence-graph-v1` JSON。
- `workflow-check --paper-key <key> --site-dir exports/site-current`: 只读验收论文检索、入库产物、五类 facts、中文产物、layout 图片/表格/公式、深度解读、公开静态 JSON 和 HTML，共 13 项；公开检查要求 `evidence-graph-v1` 和“证据关系”页面标记，失败退出码为 2。
- `python scripts/rerun_all_layouts.py --db data/airesearch.sqlite3 --layout-output-dir data/layout --log-dir <dir>`：全库强制重提取，逐篇校验成功后删除该篇旧 run/artifact/output，带空间保护和 JSONL 续跑日志。2026-08-11 生产重跑结果为 209/209 成功、0 失败；最终保留 209 个 completed run、每篇一个。

测试命令：

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_layout_parse.py \
  airesearch/tests/test_layout_service.py \
  airesearch/tests/test_layout_evidence_graph.py \
  airesearch/tests/test_workflow_check.py \
  airesearch/tests/test_paper_blog.py::test_ingest_single_paper_auto_queues_layout_parse \
  airesearch/tests/test_paper_blog.py::test_ingest_single_paper_reuses_active_layout_job -q
```

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

### 6. 单篇论文深度解读博客

研知库支持为任意已入库论文生成可发布的中文深度解读博客。该能力不是单篇 ColaVLA 的特例，而是复用 `paper_blog.py` 的通用链路：

1. `build_blog_evidence_pack()` 汇总论文 metadata、paper card、research facts、artifact text、公式、引用、代码链接和图片候选。图片候选先使用 native layout v2 的 PDF crops 与 layout visuals 评估可发布的图、表覆盖；只有 figure 或 table 必需类别不足时，才调用 source figure/table resolver 补齐。这能避免已有 layout 证据足够时仍进行不必要的 arXiv 源码下载或 PDF rasterization。
2. `select_blog_images()` 从证据包候选中挑选可发布素材；当候选包含 `quality_score` 时，优先选择 `quality_score >= 0.72` 的高质量图/表，并按内容指纹去重。
3. `generate_and_publish_blog()` 生成 outline 与各章节正文，写入 `paper_blog_posts`、`paper_blog_versions` 和 `paper_blog_generation_cache`。
4. `export_paper_blogs()` 将已发布博客导出为 `paper-blogs.json`，`research_site.py` 在静态站中生成 `/blogs/index.html`，并在对应论文详情页生成“深度解读”tab。
5. 统一管理台 `/niu-secretary/admin/airesearch/blogs` 可对任意论文触发“生成深度解读 / 强制重新生成 / 隐藏 / 回滚版本”。后端 action 为 `airesearch.admin.paper.blog.generate`、`.detail`、`.rollback`、`.hide`。

最终 Markdown 不依赖模型自行排版：每个 required section 都会规范化为可见的 `##` 标题；章节返回的有效 image IDs 会确定性地渲染为本地 Markdown 图片，并在整篇博客内去重。同一素材不会重复插入；存在 selected image evidence 但最终正文没有任何嵌入图片时，生成校验和批处理审计都会失败。

生成缓存是可恢复的分段检查点，不是最终发布事务的一部分。通过校验的 outline 或章节会立即写入 `paper_blog_generation_cache`；后续章节遇到 502/503、超时或进程重启时，使用相同 `paper_key/source_hash/prompt_version/model/request_hash` 且 `force=false` 的重试会复用这些检查点。只有整篇组装、事实覆盖、图片、公式和 Markdown 门禁全部通过后，才写入并切换 `paper_blog_versions` / `paper_blog_posts` 的发布版本。A/B 和正式 batch 都必须使用 `force=false`，管理台显式“强制重新生成”仍可绕过缓存。

深度解读的证据与事实门禁同样由运行时收口。Evidence pack 在计算 `source_hash` 前过滤包含 U+FFFD、C0 控制字符（仅允许 tab/newline/CR）或 DEL/C1（U+007F-U+009F）的公式；过滤后的可发布公式集合进入 hash，集合变化会使 outline/section 缓存正确失效。有 facts 时，outline 按 `fact_type` 分配到语义章节并跨章节去重，至少覆盖 `ceil(50%)` 的有效 facts；默认每章最多 4 条，facts 较多时动态扩容。章节请求只携带该章分配的 facts，响应 `fact_ids` 必须与输入集合完全一致，空章节保持空集合，不注入 fallback facts。Batch hard gate 要求有效事实覆盖率 `>= 0.5`、最终 Markdown 无 U+FFFD 或未转义 control token；公式门禁只按可发布公式计数。

博客生成前应优先读取 `airesearch.admin.paper.layout.detail`。如果 `capabilities.has_high_quality_evidence` 为 false，先触发 layout 解析；如果已有高质量 evidence blocks，则把图注、表格、公式和代表图候选作为深度解读的 grounded context。博客选图会复用 `layout_service` 的 `pdf_figure_crop` 候选，并按内容指纹去重，再结合 figure role、quality score、caption 语义（overview/framework/example 等）排序。高质量 layout 公式会合并进 `BlogEvidencePack.equations`，结构化表格会进入 `artifact_texts.layout_structured_tables`，并在 prompt 字符预算中保留独立空间。`OpenAICompatibleBlogProvider` 的 prompt payload 会包含 `evidence_quality_policy`，要求模型优先使用高质量 evidence。

深度解读 provider 支持两种 OpenAI-compatible 协议：`chat_completions` 向 API root 追加 `/chat/completions`；`responses` 接受 API root 或完整 `/responses` endpoint，并统一解析字符串或结构化 `output_text`。服务端通过 `AIRESEARCH_BLOG_API_STYLE`、`AIRESEARCH_BLOG_BASE_URL`、`AIRESEARCH_BLOG_MODEL`、`AIRESEARCH_BLOG_API_KEY`、`AIRESEARCH_BLOG_PROXY` 配置，其中 proxy 只作用于 Responses；管理端请求不得覆盖 endpoint、proxy 或密钥。未显式指定协议时，`/responses` endpoint 自动选择 Responses，其余默认 Chat Completions。

**[2026-09-15] 统一 LLM 层已接入**：上述 env 链的全部默认值现在由 `niu_core/llm_client`（`config/models.yaml`）提供——fact/blog/translate/formula_ocr/embeddings 的模型、base_url 在 yaml 里统一定义；显式 env 仍优先于 config 默认（顺序不变）。新增 `NIU_LLM_<NAME>_BASE_URL/_API_KEY/_MODEL` 三元组可单独重定向某用途。`DEFAULT_BLOG_MODEL/BASE_URL` 不再硬编码，import 时从统一配置解析；`DEEPSEEK_ARM_DEFAULT_MODEL`（deepseek arm 专用）与 blog 默认解耦。管理台「AI 渠道」页可视化这些路由。

已发布博客的坏公式使用局部修复链路，不重新生成整篇深度解读。`blog_formula_repair.py` 先用 MathJax v3 逐式编译；只有编译确认失败的公式才携带失败 LaTeX、局部正文和 PDF page/bbox crop 调用 `AIRESEARCH_FORMULA_OCR_*` 配置的 `gpt-5.6-luna`。Luna 返回值必须再次通过确定性规范化和 MathJax 编译，且达到置信度门槛，才会按公式 locator 精确替换并发布新版本。编译器、证据或 API 不可用、候选仍无法编译、置信度不足时都不得写博客。审计表 `paper_blog_formula_repairs` 记录原/修后 LaTeX、版本定位、PDF 证据、上下文、模型、置信度、首次和二次验证、时间戳及应用版本；唯一 input hash 保证重复执行幂等，失败重试必须显式使用 `--force-retry`。命令与字段说明见 `../docs/airesearch-api.md`。

通用深度解读 provider 的三类配置不能混写为一条回退链。模型顺序是“显式参数 -> `AIRESEARCH_BLOG_MODEL` -> `NIU_ASSISTANT_MODEL` -> `deepseek-v4-pro`”；base URL 顺序是“显式参数 -> `AIRESEARCH_BLOG_BASE_URL` -> `TRANSLATE_BASE_URL` -> `OPENAI_BASE_URL` -> `NIU_ASSISTANT_API_BASE` -> DeepSeek 默认地址”；API key 顺序是“`AIRESEARCH_BLOG_API_KEY` -> 调用方指定的 key 环境变量 -> `OPENAI_API_KEY` -> `TRANSLATE_API_KEY` -> `NIU_ASSISTANT_API_KEY`”。

OpenCode Go 的生产配置统一存放在被 Git 忽略且权限为 `600` 的 `airesearch/.env`：`OPENCODE_GO_BASE_URL` 是唯一 API root，`OPENCODE_GO_API_KEY` 是唯一凭据，`OPENCODE_GO_PROXY` 是可选代理。Chat Completions 从 root 派生 `/chat/completions`，Responses 从 root 派生 `/responses`；禁止在环境文件中复制多个 OpenCode Key 或混用完整 endpoint。模型职责必须明确：DeepSeek A/B arm 使用 Chat Completions 和 `AIRESEARCH_DEEPSEEK_BLOG_MODEL -> AIRESEARCH_BLOG_MODEL -> deepseek-v4-pro`；Luna arm 使用 `AIRESEARCH_LUNA_BLOG_MODEL`，事实抽取使用 `AIRESEARCH_FACT_MODEL`，公式 OCR 使用 `AIRESEARCH_FORMULA_OCR_MODEL`。后两类能力使用 Responses，但模型配置彼此独立，启动脚本不得用 OCR 模型覆盖事实模型。`/etc/niu-secretary-api.env` 只保留端口、数据库和管理员配置。API key 不能作为 CLI 参数、管理端 payload、日志、报告或数据库字段。

批准的 40 篇流程使用 `what-if-world`、`world2vlm` 做同证据包 A/B。原 20 篇清单之后追加 `probeact`、`gem-4d`、`agenticnav`、`ttt-vla`、`flymirage`、`ouroboros-spatial`、`phyedit`、`mbench`、`2605_27817`、`2606_03784`、`2606_02735`、`2606_05737`、`2606_08881`、`2606_00253`、`2606_06002`、`2606_10348`、`mllm-for3d`、`2606_09644`、`tabverse`、`2606_10904`。`batch` 必须接收完整 40 篇清单；前两篇胜出版本和所有已有版本先经过 fresh audit，合格版本直接复用。生产批处理使用单进程 `--concurrency 4`，每个工作线程独立持有 provider，JSONL、资产清单和最终 summary 由主线程串行写入。`omnivl-guard` 因缺少 `benchmark` fact 不进入本批次，补齐并审核该事实后才能进入后续批次。

批处理只使用 `airesearch/scripts/generate_deep_readings.py` 的 `preflight`、`backup`、`ab`、`batch`、`restore` 子命令。五个阶段共享同一个 `RUN_DIR`：`backup --out RUN_DIR`、`ab --out RUN_DIR`、`batch --out RUN_DIR`、`restore --backup-dir RUN_DIR`，这样备份 manifest、created-assets、winner、日志和恢复输入始终一致。顺序不可改变：40 篇预检全绿 -> 选择行级增量备份 -> 两篇 A/B -> 人工检查四个输出、`ab-report.json` 和自动生成的 `winner.json` -> 传入完整 40 篇清单执行 `--concurrency 4` 可恢复批处理 -> 40 篇 workflow check -> 只执行一次站点构建和部署。`ab` 会根据机器评分自动写 `winner.json`，并在数据库中把两篇样本切换到胜出版本；人工检查是执行 `batch` 前的门槛，不得覆盖 `winner.json` 冒充人工结论。执行 `batch` 前，CLI 会校验 winner 与当前 manifest 的 `backup_id`、完整且顺序一致的 40 篇清单、prompt version、运行时 model arm/model/API style，以及两篇 A/B 样本的当前 source hashes 全部一致。`restore` 只恢复清单内论文在三张博客表中的备份行，不自动删除任何博客资产或生成文件；它保留并报告 `retained_unowned_assets`，`created-assets.json` 只提供信息性计数。`ab`、`batch` 不构建或发布静态站；任一论文失败时保留旧公开站，不允许发布部分批次。具体命令、JSONL 产物和回滚步骤见 `DEVELOPMENT.md` 与 `../docs/airesearch-api.md`。

发布验证必须检查三处：

```bash
# 顶部菜单 Blog 入口
curl -s http://127.0.0.1/niu-secretary/airesearch/ | grep 'blogs/index.html'

# Blog 索引页
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/niu-secretary/airesearch/blogs/index.html

# 单篇论文详情页深度解读入口
curl -s http://127.0.0.1/niu-secretary/airesearch/papers/colavla.html | grep 'paper-tab-deep-reading'
```

注意：`exports/mvp-current/bundle/` 可能包含 `paper-blogs.json` 和博客资源，但完整公开发布目录是 `exports/site-current/`。部署到 nginx 时优先使用 `exports/site-current/`，否则容易漏掉 `/blogs/index.html`。

## 数据模型最小集

- `papers`: 映射 paperpipe `index.json` 和每篇 paper directory。
- `paper_sources`: arXiv/DOI/S2/URL/PDF hash/title search 等来源记录。
- `paper_artifacts`: `summary.md`、`equations.md`、`tldr.md`、`source.tex`、figures 的路径和 hash。
- `paper_layout_runs`: layout v2 解析 run、状态、输入 PDF、输出目录、stats。
- `paper_layout_blocks`: layout v2 页块、类型、bbox、文本、asset 和 metadata。
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

## LLM 路由与调用记录（2026-09-16）

研知库的 8 个调用点全部走 `compat.resolve("<逻辑路由>")`，路由表唯一来源是仓库根 `config/models.yaml`（管理台「AI 渠道」页改的就是它）。**优先级**：显式参数 → 路由专属 env（`AIRESEARCH_FACT_*` / `BLOG_*` / `FORMULA_OCR_*`，逃生舱）→ `config/models.yaml` → 历史通用 env → 硬编码。

- 当前映射：`fact` / `blog` / `formula_ocr` → `opencode_go/deepseek-v4.1-flash`；`translate` → `opencode_go/mimo-v2.5`；`embed` → dashscope `text-embedding-v4`；全部保留 sub2api gpt-5.6-luna 作 fallback
- ⚠️ **坑**：`airesearch/.env` 里若留着 `AIRESEARCH_FACT_MODEL` / `AIRESEARCH_FACT_BASE_URL` / `TRANSLATE_BASE_URL` 之类显式变量，会**压过 yaml** —— 这就是「改了 yaml 不生效」的根因；2026-09-16 已把这些指到 opencode 新模型，并注释掉 `OPENCODE_GO_PROXY`（该变量指向不存在的代理路径，曾让事实抽取每请求干等 300s）
- ⚠️ **自建 urllib 客户端必须带两个头**：正常 `User-Agent`（Cloudflare 拦默认 UA → `403 error code: 1010`）+ `x-opencode-session`（缺失 → `400 MissingSessionID`）。`fact_extraction.py` / `formula_ocr.py` / 两个翻译脚本都已补
- **调用记录**：统一层在 `NiuLLM.chat()` 收口；自建客户端用 `@call_log.tracked("fact", endpoint_param="base_url")` 埋点。库 `data/llm_calls.sqlite3`，管理台「AI 渠道 → API 用量」可看。papi 内部走 litellm，由 `papi_hooks/sitecustomize.py` 挂钩记录（详见 `niu_core/llm_client/README.md`）
- 改路由后的验收：真实跑一遍（探活 + 实际抽取），并可用「期间 sub2api `/v1/responses` 请求数 = 0」反证确实走了 opencode

## 站点发布与「最近上新」（2026-09-16）

产物与部署：`exports/site-current/` → `sudo rsync -av exports/site-current/ /var/www/html/niu-secretary/airesearch/`（**必须包含 `paper-assets/`、不加 `--delete`**，并把权限归一为目录 755 / 文件 644，否则 nginx 403）。

- 首页「最近上新」区块 + 每篇 `NEW` 标 + 双日期标签（arXiv 首发日 / 入库日）+ 时段筛选（近 7 天 / 30 天 / 全部）
- 实现：`research_digest.py`（算 updated_at / 热度）+ `research_site.py`（渲染）；`api/papers.json` 每篇必须带日期字段
- 验收口径：312 篇 **100% 带日期**，HTTP 200/200/200/200 + 一个预期 404，首页控件存在于 DOM
- 铁律：**改代码 → 重启 `niu-secretary-api` → 再 rebuild_site**，否则站点还是旧数据

## 会议论文 PDF 映射（2026-09-15）

arXiv/会议页 → PDF 的兜底在 `providers.py`。CVPR 用页内相对链接 `..._paper.pdf`；NeurIPS/ICLR 走 `hash/<x>-Abstract-Conference.html` → `file/<x>-Paper-Conference.pdf`；AAAI 是 JS 壳页、无解（历史遗留 1 条）。

- ⚠️ 兜底判断必须用**原始 URL**：归一化后的 URL 若是标题串，`is_conference_page()` 会返回 False，静默漏掉
- 补历史欠账时用**显式 `--paper-list` + 每批 3 篇**小批跑，别一把梭

## 数据库备份（2026-09-16）

`scripts/backup-airesearch-db.sh` + ubuntu crontab 每日 03:20（本地）/ 周日（WebDAV）。库 650MB → zstd 95MB，本地留 30 份 + `.sha256`；远端 rclone `niu:` → `webdav/airesearch/`，上传后**回读算哈希**校验。

- 恢复演练已验证：解压 2.3s、`integrity=ok`、**38 张表计数与线上库全部一致**
- 完整方法论见 skill `service-data-backup`（含 WebDAV/Seafile 配方、配额换算、`pkill -f` 自杀坑）

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
