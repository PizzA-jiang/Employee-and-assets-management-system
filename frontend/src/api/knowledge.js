import request from './request'

export function listKnowledgeDocumentsApi(params) {
  return request.get('/knowledge/documents', { params })
}

export function getKnowledgeDocumentApi(id) {
  return request.get(`/knowledge/documents/${id}`)
}

export function uploadKnowledgeDocumentApi(file, title, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)
  if (title) {
    const params = new URLSearchParams()
    params.append('title', title)
    return request.post(`/knowledge/upload?${params.toString()}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    })
  }
  return request.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
}

export function updateKnowledgeDocumentApi(id, data) {
  return request.put(`/knowledge/documents/${id}`, data)
}

export function deleteKnowledgeDocumentApi(id) {
  return request.delete(`/knowledge/documents/${id}`)
}

export function listKnowledgeChunksApi(docId, params) {
  return request.get(`/knowledge/documents/${docId}/chunks`, { params })
}

export function reprocessKnowledgeDocumentApi(id) {
  return request.post(`/knowledge/documents/${id}/reprocess`)
}

export function searchKnowledgeApi(data) {
  return request.post('/knowledge/search', data)
}
