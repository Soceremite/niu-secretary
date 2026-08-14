<template>
  <section class="admin-resource airesearch-admin airesearch-admin-console">
    <PageHeader eyebrow="研知库" :title="viewMeta.title" :description="viewMeta.description">
      <el-button :loading="loading" @click="loadState">刷新</el-button>
    </PageHeader>

    <div class="airesearch-admin-stats">
      <div v-for="card in statsCards" :key="card.label" class="admin-stat-card">
        <strong>{{ card.value }}</strong>
        <span>{{ card.label }}</span>
      </div>
    </div>

    <section v-if="view === 'overview'" class="airesearch-admin-grid">
      <article class="airesearch-admin-panel wide">
        <div class="airesearch-panel-head">
          <span>Research Operations</span>
          <h2>研知库运行总览</h2>
          <p>统一管理论文编辑、搜索配置、任务队列和发布能力，日常运营不再依赖独立旧页面。</p>
        </div>
        <div class="airesearch-health-grid">
          <div v-for="item in healthCards" :key="item.label">
            <b>{{ item.value }}</b>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </article>
      <article class="airesearch-admin-panel">
        <div class="airesearch-panel-head">
          <span>Queue</span>
          <h3>任务状态</h3>
        </div>
        <ul class="airesearch-snapshot-list">
          <li v-for="status in jobStatusRows" :key="status.name">
            <strong>{{ status.label }}</strong>
            <span>{{ status.count }}</span>
            <small>任务队列</small>
          </li>
        </ul>
      </article>
      <article class="airesearch-admin-panel">
        <div class="airesearch-panel-head">
          <span>Profiles</span>
          <h3>搜索方向</h3>
        </div>
        <div class="airesearch-profile-chip-list">
          <span v-for="profile in state.profiles" :key="profile.name">{{ profile.name }}</span>
        </div>
      </article>
    </section>

    <section v-else-if="view === 'papers'" class="airesearch-admin-split">
      <article class="airesearch-admin-panel airesearch-paper-list-panel">
        <div class="airesearch-panel-head">
          <span>Paper Library</span>
          <h2>论文管理</h2>
          <p>左侧选择论文，右侧直接维护链接、展示状态、草稿和研究事实。</p>
        </div>
        <el-input v-model="paperQuery" placeholder="搜索标题、paper key、arXiv 或 GitHub" clearable />
        <div class="airesearch-paper-list-summary">
          <span>{{ filteredPapers.length }} 篇</span>
          <span>{{ layoutParsedCount }} 篇已解析</span>
          <span>{{ layoutEvidencePaperCount }} 篇有证据块</span>
          <span>{{ layoutHighQualityEvidencePaperCount }} 篇高质证据</span>
        </div>
        <div class="airesearch-paper-list" v-loading="loading">
          <button
            v-for="paper in filteredPapers"
            :key="paper.paper_key"
            :class="{ active: selectedPaperKey === paper.paper_key }"
            type="button"
            @click="selectPaper(paper.paper_key)"
          >
            <strong>{{ paper.title }}</strong>
            <span>{{ paper.paper_key }}</span>
            <em>
              {{ paper.year || '年份未知' }}
              <b v-if="paper.hidden">隐藏</b>
              <b v-if="paper.has_draft">草稿</b>
            </em>
            <div class="airesearch-paper-layout-tags">
              <b :class="`status-${paperLayoutStatus(paper)}`">{{ layoutStatusLabel(paperLayoutStatus(paper)) }}</b>
              <b v-if="paper.layout_document_type && paper.layout_document_type !== 'digital'" class="document-scan">
                {{ documentTypeLabel(paper.layout_document_type) }}
              </b>
              <b v-if="Number(paper.layout_high_quality_evidence_blocks || 0) > 0" class="quality-good">高质 {{ paper.layout_high_quality_evidence_blocks }}</b>
              <b v-if="Number(paper.layout_evidence_ready_blocks || 0) > 0">证据 {{ paper.layout_evidence_ready_blocks }}</b>
              <b v-if="Number(paper.layout_captioned_visual_blocks || 0) > 0">图注 {{ paper.layout_captioned_visual_blocks }}</b>
              <b v-if="Number(paper.layout_structured_table_blocks || 0) > 0">表格 {{ paper.layout_structured_table_blocks }}</b>
              <b v-if="Number(paper.layout_equation_blocks || 0) > 0">公式 {{ paper.layout_equation_blocks }}</b>
              <b v-if="Number(paper.layout_reading_order_multi_column_pages || 0) > 0">多栏 {{ paper.layout_reading_order_multi_column_pages }}</b>
              <b v-if="Number(paper.layout_reading_order_low_confidence_blocks || 0) > 0" class="document-scan">读序风险 {{ paper.layout_reading_order_low_confidence_blocks }}</b>
            </div>
          </button>
        </div>
      </article>

      <article class="airesearch-admin-panel airesearch-editor-panel">
        <el-empty v-if="!selectedPaperKey" class="airesearch-editor-empty" description="选择一篇论文开始编辑" />
        <template v-else>
          <div class="airesearch-panel-head inline">
            <div>
              <span>Paper Editor</span>
              <h2>{{ paperDetail?.title || selectedPaperKey }}</h2>
              <p>{{ selectedPaperKey }}</p>
            </div>
            <div class="airesearch-toolbar">
              <el-tag v-if="paperDetail?.draft_updated_at" type="warning">有草稿 {{ paperDetail.draft_updated_at }}</el-tag>
              <el-button :loading="paperLoading" @click="loadPaperDetail(selectedPaperKey)">重载</el-button>
            </div>
          </div>

          <el-form label-position="top" :model="paperForm" class="airesearch-editor-form">
            <div class="airesearch-paper-summary">
              <div>
                <span>arXiv</span>
                <strong>{{ paperForm.arxiv_id || '未填写' }}</strong>
              </div>
              <div>
                <span>论文链接</span>
                <strong>{{ paperForm.paper_url ? '已配置' : '未配置' }}</strong>
              </div>
              <div>
                <span>GitHub</span>
                <strong>{{ paperForm.github_url ? '已配置' : '未配置' }}</strong>
              </div>
              <div>
                <span>展示</span>
                <strong>{{ paperForm.hidden ? '隐藏' : '展示' }}</strong>
              </div>
            </div>
            <div class="airesearch-form-grid">
              <el-form-item label="arXiv ID">
                <el-input v-model="paperForm.arxiv_id" placeholder="2401.00000" />
              </el-form-item>
              <el-form-item label="论文链接">
                <el-input v-model="paperForm.paper_url" placeholder="https://..." />
              </el-form-item>
              <el-form-item label="GitHub 链接">
                <el-input v-model="paperForm.github_url" placeholder="https://github.com/owner/repo" />
              </el-form-item>
              <el-form-item label="展示状态">
                <el-switch v-model="paperForm.hidden" active-text="隐藏" inactive-text="展示" />
              </el-form-item>
            </div>
          <div class="airesearch-actions-row">
            <el-button type="primary" :loading="actionLoading === 'paper.update'" @click="savePaper">保存论文编辑</el-button>
            <el-button :loading="actionLoading === 'paper.draft.save'" @click="saveDraft">保存草稿</el-button>
            <el-button :disabled="!paperDetail?.draft_updated_at" @click="loadDraft">载入草稿</el-button>
            <el-popconfirm title="确认丢弃这篇论文的草稿？" confirm-button-text="确认" cancel-button-text="取消" @confirm="deleteDraft">
                <template #reference>
                  <el-button :disabled="!paperDetail?.draft_updated_at" :loading="actionLoading === 'paper.draft.delete'">丢弃草稿</el-button>
                </template>
              </el-popconfirm>
              <el-popconfirm title="确认删除这篇论文？会从论文库移入归档。" confirm-button-text="确认删除" cancel-button-text="取消" @confirm="deletePaper">
                <template #reference>
                  <el-button type="danger" :loading="actionLoading === 'paper.delete'">删除论文</el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-form>

          <section class="airesearch-blog-entry">
            <div>
              <span>Deep Reading</span>
              <strong>论文深度解读</strong>
              <p>生成、查看任务状态及管理历史版本。</p>
            </div>
            <el-button type="primary" plain @click="openBlogGenerator">前往博客生成</el-button>
          </section>

          <section class="airesearch-layout-entry" v-loading="layoutLoading">
            <div class="airesearch-layout-head">
              <div>
                <span>Layout Parse</span>
                <strong>版面解析</strong>
                <p>{{ latestLayoutMessage }}</p>
              </div>
              <el-tag :type="layoutStatusTagType(currentLayoutStatus)">{{ layoutStatusLabel(currentLayoutStatus) }}</el-tag>
            </div>
            <dl class="airesearch-layout-metrics">
              <div>
                <dt>最近 Run</dt>
                <dd>{{ latestLayoutRun?.id ? `#${latestLayoutRun.id}` : '无' }}</dd>
              </div>
              <div>
                <dt>Markdown</dt>
                <dd>{{ layoutArtifactCount('layout_markdown') ? '已生成' : '缺失' }}</dd>
              </div>
              <div>
                <dt>layout.json</dt>
                <dd>{{ layoutArtifactCount('layout_structure_json') ? '已生成' : '缺失' }}</dd>
              </div>
              <div>
                <dt>summary.json</dt>
                <dd>{{ layoutArtifactCount('layout_summary_json') ? '已生成' : '缺失' }}</dd>
              </div>
            </dl>
            <div class="airesearch-layout-counts">
              <span>文本 {{ layoutBlockCount('text') }}</span>
              <span>图片 {{ layoutBlockCount('image') }}</span>
              <span>表格 {{ layoutBlockCount('table') }}</span>
              <span>公式 {{ layoutBlockCount('interline_equation') }}</span>
              <span>图注 {{ layoutSummaryNumber('captioned_visual_blocks') }}</span>
              <span>结构表 {{ layoutSummaryNumber('structured_table_blocks') }}</span>
              <span>几何表 {{ layoutSummaryNumber('geometry_table_blocks') }}</span>
              <span>跨列表 {{ layoutSummaryNumber('spanning_table_blocks') }}</span>
              <span>文本降级 {{ layoutSummaryNumber('text_fallback_table_blocks') }}</span>
              <span>多栏页 {{ layoutReadingOrderNumber('multi_column_pages') }}</span>
              <span>跨栏块 {{ layoutReadingOrderNumber('cross_column_blocks') }}</span>
              <span>Caption 组 {{ layoutReadingOrderNumber('caption_paired_blocks') }}</span>
              <span>读序低置信 {{ layoutReadingOrderNumber('low_confidence_blocks') }}</span>
              <span>证据块 {{ layoutSummaryNumber('evidence_ready_blocks') }}</span>
              <span>文档 {{ documentTypeLabel(String(layoutSummary.document_type || 'digital')) }}</span>
              <span>OCR 页 {{ layoutOcrNumber('pages_succeeded') }}/{{ layoutOcrNumber('pages_attempted') }}</span>
              <span>OCR 块 {{ layoutOcrNumber('block_count') }}</span>
              <span>公式 OCR {{ layoutFormulaOcrNumber('blocks_succeeded') }}/{{ layoutFormulaOcrNumber('blocks_attempted') }}</span>
              <span class="quality-good">高质证据 {{ layoutSummaryNumber('high_quality_evidence_blocks') }}</span>
              <span>高质表格 {{ layoutSummaryNumber('high_quality_table_blocks') }}</span>
              <span>高质公式 {{ layoutSummaryNumber('high_quality_equation_blocks') }}</span>
            </div>
            <el-descriptions v-if="representativeVisual" :column="2" border size="small" class="airesearch-layout-visual">
              <el-descriptions-item label="代表图">{{ visualSourceLabel(representativeVisual.source_kind) }}</el-descriptions-item>
              <el-descriptions-item label="尺寸">{{ visualDimensionsText(representativeVisual) }}</el-descriptions-item>
              <el-descriptions-item label="来源" :span="2">{{ representativeVisual.source_reference || shortPath(representativeVisual.source_path) }}</el-descriptions-item>
              <el-descriptions-item label="Caption" :span="2">{{ representativeVisual.caption || '无 caption' }}</el-descriptions-item>
              <el-descriptions-item label="评分">{{ Math.round(Number(representativeVisual.score || 0)) }}</el-descriptions-item>
              <el-descriptions-item label="依据">{{ representativeVisual.reason || 'candidate score' }}</el-descriptions-item>
            </el-descriptions>
            <div v-if="visualCandidateRows.length" class="airesearch-layout-counts">
              <span v-for="candidate in visualCandidateRows" :key="candidate.source_path">
                {{ visualSourceLabel(candidate.source_kind) }} {{ visualDimensionsText(candidate) }}
              </span>
            </div>
            <div class="airesearch-actions-row">
              <el-button
                type="primary"
                plain
                :loading="actionLoading === 'paper.layout.generate' || layoutPolling"
                :disabled="Boolean(actionLoading) || layoutPolling"
                @click="generateLayout(false)"
              >
                解析版面
              </el-button>
              <el-button
                plain
                :loading="actionLoading === 'paper.layout.force'"
                :disabled="Boolean(actionLoading) || layoutPolling"
                @click="generateLayout(true)"
              >
                强制重跑
              </el-button>
              <el-button :disabled="!layoutDetail" @click="layoutInspectorVisible = true">证据检查器</el-button>
              <el-button :disabled="!layoutArtifactRows.length" @click="layoutArtifactsVisible = true">查看产物</el-button>
            </div>
          </section>

          <div class="airesearch-facts-head">
            <div>
              <span>Facts</span>
              <h3>研究事实</h3>
            </div>
            <el-button type="primary" plain @click="showFactCreator = !showFactCreator">新增事实</el-button>
          </div>
          <el-form v-if="showFactCreator" label-position="top" :model="newFact" class="airesearch-new-fact">
            <div class="airesearch-form-grid">
              <el-form-item label="类型">
                <el-select v-model="newFact.fact_type">
                  <el-option v-for="type in state.fact_types" :key="type" :label="type" :value="type" />
                </el-select>
              </el-form-item>
              <el-form-item label="名称">
                <el-input v-model="newFact.name" />
              </el-form-item>
              <el-form-item label="置信度">
                <el-input-number v-model="newFact.confidence" :min="0" :max="1" :step="0.05" />
              </el-form-item>
            </div>
            <el-form-item label="陈述">
              <el-input v-model="newFact.statement" type="textarea" :rows="3" />
            </el-form-item>
            <el-button type="primary" :loading="actionLoading === 'fact.create'" @click="createFact">保存事实</el-button>
          </el-form>

          <div class="airesearch-fact-list" v-loading="paperLoading">
            <article v-for="fact in paperFacts" :key="fact.id" class="airesearch-fact-card">
              <div class="airesearch-form-grid">
                <el-form-item label="类型">
                  <el-select v-model="fact.fact_type">
                    <el-option v-for="type in state.fact_types" :key="type" :label="type" :value="type" />
                  </el-select>
                </el-form-item>
                <el-form-item label="名称">
                  <el-input v-model="fact.name" />
                </el-form-item>
                <el-form-item label="置信度">
                  <el-input-number v-model="fact.confidence" :min="0" :max="1" :step="0.05" />
                </el-form-item>
              </div>
              <el-form-item label="陈述">
                <el-input v-model="fact.statement" type="textarea" :rows="3" />
              </el-form-item>
              <div class="airesearch-actions-row">
                <el-button type="primary" plain :loading="actionLoading === `fact.update.${fact.id}`" @click="updateFact(fact)">保存事实</el-button>
                <el-popconfirm title="确认删除这条事实？" confirm-button-text="确认" cancel-button-text="取消" @confirm="deleteFact(fact.id)">
                  <template #reference>
                    <el-button type="danger" plain :loading="actionLoading === `fact.delete.${fact.id}`">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </article>
            <el-empty v-if="!paperFacts.length" description="这篇论文暂无研究事实" />
          </div>
        </template>
      </article>
    </section>

    <section v-else-if="view === 'search'" class="airesearch-admin-grid airesearch-search-console">
      <article class="airesearch-admin-panel airesearch-single-paper-panel wide">
        <div class="airesearch-panel-head">
          <span>Single Paper</span>
          <h2>单论文入库</h2>
          <p>输入论文标题、arXiv ID 或 URL。可先模糊检索 arXiv 匹配结果，也可直接入库。</p>
        </div>
        <div class="airesearch-single-paper-body">
          <div class="airesearch-single-paper-bar">
            <el-input
              v-model="singlePaperInput"
              size="large"
              placeholder="论文标题 / arXiv ID / URL，例如 Attention Is All You Need"
              clearable
              @keyup.enter="searchSinglePaper"
            />
            <el-button type="primary" size="large" :loading="actionLoading === 'single.search'" @click="searchSinglePaper">搜索匹配</el-button>
            <el-button size="large" :loading="actionLoading === 'single.ingest.direct'" @click="ingestSinglePaper(singlePaperInput, 'single.ingest.direct')">直接入库</el-button>
          </div>
          <div v-if="singlePaperResults.length" class="airesearch-single-paper-results">
            <article v-for="paper in singlePaperResults" :key="paper.arxiv_id || paper.title" class="airesearch-single-paper-result">
              <div>
                <strong>{{ paper.title }}</strong>
                <span>{{ (paper.authors || []).slice(0, 4).join('，') }}<template v-if="(paper.authors || []).length > 4"> 等</template></span>
                <small>{{ paper.published || '日期未知' }} · {{ paper.abstract || '暂无摘要' }}</small>
                <em v-if="paper.arxiv_id">arXiv: {{ paper.arxiv_id }}</em>
              </div>
              <el-button type="primary" plain :loading="actionLoading === `single.ingest.${paper.arxiv_id || paper.title}`" @click="ingestSinglePaper(paper.arxiv_id || paper.url || paper.title, `single.ingest.${paper.arxiv_id || paper.title}`)">入库</el-button>
            </article>
          </div>
          <el-empty v-else-if="singlePaperSearched" description="没有找到匹配论文，可尝试直接入库 URL / ID" />
        </div>
      </article>

      <article class="airesearch-admin-panel airesearch-ingest-panel">
        <div class="airesearch-panel-head">
          <span>Search Ingest</span>
          <h2>批量搜索入库</h2>
          <p>从 provider 拉取候选论文，按搜索方向打分筛选，并可选择自动重建部署。</p>
        </div>
        <el-form label-position="top" :model="searchJobForm" class="airesearch-editor-form">
          <div class="airesearch-form-block">
            <div class="airesearch-form-block-title">
              <strong>选择搜索范围</strong>
              <span>方向和数据源会合并为一个后台任务。</span>
            </div>
            <el-form-item label="搜索方向">
              <el-checkbox-group v-model="searchJobForm.profiles" class="airesearch-choice-group">
                <el-checkbox-button v-for="profile in state.profiles" :key="profile.name" :label="profile.name" />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="数据源">
              <el-checkbox-group v-model="searchJobForm.providers" class="airesearch-choice-group">
                <el-checkbox-button v-for="provider in state.providers" :key="provider" :label="provider" />
              </el-checkbox-group>
            </el-form-item>
          </div>
          <div class="airesearch-form-block">
            <div class="airesearch-form-block-title">
              <strong>筛选和排队参数</strong>
              <span>控制候选数量、评分阈值和任务优先级。</span>
            </div>
            <div class="airesearch-form-grid">
              <el-form-item label="每方向候选">
                <el-input-number v-model="searchJobForm.limit_per_profile" :min="1" :max="200" />
              </el-form-item>
              <el-form-item label="精选数量">
                <el-input-number v-model="searchJobForm.select_limit" :min="1" :max="100" />
              </el-form-item>
              <el-form-item label="最低分">
                <el-input-number v-model="searchJobForm.min_score" :min="0" :max="1" :step="0.05" />
              </el-form-item>
              <el-form-item label="优先级">
                <el-input-number v-model="searchJobForm.priority" :min="0" :max="100" />
              </el-form-item>
              <el-form-item label="主搜索起始日">
                <el-date-picker v-model="searchJobForm.primary_since" type="date" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="例外搜索起始日">
                <el-date-picker v-model="searchJobForm.exception_since" type="date" value-format="YYYY-MM-DD" />
              </el-form-item>
            </div>
          </div>
          <div class="airesearch-form-block compact">
            <div class="airesearch-toggle-row">
              <el-checkbox v-model="searchJobForm.refresh_provider_cache">刷新 provider 缓存</el-checkbox>
              <el-checkbox v-model="searchJobForm.refresh_facts">刷新事实抽取</el-checkbox>
              <el-checkbox v-model="searchJobForm.auto_deploy">完成后部署</el-checkbox>
            </div>
          </div>
          <div class="airesearch-submit-row">
            <el-button type="primary" size="large" :loading="actionLoading === 'job.search_ingest'" @click="startJob('search_ingest', searchJobForm)">启动搜索入库任务</el-button>
            <span>{{ searchJobForm.profiles.length }} 个方向 · {{ searchJobForm.providers.length }} 个数据源</span>
          </div>
        </el-form>
      </article>
      <article class="airesearch-admin-panel airesearch-job-preview">
        <div class="airesearch-panel-head">
          <span>Recent Jobs</span>
          <h3>最近任务</h3>
        </div>
        <ul class="airesearch-snapshot-list">
          <li v-for="job in state.jobs.slice(0, 6)" :key="job.id">
            <strong>#{{ job.id }} {{ job.job_type }}</strong>
            <span>{{ statusLabel(job.status) }}</span>
            <small>{{ job.message || job.created_at }}</small>
          </li>
        </ul>
      </article>
    </section>

    <section v-else-if="view === 'profiles'" class="airesearch-admin-panel wide">
      <div class="airesearch-panel-head inline">
        <div>
          <span>Research Profiles</span>
          <h2>搜索配置</h2>
          <p>管理搜索方向的关键词、时间窗口和说明，支持新增、编辑、删除。</p>
        </div>
        <el-button type="primary" @click="openProfileDialog()">新增配置</el-button>
      </div>
      <div class="airesearch-profile-card-grid">
        <article v-for="profile in state.profiles" :key="profile.name" class="airesearch-profile-card">
          <div class="airesearch-profile-card-head">
            <div>
              <span>方向 Key</span>
              <h3>{{ profile.name }}</h3>
            </div>
            <div class="airesearch-profile-card-actions">
              <el-button size="small" type="primary" plain @click="openProfileDialog(profile)">编辑</el-button>
              <el-popconfirm title="确认删除这个搜索配置？" confirm-button-text="确认" cancel-button-text="取消" @confirm="deleteProfile(profile.name)">
                <template #reference>
                  <el-button size="small" type="danger" plain>删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <p>{{ profile.description || '暂无描述' }}</p>
          <div class="airesearch-keyword-cell">
            <span v-for="keyword in (profile.keywords || []).slice(0, 8)" :key="keyword">{{ keyword }}</span>
            <em v-if="(profile.keywords || []).length > 8">+{{ profile.keywords.length - 8 }}</em>
          </div>
          <dl class="airesearch-profile-dates">
            <div>
              <dt>主搜索</dt>
              <dd>{{ profile.primary_since || '未设置' }}</dd>
            </div>
            <div>
              <dt>例外搜索</dt>
              <dd>{{ profile.exception_since || '未设置' }}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>

    <section v-else-if="view === 'tasks'" class="airesearch-admin-panel wide">
      <div class="airesearch-panel-head inline">
        <div>
          <span>Admin Jobs</span>
          <h2>任务中心</h2>
          <p>查看研知库任务队列，排队任务可直接取消。</p>
        </div>
        <el-segmented v-model="jobStatusFilter" :options="jobStatusOptions" />
      </div>
      <div class="airesearch-job-card-list">
        <article v-for="job in filteredJobs" :key="job.id" class="airesearch-job-card">
          <div class="airesearch-job-card-head">
            <div>
              <span>#{{ job.id }}</span>
              <h3>{{ job.job_type || '未命名任务' }}</h3>
            </div>
            <el-tag :type="jobTagType(job.status)">{{ statusLabel(job.status) }}</el-tag>
          </div>
          <dl class="airesearch-job-card-body">
            <div>
              <dt>消息</dt>
              <dd>{{ job.message || '暂无消息' }}</dd>
            </div>
            <div>
              <dt>当前步骤</dt>
              <dd>{{ job.current_step || '未开始' }}</dd>
            </div>
            <div>
              <dt>创建时间</dt>
              <dd>{{ job.created_at || '未知' }}</dd>
            </div>
          </dl>
          <div class="airesearch-job-card-actions">
            <el-popconfirm title="确认取消这个排队任务？" confirm-button-text="确认" cancel-button-text="取消" @confirm="cancelJob(job.id)">
              <template #reference>
                <el-button size="small" type="danger" plain :disabled="job.status !== 'queued'">取消任务</el-button>
              </template>
            </el-popconfirm>
          </div>
        </article>
        <el-empty v-if="!filteredJobs.length" description="暂无匹配任务" />
      </div>
    </section>

    <section v-else class="airesearch-admin-grid">
      <article class="airesearch-admin-panel">
        <div class="airesearch-panel-head">
          <span>Build</span>
          <h2>重建站点</h2>
          <p>按隐藏论文覆盖生成临时库，重建研知库静态站点。</p>
        </div>
        <el-button type="primary" :loading="actionLoading === 'job.rebuild_site'" @click="startJob('rebuild_site', publishJobForm)">加入重建队列</el-button>
      </article>
      <article class="airesearch-admin-panel">
        <div class="airesearch-panel-head">
          <span>Deploy</span>
          <h2>部署站点</h2>
          <p>执行研知库部署脚本，将 site-current 发布到 nginx。</p>
        </div>
        <el-button type="primary" :loading="actionLoading === 'job.deploy_site'" @click="startJob('deploy_site', publishJobForm)">加入部署队列</el-button>
      </article>
      <article class="airesearch-admin-panel">
        <div class="airesearch-panel-head">
          <span>Full Release</span>
          <h2>重建并部署</h2>
          <p>完整执行重建与部署，适合完成论文/事实编辑后发布。</p>
        </div>
        <el-checkbox v-model="publishJobForm.auto_deploy">允许部署到 nginx</el-checkbox>
        <el-button type="primary" :loading="actionLoading === 'job.rebuild_deploy'" @click="startJob('rebuild_deploy', publishJobForm)">加入发布队列</el-button>
      </article>
    </section>

    <el-dialog
      v-model="profileDialogVisible"
      :title="profileDialogMode === 'create' ? '新增搜索配置' : '编辑搜索配置'"
      width="720px"
      class="admin-crud-dialog airesearch-profile-dialog"
      align-center
    >
      <el-form label-position="top" :model="profileForm">
        <el-form-item label="方向 Key">
          <el-input v-model="profileForm.name" :disabled="profileDialogMode === 'edit'" placeholder="lowercase_profile_key" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="profileForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="关键词，每行一个">
          <el-input v-model="profileForm.keywordsText" type="textarea" :rows="6" />
        </el-form-item>
        <div class="airesearch-form-grid">
          <el-form-item label="主搜索起始日">
            <el-date-picker v-model="profileForm.primary_since" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="例外搜索起始日">
            <el-date-picker v-model="profileForm.exception_since" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="profileDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading === 'profile.save'" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="layoutArtifactsVisible" title="版面解析产物" width="760px" class="admin-crud-dialog" align-center>
      <div class="airesearch-layout-artifacts">
        <article v-for="artifact in layoutArtifactRows" :key="artifact.id || artifact.path">
          <strong>{{ artifact.artifact_type }}</strong>
          <span>{{ artifact.path }}</span>
        </article>
        <el-empty v-if="!layoutArtifactRows.length" description="暂无版面解析产物" />
      </div>
    </el-dialog>

    <el-dialog
      v-model="layoutInspectorVisible"
      title="Layout Evidence Inspector"
      width="1080px"
      class="admin-crud-dialog airesearch-layout-inspector-dialog"
      align-center
      :show-close="false"
      transition="none"
    >
      <template #header>
        <div class="airesearch-layout-inspector-dialog-head">
          <strong>Layout Evidence Inspector</strong>
          <button
            class="airesearch-layout-inspector-close"
            type="button"
            aria-label="关闭证据检查器"
            @click="layoutInspectorVisible = false"
          >
            <el-icon><Close /></el-icon>
          </button>
        </div>
      </template>
      <div class="airesearch-layout-inspector">
        <div class="airesearch-layout-inspector-head">
          <div>
            <span>Paper</span>
            <strong>{{ selectedPaper?.title || selectedPaperKey }}</strong>
            <p>{{ latestLayoutMessage }}</p>
          </div>
          <el-tag :type="layoutStatusTagType(currentLayoutStatus)">{{ layoutStatusLabel(currentLayoutStatus) }}</el-tag>
        </div>
        <div class="airesearch-layout-capabilities">
          <el-tag v-for="item in layoutCapabilityItems" :key="item.key" size="small" :type="item.enabled ? 'success' : 'info'" effect="plain">
            {{ item.label }}
          </el-tag>
        </div>
        <dl class="airesearch-layout-inspector-metrics">
          <div><dt>证据块</dt><dd>{{ layoutEvidenceBlocks.length }}</dd></div>
          <div><dt>公式</dt><dd>{{ layoutEquationBlocks.length || layoutSummaryNumber('equation_blocks') }}</dd></div>
          <div><dt>表格</dt><dd>{{ layoutTableBlocks.length || layoutBlockCount('table') }}</dd></div>
          <div><dt>OCR 块</dt><dd>{{ layoutOcrNumber('block_count') }}</dd></div>
          <div><dt>候选图</dt><dd>{{ layoutVisualCandidates.length }}</dd></div>
          <div><dt>事实关联</dt><dd>{{ Number(layoutEvidenceGraph.summary?.supported_relation_count || 0) }}</dd></div>
        </dl>
        <el-tabs v-model="layoutInspectorTab" class="airesearch-layout-inspector-tabs">
          <el-tab-pane label="事实关联" name="relations">
            <div v-if="layoutGraphFactRows.length" class="airesearch-layout-graph-list">
              <article v-for="fact in layoutGraphFactRows" :key="fact.key" class="airesearch-layout-graph-row">
                <header>
                  <span>
                    <strong>{{ graphFactTypeLabel(fact.fact_type) }}</strong>
                    <code>{{ fact.key }}</code>
                  </span>
                  <em :class="fact.links.length ? 'is-linked' : 'is-unlinked'">
                    {{ fact.links.length ? `${fact.links.length} 条证据` : '未关联' }}
                  </em>
                </header>
                <p>{{ fact.statement || fact.name || '未记录事实文本' }}</p>
                <small>置信度 {{ graphScoreLabel(fact.confidence) }} · {{ graphProvenanceText(fact.provenance) }}</small>
                <div v-if="fact.links.length" class="airesearch-layout-graph-links">
                  <div v-for="link in fact.links" :key="`${fact.key}:${link.target_key}`" class="airesearch-layout-graph-link">
                    <div>
                      <strong>{{ graphEvidenceTypeLabel(link.evidence?.evidence_type) }} · {{ graphEvidenceLocation(link.evidence) }}</strong>
                      <span>{{ link.evidence?.preview || link.target_key }}</span>
                    </div>
                    <dl>
                      <div><dt>方法</dt><dd>{{ graphMatchMethodLabel(link.match_method) }}</dd></div>
                      <div><dt>分数</dt><dd>{{ graphScoreLabel(link.score) }}</dd></div>
                      <div><dt>质量</dt><dd>{{ graphScoreLabel(link.evidence?.quality_score) }}</dd></div>
                    </dl>
                    <code>{{ link.target_key }}</code>
                    <small>{{ graphProvenanceText(link.provenance) }}</small>
                  </div>
                </div>
              </article>
            </div>
            <el-empty v-else :image-size="64" description="暂无事实与版面证据关联" />
          </el-tab-pane>
          <el-tab-pane label="证据块" name="evidence">
            <div v-if="layoutEvidenceBlocks.length" class="airesearch-layout-evidence-list">
              <article v-for="block in layoutEvidenceBlocks" :key="layoutBlockKey(block)" class="airesearch-layout-evidence-row">
                <header>
                  <strong>{{ layoutBlockTypeLabel(block.block_type) }} · {{ layoutBlockLocation(block) }}</strong>
                  <em :class="qualityClass(block)">{{ qualityLabel(block) }}</em>
                </header>
                <p>{{ layoutBlockText(block) }}</p>
                <small v-if="qualityReasons(block)">{{ qualityReasons(block) }}</small>
                <code v-if="layoutBlockSource(block)">{{ layoutBlockSource(block) }}</code>
              </article>
            </div>
            <el-empty v-else :image-size="64" description="暂无证据块" />
          </el-tab-pane>
          <el-tab-pane label="公式 OCR" name="formula">
            <div v-if="layoutEquationBlocks.length" class="airesearch-layout-evidence-list">
              <article v-for="block in layoutEquationBlocks" :key="layoutBlockKey(block)" class="airesearch-layout-evidence-row">
                <header>
                  <strong>公式 · {{ layoutBlockLocation(block) }}</strong>
                  <em :class="qualityClass(block)">{{ qualityLabel(block) }}</em>
                </header>
                <pre>{{ formulaText(block) }}</pre>
                <small>{{ formulaMetaText(block) }}</small>
                <code v-if="layoutBlockSource(block)">{{ layoutBlockSource(block) }}</code>
              </article>
            </div>
            <el-empty v-else :image-size="64" description="暂无公式块样本" />
          </el-tab-pane>
          <el-tab-pane label="表格结构" name="tables">
            <div v-if="layoutTableBlocks.length" class="airesearch-layout-evidence-list">
              <article v-for="block in layoutTableBlocks" :key="layoutBlockKey(block)" class="airesearch-layout-evidence-row">
                <header>
                  <strong>表格 · {{ layoutBlockLocation(block) }}</strong>
                  <em :class="qualityClass(block)">{{ qualityLabel(block) }}</em>
                </header>
                <p>{{ tableShapeText(block) }}</p>
                <pre>{{ tableMarkdown(block) || layoutBlockText(block) }}</pre>
                <small v-if="qualityReasons(block)">{{ qualityReasons(block) }}</small>
                <code v-if="layoutBlockSource(block)">{{ layoutBlockSource(block) }}</code>
              </article>
            </div>
            <el-empty v-else :image-size="64" description="暂无表格结构样本" />
          </el-tab-pane>
          <el-tab-pane label="OCR / 读序" name="ocr">
            <div class="airesearch-layout-ocr-summary">
              <article>
                <strong>OCR</strong>
                <span>{{ layoutOcrNumber('pages_succeeded') }}/{{ layoutOcrNumber('pages_attempted') }} 页，{{ layoutOcrNumber('block_count') }} 块</span>
                <small>{{ layoutOcrErrorText }}</small>
              </article>
              <article>
                <strong>公式 OCR</strong>
                <span>{{ layoutFormulaOcrNumber('blocks_succeeded') }}/{{ layoutFormulaOcrNumber('blocks_attempted') }} 块</span>
                <small>{{ layoutFormulaOcrErrorText }}</small>
              </article>
              <article>
                <strong>阅读顺序</strong>
                <span>多栏 {{ layoutReadingOrderNumber('multi_column_pages') }} 页，低置信 {{ layoutReadingOrderNumber('low_confidence_blocks') }} 块</span>
                <small>Caption 组 {{ layoutReadingOrderNumber('caption_paired_blocks') }}，跨栏块 {{ layoutReadingOrderNumber('cross_column_blocks') }}</small>
              </article>
            </div>
            <div v-if="layoutOcrBlocks.length" class="airesearch-layout-evidence-list">
              <article v-for="block in layoutOcrBlocks" :key="layoutBlockKey(block)" class="airesearch-layout-evidence-row">
                <header>
                  <strong>OCR · {{ layoutBlockLocation(block) }}</strong>
                  <em :class="qualityClass(block)">{{ qualityLabel(block) }}</em>
                </header>
                <p>{{ layoutBlockText(block) }}</p>
                <code v-if="layoutBlockSource(block)">{{ layoutBlockSource(block) }}</code>
              </article>
            </div>
          </el-tab-pane>
          <el-tab-pane label="视觉候选" name="visuals">
            <div class="airesearch-layout-visual-inspector">
              <article v-if="representativeVisual" class="airesearch-layout-visual-card">
                <div class="airesearch-layout-card-head">
                  <span>Selected Visual</span>
                  <strong>代表图</strong>
                  <em>{{ evidenceConfidenceLabel(representativeVisual) }}</em>
                </div>
                <b>{{ visualSourceLabel(representativeVisual.source_kind) }} · {{ visualDimensionsText(representativeVisual) }}</b>
                <p>{{ representativeVisual.caption || representativeVisual.reason || '已选择视觉素材' }}</p>
                <em>{{ representativeVisual.source_reference || shortPath(representativeVisual.source_path) }}</em>
              </article>
              <article v-for="candidate in layoutVisualCandidates" :key="candidate.source_path || candidate.source_reference" class="airesearch-layout-visual-card">
                <div class="airesearch-layout-card-head">
                  <span>{{ visualSourceLabel(candidate.source_kind) }}</span>
                  <strong>{{ visualDimensionsText(candidate) }}</strong>
                  <em>{{ evidenceConfidenceLabel(candidate) }}</em>
                </div>
                <p>{{ candidate.caption || candidate.reason || candidate.source_reference || '未命名候选' }}</p>
                <em>{{ candidate.source_reference || shortPath(candidate.source_path) }}</em>
              </article>
            </div>
            <el-empty v-if="!representativeVisual && !layoutVisualCandidates.length" :image-size="64" description="暂无视觉候选" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { executeAdminAction, fetchAdminData } from '@/app/api/admin'
