<template>
  <main class="news-workbench">
    <PageHeader
      eyebrow="牛秘书新闻社"
      title="牛秘书新闻社"
      description="头条先行，栏目分明，要事一目了然。"
    >
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      <el-button type="primary" :icon="HomeFilled" @click="$router.push('/')">返回主页</el-button>
    </PageHeader>

    <el-alert v-if="error" :title="error" type="error" show-icon class="section-gap" />

    <section class="news-hero-panel section-gap">
      <div>
        <span class="muted-label">{{ personalized ? '个性化推荐' : '今日要闻' }}</span>
        <h2>{{ message || '今日新闻推荐已加载' }}</h2>
        <p>默认呈现智能推荐，从五版要闻中筛出与你最相关的新闻；也可以按栏目翻阅完整日报。</p>
        <div class="news-edition-strip" aria-label="今日新闻概览">
          <span><strong>{{ recommendations.length }}</strong> 条推荐</span>
          <span><strong>{{ availableSectionCount }}</strong> 个栏目有稿</span>
          <span>{{ personalized ? '已按偏好筛选' : '默认编辑精选' }}</span>
        </div>
      </div>
      <el-form class="news-search" :model="searchForm" @submit.prevent>
        <el-input v-model="searchForm.q" placeholder="搜索关键词，例如 AI、财经、政策" clearable />
        <el-select v-model="searchForm.section" placeholder="栏目" clearable>
          <el-option label="国内" value="domestic" />
          <el-option label="国际" value="international" />
          <el-option label="财经" value="finance" />
          <el-option label="科技" value="tech" />
          <el-option label="AI" value="ai" />
        </el-select>
        <el-button type="primary" :loading="searching" @click="submitSearch">搜索</el-button>
      </el-form>
    </section>

    <nav class="news-section-nav section-gap" aria-label="新闻栏目">
      <button
        v-for="section in sectionNav"
        :key="section.value"
        type="button"
        :class="['news-section-tab', { active: activeSection === section.value }]"
        :data-section="section.value"
        :aria-pressed="activeSection === section.value"
        @click="activeSection = section.value"
      >
        <span class="section-mark">{{ section.mark }}</span>
        <span>
          <strong>{{ section.label }}</strong>
          <small>{{ section.caption }}</small>
        </span>
        <b>{{ sectionCount(section.value) }}</b>
      </button>
    </nav>

    <el-tabs v-model="activeTab" class="section-gap">
      <el-tab-pane label="推荐" name="recommend">
        <div class="news-card-grid">
          <el-card
            v-for="(item, index) in filteredRecommendations"
            :key="item.id || item.title"
            shadow="never"
            :class="['news-card', sectionClass(item), { featured: index === 0 }]"
            role="button"
            tabindex="0"
            @click="openDetail(item)"
            @keydown.enter.prevent="openDetail(item)"
            @keydown.space.prevent="openDetail(item)"
          >
            <template #header>
              <div class="news-card-head">
                <span class="news-section-badge">{{ sectionLabel(item) }}</span>
                <span>{{ item.dateText || item.date || item.sourceName || '今日' }}</span>
              </div>
            </template>
            <figure v-if="cardImage(item)" class="news-card-media">
              <img :src="cardImage(item)" :alt="`${item.title} 配图`" loading="lazy" />
            </figure>
            <h3>{{ item.title }}</h3>
            <p>{{ item.summary || '暂无摘要。' }}</p>
            <div class="news-brief-meta">
              <span>{{ item.sourceName || '新闻社' }}</span>
              <span v-if="item.tag || item.tags?.length">{{ item.tag || item.tags?.slice(0, 2).join(' / ') }}</span>
            </div>
            <div class="news-card-actions">
              <span class="news-read-link">阅读全文</span>
              <span :class="['news-source-link', { 'is-disabled': !sourceHref(item) }]">
                {{ sourceHref(item) ? '原文可追溯' : '原文待补' }}
              </span>
            </div>
          </el-card>
        </div>
        <el-empty v-if="!filteredRecommendations.length && !loading" description="暂无推荐新闻" />
      </el-tab-pane>

      <el-tab-pane label="搜索结果" name="search">
        <section class="news-search-results" aria-label="新闻搜索结果">
          <div class="news-search-result-head">
            <div>
              <strong>搜索结果</strong>
              <span>{{ searchResults.length }} 条</span>
            </div>
            <small>{{ searchForm.q || searchForm.section ? '按当前条件筛选' : '输入关键词或栏目后搜索' }}</small>
          </div>

          <div v-if="searchResults.length" class="news-card-grid search-grid">
            <article
              v-for="item in searchResults"
              :key="item.id || item.openId || item.title"
              :class="['news-search-card', sectionClass(item)]"
              role="button"
              tabindex="0"
              @click="openDetail(item)"
              @keydown.enter.prevent="openDetail(item)"
              @keydown.space.prevent="openDetail(item)"
            >
              <div class="news-card-head">
                <span class="news-section-badge">{{ sectionLabel(item) }}</span>
                <span>{{ item.dateText || item.date || item.sourceName || '今日' }}</span>
              </div>
              <figure v-if="cardImage(item)" class="news-search-media">
                <img :src="cardImage(item)" :alt="`${item.title} 配图`" loading="lazy" />
              </figure>
              <h3>{{ item.title }}</h3>
              <p>{{ item.summary || '暂无摘要。' }}</p>
              <div class="news-brief-meta">
                <span>{{ item.sourceName || '新闻社' }}</span>
                <span>{{ sourceHref(item) ? '原文可追溯' : '原文待补' }}</span>
              </div>
            </article>
          </div>
          <el-empty v-else description="暂无搜索结果" />
        </section>
      </el-tab-pane>
    </el-tabs>

    <div v-if="detailVisible" class="news-detail-overlay active" @click.self="closeDetail">
      <section
        :class="[
          'news-detail-panel',
          sectionClass(selectedItem),
          { 'is-fullscreen': detailFullscreen, 'is-minimized': detailMinimized }
        ]"
        role="dialog"
        aria-modal="true"
        :aria-label="detailWindowTitle"
      >
        <header class="news-window-bar">
          <div class="news-window-controls" aria-label="详情窗口控制">
            <button class="news-window-dot close" type="button" title="关闭" aria-label="关闭详情" @click="closeDetail"></button>
            <button class="news-window-dot minimize" type="button" title="缩小" aria-label="缩小详情" @click="toggleDetailMinimize"></button>
            <button class="news-window-dot fullscreen" type="button" title="全屏" aria-label="切换全屏详情" @click="toggleDetailFullscreen"></button>
          </div>
          <div class="news-window-title">{{ detailWindowTitle }}</div>
          <button
            v-if="detailMinimized"
            type="button"
            class="news-minimized-restore"
            @click="toggleDetailMinimize"
          >
            恢复阅读
          </button>
        </header>

        <div v-if="!detailMinimized" class="news-detail-body">
          <template v-if="selectedItem?.detailHtml">
            <div class="news-legacy-detail" v-html="selectedItem.detailHtml"></div>
            <div class="news-reader-source-footer">
              <div>
                <span>原文追溯</span>
                <strong>{{ selectedItem.sourceName || '新闻社资料' }}</strong>
              </div>
              <a
                v-if="sourceHref(selectedItem)"
                class="news-reader-source-link"
                :href="sourceHref(selectedItem)"
                target="_blank"
                rel="noopener"
              >
                打开原文链接
              </a>
              <span v-else class="news-reader-source-link is-disabled">原文链接待补</span>
            </div>
          </template>
          <article v-else-if="selectedItem" :class="['news-detail-fallback', sectionClass(selectedItem)]">
            <figure v-if="cardImage(selectedItem)" class="detail-visual news-fallback-visual">
              <img :src="cardImage(selectedItem)" :alt="`${selectedItem.title} 配图`" loading="lazy" />
            </figure>
            <div class="detail-meta">
              <span class="news-section-badge">{{ sectionLabel(selectedItem) }}</span>
              <span>{{ selectedItem.sourceName || '未知来源' }}</span>
              <span>{{ selectedItem.dateText || selectedItem.date || '' }}</span>
            </div>
            <h2>{{ selectedItem.title }}</h2>
            <p class="detail-lead">{{ selectedItem.summary || '暂无摘要。' }}</p>
            <div v-if="selectedItem.tag || selectedItem.tags?.length" class="detail-tags">
              <span v-for="tag in detailTags(selectedItem)" :key="tag">{{ tag }}</span>
            </div>
            <div class="news-reader-source-footer">
              <div>
                <span>原文追溯</span>
                <strong>{{ selectedItem.sourceName || '新闻社资料' }}</strong>
              </div>
              <a
                v-if="sourceHref(selectedItem)"
                class="news-reader-source-link"
                :href="sourceHref(selectedItem)"
                target="_blank"
                rel="noopener"
              >
                打开原文链接
              </a>
              <span v-else class="news-reader-source-link is-disabled">原文链接待补</span>
            </div>
          </article>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useStorage } from '@vueuse/core'
