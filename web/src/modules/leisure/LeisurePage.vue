<template>
  <main class="leisure-workbench">
    <header class="leisure-topbar">
      <button class="leisure-brand" type="button" @click="router.push('/')">
        <span class="leisure-brand-mark">牛</span>
        <span>
          <strong>牛秘书闲趣集</strong>
          <small>Leisure Collection</small>
        </span>
      </button>
      <div class="leisure-topbar-actions">
        <el-button :icon="Refresh" :loading="loading" @click="refreshRecommendations">刷新推荐</el-button>
        <el-button type="primary" :icon="HomeFilled" @click="router.push('/')">返回主页</el-button>
      </div>
    </header>

    <el-alert v-if="error" :title="error" type="error" show-icon class="section-gap" />

    <section class="leisure-hero section-gap">
      <div>
        <p class="leisure-kicker">{{ recommendation.personalized ? '个性化推荐' : '通用推荐' }}</p>
        <h1>闲趣集</h1>
        <p class="leisure-lead">按时间和心情精选，今晚看什么、听什么、读什么。</p>
      </div>
      <aside class="leisure-taste-card">
        <h2>口味档案</h2>
        <div class="taste-meter"><span /></div>
        <div class="taste-tags">
          <span v-for="tag in profileTags" :key="tag">{{ tag }}</span>
          <span v-if="!profileTags.length">去主页和牛秘书 AI 聊聊</span>
        </div>
      </aside>
    </section>

    <nav class="leisure-nav" aria-label="闲趣分类">
      <button
        v-for="item in categoryNav"
        :key="item.value"
        type="button"
        :class="{ active: categoryFilter === item.value }"
        @click="categoryFilter = item.value"
      >
        <span>{{ item.short }}</span>{{ item.label }}
      </button>
    </nav>

    <el-tabs v-model="activeTab" class="section-gap">
      <el-tab-pane label="推荐" name="recommend">
        <div class="leisure-filter-line">
          <div>
            <h2>今晚首推</h2>
            <p>{{ recommendation.message || '今日闲趣候选已准备好，所有反馈都写入后端画像。' }}</p>
          </div>
          <div class="leisure-filter-tools">
            <el-input
              v-model="searchTerm"
              class="leisure-search"
              clearable
              :prefix-icon="Search"
              placeholder="搜索片名、音乐、播客、小说"
            />
            <el-segmented v-model="categoryFilter" :options="categoryOptions" />
          </div>
        </div>

        <section class="recommend-workbench">
          <article class="leisure-panel featured-panel">
            <div v-if="featuredItem" class="featured-choice">
              <button
                class="poster"
                :class="{ 'has-cover': Boolean(coverUrl(featuredItem)) }"
                type="button"
                @click="openDetail(featuredItem)"
              >
                <img
                  v-if="coverUrl(featuredItem)"
                  :src="coverUrl(featuredItem)"
                  :alt="featuredItem.title"
                  loading="lazy"
                  @error="hideBrokenImage"
                />
                <span>{{ categoryShort(featuredItem.category) }}</span>
              </button>
              <div class="feature-copy">
                <div class="leisure-card-head">
                  <el-tag :type="categoryType(featuredItem.category)" effect="dark">
                    {{ categoryLabel(featuredItem.category) }}
                  </el-tag>
                  <span>{{ featuredItem.duration || durationFallback(featuredItem) }}</span>
                </div>
                <h3>{{ featuredItem.title }}</h3>
                <div class="genre-line">
                  <span v-for="genre in featuredItem.genres || []" :key="genre">{{ genre }}</span>
                </div>
                <p>{{ featuredItem.reason || '适合今天的空档，点开详情后再决定是否收藏。' }}</p>
                <div class="feature-meta">
                  <span v-if="featuredItem.matchScore" class="score">匹配度 {{ featuredItem.matchScore }}</span>
                  <span v-if="feedbackState(featuredItem)" :class="['feedback-chip', feedbackState(featuredItem)?.className]">
                    {{ feedbackState(featuredItem)?.label }}
                  </span>
                </div>
                <div class="leisure-actions">
                  <el-button @click="openDetail(featuredItem)">查看详情</el-button>
                  <el-button
                    type="primary"
                    :loading="pendingId === actionKey(featuredItem, 'save')"
                    @click="save(featuredItem)"
                  >
                    收藏
                  </el-button>
                  <el-button
                    type="info"
                    :loading="pendingId === actionKey(featuredItem, 'dismiss')"
                    @click="dismiss(featuredItem)"
                  >
                    忽略
                  </el-button>
                </div>
              </div>
            </div>
            <div v-else class="feature-empty">
              <strong>暂无推荐</strong>
              <span>刷新后仍为空时，先到主页补充偏好或稍后再试。</span>
            </div>
          </article>

          <aside class="leisure-panel">
            <div class="candidate-head">
              <h2>今日候选</h2>
              <span>{{ candidateItems.length }} 条</span>
            </div>
            <div class="candidate-list">
              <button
                v-for="card in candidateItems"
                :key="`${card.category}-${card.id}`"
                class="candidate"
                :class="feedbackState(card)?.className"
                type="button"
                @click="openDetail(card)"
              >
                <span class="candidate-icon">{{ categoryShort(card.category) }}</span>
                <span>
                  <b>{{ card.title }}</b>
                  <small>{{ card.reason || '适合今天的空档。' }}</small>
                </span>
                <span class="candidate-side">
                  <span v-if="feedbackState(card)" :class="['candidate-status', feedbackState(card)?.className]">
                    {{ feedbackState(card)?.label }}
                  </span>
                  <span class="time-pill">{{ card.duration || durationFallback(card) }}</span>
                </span>
              </button>
            </div>
          </aside>
        </section>

        <section class="leisure-note">
          <div>
            <p class="note-label">闲趣批注</p>
            <p><strong>{{ recommendation.message || '结合日程负载和恢复状态自动调整推荐。' }}</strong></p>
            <small>当前页面不会跳转到缺失的中文静态页；详情、收藏、忽略和评分都在 Vue 工作台内完成。</small>
          </div>
          <div class="note-actions">
            <el-button :loading="loading" @click="refreshRecommendations">刷新推荐</el-button>
          </div>
        </section>

        <section v-if="lastFeedback" class="leisure-feedback-strip" aria-live="polite">
          <span>{{ lastFeedback.action }}</span>
          <strong>{{ lastFeedback.title }}</strong>
          <small>已写入后端画像，推荐池会随反馈更新。</small>
        </section>

        <section class="leisure-panel profile-review-panel" aria-label="画像建议">
          <div class="profile-review-head">
            <h2>画像建议</h2>
            <span>{{ profileSuggestions.length }}</span>
          </div>
          <div v-if="profileSuggestions.length" class="profile-suggestion-list">
            <article v-for="suggestion in profileSuggestions" :key="suggestion.id" class="suggestion-item">
              <div>
                <b>{{ suggestionTitle(suggestion) }}</b>
                <small>{{ suggestionPatchSummary(suggestion) }}</small>
              </div>
              <el-button
                class="suggestion-apply-button"
                :loading="applyingSuggestionId === suggestion.id"
                @click="applySuggestion(suggestion.id)"
              >
                应用
              </el-button>
            </article>
          </div>
          <p v-else class="suggestion-empty">暂无待处理建议。收藏、忽略或评分后，牛秘书会把可用偏好沉淀到这里。</p>
        </section>

        <div class="leisure-card-grid">
          <article
            v-for="card in secondaryItems"
            :key="`${card.category}-${card.id}`"
            class="leisure-card"
            :class="feedbackState(card)?.className"
          >
            <div class="leisure-card-head">
              <el-tag :type="categoryType(card.category)" effect="dark">{{ categoryLabel(card.category) }}</el-tag>
              <span>{{ card.duration || durationFallback(card) }}</span>
            </div>
            <h3>{{ card.title }}</h3>
            <p>{{ card.reason || '适合今天的空档，点开详情后再决定是否收藏。' }}</p>
            <div class="genre-line">
              <span v-for="genre in card.genres || []" :key="genre">{{ genre }}</span>
            </div>
            <div v-if="feedbackState(card)" :class="['feedback-chip', feedbackState(card)?.className]">
              {{ feedbackState(card)?.label }}
            </div>
            <div class="leisure-actions">
              <el-button @click="openDetail(card)">详情</el-button>
              <el-button type="primary" :loading="pendingId === actionKey(card, 'save')" @click="save(card)">收藏</el-button>
              <el-button type="info" :loading="pendingId === actionKey(card, 'dismiss')" @click="dismiss(card)">忽略</el-button>
            </div>
          </article>
        </div>
        <el-empty v-if="!visibleRecommendations.length && !loading" description="暂无推荐" />
      </el-tab-pane>

      <el-tab-pane label="已存条目" name="saved">
        <el-table :data="savedItems" stripe>
          <el-table-column prop="title" label="标题" show-overflow-tooltip />
          <el-table-column prop="category" label="分类" width="110">
            <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="140" show-overflow-tooltip />
          <el-table-column prop="updatedAt" label="更新" width="180" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" @click="openDetail(normalizeSaved(row))">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="互动历史" name="history">
        <el-table :data="history" stripe>
          <el-table-column prop="title" label="标题" show-overflow-tooltip />
          <el-table-column prop="interaction" label="动作" width="100">
            <template #default="{ row }">{{ interactionLabel(row.interaction) }}</template>
          </el-table-column>
          <el-table-column prop="rating" label="评分" width="120">
            <template #default="{ row }">
              <el-rate v-if="row.rating" :model-value="row.rating" disabled size="small" />
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="时间" width="180" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <div
      v-if="detailVisible"
      class="leisure-detail-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="selectedItem?.title || '闲趣详情'"
      @click.self="closeDetail"
    >
      <section v-if="selectedItem" class="leisure-detail-sheet">
        <div class="detail-shell-grid">
          <aside class="detail-media" :class="{ 'has-cover': Boolean(coverUrl(selectedItem)) }">
            <img
              v-if="coverUrl(selectedItem)"
              :src="coverUrl(selectedItem)"
              :alt="selectedItem.title"
              loading="lazy"
              @error="hideBrokenImage"
            />
            <div v-else class="detail-media-fallback">{{ categoryShort(selectedCategory) }}</div>
            <span>{{ categoryLabel(selectedCategory) }}</span>
          </aside>

          <div class="detail-copy">
            <div class="detail-topline">
              <p class="leisure-kicker">
                {{ categoryLabel(selectedCategory) }} · {{ selectedItem.duration || durationFallback(selectedItem) }}
              </p>
              <div class="detail-controls">
                <button class="detail-icon-button" type="button" aria-label="最小化详情" @click="minimizeDetail">−</button>
                <button class="detail-icon-button detail-close" type="button" aria-label="关闭详情" @click="closeDetail">×</button>
              </div>
            </div>
            <h2>{{ selectedItem.title }}</h2>
            <p class="detail-reason">{{ selectedItem.reason || '暂无推荐说明。' }}</p>
            <div class="detail-grid">
              <div v-for="row in detailRows" :key="row.label">
                <span>{{ row.label }}</span>
                <strong>{{ row.value }}</strong>
              </div>
            </div>
            <div class="genre-line">
              <span v-for="genre in selectedItem.genres || []" :key="genre">{{ genre }}</span>
            </div>
            <el-form label-position="top" class="rating-form">
              <el-form-item label="评分">
                <el-rate v-model="ratingValue" />
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="feedbackNote" type="textarea" :rows="3" placeholder="记录为什么喜欢或不喜欢" />
              </el-form-item>
            </el-form>
            <div class="detail-actions">
              <el-button v-if="detailSourceUrl" @click="openExternal(detailSourceUrl)">打开来源</el-button>
              <el-button @click="minimizeDetail">稍后再看</el-button>
              <el-button :loading="pendingId === actionKey(selectedItem, 'rate')" type="primary" @click="rateSelected">
                提交评分
              </el-button>
              <el-button :loading="pendingId === actionKey(selectedItem, 'save')" @click="save(selectedItem)">收藏</el-button>
              <el-button :loading="pendingId === actionKey(selectedItem, 'dismiss')" type="info" @click="dismiss(selectedItem)">
                忽略
              </el-button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <button v-if="detailMinimized && selectedItem" class="leisure-detail-dock" type="button" @click="restoreDetail">
      <span>继续查看</span>
      <strong>{{ selectedItem.title }}</strong>
      <small>{{ categoryLabel(selectedCategory) }} · 点击展开详情</small>
    </button>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStorage } from '@vueuse/core'
