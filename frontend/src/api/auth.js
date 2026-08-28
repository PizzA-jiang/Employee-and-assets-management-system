import request from './request'

export function loginApi(data) {
  return request.post('/auth/login', data)
}

export function getMeApi() {
  return request.get('/auth/me')
}

export function registerApi(data) {
  return request.post('/auth/register', data)
}
