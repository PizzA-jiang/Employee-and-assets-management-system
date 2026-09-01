import request from './request'

export function getDashboardStatsApi() {
  return request.get('/dashboard/stats')
}

export function getAssetsByTypeApi() {
  return request.get('/dashboard/charts/assets-by-type')
}

export function getAssetsByStatusApi() {
  return request.get('/dashboard/charts/assets-by-status')
}

export function getLogsByActionApi() {
  return request.get('/dashboard/charts/logs-by-action')
}

export function getEmployeesByDeptApi() {
  return request.get('/dashboard/charts/employees-by-department')
}
