import request from './request'

export function listOperationLogsApi(params) {
  return request.get('/operation-logs', { params })
}