import { ElMessage } from 'element-plus'
import { HomeFilled, Refresh, Search } from '@element-plus/icons-vue'
import {
  applyLeisureProfileSuggestion,
  dismissLeisureItem,
  fetchLeisureSnapshot,
  rateLeisureItem,
  saveLeisureItem,
  type LeisureCategory,
  type LeisureGroup,
  type LeisureHistoryItem,
  type LeisureItem,
  type LeisureProfileSuggestion,
  type LeisureRecommendationResponse
} from './api'

type CategoryFilter = LeisureCategory | 'all'
type ActionName = 'save' | 'dismiss' | 'rate'

const router = useRouter()
const activeTab = useStorage('niu-vue-leisure-active-tab', 'recommend')
const categoryFilter = ref<CategoryFilter>('all')
const loading = ref(false)
const error = ref('')
const pendingId = ref('')
const recommendation = ref<LeisureRecommendationResponse>({ groups: [], count: 0 })
const savedItems = ref<LeisureItem[]>([])
const history = ref<LeisureHistoryItem[]>([])
const profileSuggestions = ref<LeisureProfileSuggestion[]>([])
const profile = ref<Record<string, any>>({})
const detailVisible = ref(false)
const selectedItem = ref<LeisureItem | null>(null)
const selectedCategory = ref<LeisureCategory>('movie')
const ratingValue = ref(4)
const feedbackNote = ref('')
const applyingSuggestionId = ref('')
const searchTerm = ref('')
const detailMinimized = ref(false)
const lastFeedback = ref<{ action: string; title: string; at: number } | null>(null)
const localFeedbackStates = ref<Record<string, { label: string; className: string }>>({})