import { useAuthStore } from '@/app/stores/auth'
import { adminConfirm, adminToast } from '@/shared/lib/adminFeedback'

type View = 'overview' | 'papers' | 'search' | 'profiles' | 'tasks' | 'publish'

interface AdminState {
  papers: any[]
  profiles: any[]
  jobs: any[]
  job_statuses: string[]
  providers: string[]
  fact_types: string[]
  stats: Record<string, any>
}

const props = defineProps<{ view: View }>()
const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const paperLoading = ref(false)
const actionLoading = ref('')
const selectedPaperKey = ref('')
const paperQuery = ref('')
const singlePaperInput = ref('')
const singlePaperResults = ref<any[]>([])
const singlePaperSearched = ref(false)
const paperDetail = ref<Record<string, any> | null>(null)
const layoutDetail = ref<Record<string, any> | null>(null)
const layoutLoading = ref(false)
const layoutPolling = ref(false)
const layoutArtifactsVisible = ref(false)
const layoutInspectorVisible = ref(false)
const layoutInspectorTab = ref('evidence')
const paperFacts = ref<any[]>([])
const showFactCreator = ref(false)
const jobStatusFilter = ref('all')
const profileDialogVisible = ref(false)
const profileDialogMode = ref<'create' | 'edit'>('create')
let layoutPollToken = 0
let paperRequestToken = 0
let layoutRequestToken = 0