import { ElMessage } from 'element-plus'
import { HomeFilled, Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { fetchNewsSnapshot, searchNews, type NewsItem } from './api'

const activeTab = useStorage('niu-vue-news-active-tab', 'recommend')
const loading = ref(false)
const searching = ref(false)
const error = ref('')
const message = ref('')
const personalized = ref(false)
const recommendations = ref<NewsItem[]>([])
const searchResults = ref<NewsItem[]>([])
const detailVisible = ref(false)
const detailFullscreen = ref(false)
const detailMinimized = ref(false)
const selectedItem = ref<NewsItem | null>(null)
const searchForm = reactive({ q: '', section: '' })
const activeSection = ref('all')

const sectionNav = [
  { value: 'all', label: '全部', caption: '编辑精选', mark: '总' },
  { value: 'domestic', label: '国内', caption: '政策与社会', mark: '中' },
  { value: 'international', label: '国际', caption: '全球现场', mark: '外' },
  { value: 'finance', label: '财经', caption: '市场与产业', mark: '财' },
  { value: 'tech', label: '科技', caption: '公司与工程', mark: '科' },
  { value: 'ai', label: 'AI', caption: '模型与智能体', mark: '智' }
]

const filteredRecommendations = computed(() => {
  if (activeSection.value === 'all') return recommendations.value
  return recommendations.value.filter((item) => normalizeSection(item) === activeSection.value)
})

const availableSectionCount = computed(() => {
  return sectionNav
    .filter((section) => section.value !== 'all')
    .filter((section) => sectionCount(section.value) > 0)
    .length
})

const detailWindowTitle = computed(() => {
  if (!selectedItem.value) return '牛秘书新闻社 · 详情'
  return `牛秘书新闻社 · ${sectionLabel(selectedItem.value)} · 详情`
})

load()

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  document.body.style.overflow = ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const snapshot = await fetchNewsSnapshot(12)
    recommendations.value = snapshot.recommendations
    message.value = snapshot.message
    personalized.value = snapshot.personalized
  } catch (err: any) {
    error.value = err.message || '新闻推荐读取失败'
  } finally {
    loading.value = false
  }
}

