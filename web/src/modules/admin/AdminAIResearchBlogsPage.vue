<template>
  <section class="admin-resource airesearch-admin airesearch-admin-console airesearch-blog-workspace">
    <PageHeader eyebrow="研知库" title="博客生成" description="选择论文，生成可发布的深度解读并管理历史版本。">
      <el-button :icon="Refresh" :loading="loading" @click="refreshWorkspace">刷新</el-button>
    </PageHeader>

    <div class="airesearch-blog-layout">
      <aside class="airesearch-blog-library" aria-label="论文列表">
        <div class="airesearch-blog-library-head">
          <div>
            <span>Paper Library</span>
            <h2>待解读论文</h2>
          </div>
          <strong>{{ filteredPapers.length }}</strong>
        </div>
        <el-input v-model="paperQuery" :prefix-icon="Search" placeholder="搜索标题或 paper key" clearable />
        <el-segmented v-model="statusFilter" :options="statusOptions" class="airesearch-blog-status-filter" />
        <div class="airesearch-blog-paper-list" v-loading="loading">
          <button
            v-for="paper in filteredPapers"
            :key="paper.paper_key"
            type="button"
            :class="{ active: selectedPaperKey === paper.paper_key }"
            :aria-current="selectedPaperKey === paper.paper_key ? 'true' : undefined"
            @click="selectPaper(paper.paper_key)"
          >
            <span class="airesearch-blog-paper-row">
              <strong>{{ paper.title || paper.paper_key }}</strong>
              <el-tag size="small" :type="blogStatusTagType(paperBlogStatus(paper))">
                {{ blogStatusLabel(paperBlogStatus(paper)) }}
              </el-tag>
            </span>
            <span class="airesearch-blog-paper-key">{{ paper.paper_key }}</span>
            <span class="airesearch-blog-paper-meta">
              {{ paper.year || '年份未知' }}
              <i>{{ Number(paper.blog_word_count || 0) ? `${paper.blog_word_count} 字` : '尚未生成' }}</i>
            </span>
          </button>
          <el-empty v-if="!loading && !filteredPapers.length" :image-size="72" description="没有符合条件的论文" />
        </div>
      </aside>

      <main class="airesearch-blog-detail" v-loading="paperBlogLoading">
        <el-empty v-if="!selectedPaper" description="选择一篇论文开始生成" />
        <template v-else>
          <header class="airesearch-blog-detail-head">
            <div>
              <span>Deep Reading Studio</span>
              <h2>{{ selectedPaper.title || selectedPaper.paper_key }}</h2>
              <p>{{ selectedPaper.paper_key }}</p>
            </div>
            <el-tag :type="blogStatusTagType(currentBlogStatus)">{{ blogStatusLabel(currentBlogStatus) }}</el-tag>
          </header>

          <section class="airesearch-blog-evidence-preflight" v-loading="layoutLoading" aria-label="证据预检">
            <div class="airesearch-blog-evidence-head">
              <div>
                <span>Evidence Preflight</span>
                <strong>证据预检</strong>
                <p>{{ layoutPreflightMessage }}</p>
              </div>
              <el-tag :type="layoutStatusTagType(currentLayoutStatus)">{{ layoutStatusLabel(currentLayoutStatus) }}</el-tag>
            </div>
            <dl class="airesearch-blog-evidence-metrics">
              <div><dt>解析器</dt><dd>{{ layoutParserVersion }}</dd></div>
              <div><dt>文档类型</dt><dd>{{ documentTypeLabel(String(layoutSummary.document_type || 'digital')) }}</dd></div>
              <div><dt>OCR 页</dt><dd>{{ layoutOcrNumber('pages_succeeded') }}/{{ layoutOcrNumber('pages_attempted') }}</dd></div>
              <div><dt>OCR 块</dt><dd>{{ layoutOcrNumber('block_count') }}</dd></div>
              <div><dt>公式 OCR</dt><dd>{{ layoutFormulaOcrNumber('blocks_succeeded') }}/{{ layoutFormulaOcrNumber('blocks_attempted') }}</dd></div>
              <div><dt>图注</dt><dd>{{ layoutSummaryNumber('captioned_visual_blocks') }}</dd></div>
              <div><dt>结构表</dt><dd>{{ layoutSummaryNumber('structured_table_blocks') }}</dd></div>
              <div><dt>几何表</dt><dd>{{ layoutSummaryNumber('geometry_table_blocks') }}</dd></div>
              <div><dt>跨列表</dt><dd>{{ layoutSummaryNumber('spanning_table_blocks') }}</dd></div>
              <div><dt>文本降级</dt><dd>{{ layoutSummaryNumber('text_fallback_table_blocks') }}</dd></div>
              <div><dt>多栏页</dt><dd>{{ layoutReadingOrderNumber('multi_column_pages') }}</dd></div>
              <div><dt>跨栏块</dt><dd>{{ layoutReadingOrderNumber('cross_column_blocks') }}</dd></div>
              <div><dt>Caption 组</dt><dd>{{ layoutReadingOrderNumber('caption_paired_blocks') }}</dd></div>
              <div><dt>读序风险</dt><dd>{{ layoutReadingOrderNumber('low_confidence_blocks') }}</dd></div>
              <div><dt>公式</dt><dd>{{ layoutSummaryNumber('equation_blocks') || layoutBlockCount('interline_equation') }}</dd></div>
              <div><dt>证据块</dt><dd>{{ layoutSummaryNumber('evidence_ready_blocks') }}</dd></div>
              <div><dt>高质证据</dt><dd>{{ layoutSummaryNumber('high_quality_evidence_blocks') }}</dd></div>
              <div><dt>高质表格</dt><dd>{{ layoutSummaryNumber('high_quality_table_blocks') }}</dd></div>
              <div><dt>高质公式</dt><dd>{{ layoutSummaryNumber('high_quality_equation_blocks') }}</dd></div>
              <div><dt>视觉素材</dt><dd>{{ layoutBlockCount('image') + layoutBlockCount('table') + layoutBlockCount('chart') }}</dd></div>
            </dl>
            <div v-if="layoutDetail" class="airesearch-layout-inspector">
              <div class="airesearch-layout-capabilities">
                <el-tag v-for="item in layoutCapabilityItems" :key="item.key" size="small" :type="item.enabled ? 'success' : 'info'" effect="plain">
                  {{ item.label }}
                </el-tag>
              </div>
              <div class="airesearch-layout-detail-grid">
                <article class="airesearch-layout-visual-card">
                  <div class="airesearch-layout-card-head">
                    <span>Selected Visual</span>
                    <strong>代表图</strong>
                  </div>
                  <template v-if="representativeVisual">
                    <b>{{ visualSourceLabel(representativeVisual.source_kind) }}</b>
                    <p>{{ representativeVisual.caption || representativeVisual.reason || representativeVisual.source_reference || '已选择视觉素材' }}</p>
                    <em>{{ representativeVisual.source_reference || representativeVisual.reason || '来源未记录' }}</em>
                  </template>
                  <el-empty v-else :image-size="48" description="暂无代表图" />
                </article>
                <article class="airesearch-layout-evidence-preview">
                  <div class="airesearch-layout-card-head">
                    <span>Evidence Blocks</span>
                    <strong>证据块预览</strong>
                    <em>{{ layoutEvidenceBlocks.length }}</em>
                  </div>
                  <div v-if="layoutEvidenceBlocks.length" class="airesearch-layout-evidence-stack">
                    <div v-for="block in layoutEvidencePreview" :key="`${block.page_index}-${block.block_index}-${block.block_type}`">
                      <strong>
                        {{ layoutBlockTypeLabel(block.block_type) }} · {{ block.source_reference || `page=${Number(block.page_index || 0) + 1}` }}
                        <em :class="qualityClass(block)">{{ qualityLabel(block) }}</em>
                      </strong>
                      <span>{{ layoutBlockText(block) }}</span>
                      <small v-if="qualityReasons(block)">{{ qualityReasons(block) }}</small>
                    </div>
                  </div>
                  <el-empty v-else :image-size="48" description="暂无证据块" />
                </article>
              </div>
              <details v-if="layoutVisualCandidates.length" class="airesearch-layout-candidates">
                <summary>候选视觉素材 {{ layoutVisualCandidates.length }} 项</summary>
                <div>
                  <article v-for="candidate in layoutVisualCandidatesPreview" :key="candidate.source_path || candidate.source_reference">
                    <strong>{{ visualSourceLabel(candidate.source_kind) }}</strong>
                    <span>{{ candidate.caption || candidate.reason || candidate.source_reference || '未命名候选' }}</span>
                    <em>{{ evidenceConfidenceLabel(candidate) }}</em>
                  </article>
                </div>
              </details>
            </div>
            <div class="airesearch-blog-evidence-actions">
              <el-button
                type="primary"
                plain
                :loading="actionLoading === 'paper.layout.generate' || layoutPolling"
                :disabled="Boolean(actionLoading) || layoutPolling"
                @click="generateLayout(false)"
              >
                {{ currentLayoutStatus === 'completed' ? '补充解析' : '先解析版面' }}
              </el-button>
              <el-button
                plain
                :loading="actionLoading === 'paper.layout.force'"
                :disabled="Boolean(actionLoading) || layoutPolling"
                @click="generateLayout(true)"
              >
                强制重跑解析
              </el-button>
            </div>
          </section>

          <section class="airesearch-blog-command" aria-label="生成设置">
            <div class="airesearch-blog-command-copy">
              <span>生成设置</span>
              <strong>目标字数</strong>
              <p>输出范围固定为 3000-8000 字。</p>
            </div>
            <el-input-number v-model="blogTargetWordCount" :min="3000" :max="8000" :step="500" controls-position="right" />
            <div class="airesearch-blog-command-actions">
              <el-button
                type="primary"
                :loading="actionLoading === 'paper.blog.generate' || blogPolling"
                :disabled="Boolean(actionLoading) || blogPolling"
                @click="generatePaperBlog(false)"
              >
                生成深度解读
              </el-button>
              <el-button
                :loading="actionLoading === 'paper.blog.force'"
                :disabled="Boolean(actionLoading) || blogPolling"
                @click="generatePaperBlog(true)"
              >
                强制重新生成
              </el-button>
            </div>
          </section>

          <section class="airesearch-blog-job-status" aria-live="polite" data-testid="paper-blog-status">
            <div class="airesearch-blog-job-head">
              <div>
                <span>生成任务</span>
                <strong>{{ latestBlogJob ? `#${latestBlogJob.id} ${statusLabel(latestBlogJob.status)}` : '暂无任务' }}</strong>
              </div>
              <el-tag v-if="latestBlogJob" :type="jobTagType(latestBlogJob.status)">{{ statusLabel(latestBlogJob.status) }}</el-tag>
            </div>
            <p>{{ latestBlogJob?.message || (blogPolling ? '正在等待生成任务状态更新' : '尚未提交深度解读生成任务') }}</p>
            <dl class="airesearch-blog-meta airesearch-blog-generation-meta">
              <div><dt>当前状态</dt><dd>{{ blogStatusLabel(currentBlogStatus) }}</dd></div>
              <div><dt>请求目标</dt><dd>{{ requestedTargetWordCount ? `${requestedTargetWordCount} 字` : '未记录' }}</dd></div>
              <div><dt>实际字数</dt><dd>{{ actualBlogWordCount ? `${actualBlogWordCount} 字` : '未生成' }}</dd></div>
              <div><dt>缓存命中</dt><dd>{{ generationMetric('cache_hits') }}</dd></div>
              <div><dt>LLM 调用</dt><dd>{{ generationMetric('llm_calls') }}</dd></div>
              <div><dt>最近生成</dt><dd>{{ lastGenerationTime || '未记录' }}</dd></div>
            </dl>
            <div v-if="lastBlogFailureMessage" class="airesearch-blog-failure" role="alert">
              <strong>最近失败</strong>
              <span>{{ lastBlogFailureMessage }}</span>
            </div>
          </section>

          <section class="airesearch-blog-content-section">
            <div class="airesearch-blog-section-head">
              <div>
                <span>Current Draft</span>
                <h3>当前解读</h3>
              </div>
              <el-popconfirm
                v-if="paperBlog?.post"
                title="确认隐藏这篇论文的深度解读？"
                confirm-button-text="确认"
                cancel-button-text="取消"
                @confirm="hidePaperBlog"
              >
                <template #reference>
                  <el-button type="danger" plain :loading="actionLoading === 'paper.blog.hide'" :disabled="Boolean(actionLoading) || paperBlog.post.status === 'hidden'">
                    隐藏解读
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
            <template v-if="paperBlog?.post">
              <dl class="airesearch-blog-meta">
                <div><dt>模型</dt><dd>{{ paperBlog.post.model || '未记录' }}</dd></div>
                <div><dt>更新时间</dt><dd>{{ paperBlog.post.updated_at || '未知' }}</dd></div>
                <div><dt>当前版本</dt><dd>{{ paperBlog.post.current_version_id ? `#${paperBlog.post.current_version_id}` : '未发布' }}</dd></div>
              </dl>
              <div class="airesearch-blog-evidence-used">
                <div class="airesearch-blog-evidence-used-head">
                  <span>Evidence Used</span>
                  <strong>本篇使用的证据素材</strong>
                  <em>{{ currentEvidenceRefs.length }} 项</em>
                </div>
                <div v-if="currentEvidenceRefs.length" class="airesearch-blog-evidence-list">
                  <article v-for="image in currentEvidenceRefs" :key="image.image_id || image.asset_path" class="airesearch-blog-evidence-item">
                    <div>
                      <strong>{{ image.caption || image.caption_seed || image.asset_path }}</strong>
                      <span>{{ evidenceKindLabel(image) }} · {{ image.source_reference || image.extraction_method || '来源未记录' }}</span>
                    </div>
                    <em>{{ evidenceConfidenceLabel(image) }}</em>
                  </article>
                </div>
                <el-empty v-else :image-size="58" description="当前版本没有记录证据素材" />
              </div>
              <details class="airesearch-blog-preview">
                <summary>Markdown 预览</summary>
                <pre>{{ paperBlog.post.markdown || '暂无内容' }}</pre>
              </details>
            </template>
            <el-empty v-else :image-size="84" description="这篇论文还没有深度解读" />
          </section>

          <section v-if="paperBlog?.versions?.length" class="airesearch-blog-content-section">
            <div class="airesearch-blog-section-head">
              <div>
                <span>Version History</span>
                <h3>版本历史</h3>
              </div>
              <strong>{{ paperBlog.versions.length }} 个版本</strong>
            </div>
            <div class="airesearch-blog-history">
              <article
                v-for="version in paperBlog.versions"
                :key="version.id"
                class="airesearch-blog-version-item"
                :data-current="paperBlog?.post?.current_version_id === version.id ? 'true' : undefined"
              >
                <div class="airesearch-blog-version-head">
                  <div class="airesearch-blog-version-title">
                    <span>v{{ version.version_number }}</span>
                    <h4>{{ version.title || '未命名版本' }}</h4>
                  </div>
                  <div class="airesearch-blog-version-tags">
                    <el-tag v-if="paperBlog?.post?.current_version_id === version.id" type="success">当前</el-tag>
                    <el-tag :type="blogStatusTagType(version.status)">{{ blogStatusLabel(version.status) }}</el-tag>
                  </div>
                </div>
                <dl class="airesearch-blog-version-meta">
                  <div><dt>字数</dt><dd>{{ version.word_count || 0 }}</dd></div>
                  <div><dt>生成时间</dt><dd>{{ version.created_at || '未知' }}</dd></div>
                  <div><dt>证据素材</dt><dd>{{ evidenceRefsForVersion(version).length }}</dd></div>
                </dl>
                <details v-if="evidenceRefsForVersion(version).length" class="airesearch-blog-version-evidence">
                  <summary>查看本版本证据</summary>
                  <div class="airesearch-blog-evidence-list compact">
                    <article v-for="image in evidenceRefsForVersion(version)" :key="`${version.id}-${image.image_id || image.asset_path}`" class="airesearch-blog-evidence-item">
                      <div>
                        <strong>{{ image.caption || image.caption_seed || image.asset_path }}</strong>
                        <span>{{ evidenceKindLabel(image) }} · {{ image.source_reference || image.extraction_method || '来源未记录' }}</span>
                      </div>
                      <em>{{ evidenceConfidenceLabel(image) }}</em>
                    </article>
                  </div>
                </details>
                <el-button
                  size="small"
                  plain
                  :loading="actionLoading === `paper.blog.rollback.${version.id}`"
                  :disabled="Boolean(actionLoading) || paperBlog?.post?.current_version_id === version.id"
                  @click="rollbackPaperBlog(version.id)"
                >
                  回退到此版本
                </el-button>
              </article>
            </div>
          </section>
        </template>
      </main>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh, Search } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { executeAdminAction, fetchAdminData } from '@/app/api/admin'