const state = reactive<AdminState>({
  papers: [],
  profiles: [],
  jobs: [],
  job_statuses: [],
  providers: [],
  fact_types: [],
  stats: {}
})

const paperForm = reactive({
  hidden: false,
  arxiv_id: '',
  paper_url: '',
  github_url: ''
})

const newFact = reactive({
  fact_type: 'method',
  name: '',
  confidence: 0.9,
  statement: ''
})

const searchJobForm = reactive({
  profiles: [] as string[],
  providers: [] as string[],
  limit_per_profile: 30,
  select_limit: 10,
  min_score: 0.6,
  primary_since: '',
  exception_since: '',
  refresh_provider_cache: false,
  refresh_facts: false,
  auto_deploy: true,
  priority: 0
})

const publishJobForm = reactive({
  auto_deploy: true,
  priority: 0
})

const profileForm = reactive({
  name: '',
  description: '',
  keywordsText: '',
  primary_since: '',
  exception_since: ''
})

const viewMeta = computed(() => ({
  overview: { title: '研知库总览', description: '论文、搜索方向、任务队列和发布状态。' },
  papers: { title: '论文管理', description: '编辑论文链接、隐藏状态、草稿和研究事实。' },
  search: { title: '搜索入库', description: '按搜索方向和 provider 启动候选发现入库任务。' },
  profiles: { title: '搜索配置', description: '管理 research_profiles 的关键词、日期范围和描述。' },
  tasks: { title: '任务中心', description: '查看 admin_jobs 队列并取消排队任务。' },
  publish: { title: '重建部署', description: '重建研知库静态站点并部署到 nginx。' }
}[props.view]))

