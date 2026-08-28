import request from './request'

export function listAssetsApi(params) {
  return request.get('/assets', { params })
}

export function getAssetDetailApi(id) {
  return request.get(`/assets/${id}`)
}

export function createAssetApi(data) {
  return request.post('/assets', data)
}

export function updateAssetApi(id, data) {
  return request.put(`/assets/${id}`, data)
}

export function deleteAssetApi(id) {
  return request.delete(`/assets/${id}`)
}