import { useAuthStore } from '@/app/stores/auth'
import { adminToast } from '@/shared/lib/adminFeedback'

type BlogFilter = 'all' | 'published' | 'hidden' | 'failed' | 'not_generated'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const paperBlogLoading = ref(false)
const actionLoading = ref('')
const paperQuery = ref('')
const selectedPaperKey = ref('')
const papers = ref<any[]>([])
const jobs = ref<any[]>([])
const paperBlog = ref<Record<string, any> | null>(null)
const layoutDetail = ref<Record<string, any> | null>(null)
const layoutLoading = ref(false)
const layoutPolling = ref(false)
const blogTargetWordCount = ref(5000)
const blogPolling = ref(false)
let blogPollToken = 0
let layoutPollToken = 0
let blogDetailRequestId = 0

const filterValues: BlogFilter[] = ['all', 'published', 'hidden', 'failed', 'not_generated']
const statusFilter = ref<BlogFilter>(filterValues.includes(String(route.query.status) as BlogFilter) ? String(route.query.status) as BlogFilter : 'all')
const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '已发布', value: 'published' },
  { label: '已隐藏', value: 'hidden' },
  { label: '失败', value: 'failed' },
  { label: '未生成', value: 'not_generated' }
]

const selectedPaper = computed(() => papers.value.find((paper) => paper.paper_key === selectedPaperKey.value) || null)
const selectedPaperBlogJobs = computed(() => {
  const matches = jobs.value.filter((job) => isPaperBlogJobFor(job, selectedPaperKey.value))
  const detailJob = paperBlog.value?.latest_job
  if (isPaperBlogJobFor(detailJob, selectedPaperKey.value) && !matches.some((job) => Number(job.id) === Number(detailJob.id))) matches.push(detailJob)
  return matches
})
const latestBlogJob = computed(() => selectedPaperBlogJobs.value.reduce<any | null>((latest, job) => (
  !latest || Number(job.id || 0) > Number(latest.id || 0) ? job : latest
), null))
const currentBlogVersion = computed(() => {
  const versions = Array.isArray(paperBlog.value?.versions) ? paperBlog.value.versions : []
  const currentId = Number(paperBlog.value?.post?.current_version_id || 0)
  return versions.find((version: any) => Number(version.id) === currentId) || versions[0] || null
})
const generationMeta = computed(() => (
  safeJsonObject(currentBlogVersion.value?.generation_meta_json)
  || safeJsonObject(currentBlogVersion.value?.generation_meta)
  || safeJsonObject(paperBlog.value?.generation_meta_json)
  || safeJsonObject(paperBlog.value?.generation_meta)
  || {}
))
const requestedTargetWordCount = computed(() => {
  const params = safeJsonObject(latestBlogJob.value?.params) || safeJsonObject(latestBlogJob.value?.params_json) || {}
  const target = params.targetWordCount ?? params.target_chars ?? generationMeta.value.target_chars ?? generationMeta.value.target_word_count
  return Number(target) > 0 ? Number(target) : 0
})
const actualBlogWordCount = computed(() => Number(paperBlog.value?.post?.word_count ?? currentBlogVersion.value?.word_count ?? 0))
const lastGenerationTime = computed(() => currentBlogVersion.value?.created_at || paperBlog.value?.post?.updated_at || '')
const lastBlogFailureMessage = computed(() => selectedPaperBlogJobs.value
  .filter((job) => ['failed', 'publish_failed'].includes(job.status))
  .sort((a, b) => Number(b.id || 0) - Number(a.id || 0))[0]?.message || '')