const statsCards = computed(() => [
  { label: '论文', value: state.stats.paper_count ?? state.papers.length },
  { label: '展示中', value: state.stats.visible_count ?? 0 },
  { label: '隐藏', value: state.stats.hidden_count ?? 0 },
  { label: '版面已解析', value: layoutParsedCount.value },
  { label: '搜索方向', value: state.profiles.length },
  { label: '任务', value: state.jobs.length }
])

const healthCards = computed(() => [
  { label: '论文总数', value: state.stats.paper_count ?? 0 },
  { label: '展示论文', value: state.stats.visible_count ?? 0 },
  { label: '隐藏论文', value: state.stats.hidden_count ?? 0 },
  { label: '搜索配置', value: state.profiles.length },
  { label: 'Provider', value: state.providers.length },
  { label: '可编辑事实类型', value: state.fact_types.length }
])

const jobStatusRows = computed(() => (state.job_statuses.length ? state.job_statuses : ['queued', 'running', 'completed', 'failed', 'publish_failed', 'canceled']).map((name) => ({
  name,
  label: statusLabel(name),
  count: state.stats.job_status_counts?.[name] ?? 0
})))

const jobStatusOptions = computed(() => [
  { label: '全部', value: 'all' },
  ...jobStatusRows.value.map((row) => ({ label: `${row.label} ${row.count}`, value: row.name }))
])

