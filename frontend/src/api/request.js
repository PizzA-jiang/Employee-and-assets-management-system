import axios from 'axios'
import { ElMessage } from 'element-plus'

const TOKEN_KEY = 'asset_token'

const service = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

service.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem('asset_user')
}

service.interceptors.response.use(
  (response) => {
    const res = response.data
    // 信封格式 {code, message, data}（auth 模块）
    if (res && typeof res === 'object' && 'code' in res && !('total' in res)) {
      if ([200, 201].includes(res.code)) {
        return res.data
      }
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    // 裸格式（employees/assets/asset-logs 模块）直接返回
    return res
  },
  (error) => {
    const status = error.response?.status
    const data = error.response?.data
    let msg
    if (data && typeof data === 'object') {
      msg = data.code === 422 && data.data ? `${data.message}: ${data.data}` : data.message || data.detail
    } else {
      msg = data
    }
    if (!msg) msg = error.message || '网络错误'
    if (status === 401) {
      clearAuth()
      ElMessage.error(msg)
      setTimeout(() => {
        window.location.href = '/login'
      }, 500)
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export default service
export { TOKEN_KEY }
