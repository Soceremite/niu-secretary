<template>
  <el-container class="admin-app">
    <el-aside width="280px" class="admin-aside">
      <div class="admin-brand-block">
        <router-link class="admin-brand" to="/">
          <span>牛</span>
          <strong>牛秘书管理台</strong>
        </router-link>
        <small>统一管理五个模块的数据、队列和操作记录</small>
      </div>
      <nav class="admin-mobile-nav" aria-label="管理台快速导航">
        <router-link
          v-for="item in flatMenu"
          :key="item.path"
          :to="item.path"
          :class="{ active: normalizePath(item.path) === canonicalPath }"
          :aria-current="normalizePath(item.path) === canonicalPath ? 'page' : undefined"
        >
          <span>{{ item.group }}</span>
          <strong>{{ item.title }}</strong>
        </router-link>
      </nav>
      <el-menu :default-active="$route.path" :default-openeds="defaultOpeneds" router class="admin-menu">
        <template v-for="group in adminMenu" :key="group.title">
          <el-sub-menu v-if="group.items.length > 1" :index="group.path">
            <template #title>
              <span class="admin-menu-group">
                <b>{{ group.title }}</b>
                <small>{{ group.items.length }} 页</small>
              </span>
            </template>
            <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path">
              {{ item.title }}
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="group.path">{{ group.title }}</el-menu-item>
        </template>
      </el-menu>
      <div class="admin-aside-footer">
        <el-button text @click="$router.push('/')">返回主页</el-button>
        <el-button text type="danger" @click="logout">退出登录</el-button>
      </div>
    </el-aside>
    <el-container class="admin-workspace">
      <el-header class="admin-topbar">
        <div class="admin-topbar-context">
          <span>{{ currentMenu.group }}</span>
          <strong>{{ currentMenu.title }}</strong>
        </div>
        <div class="admin-topbar-actions">
          <el-tag effect="plain" type="success">会话已验证</el-tag>
          <el-button class="admin-topbar-button" @click="refreshCurrent">刷新当前</el-button>
        </div>
      </el-header>
      <el-main class="admin-main">
        <AdminFeedbackBar />
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AdminFeedbackBar from '@/shared/components/AdminFeedbackBar.vue'
import { adminMenu } from './resources'
import { useAuthStore } from '@/app/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const flatMenu = computed(() => adminMenu.flatMap((group) => group.items.map((item) => ({
  ...item,
  group: group.title
}))))
const defaultOpeneds = computed(() => adminMenu.map((group) => group.path))

const normalizePath = (path: string) => path.length > 1 ? path.replace(/\/+$/, '') : path
const normalizedPath = computed(() => normalizePath(route.path))
const canonicalPath = computed(() => normalizedPath.value === '/admin/airesearch/jobs'
  ? '/admin/airesearch/tasks'
  : normalizedPath.value)
const currentMenu = computed(() => flatMenu.value.find((item) => {
  return normalizePath(item.path) === canonicalPath.value
}) || { title: '运营总览', group: '总览', path: '/admin/' })

function refreshCurrent() {
  window.dispatchEvent(new CustomEvent('niu-admin-refresh'))
}

async function logout() {
  auth.logout()
  await router.push('/admin/login')
}
</script>