const filteredJobs = computed(() => {
  if (jobStatusFilter.value === 'all') return state.jobs
  return state.jobs.filter((job) => job.status === jobStatusFilter.value)
})

const filteredPapers = computed(() => {
  const keyword = paperQuery.value.trim().toLowerCase()
  const papers = state.papers
  if (!keyword) return papers
  return papers.filter((paper) => [
    paper.title,
    paper.paper_key,
    paper.arxiv_id,
    paper.paper_url,
    paper.github_url
  ].some((value) => String(value || '').toLowerCase().includes(keyword)))
})
const selectedPaper = computed(() => paperDetail.value || state.papers.find((paper) => paper.paper_key === selectedPaperKey.value) || null)

const layoutParsedCount = computed(() => state.papers.filter((paper) => paperLayoutStatus(paper) === 'completed').length)
const layoutEvidencePaperCount = computed(() => state.papers.filter((paper) => Number(paper.layout_evidence_ready_blocks || 0) > 0).length)
const layoutHighQualityEvidencePaperCount = computed(() => state.papers.filter((paper) => Number(paper.layout_high_quality_evidence_blocks || 0) > 0).length)

const latestLayoutRun = computed(() => layoutDetail.value?.latest_run || null)
const latestLayoutJob = computed(() => layoutDetail.value?.latest_job || null)
const layoutArtifactRows = computed(() => layoutDetail.value?.artifacts || [])
const layoutSummary = computed(() => layoutDetail.value?.summary || latestLayoutRun.value?.stats?.summary || {})
const layoutCapabilities = computed(() => layoutDetail.value?.capabilities || {})
const layoutCapabilityItems = computed(() => [
  { key: 'has_structure_json', label: '结构 JSON', enabled: Boolean(layoutCapabilities.value.has_structure_json) },
  { key: 'has_captioned_visual_blocks', label: '图注配对', enabled: Boolean(layoutCapabilities.value.has_captioned_visual_blocks) },
  { key: 'has_structured_tables', label: '表格结构', enabled: Boolean(layoutCapabilities.value.has_structured_tables) },
  { key: 'has_geometry_tables', label: '几何表格', enabled: Boolean(layoutCapabilities.value.has_geometry_tables) },
  { key: 'has_spanning_table_cells', label: '跨列单元格', enabled: Boolean(layoutCapabilities.value.has_spanning_table_cells) },
  { key: 'has_text_fallback_tables', label: '文本降级表', enabled: Boolean(layoutCapabilities.value.has_text_fallback_tables) },
  { key: 'has_reading_order', label: '阅读顺序', enabled: Boolean(layoutCapabilities.value.has_reading_order) },
  { key: 'has_multi_column_reading_order', label: '多栏读序', enabled: Boolean(layoutCapabilities.value.has_multi_column_reading_order) },
  { key: 'has_equations', label: '公式块', enabled: Boolean(layoutCapabilities.value.has_equations) },
  { key: 'has_evidence_blocks', label: '证据块', enabled: Boolean(layoutCapabilities.value.has_evidence_blocks) },
  { key: 'has_high_quality_evidence', label: '高质证据', enabled: Boolean(layoutCapabilities.value.has_high_quality_evidence) },
  { key: 'ocr_available', label: 'OCR 可用', enabled: Boolean(layoutCapabilities.value.ocr_available) },
  { key: 'has_ocr_blocks', label: 'OCR 文本', enabled: Boolean(layoutCapabilities.value.has_ocr_blocks) },
  { key: 'formula_ocr_configured', label: '公式 OCR 已配置', enabled: Boolean(layoutCapabilities.value.formula_ocr_configured) },
  { key: 'has_formula_ocr', label: '公式 OCR 结果', enabled: Boolean(layoutCapabilities.value.has_formula_ocr) }
])
const representativeVisual = computed(() => layoutDetail.value?.representative_visual || null)
const layoutEvidenceBlocks = computed(() => Array.isArray(layoutDetail.value?.evidence_blocks) ? layoutDetail.value.evidence_blocks : [])
const layoutSampleBlocks = computed(() => Array.isArray(layoutDetail.value?.sample_blocks) ? layoutDetail.value.sample_blocks : [])
const layoutInspectorBlocks = computed(() => {
  const seen = new Set<string>()
  return [...layoutEvidenceBlocks.value, ...layoutSampleBlocks.value].filter((block) => {
    const key = layoutBlockKey(block)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})
const layoutEquationBlocks = computed(() => layoutInspectorBlocks.value.filter((block) => String(block?.block_type || '') === 'interline_equation'))
const layoutTableBlocks = computed(() => layoutInspectorBlocks.value.filter((block) => String(block?.block_type || '') === 'table'))
const layoutOcrBlocks = computed(() => layoutInspectorBlocks.value.filter((block) => Boolean(layoutBlockMetadata(block).ocr)))
const layoutVisualCandidates = computed(() => Array.isArray(layoutDetail.value?.visual_candidates) ? layoutDetail.value.visual_candidates : [])
const layoutEvidenceGraph = computed<Record<string, any>>(() => {
  const graph = layoutDetail.value?.evidence_graph
  return graph && typeof graph === 'object' ? graph : { summary: {}, facts: [], evidence: [], relations: [] }
})
const layoutGraphFactRows = computed(() => {
  const facts = safeJsonArray(layoutEvidenceGraph.value.facts).slice(0, 200)
  const evidence = safeJsonArray(layoutEvidenceGraph.value.evidence).slice(0, 200)
  const relations = safeJsonArray(layoutEvidenceGraph.value.relations).filter((item: any) => item?.relation === 'supported_by')
  const evidenceByKey = new Map(evidence.map((item: any) => [String(item?.key || ''), item]))
  const relationsByFact = new Map<string, any[]>()
  relations.forEach((relation: any) => {
    const sourceKey = String(relation?.source_key || '')
    if (!sourceKey) return
    const rows = relationsByFact.get(sourceKey) || []
    rows.push({
      ...relation,
      evidence: evidenceByKey.get(String(relation?.target_key || '')) || null
    })
    relationsByFact.set(sourceKey, rows)
  })
  return facts.map((fact: any) => ({
    ...fact,
    links: (relationsByFact.get(String(fact?.key || '')) || []).slice(0, 3)
  }))
})
const visualCandidateRows = computed(() => layoutVisualCandidates.value.slice(0, 4))
const layoutOcrErrorText = computed(() => layoutErrorText(layoutSummary.value?.ocr?.errors))
const layoutFormulaOcrErrorText = computed(() => layoutErrorText(layoutSummary.value?.formula_ocr?.errors))
const currentLayoutStatus = computed(() => {
  const jobStatus = String(latestLayoutJob.value?.status || '')
  if (['queued', 'running'].includes(jobStatus)) return jobStatus
  return String(latestLayoutRun.value?.status || 'not_parsed')
})
const latestLayoutMessage = computed(() => {
  if (latestLayoutJob.value?.message) return latestLayoutJob.value.message
  if (latestLayoutRun.value?.error) return latestLayoutRun.value.error
  if (latestLayoutRun.value?.finished_at) return `最近完成于 ${latestLayoutRun.value.finished_at}`
  return '尚未解析 PDF 版面'
})

watch(() => props.view, async () => {
  await loadState()
  if (props.view === 'papers' && selectedPaperKey.value && !paperDetail.value) await loadPaperDetail(selectedPaperKey.value)
})

onMounted(() => {
  loadState()
  window.addEventListener('niu-admin-refresh', loadState)
})
onBeforeUnmount(() => {
  layoutPollToken += 1
  paperRequestToken += 1
  layoutRequestToken += 1
  layoutPolling.value = false
  window.removeEventListener('niu-admin-refresh', loadState)
})

async function loadState() {
  loading.value = true
  try {
    const payload = await fetchAdminData<Record<string, any>>('airesearch.admin.state', auth.token)
    const next = payload.state || {}
    state.papers = next.papers || []
    state.profiles = next.profiles || []
    state.jobs = next.jobs || []
    state.job_statuses = next.job_statuses || []
    state.providers = next.providers || []
    state.fact_types = next.fact_types || ['method', 'claim', 'limitation', 'dataset', 'benchmark']
    state.stats = next.stats || {}
    if (!searchJobForm.profiles.length) searchJobForm.profiles = state.profiles.map((profile) => profile.name).slice(0, 3)
    if (!searchJobForm.providers.length) searchJobForm.providers = state.providers.slice(0, 3)
    if (!selectedPaperKey.value && state.papers.length) selectedPaperKey.value = state.papers[0].paper_key
    if (props.view === 'papers' && selectedPaperKey.value && !paperDetail.value) await loadPaperDetail(selectedPaperKey.value)
  } catch (error: any) {
    adminToast.error(error.message || '研知库管理状态读取失败')
  } finally {
    loading.value = false
  }
}

async function selectPaper(paperKey: string) {
  selectedPaperKey.value = paperKey
  paperRequestToken += 1
  layoutRequestToken += 1
  paperDetail.value = null
  layoutDetail.value = null
  paperFacts.value = []
  layoutInspectorVisible.value = false
  await loadPaperDetail(paperKey)
}

async function loadPaperDetail(paperKey: string) {
  const requestToken = ++paperRequestToken
  paperLoading.value = true
  try {
    const payload = await fetchAdminData<Record<string, any>>('airesearch.admin.paper', auth.token, { paperKey })
    if (requestToken !== paperRequestToken || selectedPaperKey.value !== paperKey) return
    const detail = payload.result || {}
    paperDetail.value = detail
    paperForm.hidden = Boolean(detail.hidden)
    paperForm.arxiv_id = detail.arxiv_id || ''
    paperForm.paper_url = detail.paper_url || ''
    paperForm.github_url = detail.github_url || ''
    paperFacts.value = (detail.facts || []).map((fact: any) => ({ ...fact }))
    await loadLayoutDetail(paperKey, true)
  } catch (error: any) {
    if (requestToken === paperRequestToken && selectedPaperKey.value === paperKey) {
      adminToast.error(error.message || '论文详情读取失败')
    }
  } finally {
    if (requestToken === paperRequestToken) paperLoading.value = false
  }
}

async function savePaper() {
  await runAdminMutation('paper.update', 'airesearch.admin.paper.update', { paperKey: selectedPaperKey.value, ...paperForm })
  await loadPaperDetail(selectedPaperKey.value)
  await loadState()
}

async function saveDraft() {
  await runAdminMutation('paper.draft.save', 'airesearch.admin.paper.draft.save', {
    paperKey: selectedPaperKey.value,
    ...paperForm,
    facts: paperFacts.value
  })
  await loadPaperDetail(selectedPaperKey.value)
  await loadState()
}

function loadDraft() {
  const draft = paperDetail.value?.draft || {}
  Object.assign(paperForm, {
    hidden: Boolean(draft.hidden ?? paperForm.hidden),
    arxiv_id: draft.arxiv_id ?? paperForm.arxiv_id,
    paper_url: draft.paper_url ?? paperForm.paper_url,
    github_url: draft.github_url ?? paperForm.github_url
  })
  if (Array.isArray(draft.facts)) paperFacts.value = draft.facts.map((fact: any) => ({ ...fact }))
  adminToast.success('已载入草稿')
}

async function deleteDraft() {
  await runAdminMutation('paper.draft.delete', 'airesearch.admin.paper.draft.delete', { paperKey: selectedPaperKey.value })
  await loadPaperDetail(selectedPaperKey.value)
  await loadState()
}

async function deletePaper() {
  await runAdminMutation('paper.delete', 'airesearch.admin.paper.delete', { paperKey: selectedPaperKey.value })
  paperRequestToken += 1
  layoutRequestToken += 1
  selectedPaperKey.value = ''
  paperDetail.value = null
  layoutDetail.value = null
  await loadState()
}

function openBlogGenerator() {
  router.push({ path: '/admin/airesearch/blogs', query: { paperKey: selectedPaperKey.value } })
}

async function loadLayoutDetail(paperKey: string, silent = false) {
  if (!paperKey) return
  const requestToken = ++layoutRequestToken
  if (!silent) layoutLoading.value = true
  try {
    const payload = await fetchAdminData<Record<string, any>>('airesearch.admin.paper.layout.detail', auth.token, { paperKey })
    if (requestToken !== layoutRequestToken || selectedPaperKey.value !== paperKey) return
    layoutDetail.value = payload.result || null
  } catch (error: any) {
    if (!silent && requestToken === layoutRequestToken && selectedPaperKey.value === paperKey) {
      adminToast.error(error.message || '版面解析状态读取失败')
    }
  } finally {
    if (!silent && requestToken === layoutRequestToken) layoutLoading.value = false
  }
}

async function generateLayout(force: boolean) {
  const paperKey = selectedPaperKey.value
  if (!paperKey) return adminToast.warning('请先选择论文')
  await adminConfirm(force ? '确认强制重跑版面解析？' : '确认解析这篇论文的 PDF 版面？', '版面解析确认')
    .catch(() => Promise.reject(new Error('cancelled')))
  await runAdminMutation(force ? 'paper.layout.force' : 'paper.layout.generate', 'airesearch.admin.paper.layout.generate', { paperKey, force })
  await Promise.all([loadState(), loadLayoutDetail(paperKey, true)])
  startLayoutPolling(paperKey)
}

async function startLayoutPolling(paperKey: string) {
  const token = ++layoutPollToken
  layoutPolling.value = true
  try {
    for (let attempt = 0; attempt < 90 && token === layoutPollToken && selectedPaperKey.value === paperKey; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 2000))
      if (token !== layoutPollToken || selectedPaperKey.value !== paperKey) return
      await Promise.all([loadState(), loadLayoutDetail(paperKey, true)])
      if (!['queued', 'running'].includes(currentLayoutStatus.value)) return
    }
  } finally {
    if (token === layoutPollToken) layoutPolling.value = false
  }
}

