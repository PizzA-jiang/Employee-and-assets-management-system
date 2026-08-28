import { defineStore } from 'pinia'
import { loginApi, getMeApi } from '../api/auth'
import { TOKEN_KEY } from '../api/request'

const USER_KEY = 'asset_user'

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    userInfo: loadUser(),
  }),
  getters: {
    role(state) {
      const r = state.userInfo?.role
      return typeof r === 'string' ? r.toLowerCase() : ''
    },
    isAdmin() {
      return this.role === 'admin'
    },
    displayName(state) {
      const info = state.userInfo
      if (!info) return ''
      return info.employee?.name || info.username || ''
    },
  },
  actions: {
    async login(username, password) {
      const data = await loginApi({ username, password })
      this.token = data.access_token
      localStorage.setItem(TOKEN_KEY, this.token)
      await this.fetchMe()
    },
    async fetchMe() {
      const data = await getMeApi()
      this.userInfo = data
      localStorage.setItem(USER_KEY, JSON.stringify(data))
    },
    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})