const currentBlogStatus = computed(() => paperBlog.value?.post?.status || paperBlogStatus(selectedPaper.value))
const latestLayoutRun = computed(() => layoutDetail.value?.latest_run || null)
const latestLayoutJob = computed(() => layoutDetail.value?.latest_job || null)
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
  { key: 'has_caption_paired_reading_order', label: 'Caption 读序', enabled: Boolean(layoutCapabilities.value.has_caption_paired_reading_order) },
  { key: 'needs_reading_order_attention', label: '读序需复核', enabled: Boolean(layoutCapabilities.value.needs_reading_order_attention) },
  { key: 'has_equations', label: '公式块', enabled: Boolean(layoutCapabilities.value.has_equations) },
  { key: 'has_evidence_blocks', label: '证据块', enabled: Boolean(layoutCapabilities.value.has_evidence_blocks) },
  { key: 'has_high_quality_evidence', label: '高质证据', enabled: Boolean(layoutCapabilities.value.has_high_quality_evidence) },
  { key: 'has_high_quality_tables', label: '高质表格', enabled: Boolean(layoutCapabilities.value.has_high_quality_tables) },
  { key: 'has_high_quality_equations', label: '高质公式', enabled: Boolean(layoutCapabilities.value.has_high_quality_equations) },
  { key: 'ocr_available', label: 'OCR 可用', enabled: Boolean(layoutCapabilities.value.ocr_available) },
  { key: 'has_ocr_blocks', label: 'OCR 文本', enabled: Boolean(layoutCapabilities.value.has_ocr_blocks) },
  { key: 'formula_ocr_configured', label: '公式 OCR 已配置', enabled: Boolean(layoutCapabilities.value.formula_ocr_configured) },
  { key: 'has_formula_ocr', label: '公式 OCR 结果', enabled: Boolean(layoutCapabilities.value.has_formula_ocr) }
])
const representativeVisual = computed(() => layoutDetail.value?.representative_visual || null)
const layoutEvidenceBlocks = computed(() => Array.isArray(layoutDetail.value?.evidence_blocks) ? layoutDetail.value.evidence_blocks : [])
const layoutEvidencePreview = computed(() => layoutEvidenceBlocks.value.slice(0, 6))
const layoutVisualCandidates = computed(() => Array.isArray(layoutDetail.value?.visual_candidates) ? layoutDetail.value.visual_candidates : [])
const layoutVisualCandidatesPreview = computed(() => layoutVisualCandidates.value.slice(0, 4))
const currentLayoutStatus = computed(() => {
  const jobStatus = String(latestLayoutJob.value?.status || '')
  if (['queued', 'running'].includes(jobStatus)) return jobStatus
  return String(latestLayoutRun.value?.status || 'not_parsed')
})
const layoutParserVersion = computed(() => latestLayoutRun.value?.provider_version || layoutSummary.value?.parser_version || '未解析')
const layoutPreflightMessage = computed(() => {
  if (latestLayoutJob.value?.message) return latestLayoutJob.value.message
  if (latestLayoutRun.value?.error) return latestLayoutRun.value.error
  if (currentLayoutStatus.value === 'completed') return `已完成版面解析，深度解读会自动使用图注、表格、公式和视觉证据。`
  if (['queued', 'running'].includes(currentLayoutStatus.value)) return '版面解析正在后台执行，完成后会自动进入证据预检。'
  return '尚未解析版面。可以直接生成，但建议先解析以提升图片、表格和公式引用质量。'
})
const currentEvidenceRefs = computed(() => {
  const fromPost = safeJsonArray(paperBlog.value?.post?.image_refs_json || paperBlog.value?.post?.image_refs)
  if (fromPost.length) return fromPost
  return evidenceRefsForVersion(currentBlogVersion.value)
})
const filteredPapers = computed(() => {
  const keyword = paperQuery.value.trim().toLowerCase()
  return papers.value.filter((paper) => {
    const matchesStatus = statusFilter.value === 'all' || paperBlogStatus(paper) === statusFilter.value
    const matchesKeyword = !keyword || [paper.title, paper.paper_key, paper.arxiv_id]
      .some((value) => String(value || '').toLowerCase().includes(keyword))
    return matchesStatus && matchesKeyword
  })
})

