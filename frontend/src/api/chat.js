import request from './request'

export function chatAskApi(data) {
  return request.post('/chat/ask', data)
}

export function getChatStatusApi() {
  return request.get('/chat/status')
}

// ─── 对话历史 ──────────────────────────────────────────────────────
export function listConversationsApi() {
  return request.get('/chat/conversations')
}

export function getConversationApi(convId) {
  return request.get(`/chat/conversations/${convId}`)
}

export function deleteConversationApi(convId) {
  return request.delete(`/chat/conversations/${convId}`)
}

// ─── SSE 流式问答 ─────────────────────────────────────────────────
export function chatAskStreamApi(data, onChunk, onDone, onError, onConvId) {
  const TOKEN_KEY = 'asset_token'
  const token = localStorage.getItem(TOKEN_KEY)

  fetch('/api/chat/ask/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      function processStream() {
        reader.read().then(({ done, value }) => {
          if (done) {
            return
          }
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed || !trimmed.startsWith('data: ')) continue
            const payload = trimmed.slice(6)
            if (payload === '[DONE]') {
              return
            }
            try {
              const event = JSON.parse(payload)
              if (event.type === 'content') {
                onChunk && onChunk(event.data)
              } else if (event.type === 'done') {
                onDone && onDone(event.data)
              } else if (event.type === 'error') {
                onError && onError(event.data)
              } else if (event.type === 'conv_id') {
                onConvId && onConvId(event.data)
              }
            } catch {
              // skip parse errors
            }
          }
          processStream()
        })
      }
      processStream()
    })
    .catch((err) => {
      onError && onError(err.message || '网络错误')
    })
}
