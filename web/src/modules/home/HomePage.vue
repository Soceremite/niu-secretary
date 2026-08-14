<template>
  <main class="home-shell home-brand-shell">
    <header class="home-topbar">
      <div class="home-topbar-inner">
        <router-link class="home-brand-mark" to="/" aria-label="牛秘书主页">
          <img :src="logoSrc" alt="牛秘书" @error="hideBrokenLogo" />
          <span>
            <strong>牛秘书</strong>
            <small>Private AI Steward</small>
          </span>
        </router-link>
        <nav class="home-nav">
          <router-link to="/fitness/">塑形馆</router-link>
          <router-link to="/schedule/">时务局</router-link>
          <router-link to="/leisure/">闲趣集</router-link>
          <router-link to="/news/">新闻社</router-link>
          <a href="/niu-secretary/airesearch/">研知库</a>
          <router-link class="admin-link" to="/admin/">管理台</router-link>
        </nav>
      </div>
    </header>

    <section class="home-hero">
      <div class="hero-grid">
        <div class="hero-copy">
          <p class="eyebrow">Niu Secretary Platform</p>
          <h1>牛秘书<span>你私人 AI 管家</span></h1>
          <p class="hero-lead">把新闻、健身、日程、闲趣和研知库放进同一个行动台。你说一句话，牛秘书先识别、再让你确认，最后写入对应模块。</p>
          <div class="hero-actions">
            <a class="home-button primary" href="#home-assistant">开始识别一句话</a>
            <router-link class="home-button" to="/fitness/">进入塑形馆</router-link>
            <a class="home-button subtle" href="#platform-overview">查看平台状态</a>
          </div>
          <div class="home-promise-grid">
            <article>
              <b>先审阅</b>
              <span>AI 只生成待执行动作，所有写入都需要你确认。</span>
            </article>
            <article>
              <b>走后端</b>
              <span>模块写入统一经过 Action Protocol 和审计记录。</span>
            </article>
            <article>
              <b>可回溯</b>
              <span>主页直接读取今日上下文和运行中心状态。</span>
            </article>
          </div>
        </div>

        <section
          id="home-assistant"
          class="assistant-panel home-assistant-panel"
          aria-label="牛秘书 AI 助手"
          :aria-busy="loading || executing"
        >
          <div class="assistant-panel-inner">
            <div class="assistant-head">
              <div>
                <h2>牛秘书 AI</h2>
                <p>输入自然语言，审阅后写入对应模块。</p>
              </div>
              <el-tag effect="plain">Action Protocol</el-tag>
            </div>

            <div class="assistant-scope-strip" aria-label="可识别模块">
              <span>营养日志</span>
              <span>日程待办</span>
              <span>闲趣反馈</span>
              <span>研知队列</span>
            </div>

            <div class="assistant-messages" aria-live="polite">
              <p class="assistant-message assistant">可以直接说：“我今天中午吃了牛肉面和瑞幸的橙 C 美式”。我会先生成动作卡片，不会自动写入。</p>
              <p v-if="lastPrompt" class="assistant-message user">{{ lastPrompt }}</p>
              <p v-if="message" class="assistant-message assistant">{{ message }}</p>
              <p v-if="assistantError" class="assistant-message assistant error">{{ assistantError }}</p>
            </div>

            <div v-if="loading" class="ai-progress" aria-label="AI 处理进度">
              <span class="ai-progress-dot"></span>
              <span class="ai-progress-steps">
                <span class="ai-progress-step done">理解意图</span>
                <span class="ai-progress-arrow">→</span>
                <span class="ai-progress-step current">分析板块</span>
                <span class="ai-progress-arrow">→</span>
                <span class="ai-progress-step">生成动作</span>
                <span class="ai-progress-arrow">→</span>
                <span class="ai-progress-step">等待确认</span>
              </span>
              <span class="ai-spinner"></span>
            </div>

            <div v-if="reviewItems.length" class="review-summary">
              <el-tag type="info">{{ reviewItems.length }} 个动作</el-tag>
              <el-tag v-if="pendingCount" type="warning">{{ pendingCount }} 待执行</el-tag>
              <el-tag v-if="successfulCount" type="success">{{ successfulCount }} 已完成</el-tag>
              <el-tag v-if="failedCount" type="danger">{{ failedCount }} 失败</el-tag>
            </div>

            <div v-if="reviewItems.length" class="action-list">
              <article
                v-for="(item, index) in reviewItems"
                :key="item.id"
                class="action-card"
                :data-action-key="actionIdentity(item)"
              >
                <div class="action-card-head">
                  <div>
                    <strong>{{ item.title || actionTitle(item.action) || `动作 ${index + 1}` }}</strong>
                    <code>{{ item.action }}</code>
                  </div>
                  <el-tag :type="actionStatusType(item.status)">{{ actionStatusLabel(item.status) }}</el-tag>
                </div>
                <dl class="action-fields">
                  <template v-for="field in actionFieldRows(item.input)" :key="field.key">
                    <dt>{{ field.key }}</dt>
                    <dd>{{ field.value }}</dd>
                  </template>
                </dl>
                <el-alert
                  v-if="item.errorMessage"
                  :title="item.errorMessage"
                  type="error"
                  show-icon
                  :closable="false"
                />
                <p v-else-if="item.statusMessage" class="action-status-note">{{ item.statusMessage }}</p>
                <div class="action-card-actions">
                  <el-button
                    size="small"
                    type="primary"
                    :icon="item.status === 'error' ? RefreshRight : Check"
                    :loading="item.status === 'running'"
                    :disabled="item.status === 'success' || executing"
                    @click="executeOne(item)"
                  >
                    {{ item.status === 'error' ? '重试写入' : '确认写入' }}
                  </el-button>
                  <el-button size="small" :icon="Close" :disabled="item.status === 'running'" @click="removeReviewItem(item.id)">
                    移除
                  </el-button>
                </div>
              </article>
            </div>

            <div
              v-if="assistantFeedback"
              :class="['assistant-feedback', assistantFeedback.type]"
              :role="assistantFeedback.type === 'error' ? 'alert' : 'status'"
              aria-live="polite"
            >
              <strong>{{ assistantFeedback.title }}</strong>
              <span>{{ assistantFeedback.detail }}</span>
            </div>

            <form class="assistant-composer" @submit.prevent="submitPrompt">
              <el-input
                v-model="prompt"
                resize="none"
                placeholder="例如：我今天中午吃了牛肉面和瑞幸的橙 C 美式"
                aria-label="给牛秘书 AI 发送消息"
                :disabled="loading"
              />
              <el-button native-type="submit" type="primary" :loading="loading" :disabled="!prompt.trim() || loading">
                识别意图
              </el-button>
            </form>

            <div class="assistant-actions">
              <el-button :disabled="!runnableCount || executing" :loading="executing" type="primary" plain @click="executeAll">
                确认全部执行
              </el-button>
              <el-button :disabled="!reviewItems.length || executing" @click="clearReview">清空审阅</el-button>
            </div>
          </div>
        </section>
      </div>
    </section>

    <section class="home-section" aria-labelledby="module-title">
      <div class="section-head">
        <h2 id="module-title">五个板块</h2>
        <p>保留原来的入口关系和模块气质，Vue 只负责把它们统一成同一个可维护前端。</p>
      </div>
      <div class="module-grid home-service-grid">
        <component
          :is="item.external ? 'a' : 'router-link'"
          v-for="item in modules"
          :key="item.path"
          class="module-card home-service-card"
          :class="item.key"
          :data-module="item.key"
          v-bind="item.external ? { href: item.path } : { to: item.path }"
        >
          <div class="module-card-top">
            <span>{{ item.badge }}</span>
            <i class="module-card-icon" aria-hidden="true">{{ item.icon }}</i>
          </div>
          <div class="module-card-main">
            <h2>{{ item.title }}</h2>
            <p>{{ item.description }}</p>
            <div class="feature-list">
              <em v-for="feature in item.features" :key="feature">{{ feature }}</em>
            </div>
          </div>
          <strong class="module-card-cta">打开模块 <span aria-hidden="true">→</span></strong>
        </component>
      </div>
    </section>

    <section id="platform-overview" class="home-section platform-overview" aria-labelledby="platform-title">
      <div class="section-head">
        <h2 id="platform-title">平台运行</h2>
        <p>这里读取真实后端：今日上下文、模块状态、最近运行和助手动作，方便发现跨模块链路是否正常。</p>
      </div>
      <div :class="['platform-state-bar', { error: platformError, loading: platformLoading }]" role="status" aria-live="polite">
        <span class="platform-state-dot" aria-hidden="true"></span>
        <div>
          <strong>{{ platformStateTitle }}</strong>
          <small>{{ platformStateDetail }}</small>
        </div>
        <el-button v-if="platformError" size="small" :loading="platformLoading" @click="loadPlatform">重新连接</el-button>
      </div>
      <div class="platform-grid">
        <section class="platform-panel today-panel">
          <div class="platform-panel-inner">
            <div class="platform-panel-header">
              <h3>今日上下文</h3>
              <el-button size="small" :loading="platformLoading" @click="loadPlatform">刷新</el-button>
            </div>
            <el-skeleton v-if="platformLoading && !todayContext" animated :rows="4" class="home-platform-skeleton" />
            <div v-else class="today-facts">
              <article v-for="fact in todayFacts" :key="fact.label" class="today-fact">
                <b>{{ fact.value }}</b>
                <span>{{ fact.label }}</span>
              </article>
            </div>
            <div class="audit-row">
              <div class="audit-row-top">
                <b>当前推荐</b>
                <span>{{ todayContext?.date || todayDate }}</span>
              </div>
              <span>{{ contextHeadline }}</span>
            </div>
          </div>
        </section>

        <section class="platform-panel">
          <div class="platform-panel-inner">
            <div class="platform-panel-header">
              <h3>模块状态</h3>
              <el-tag>{{ moduleStatuses.length || 0 }} 模块</el-tag>
            </div>
            <div class="module-status-grid">
              <article v-for="item in moduleStatuses.slice(0, 6)" :key="item.module" class="module-status">
                <div class="module-status-top">
                  <b>{{ moduleLabel(item.module) }}</b>
                  <span class="module-pill">{{ item.status || 'unknown' }}</span>
                </div>
                <span>{{ item.capabilityCount || 0 }} 个 Action 能力</span>
              </article>
            </div>
            <div v-if="!moduleStatuses.length && !platformLoading" class="platform-empty">暂未读取到模块状态。</div>
          </div>
        </section>

        <section class="platform-panel ops-panel">
          <div class="platform-panel-inner">
            <div class="platform-panel-header">
              <h3>Ops Center</h3>
              <el-tag effect="plain">审计摘要</el-tag>
            </div>
            <div class="ops-metrics">
              <article v-for="metric in opsMetrics" :key="metric.label" class="ops-metric">
                <b>{{ metric.value }}</b>
                <span>{{ metric.label }}</span>
              </article>
            </div>
            <div class="audit-stack">
              <article v-for="run in recentRuns" :key="run.id" class="audit-row">
                <div class="audit-row-top">
                  <b>{{ moduleLabel(run.module) }} · {{ run.runType || 'run' }}</b>
                  <span>{{ run.status || 'unknown' }}</span>
                </div>
                <span>{{ formatTime(run.finishedAt || run.startedAt) }}</span>
              </article>
              <div v-if="!recentRuns.length" class="platform-empty">暂无最近运行记录。</div>
            </div>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Close, RefreshRight } from '@element-plus/icons-vue'