const categoryOptions = [
  { label: '全部', value: 'all' },
  { label: '影视', value: 'movie' },
  { label: '音乐', value: 'music' },
  { label: '播客', value: 'podcast' },
  { label: '小说', value: 'novel' }
]
const categoryNav = [
  { label: '首页', short: '首', value: 'all' },
  { label: '影视', short: '影', value: 'movie' },
  { label: '音乐', short: '乐', value: 'music' },
  { label: '播客', short: '播', value: 'podcast' },
  { label: '小说', short: '书', value: 'novel' }
] as Array<{ label: string; short: string; value: CategoryFilter }>

const recommendationItems = computed(() =>
  (recommendation.value.groups || []).flatMap((group: LeisureGroup) =>
    (group.items || []).map((item) => ({ ...item, category: group.category }))
  )
)
const visibleRecommendations = computed(() => {
  const filteredByCategory =
    categoryFilter.value === 'all'
      ? recommendationItems.value
      : recommendationItems.value.filter((item) => item.category === categoryFilter.value)
  const keyword = searchTerm.value.trim().toLowerCase()
  if (!keyword) return filteredByCategory
  return filteredByCategory.filter((item) => searchableText(item).includes(keyword))
})
const featuredItem = computed(() => visibleRecommendations.value[0] || null)
const candidateItems = computed(() => visibleRecommendations.value.slice(1, 5))
const secondaryItems = computed(() => visibleRecommendations.value.slice(5))
const profileTags = computed(() => {
  const tags: string[] = []
  const genres = profile.value.genres || {}
  for (const key of ['movie', 'music', 'podcast', 'novel']) {
    if (Array.isArray(genres[key])) tags.push(...genres[key])
  }
  if (Array.isArray(profile.value.moods)) tags.push(...profile.value.moods)
  return Array.from(new Set(tags.filter(Boolean))).slice(0, 10)
})
const detailSourceUrl = computed(() => (selectedItem.value ? sourceUrl(selectedItem.value) : ''))
const detailRows = computed(() => {
  if (!selectedItem.value) return []
  const item = selectedItem.value
  return [
    { label: '分类', value: categoryLabel(selectedCategory.value) },
    { label: '时长', value: item.duration || durationFallback(item) },
    { label: '心情', value: item.mood || '未标注' },
    { label: '来源', value: item.source || item.region || '牛秘书推荐池' },
    { label: '年份', value: item.year ? String(item.year) : '未标注' },
    { label: '匹配度', value: item.matchScore ? String(item.matchScore) : item.score ? String(item.score) : '动态计算' }
  ]
})

