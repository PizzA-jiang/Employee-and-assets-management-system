import request from './request'

export function listEmployeesApi(params) {
  return request.get('/employees', { params })
}

export function getEmployeeDetailApi(id) {
  return request.get(`/employees/${id}`)
}

export function createEmployeeApi(data) {
  return request.post('/employees', data)
}

export function updateEmployeeApi(id, data) {
  return request.put(`/employees/${id}`, data)
}

export function deleteEmployeeApi(id) {
  return request.delete(`/employees/${id}`)
}
