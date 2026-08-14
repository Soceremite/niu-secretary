import { defineStore } from 'pinia'
import { checkAdminSession, loginAdmin } from '@/app/api/admin'

const TOKEN_KEY = 'niu-secretary-admin-token'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    username: 'admin',
    checked: false
  }),
  getters: {
    authenticated: (state) => Boolean(state.token)
  },
  actions: {
    async login(username: string, password: string) {
      const result = await loginAdmin(username, password)
      this.token = result.token
      this.username = username
      this.checked = true
      localStorage.setItem(TOKEN_KEY, result.token)
    },
    async verify() {
      if (!this.token) {
        this.checked = true
        return false
      }
      try {
        const result = await checkAdminSession(this.token)
        this.checked = true
        if (!result.authenticated) this.logout()
        return result.authenticated
      } catch {
        this.logout()
        return false
      }
    },
    logout() {
      this.token = ''
      this.checked = true
      localStorage.removeItem(TOKEN_KEY)
    }
  }
})