watch(statusFilter, async (status) => {
  await replaceQuery({ status: status === 'all' ? undefined : status })
})
watch(() => route.query.paperKey, async (value) => {
  const paperKey = String(value || '')
  if (paperKey && paperKey !== selectedPaperKey.value && papers.value.some((paper) => paper.paper_key === paperKey)) {
    await selectPaper(paperKey, false)
  }
})

onMounted(() => {
  loadState()
  window.addEventListener('niu-admin-refresh', refreshWorkspace)
})
onBeforeUnmount(() => {
  cancelPolling()
  cancelLayoutPolling()
  window.removeEventListener('niu-admin-refresh', refreshWorkspace)
})

async function loadState({ preserveSelection = true } = {}) {
  loading.value = true
  try {
    const payload = await fetchAdminData<Record<string, any>>('airesearch.admin.state', auth.token)
    const next = payload.state || {}
    papers.value = next.papers || []
    jobs.value = next.jobs || []
    const queryPaperKey = String(route.query.paperKey || '')
    const preferred = preserveSelection ? selectedPaperKey.value || queryPaperKey : queryPaperKey
    const validKey = papers.value.some((paper) => paper.paper_key === preferred) ? preferred : papers.value[0]?.paper_key || ''
    if (validKey && validKey !== selectedPaperKey.value) await selectPaper(validKey)
    else if (validKey && !paperBlog.value) await Promise.all([loadPaperBlog(validKey), loadLayoutDetail(validKey, { silent: true })])
  } catch (error: any) {
    adminToast.error(error.message || '研知库管理状态读取失败')
  } finally {
    loading.value = false
  }
}