async function createFact() {
  if (!newFact.statement.trim()) return adminToast.warning('请填写事实陈述')
  await runAdminMutation('fact.create', 'airesearch.admin.fact.create', { paperKey: selectedPaperKey.value, ...newFact })
  Object.assign(newFact, { fact_type: state.fact_types[0] || 'method', name: '', confidence: 0.9, statement: '' })
  showFactCreator.value = false
  await loadPaperDetail(selectedPaperKey.value)
}

async function updateFact(fact: any) {
  await runAdminMutation(`fact.update.${fact.id}`, 'airesearch.admin.fact.update', fact)
  await loadPaperDetail(selectedPaperKey.value)
}

async function deleteFact(id: number) {
  await runAdminMutation(`fact.delete.${id}`, 'airesearch.admin.fact.delete', { id })
  await loadPaperDetail(selectedPaperKey.value)
}

function openProfileDialog(profile?: any) {
  profileDialogMode.value = profile ? 'edit' : 'create'
  Object.assign(profileForm, {
    name: profile?.name || '',
    description: profile?.description || '',
    keywordsText: (profile?.keywords || []).join('\n'),
    primary_since: profile?.primary_since || '2025-06-08',
    exception_since: profile?.exception_since || '2024-01-01'
  })
  profileDialogVisible.value = true
}

