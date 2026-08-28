export function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

export function formatDate(value) {
  if (!value) return '-'
  return String(value).slice(0, 10)
}

// 后端采购价格单位为分，前端展示/录入使用元
export function fenToYuan(fen) {
  if (fen === null || fen === undefined || fen === '') return null
  return Math.round(Number(fen)) / 100
}

export function yuanToFen(yuan) {
  if (yuan === null || yuan === undefined || yuan === '') return null
  return Math.round(Number(yuan) * 100)
}