async function refreshWorkspace() {
  await loadState()
  if (selectedPaperKey.value) await Promise.all([loadPaperBlog(selectedPaperKey.value), loadLayoutDetail(selectedPaperKey.value)])
}

async function selectPaper(paperKey: string, updateQuery = true) {
  cancelPolling()
  cancelLayoutPolling()
  selectedPaperKey.value = paperKey
  paperBlog.value = null
  layoutDetail.value = null
  if (updateQuery) await replaceQuery({ paperKey })
  await Promise.all([loadPaperBlog(paperKey), loadLayoutDetail(paperKey, { silent: true })])
}

async function replaceQuery(values: Record<string, string | undefined>) {
  const query = { ...route.query, ...values }
  Object.keys(query).forEach((key) => query[key] === undefined && delete query[key])
  await router.replace({ query })
}

async function loadPaperBlog(paperKey: string, { silent = false } = {}) {
  const requestId = ++blogDetailRequestId
  if (!silent) paperBlogLoading.value = true
  try {
    const payload = await fetchAdminData<Record<string, any>>('airesearch.admin.paper.blog.detail', auth.token, { paperKey })
    if (selectedPaperKey.value === paperKey) paperBlog.value = payload.result || null
  } catch (error: any) {
    if (!silent && requestId === blogDetailRequestId && selectedPaperKey.value === paperKey) {
      paperBlog.value = null
      adminToast.error(error.message || '深度解读状态读取失败')
    }
  } finally {
    if (!silent && requestId === blogDetailRequestId) paperBlogLoading.value = false
  }
}