async function submitSearch() {
  searching.value = true
  try {
    searchResults.value = await searchNews(searchForm.q, searchForm.section, 30)
    activeTab.value = 'search'
  } catch (err: any) {
    ElMessage.error(err.message || '新闻搜索失败')
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

function openDetail(item: NewsItem) {
  selectedItem.value = item
  detailFullscreen.value = false
  detailMinimized.value = false
  detailVisible.value = true
  document.body.style.overflow = 'hidden'
}

function closeDetail() {
  detailVisible.value = false
  detailFullscreen.value = false
  detailMinimized.value = false
  document.body.style.overflow = ''
}

function toggleDetailMinimize() {
  detailMinimized.value = !detailMinimized.value
  if (detailMinimized.value) detailFullscreen.value = false
}

function toggleDetailFullscreen() {
  detailMinimized.value = false
  detailFullscreen.value = !detailFullscreen.value
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (!detailVisible.value) return
  if (event.key === 'Escape') closeDetail()
}

function normalizeSection(item?: NewsItem | null) {
  if (!item) return 'all'
  const raw = String(item.section || item.sectionName || item.sectionLabel || '').toLowerCase()
  if (/国内|domestic/.test(raw)) return 'domestic'
  if (/国际|international|world|global/.test(raw)) return 'international'
  if (/财经|finance|business|market/.test(raw)) return 'finance'
  if (/科技|tech|technology/.test(raw)) return 'tech'
  if (/ai|人工智能|大模型|智能/.test(raw)) return 'ai'
  return 'all'
}

function sectionLabel(item: NewsItem) {
  const found = sectionNav.find((section) => section.value === normalizeSection(item))
  return found?.label || item.sectionLabel || item.sectionName || item.section || '新闻'
}

function sectionClass(item?: NewsItem | null) {
  return `section-${normalizeSection(item)}`
}

function sectionCount(section: string) {
  if (section === 'all') return recommendations.value.length
  return recommendations.value.filter((item) => normalizeSection(item) === section).length
}

function sourceHref(item?: NewsItem | null) {
  return item?.sourceUrl || item?.url || ''
}

function cardImage(item?: NewsItem | null) {
  const raw = item?.imagePath?.trim()
  if (!raw) return ''
  if (/^https?:\/\//.test(raw) || raw.startsWith('/')) return raw
  return `/niu-secretary/news-daily/${raw.replace(/^\.?\//, '')}`
}

function detailTags(item: NewsItem) {
  return Array.from(new Set([item.tag, ...(item.tags || [])].filter(Boolean).map(String))).slice(0, 6)
}
</script>