load()

async function load(showMessage = false) {
  loading.value = true
  error.value = ''
  try {
    const snapshot = await fetchLeisureSnapshot()
    recommendation.value = snapshot.recommendation
    savedItems.value = snapshot.savedItems
    history.value = snapshot.history
    profileSuggestions.value = snapshot.profileSuggestions
    profile.value = snapshot.profile
    if (showMessage) {
      ElMessage({ message: '推荐已刷新', type: 'success', duration: 2200, customClass: 'leisure-message' })
    }
  } catch (err: any) {
    error.value = err.message || '闲趣集读取失败'
  } finally {
    loading.value = false
  }
}

function openDetail(item: LeisureItem) {
  selectedItem.value = item
  selectedCategory.value = (item.category || 'movie') as LeisureCategory
  ratingValue.value = 4
  feedbackNote.value = ''
  detailMinimized.value = false
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  detailMinimized.value = false
}

function minimizeDetail() {
  detailVisible.value = false
  detailMinimized.value = Boolean(selectedItem.value)
}

function restoreDetail() {
  if (!selectedItem.value) return
  detailMinimized.value = false
  detailVisible.value = true
}

async function refreshRecommendations() {
  await load(true)
}

async function save(item: LeisureItem) {
  await runFeedback(item, 'save', () => saveLeisureItem(item, item.category || 'movie'))
}

