<template>
  <main class="admin-login-shell">
    <el-card class="admin-login-card" shadow="never">
      <div class="login-brand">
        <span>牛</span>
        <strong>牛秘书管理台</strong>
      </div>
      <h1>管理员登录</h1>
      <p>登录后进入 Vue 版多子页面后台。</p>
      <el-alert
        v-if="loginError"
        class="admin-login-alert"
        type="error"
        :title="loginError"
        show-icon
        :closable="false"
        role="alert"
      />
      <el-form label-position="top" :model="form" @submit.prevent="login">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" @input="loginError = ''" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            show-password
            @input="loginError = ''"
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" size="large" :loading="loading">登录</el-button>
      </el-form>
    </el-card>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/app/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const loginError = ref('')
const form = reactive({ username: 'admin', password: '' })

async function login() {
  loading.value = true
  loginError.value = ''
  try {
    await auth.login(form.username, form.password)
    await router.push(String(route.query.redirect || '/admin/'))
  } catch (error: any) {
    loginError.value = error.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