async function saveProfile() {
  const payload = {
    name: profileForm.name.trim(),
    description: profileForm.description,
    keywords: profileForm.keywordsText.split('\n').map((item) => item.trim()).filter(Boolean),
    primary_since: profileForm.primary_since,
    exception_since: profileForm.exception_since
  }
  if (!payload.name) return adminToast.warning('请填写方向 Key')
  const action = profileDialogMode.value === 'create' ? 'airesearch.admin.profile.create' : 'airesearch.admin.profile.update'
  await runAdminMutation('profile.save', action, payload)
  profileDialogVisible.value = false
  await loadState()
}

async function deleteProfile(name: string) {
  await runAdminMutation(`profile.delete.${name}`, 'airesearch.admin.profile.delete', { name })
  await loadState()
}

async function startJob(jobType: string, form: Record<string, any>) {
  const options = JSON.parse(JSON.stringify(form))
  await adminConfirm('确认加入研知库任务队列？长任务会在后台执行。', '研知库任务确认')
    .catch(() => Promise.reject(new Error('cancelled')))
  await runAdminMutation(`job.${jobType}`, 'airesearch.admin.job.start', { jobType, options })
  await loadState()
}

async function cancelJob(id: number) {
  await runAdminMutation(`job.cancel.${id}`, 'airesearch.admin.job.cancel', { id })
  await loadState()
}

async function searchSinglePaper() {
  const query = singlePaperInput.value.trim()
  if (!query) return adminToast.warning('请先输入论文标题、arXiv ID 或 URL')
  actionLoading.value = 'single.search'
  singlePaperSearched.value = false
  try {
    const result = await executeAdminAction<Record<string, any>>(auth.token, 'airesearch.paper.search_arxiv', { query, limit: 10 })
    singlePaperResults.value = result.results || []
    singlePaperSearched.value = true
    if (singlePaperResults.value.length) adminToast.success(`找到 ${singlePaperResults.value.length} 篇匹配论文`)
    else adminToast.warning('arXiv 未找到匹配论文，可尝试直接入库 URL / ID')
  } catch (error: any) {
    adminToast.error(error.message || '论文搜索失败')
  } finally {
    actionLoading.value = ''
  }
}

async function ingestSinglePaper(input: string, loadingKey: string) {
  const paperInput = String(input || '').trim()
  if (!paperInput) return adminToast.warning('请先输入论文标题、arXiv ID 或 URL')
  await adminConfirm(`确认入库这篇论文？\n${paperInput}`, '单论文入库确认')
    .catch(() => Promise.reject(new Error('cancelled')))
  await runAdminMutation(loadingKey, 'airesearch.paper.ingest_single', { input: paperInput })
  singlePaperInput.value = ''
  singlePaperResults.value = []
  singlePaperSearched.value = false
  await loadState()
}

async function runAdminMutation(key: string, action: string, input: Record<string, unknown>) {
  actionLoading.value = key
  try {
    const result = await executeAdminAction<Record<string, any>>(auth.token, action, input)
    adminToast.success(result.message || '操作已完成')
    return result
  } catch (error: any) {
    if (error.message !== 'cancelled') adminToast.error(error.message || '操作失败')
    throw error
  } finally {
    actionLoading.value = ''
  }
}

