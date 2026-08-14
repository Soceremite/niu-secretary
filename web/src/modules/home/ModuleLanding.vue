<template>
  <main class="module-shell" :class="`module-${moduleKey}`">
    <nav class="home-nav compact">
      <router-link to="/">牛秘书</router-link>
      <router-link to="/admin/">管理台</router-link>
    </nav>
    <section class="module-hero">
      <p class="eyebrow">{{ meta.badge }}</p>
      <h1>{{ meta.title }}</h1>
      <p>{{ meta.description }}</p>
      <div class="module-actions">
        <el-button type="primary" @click="openLegacy">打开现有模块</el-button>
        <el-button @click="$router.push('/admin/')">进入管理台</el-button>
      </div>
    </section>
    <section class="module-note">
      <h2>Vue 迁移状态</h2>
      <p>该板块已接入新版 Vue Router。完整业务页面会按计划逐步迁移；迁移完成前，按钮会跳转到现有稳定页面。</p>
    </section>
  </main>
</template>

<script setup lang="ts">
const props = defineProps<{ moduleKey: 'fitness' | 'schedule' | 'leisure' | 'news' | 'airesearch' }>()

const metas = {
  fitness: { title: '塑形馆', badge: 'Fitness', description: '营养、训练、恢复和身体评估。', legacy: '/niu-secretary/fitness/index.html' },
  schedule: { title: '时务局', badge: 'Schedule', description: '日程、待办、重要日期和日计划。', legacy: '/niu-secretary/schedule/index.html' },
  leisure: { title: '闲趣集', badge: 'Leisure', description: '推荐、收藏、忽略、评分和偏好。', legacy: '/niu-secretary/leisure/index.html' },
  news: { title: '新闻社', badge: 'News', description: '新闻推荐、搜索和归档。', legacy: '/niu-secretary/news/index.html' },
  airesearch: { title: '研知库', badge: 'AIResearch', description: '论文概览、研究候选和报告。', legacy: '/niu-secretary/airesearch/index.html' }
}

const meta = metas[props.moduleKey]

function openLegacy() {
  window.location.href = meta.legacy
}
</script>