async function dismiss(item: LeisureItem) {
  await runFeedback(item, 'dismiss', () => dismissLeisureItem(item, item.category || 'movie'))
}

async function rateSelected() {
  if (!selectedItem.value) return
  await runFeedback(selectedItem.value, 'rate', () =>
    rateLeisureItem(selectedItem.value as LeisureItem, selectedCategory.value, ratingValue.value, feedbackNote.value)
  )
  detailVisible.value = false
  detailMinimized.value = false
}

async function runFeedback(item: LeisureItem, action: ActionName, task: () => Promise<unknown>) {
  pendingId.value = actionKey(item, action)
  try {
    await task()
    const message = action === 'save' ? '已收藏' : action === 'dismiss' ? '已忽略' : '评分已提交'
    localFeedbackStates.value = { ...localFeedbackStates.value, [itemIdentity(item)]: feedbackStateForAction(action) }
    lastFeedback.value = { action: message, title: item.title, at: Date.now() }
    ElMessage({ message, type: 'success', duration: 2600, customClass: 'leisure-message' })
    await load()
  } catch (err: any) {
    ElMessage({ message: err.message || '反馈写入失败', type: 'error', duration: 3200, customClass: 'leisure-message' })
  } finally {
    pendingId.value = ''
  }
}

async function applySuggestion(eventId: string) {
  applyingSuggestionId.value = eventId
  try {
    await applyLeisureProfileSuggestion(eventId)
    ElMessage({ message: '画像建议已应用', type: 'success', duration: 2600, customClass: 'leisure-message' })
    await load()
  } catch (err: any) {
    ElMessage({ message: err.message || '应用画像建议失败', type: 'error', duration: 3200, customClass: 'leisure-message' })
  } finally {
    applyingSuggestionId.value = ''
  }
}

function normalizeSaved(row: LeisureItem): LeisureItem {
  return {
    ...(row.payload || {}),
    ...row,
    id: row.itemId || row.id,
    category: row.category || ((row.payload || {}).category as LeisureCategory)
  }
}

function actionKey(item: LeisureItem, action: ActionName) {
  return `${action}:${item.id || item.itemId || item.title}`
}