function statusLabel(status: string) {
  return {
    queued: '排队',
    running: '运行中',
    completed: '完成',
    failed: '失败',
    publish_failed: '发布失败',
    canceled: '已取消'
  }[status] || status
}

function safeJsonObject(value: unknown): Record<string, any> {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, any>
  if (typeof value !== 'string' || !value.trim()) return {}
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

function safeJsonArray(value: unknown): any[] {
  if (Array.isArray(value)) return value
  if (typeof value !== 'string' || !value.trim()) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function layoutBlockMetadata(block: any) {
  return safeJsonObject(block?.metadata)
}

function layoutBlockKey(block: any) {
  return [
    block?.page_index ?? 'p',
    block?.block_index ?? 'b',
    block?.block_type || 'text',
    block?.source_reference || block?.asset_path || ''
  ].join(':')
}

function layoutBlockLocation(block: any) {
  const page = Number(block?.page_index ?? 0) + 1
  const index = block?.block_index !== undefined && block?.block_index !== null ? ` #${block.block_index}` : ''
  return `page ${page}${index}`
}

function layoutBlockTypeLabel(type: string) {
  const blockType = String(type || '')
  if (blockType === 'image') return '图片'
  if (blockType === 'chart') return '图表'
  if (blockType === 'table') return '表格'
  if (blockType === 'interline_equation') return '公式'
  if (blockType === 'title') return '标题'
  return blockType || '文本'
}

function graphFactTypeLabel(type: string) {
  return ({
    method: '方法',
    claim: '结论',
    limitation: '局限',
    dataset: '数据集',
    benchmark: '评测'
  } as Record<string, string>)[String(type || '')] || String(type || '事实')
}

function graphEvidenceTypeLabel(type: string) {
  return ({
    layout_figure: '图像',
    layout_table: '表格',
    layout_equation: '公式'
  } as Record<string, string>)[String(type || '')] || String(type || '版面证据')
}

function graphMatchMethodLabel(method: string) {
  return ({
    direct_provenance: '显式引用',
    normalized_containment: '文本包含',
    strict_token: '严格词元'
  } as Record<string, string>)[String(method || '')] || String(method || '自动关联')
}

function graphScoreLabel(value: unknown) {
  const score = Number(value)
  return Number.isFinite(score) ? score.toFixed(2) : 'n/a'
}

function graphEvidenceLocation(evidence: any) {
  if (!evidence) return '位置未知'
  const page = Number(evidence.page_number || Number(evidence.page_index || 0) + 1)
  const block = evidence.block_index !== undefined && evidence.block_index !== null ? ` · block ${evidence.block_index}` : ''
  return `page ${page || '?'}${block}`
}

function graphProvenanceText(value: unknown) {
  const provenance = safeJsonArray(value)
  if (!provenance.length) return '无 provenance'
  return provenance.slice(0, 4).map((item: any) => {
    if (!item || typeof item !== 'object') return String(item || '')
    return `${item.source_table || 'source'}:${item.source_key || '?'}${item.source_field ? `.${item.source_field}` : ''}`
  }).filter(Boolean).join(' · ')
}

function layoutBlockText(block: any) {
  const metadata = layoutBlockMetadata(block)
  return String(
    metadata.caption ||
    metadata.text ||
    metadata.table_markdown ||
    block?.text ||
    block?.asset_path ||
    block?.evidence_kind ||
    '无文本内容'
  ).slice(0, 320)
}

function layoutBlockSource(block: any) {
  const metadata = layoutBlockMetadata(block)
  return shortPath(String(metadata.source_path || block?.source_reference || block?.asset_path || ''))
}

function qualityScore(block: any) {
  const metadata = layoutBlockMetadata(block)
  const score = Number(metadata.quality_score ?? metadata.evidence_confidence ?? block?.confidence)
  return Number.isFinite(score) ? score : 0
}

function qualityLabel(block: any) {
  const score = qualityScore(block)
  if (score <= 0) return '未评分'
  return `${Math.round(score * 100)}%`
}

function qualityClass(block: any) {
  const score = qualityScore(block)
  if (score >= 0.72) return 'quality-good'
  if (score > 0) return 'quality-mid'
  return 'quality-low'
}

function qualityReasons(block: any) {
  const reasons = safeJsonArray(layoutBlockMetadata(block).quality_reasons)
  return reasons.slice(0, 5).join(' · ')
}

function evidenceConfidenceLabel(candidate: any) {
  const score = Number(candidate?.confidence ?? candidate?.score ?? candidate?.quality_score)
  if (!Number.isFinite(score) || score <= 0) return '未评分'
  return score <= 1 ? `${Math.round(score * 100)}%` : `${Math.round(score)}`
}

function formulaText(block: any) {
  const metadata = layoutBlockMetadata(block)
  return String(metadata.formula_latex || metadata.formula_ocr_candidate_latex || block?.text || '暂无公式文本').slice(0, 1200)
}

function formulaMetaText(block: any) {
  const metadata = layoutBlockMetadata(block)
  const parts = [
    metadata.formula_ocr_status ? `状态 ${metadata.formula_ocr_status}` : '',
    metadata.formula_ocr_model ? `模型 ${metadata.formula_ocr_model}` : '',
    metadata.formula_ocr_confidence ? `置信度 ${metadata.formula_ocr_confidence}` : '',
    qualityReasons(block)
  ].filter(Boolean)
  return parts.join(' · ') || '未记录公式 OCR 元数据'
}

function tableMarkdown(block: any) {
  const metadata = layoutBlockMetadata(block)
  return String(metadata.table_markdown || metadata.table_html || block?.text || '').slice(0, 1400)
}

function tableShapeText(block: any) {
  const metadata = layoutBlockMetadata(block)
  const rows = safeJsonArray(metadata.table_rows)
  const rowCount = Number(metadata.row_count || rows.length || 0)
  const colCount = Number(metadata.column_count || rows.reduce((max, row) => Math.max(max, Array.isArray(row) ? row.length : 0), 0))
  const method = metadata.reconstruction_method || metadata.table_reconstruction || metadata.evidence_kind || '未记录结构来源'
  const shape = rowCount || colCount ? `${rowCount || '?'} 行 x ${colCount || '?'} 列` : '行列数未知'
  return `${shape} · ${method}`
}

function layoutErrorText(errors: unknown) {
  const rows = safeJsonArray(errors)
  if (!rows.length) return '未记录错误'
  return rows.slice(0, 3).map((item) => typeof item === 'string' ? item : JSON.stringify(item)).join(' · ')
}

function layoutArtifactCount(type: string) {
  return layoutArtifactRows.value.filter((artifact: any) => artifact.artifact_type === type).length
}

function layoutBlockCount(type: string) {
  return Number(layoutDetail.value?.block_counts?.[type] || 0)
}

function layoutSummaryNumber(key: string) {
  return Number(layoutSummary.value?.[key] || 0)
}

function layoutReadingOrderNumber(key: string) {
  return Number(layoutSummary.value?.reading_order?.[key] || 0)
}

function layoutOcrNumber(key: string) {
  return Number(layoutSummary.value?.ocr?.[key] || 0)
}

function layoutFormulaOcrNumber(key: string) {
  return Number(layoutSummary.value?.formula_ocr?.[key] || 0)
}

function documentTypeLabel(type: string) {
  return ({ digital: '文本型', scanned: '扫描型', mixed: '混合型' } as Record<string, string>)[type] || type || '未知'
}

function visualSourceLabel(sourceKind: string) {
  return {
    layout_block: 'layout v2',
    source_figure: '论文 figures',
    cover_fallback: '旧 cover'
  }[sourceKind] || sourceKind || '未知来源'
}

function visualDimensionsText(candidate: any) {
  const dimensions = candidate?.dimensions || {}
  if (dimensions.width && dimensions.height) return `${dimensions.width}x${dimensions.height}`
  return '未知尺寸'
}

function shortPath(path: string) {
  const value = String(path || '')
  if (value.length <= 68) return value
  return `...${value.slice(-65)}`
}

function layoutStatusLabel(status: string) {
  return {
    not_parsed: '未解析',
    queued: '排队',
    running: '运行中',
    completed: '完成',
    failed: '失败',
    skipped: '已复用'
  }[status] || status
}

function layoutStatusTagType(status: string) {
  return {
    not_parsed: 'info',
    queued: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    skipped: 'success'
  }[status] || 'info'
}

function paperLayoutStatus(paper: any) {
  const status = String(paper?.layout_status || '')
  return status || 'not_parsed'
}

function jobTagType(status: string) {
  return {
    queued: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    publish_failed: 'danger',
    canceled: 'info'
  }[status] || 'info'
}

</script>