import { executeAction, getPublicData, sendAssistantMessage, type ProposedAction } from '@/app/api/actions'

type ReviewStatus = 'pending' | 'running' | 'success' | 'error'

interface ReviewAction extends ProposedAction {
  id: string
  status: ReviewStatus
  statusMessage: string
  errorMessage: string
}

interface PlatformTodayContext {
  date: string
  schedule?: { eventCount?: number; todoCount?: number; conflictCount?: number }
  fitness?: { mealCount?: number; calories?: number; proteinG?: number }
  news?: { count?: number; items?: Array<Record<string, any>> }
  leisure?: { count?: number; groups?: Array<Record<string, any>> }
}

interface PlatformTodayResponse {
  ok: boolean
  context: PlatformTodayContext
}

interface PlatformOpsResponse {
  ok: boolean
  summary?: Record<string, number>
  modules?: Array<Record<string, any>>
  runs?: Array<Record<string, any>>
}

const prompt = ref('')
const lastPrompt = ref('')
const loading = ref(false)
const message = ref('')
const assistantError = ref('')
const deduplicatedCount = ref(0)
const reviewItems = ref<ReviewAction[]>([])
const todayContext = ref<PlatformTodayContext | null>(null)
const platformOps = ref<PlatformOpsResponse | null>(null)
const platformLoading = ref(true)
const platformError = ref('')
const todayDate = new Date().toISOString().slice(0, 10)
const logoSrc = '/niu-secretary/logo.png'