async function loadLayoutDetail(paperKey: string, { silent = false } = {}) {
  if (!paperKey) return
  if (!silent) layoutLoading.value = true
  try {
    const payload = await fetchAdminData<Record<string, any>>('airesearch.admin.paper.layout.detail', auth.token, { paperKey })
    if (selectedPaperKey.value === paperKey) layoutDetail.value = payload.result || null
  } catch (error: any) {
    if (!silent && selectedPaperKey.value === paperKey) adminToast.error(error.message || '版面解析状态读取失败')
  } finally {
    if (!silent) layoutLoading.value = false
  }
}

async function generatePaperBlog(force = false) {
  if (!selectedPaperKey.value) return adminToast.warning('请先选择论文')
  const paperKey = selectedPaperKey.value
  const result = await runAdminMutation(force ? 'paper.blog.force' : 'paper.blog.generate', 'airesearch.admin.paper.blog.generate', {
    paperKey,
    force,
    targetWordCount: blogTargetWordCount.value
  })
  const jobId = Number(result?.result?.job_id ?? result?.job_id ?? 0)
  await pollPaperBlogGeneration(paperKey, jobId)
}

async function generateLayout(force = false) {
  if (!selectedPaperKey.value) return adminToast.warning('请先选择论文')
  const paperKey = selectedPaperKey.value
  const result = await runAdminMutation(force ? 'paper.layout.force' : 'paper.layout.generate', 'airesearch.admin.paper.layout.generate', {
    paperKey,
    force
  })
  const jobId = Number(result?.result?.job_id ?? result?.job_id ?? 0)
  await pollLayoutParse(paperKey, jobId)
}

