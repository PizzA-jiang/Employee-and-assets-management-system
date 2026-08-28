import request from './request'

export function listAssetLogsApi(params) {
  return request.get('/asset-logs', { params })
}

export function createAssetLogApi(data) {
  return request.post('/asset-logs', data)
}

export function getAssetHistoryApi(assetId, params) {
  return request.get(`/asset-logs/asset/${assetId}`, { params })
}