function itemIdentity(item: LeisureItem) {
  return item.id || item.itemId || `${item.category || 'movie'}:${item.title}`
}

function feedbackState(item: LeisureItem) {
  const identity = itemIdentity(item)
  const localState = localFeedbackStates.value[identity]
  if (localState) return localState
  const latest = history.value.find((entry) => entry.itemId === identity || entry.title === item.title)
  if (latest?.interaction === 'dismiss') return { label: '已忽略', className: 'is-dismissed' }
  if (latest?.interaction === 'rate') return { label: '已评分', className: 'is-rated' }
  if (latest?.interaction === 'save') return { label: '已收藏', className: 'is-saved' }
  if (savedItems.value.some((saved) => itemIdentity(normalizeSaved(saved)) === identity || saved.title === item.title)) {
    return { label: '已收藏', className: 'is-saved' }
  }
  return null
}

function feedbackStateForAction(action: ActionName) {
  if (action === 'dismiss') return { label: '已忽略', className: 'is-dismissed' }
  if (action === 'rate') return { label: '已评分', className: 'is-rated' }
  return { label: '已收藏', className: 'is-saved' }
}

function searchableText(item: LeisureItem) {
  return [
    item.title,
    item.reason,
    item.mood,
    item.source,
    item.region,
    item.director,
    item.actors,
    item.album,
    item.author,
    ...(item.genres || [])
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

function payloadString(item: LeisureItem, keys: string[]) {
  const payload = item.payload || {}
  for (const key of keys) {
    const value = payload[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function coverUrl(item: LeisureItem | null) {
  if (!item) return ''
  return (
    item.posterUrl ||
    item.coverUrl ||
    item.imageUrl ||
    item.thumbnailUrl ||
    payloadString(item, ['posterUrl', 'coverUrl', 'imageUrl', 'thumbnailUrl', 'poster', 'cover'])
  )
}

function sourceUrl(item: LeisureItem) {
  return item.url || item.externalUrl || item.doubanUrl || payloadString(item, ['url', 'externalUrl', 'doubanUrl', 'sourceUrl'])
}

function hideBrokenImage(event: Event) {
  const image = event.target as HTMLImageElement
  image.style.display = 'none'
}

function categoryLabel(category?: string) {
  return { movie: '影视', music: '音乐', podcast: '播客', novel: '小说' }[category || ''] || '闲趣'
}

function categoryShort(category?: string) {
  return { movie: '影', music: '乐', podcast: '播', novel: '书' }[category || ''] || '闲'
}

function categoryType(category?: string) {
  return category === 'movie' ? 'success' : category === 'music' ? 'warning' : category === 'podcast' ? 'info' : 'primary'
}

function durationFallback(item: LeisureItem) {
  return item.durationMinutes ? `${item.durationMinutes} 分钟` : '弹性时长'
}

function suggestionTitle(suggestion: LeisureProfileSuggestion) {
  return suggestion.payload?.item?.title || suggestion.title || '闲趣偏好建议'
}

function suggestionPatchSummary(suggestion: LeisureProfileSuggestion) {
  const patch = suggestion.payload?.patch || {}
  const parts: string[] = []
  const genres = (patch as any).genres || {}
  for (const key of ['movie', 'music', 'podcast', 'novel']) {
    const values = Array.isArray(genres[key]) ? genres[key].filter(Boolean) : []
    if (values.length) parts.push(`${categoryLabel(key)}：${values.slice(0, 4).join('、')}`)
  }
  const moods = Array.isArray((patch as any).moods) ? (patch as any).moods.filter(Boolean) : []
  const avoid = Array.isArray((patch as any).avoid) ? (patch as any).avoid.filter(Boolean) : []
  if (moods.length) parts.push(`心情：${moods.slice(0, 4).join('、')}`)
  if (avoid.length) parts.push(`避开：${avoid.slice(0, 3).join('、')}`)
  return parts.join(' · ') || '画像暂无新增字段'
}

function interactionLabel(interaction: string) {
  return { save: '收藏', dismiss: '忽略', rate: '评分' }[interaction] || interaction
}

function openExternal(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>
