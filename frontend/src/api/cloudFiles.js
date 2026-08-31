import request from './request'

export function listCloudFilesApi(params) {
  return request.get('/cloud-files', { params })
}

export function uploadCloudFileApi(file, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/cloud-files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
}

export function downloadCloudFileApi(id) {
  return request.get(`/cloud-files/${id}/download`, { responseType: 'blob' })
}

export function deleteCloudFileApi(id) {
  return request.delete(`/cloud-files/${id}`)
}

export function shareCloudFileApi(id, data) {
  return request.post(`/cloud-files/${id}/share`, data)
}

export function listSharedFilesApi(params) {
  return request.get('/cloud-files/shared', { params })
}