async function pollLayoutParse(paperKey: string, jobId: number) {
  const token = ++layoutPollToken
  const deadline = Date.now() + 90_000
  layoutPolling.value = true
  try {
    while (token === layoutPollToken && selectedPaperKey.value === paperKey) {
      const remaining = deadline - Date.now()
      if (remaining <= 0) {
        adminToast.warning('版面解析仍在后台运行，稍后刷新即可查看证据预检')
        return
      }
      await Promise.all([loadState(), loadLayoutDetail(paperKey, { silent: true })])
      const job = latestLayoutJob.value
      if ((jobId && Number(job?.id || 0) === jobId && ['completed', 'failed', 'canceled'].includes(String(job?.status || ''))) || (!['queued', 'running'].includes(currentLayoutStatus.value))) {
        await loadLayoutDetail(paperKey, { silent: true })
        return
      }
      await delay(1500)
    }
  } finally {
    if (token === layoutPollToken) layoutPolling.value = false
  }
}

async function pollPaperBlogGeneration(paperKey: string, jobId: number) {
  const token = ++blogPollToken
  const deadline = Date.now() + 120_000
  blogPolling.value = true
  try {
    while (token === blogPollToken && selectedPaperKey.value === paperKey) {
      const remaining = deadline - Date.now()
      if (remaining <= 0) {
        adminToast.warning('生成任务仍在后台运行，状态轮询已停止，可稍后手动刷新')
        return
      }
      const refreshedJobs = await withTimeout(refreshPaperBlogStatus(paperKey), Math.min(10_000, remaining), '生成任务状态请求超时')
      const job = refreshedJobs.find((item: any) => Number(item.id) === jobId) || refreshedJobs[0]
      if (job && ['completed', 'failed', 'publish_failed', 'canceled'].includes(job.status)) {
        await loadPaperBlog(paperKey, { silent: true })
        return
      }
      await delay(1500)
    }
  } catch (error: any) {
    adminToast.error(error.message || '生成任务状态刷新失败')
  } finally {
    if (token === blogPollToken) blogPolling.value = false
  }
}

async function refreshPaperBlogStatus(paperKey: string) {
  const [statePayload, blogPayload, layoutPayload] = await Promise.all([
    fetchAdminData<Record<string, any>>('airesearch.admin.state', auth.token),
    fetchAdminData<Record<string, any>>('airesearch.admin.paper.blog.detail', auth.token, { paperKey }),
    fetchAdminData<Record<string, any>>('airesearch.admin.paper.layout.detail', auth.token, { paperKey })
  ])
  papers.value = statePayload.state?.papers || papers.value
  jobs.value = statePayload.state?.jobs || []
  const detail = blogPayload.result || null
  if (selectedPaperKey.value === paperKey) paperBlog.value = detail
  if (selectedPaperKey.value === paperKey) layoutDetail.value = layoutPayload.result || null
  const matches = jobs.value.filter((job: any) => isPaperBlogJobFor(job, paperKey))
  if (isPaperBlogJobFor(detail?.latest_job, paperKey) && !matches.some((job: any) => Number(job.id) === Number(detail.latest_job.id))) matches.push(detail.latest_job)
  return matches.sort((a: any, b: any) => Number(b.id || 0) - Number(a.id || 0))
}

async function rollbackPaperBlog(versionId: number) {
  try {
    await runAdminMutation(`paper.blog.rollback.${versionId}`, 'airesearch.admin.paper.blog.rollback', { paperKey: selectedPaperKey.value, versionId })
  } finally {
    await refreshWorkspace()
  }
}

async function hidePaperBlog() {
  try {
    await runAdminMutation('paper.blog.hide', 'airesearch.admin.paper.blog.hide', { paperKey: selectedPaperKey.value })
  } finally {
    await refreshWorkspace()
  }
}

async function runAdminMutation(key: string, action: string, input: Record<string, unknown>) {
  actionLoading.value = key
  try {
    const result = await executeAdminAction<Record<string, any>>(auth.token, action, input)
    adminToast.success(result.message || '操作已完成')
    return result
  } catch (error: any) {
    adminToast.error(error.message || '操作失败')
    throw error
  } finally {
    actionLoading.value = ''
  }
}

