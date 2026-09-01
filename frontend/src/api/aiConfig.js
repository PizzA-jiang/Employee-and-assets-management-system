import request from './request'

// ─── LLM Config ────────────────────────────────────────────────────
export function getAIConfigsApi() {
  return request.get('/ai-config')
}

export function updateAIConfigsApi(configs) {
  return request.put('/ai-config', { configs })
}

export function testAIConfigApi(data) {
  return request.post('/ai-config/test', data)
}

export function listAIModelsApi() {
  return request.get('/ai-config/models')
}

export function fixAIConfigsApi() {
  return request.post('/ai-config/fix')
}

// ─── MCP Servers ───────────────────────────────────────────────────
export function listMCPServersApi() {
  return request.get('/ai-config/mcp-servers')
}

export function createMCPServerApi(data) {
  return request.post('/ai-config/mcp-servers', data)
}

export function updateMCPServerApi(id, data) {
  return request.put(`/ai-config/mcp-servers/${id}`, data)
}

export function deleteMCPServerApi(id) {
  return request.delete(`/ai-config/mcp-servers/${id}`)
}

export function testMCPServerApi(data) {
  return request.post('/ai-config/mcp-servers/test', data)
}