const executing = computed(() => reviewItems.value.some((item) => item.status === 'running'))
const pendingCount = computed(() => reviewItems.value.filter((item) => item.status === 'pending').length)
const successfulCount = computed(() => reviewItems.value.filter((item) => item.status === 'success').length)
const failedCount = computed(() => reviewItems.value.filter((item) => item.status === 'error').length)
const runnableCount = computed(() => reviewItems.value.filter((item) => item.status !== 'success').length)
const assistantFeedback = computed(() => {
  if (assistantError.value) {
    return { type: 'error', title: '识别未完成', detail: assistantError.value }
  }
  if (deduplicatedCount.value) {
    return {
      type: 'info',
      title: '已合并重复动作',
      detail: `合并了 ${deduplicatedCount.value} 个内容相同的写入建议，请确认保留的动作。`
    }
  }
  if (reviewItems.value.length) {
    return { type: 'ready', title: '动作已就绪', detail: `已生成 ${reviewItems.value.length} 个唯一动作，确认后才会写入后端。` }
  }
  return null
})
const platformStateTitle = computed(() => {
  if (platformLoading.value) return '正在同步平台状态'
  if (platformError.value) return '平台状态暂不可用'
  return '平台连接正常'
})
const platformStateDetail = computed(() => {
  if (platformLoading.value) return '正在读取今日上下文和运行中心数据。'
  if (platformError.value) return platformError.value
  return `已读取 ${moduleStatuses.value.length} 个模块和 ${recentRuns.value.length} 条最近运行。`
})