function cancelPolling() {
  blogPollToken += 1
  blogPolling.value = false
}

function cancelLayoutPolling() {
  layoutPollToken += 1
  layoutPolling.value = false
}

function paperBlogStatus(paper: any): BlogFilter {
  if (!paper) return 'not_generated'
  if (['failed', 'publish_failed'].includes(String(paper.blog_latest_job_status || ''))) return 'failed'
  const status = String(paper.blog_status || '')
  if (status === 'published' || status === 'hidden' || status === 'failed') return status
  return 'not_generated'
}

function statusLabel(status: string) {
  return ({ queued: '排队', running: '运行中', completed: '完成', failed: '失败', publish_failed: '发布失败', canceled: '已取消' } as Record<string, string>)[status] || status
}

function blogStatusLabel(status: string) {
  return ({ published: '已发布', superseded: '已替换', hidden: '已隐藏', failed: '失败', not_generated: '未生成' } as Record<string, string>)[status] || status || '未生成'
}

function blogStatusTagType(status: string) {
  return ({ published: 'success', superseded: 'info', hidden: 'warning', failed: 'danger', not_generated: 'info' } as Record<string, string>)[status] || 'info'
}

function jobTagType(status: string) {
  return ({ queued: 'info', running: 'warning', completed: 'success', failed: 'danger', publish_failed: 'danger', canceled: 'info' } as Record<string, string>)[status] || 'info'
}

function layoutStatusLabel(status: string) {
  return ({ not_parsed: '未解析', queued: '排队', running: '运行中', completed: '完成', failed: '失败', skipped: '已复用' } as Record<string, string>)[status] || status
}

function layoutStatusTagType(status: string) {
  return ({ not_parsed: 'info', queued: 'info', running: 'warning', completed: 'success', failed: 'danger', skipped: 'success' } as Record<string, string>)[status] || 'info'
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

function safeJsonObject(value: unknown): Record<string, any> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, any>
  if (typeof value !== 'string' || !value.trim()) return null
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
  } catch {
    return null
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

function evidenceRefsForVersion(version: any): any[] {
  return safeJsonArray(version?.image_refs_json || version?.image_refs)
}

function evidenceKindLabel(image: any) {
  const kind = String(image?.asset_kind || image?.figure_role || '')
  if (kind === 'table') return '表格'
  if (kind === 'chart') return '图表'
  return '图片'
}

function evidenceConfidenceLabel(image: any) {
  const confidence = Number(image?.confidence)
  return Number.isFinite(confidence) && confidence > 0 ? `${Math.round(confidence * 100)}%` : '未评分'
}

function visualSourceLabel(sourceKind: string) {
  const kind = String(sourceKind || '')
  if (kind === 'pdf_figure_crop') return 'PDF 重渲染截图'
  if (kind === 'layout_block') return '版面块'
  if (kind === 'source_figure') return '论文原图'
  if (kind === 'cover_fallback') return '封面兜底'
  return kind || '未知来源'
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

function layoutBlockText(block: any) {
  const metadata = safeJsonObject(block?.metadata) || {}
  return String(metadata.caption || block?.text || block?.asset_path || block?.evidence_kind || '无文本内容').slice(0, 220)
}

function qualityScore(block: any) {
  const metadata = safeJsonObject(block?.metadata) || {}
  const score = Number(metadata.quality_score)
  return Number.isFinite(score) ? score : 0
}

function qualityLabel(block: any) {
  const score = qualityScore(block)
  if (score <= 0) return '未评分'
  return `${Math.round(score * 100)}%`
}

function qualityClass(block: any) {
  return qualityScore(block) >= 0.72 ? 'quality-good' : 'quality-low'
}

function qualityReasons(block: any) {
  const metadata = safeJsonObject(block?.metadata) || {}
  const reasons = Array.isArray(metadata.quality_reasons) ? metadata.quality_reasons : []
  return reasons.slice(0, 4).join(' · ')
}

function generationMetric(key: 'cache_hits' | 'llm_calls') {
  const value = generationMeta.value[key]
  return value !== null && value !== undefined && Number.isFinite(Number(value)) ? Number(value) : '未记录'
}

function isPaperBlogJobFor(job: any, paperKey: string) {
  if (!job || !['paper_blog_generate', 'paper_blog_publish'].includes(job.job_type)) return false
  const params = safeJsonObject(job.params) || safeJsonObject(job.params_json) || {}
  return String(params.paperKey || params.paper_key || '') === paperKey
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => reject(new Error(message)), timeoutMs)
    promise.then(
      (value) => { window.clearTimeout(timeout); resolve(value) },
      (error) => { window.clearTimeout(timeout); reject(error) }
    )
  })
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}
</script>