const modules = [
  { key: 'fitness', icon: '塑', title: '塑形馆', badge: 'Fitness', path: '/fitness/', description: '营养、训练、恢复、体征和身体评估。', features: ['营养日志', '训练记录', '身体评估'] },
  { key: 'schedule', icon: '时', title: '时务局', badge: 'Schedule', path: '/schedule/', description: '日程、待办、重要日期和日计划。', features: ['日程', '待办', '日计划'] },
  { key: 'leisure', icon: '闲', title: '闲趣集', badge: 'Leisure', path: '/leisure/', description: '推荐、收藏、忽略、评分和偏好画像。', features: ['影视', '音乐', '播客'] },
  { key: 'news', icon: '新', title: '新闻社', badge: 'News', path: '/news/', description: '今日新闻、搜索归档和完整阅读器。', features: ['今日要闻', '详情阅读', '搜索'] },
  { key: 'airesearch', icon: '研', title: '研知库', badge: 'AIResearch', path: '/niu-secretary/airesearch/', external: true, description: '论文、深度解读和研究报告。', features: ['Papers', 'Blog', 'Research Map'] }
]

const moduleStatuses = computed(() => platformOps.value?.modules || [])
const recentRuns = computed(() => platformOps.value?.runs?.slice(0, 5) || [])
const todayFacts = computed(() => {
  const context = todayContext.value
  return [
    { label: '日程', value: Number(context?.schedule?.eventCount || 0) },
    { label: '待办', value: Number(context?.schedule?.todoCount || 0) },
    { label: '千卡', value: Number(context?.fitness?.calories || 0) },
    { label: '新闻', value: Number(context?.news?.count || 0) }
  ]
})
const opsMetrics = computed(() => {
  const summary = platformOps.value?.summary || {}
  return [
    { label: '最近运行', value: Number(summary.recentRunCount || 0) },
    { label: '最近事件', value: Number(summary.recentEventCount || 0) },
    { label: '待审核', value: Number(summary.pendingReviewCount || 0) },
    { label: '助手动作', value: Number(summary.assistantActionCount || 0) }
  ]
})
const contextHeadline = computed(() => {
  const newsTitle = todayContext.value?.news?.items?.[0]?.title
  if (newsTitle) return String(newsTitle)
  const leisureGroup = todayContext.value?.leisure?.groups?.[0]
  const leisureTitle = leisureGroup?.items?.[0]?.title || leisureGroup?.title
  if (leisureTitle) return String(leisureTitle)
  return '暂无跨模块推荐。'
})

onMounted(loadPlatform)

async function submitPrompt() {
  const text = prompt.value.trim()
  if (!text || loading.value) return
  loading.value = true
  lastPrompt.value = text
  message.value = ''
  assistantError.value = ''
  deduplicatedCount.value = 0
  reviewItems.value = []
  try {
    const response = await sendAssistantMessage(text)
    message.value = response.reply
    const uniqueActions = dedupeProposedActions(response.proposedActions || [])
    deduplicatedCount.value = (response.proposedActions || []).length - uniqueActions.length
    reviewItems.value = uniqueActions.map(createReviewItem)
    prompt.value = ''
    if (!reviewItems.value.length) ElMessage.info('没有需要写入的动作')
  } catch (error: any) {
    assistantError.value = error.message || 'AI 识别失败'
    ElMessage.error(assistantError.value)
  } finally {
    loading.value = false
  }
}

function dedupeProposedActions(actions: ProposedAction[]) {
  const seen = new Set<string>()
  return actions.filter((action) => {
    const key = actionIdentity(action)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function createReviewItem(action: ProposedAction, index: number): ReviewAction {
  return {
    ...action,
    title: action.title || actionTitle(action.action),
    id: `${index}-${action.action}-${stableStringify(action.input || {}).slice(0, 48)}`,
    status: 'pending',
    statusMessage: '',
    errorMessage: ''
  }
}

function actionTitle(action: string) {
  return {
    'fitness.nutrition.create': '写入：塑形馆/营养日志',
    'schedule.event.create': '写入：时务局/日程',
    'schedule.todo.create': '写入：时务局/待办',
    'profile.update': '更新：个人画像'
  }[action] || action
}

function actionStatusLabel(status: ReviewStatus) {
  return {
    pending: '待执行',
    running: '执行中',
    success: '已完成',
    error: '失败'
  }[status]
}

function actionStatusType(status: ReviewStatus) {
  return {
    pending: 'warning',
    running: 'info',
    success: 'success',
    error: 'danger'
  }[status] as 'warning' | 'info' | 'success' | 'danger'
}

async function executeOne(item: ReviewAction, silent = false) {
  item.status = 'running'
  item.statusMessage = ''
  item.errorMessage = ''
  try {
    const result = await executeAction(item.action, item.input, 'vue-home', {
      source: 'vue-home-review',
      reviewItemId: item.id,
      requiresConfirmation: item.requiresConfirmation !== false
    })
    item.status = 'success'
    item.statusMessage = result.message || '执行成功'
    if (!silent) ElMessage.success(item.statusMessage)
    await loadPlatform()
  } catch (error: any) {
    const payloadMessage = error?.payload?.message
    item.status = 'error'
    item.errorMessage = payloadMessage || error.message || '执行失败'
    if (!silent) ElMessage.error(item.errorMessage)
  }
}

async function executeAll() {
  const runnableItems = reviewItems.value.filter((item) => item.status !== 'success')
  for (const item of runnableItems) {
    await executeOne(item, true)
  }
  const failed = runnableItems.filter((item) => item.status === 'error').length
  if (failed) {
    ElMessage.warning(`已完成 ${runnableItems.length - failed} 个动作，${failed} 个失败`)
  } else if (runnableItems.length) {
    ElMessage.success(`已执行 ${runnableItems.length} 个动作`)
  }
}

function removeReviewItem(id: string) {
  reviewItems.value = reviewItems.value.filter((item) => item.id !== id)
}

function clearReview() {
  reviewItems.value = []
  assistantError.value = ''
  message.value = ''
  deduplicatedCount.value = 0
}

async function loadPlatform() {
  platformLoading.value = true
  platformError.value = ''
  try {
    const [today, ops] = await Promise.all([
      getPublicData<PlatformTodayResponse>(`/platform/today?date=${encodeURIComponent(todayDate)}&limit=3`),
      getPublicData<PlatformOpsResponse>('/platform/ops?limit=8')
    ])
    todayContext.value = today.context
    platformOps.value = ops
  } catch (error: any) {
    platformError.value = error.message || '平台状态读取失败'
  } finally {
    platformLoading.value = false
  }
}

function actionFieldRows(input: Record<string, unknown>) {
  return Object.entries(input || {})
    .filter(([key]) => key !== 'source')
    .map(([key, value]) => ({
      key,
      value: typeof value === 'object' ? JSON.stringify(value) : String(value ?? '')
    }))
}

function actionIdentity(action: Pick<ProposedAction, 'action' | 'input'>) {
  return `${action.action}:${stableStringify(action.input || {})}`
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
    return `{${entries.join(',')}}`
  }
  return JSON.stringify(value) ?? 'null'
}

function moduleLabel(module: string) {
  return {
    fitness: '塑形馆',
    schedule: '时务局',
    leisure: '闲趣集',
    news: '新闻社',
    airesearch: '研知库',
    platform: '平台',
    profile: '画像'
  }[module] || module || '模块'
}

function formatTime(value: string) {
  if (!value) return '未记录时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function hideBrokenLogo(event: Event) {
  const target = event.target as HTMLImageElement
  target.style.display = 'none'
}
</script>
