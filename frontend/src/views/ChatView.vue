<template>
  <div class="chat-container">
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="handleNewChat">
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
      </div>
      <div class="sidebar-list">
        <div
          v-for="(conv, idx) in conversations"
          :key="conv.id || idx"
          :class="['conv-item', { active: conv.id === activeConvId }]"
          @click="handleSelectConv(conv)"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span class="conv-title">{{ conv.title || '新对话' }}</span>
          <el-icon class="conv-del" @click.stop="handleDeleteConv(conv.id)"><Delete /></el-icon>
        </div>
      </div>
    </div>

    <div class="chat-main">
      <div class="messages-area" ref="messagesRef">
        <div v-if="currentMessages.length === 0" class="empty-hint">
          <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
          <p>开始提问吧，我将基于知识库为您回答</p>
          <p class="hint-sub">支持自然语言查询员工、资产、流转记录等数据</p>
        </div>
        <div v-for="(msg, idx) in currentMessages" :key="idx" :class="['message', msg.role]">
          <div class="msg-avatar">
            <el-avatar v-if="msg.role === 'user'" :size="32">{{ userInitial }}</el-avatar>
            <el-avatar v-else :size="32" style="background:#67c23a">AI</el-avatar>
          </div>
          <div class="msg-body">
            <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.loading" class="msg-loading">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
            <div v-if="msg.sources && msg.sources.length" class="msg-sources">
              <el-collapse>
                <el-collapse-item title="引用来源">
                  <div v-for="(src, si) in msg.sources" :key="si" class="source-item">
                    <div class="source-title">
                      <el-tag size="small">{{ src.document_title }}</el-tag>
                      <span class="source-score">相关度 {{ (src.score * 100).toFixed(0) }}%</span>
                    </div>
                    <div class="source-content">{{ src.content }}</div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入你的问题... (Enter发送, Shift+Enter换行)"
            :disabled="streaming"
            @keydown.enter.exact.prevent="handleSend"
          />
          <el-button
            v-if="streaming"
            type="danger"
            circle
            @click="handleStop"
          >
            <el-icon><VideoPause /></el-icon>
          </el-button>
          <el-button
            v-else
            type="primary"
            circle
            :disabled="!inputText.trim()"
            @click="handleSend"
          >
            <el-icon><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { chatAskStreamApi, listConversationsApi, getConversationApi, deleteConversationApi } from '../api/chat'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const userStore = useUserStore()
const userInitial = computed(() => (userStore.displayName || 'U').slice(0, 1).toUpperCase())

const messagesRef = ref(null)
const inputText = ref('')
const streaming = ref(false)
const conversations = ref([])
const activeConvId = ref(null)
const currentMessages = ref([])

function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

async function loadConversations() {
  try {
    const res = await listConversationsApi()
    conversations.value = res || []
  } catch { /* ignore */ }
}

async function handleSelectConv(conv) {
  activeConvId.value = conv.id
  try {
    const detail = await getConversationApi(conv.id)
    currentMessages.value = (detail.messages || []).map(m => ({
      role: m.role,
      content: m.content,
      sources: m.sources || [],
      loading: false,
    }))
    scrollToBottom()
  } catch {
    currentMessages.value = []
  }
}

function handleNewChat() {
  activeConvId.value = null
  currentMessages.value = []
}

async function handleDeleteConv(convId) {
  try {
    await ElMessageBox.confirm('确定删除该对话？', '提示', { type: 'warning' })
    await deleteConversationApi(convId)
    await loadConversations()
    if (activeConvId.value === convId) {
      handleNewChat()
    }
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || streaming.value) return

  currentMessages.value.push({ role: 'user', content: text })
  const aiMsg = { role: 'assistant', content: '', loading: true, sources: [] }
  currentMessages.value.push(aiMsg)
  inputText.value = ''
  scrollToBottom()

  streaming.value = true

  chatAskStreamApi(
    { query: text, top_k: 5, conversation_id: activeConvId.value },
    (chunk) => {
      aiMsg.loading = false
      aiMsg.content += chunk
      scrollToBottom()
    },
    (data) => {
      aiMsg.loading = false
      if (data?.sources) aiMsg.sources = data.sources
      streaming.value = false
      scrollToBottom()
    },
    (err) => {
      aiMsg.loading = false
      if (!aiMsg.content) {
        aiMsg.content = typeof err === 'string' ? err : '请求失败，请稍后重试'
      }
      streaming.value = false
    },
    (convId) => {
      activeConvId.value = convId
      loadConversations()
    },
  )
}

function handleStop() {
  streaming.value = false
}

onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 92px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}
.chat-sidebar {
  width: 240px;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}
.sidebar-header {
  padding: 12px;
}
.new-chat-btn {
  width: 100%;
}
.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  margin-bottom: 2px;
}
.conv-item:hover {
  background: #ecf5ff;
}
.conv-item.active {
  background: #d9ecff;
  color: #409eff;
}
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-del {
  opacity: 0;
  color: #f56c6c;
}
.conv-item:hover .conv-del {
  opacity: 1;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
}
.empty-hint p {
  margin: 8px 0 0;
  font-size: 15px;
}
.hint-sub {
  font-size: 13px !important;
  color: #909399;
}
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 800px;
}
.message.user {
  flex-direction: row-reverse;
  margin-left: auto;
}
.msg-body {
  max-width: 85%;
}
.msg-content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.message.user .msg-content {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.message.assistant .msg-content {
  background: #f4f4f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}
.msg-loading {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: dot-bounce 1.2s infinite ease-in-out;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
.msg-sources {
  margin-top: 8px;
}
.source-item {
  margin-bottom: 8px;
}
.source-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.source-score {
  font-size: 12px;
  color: #909399;
}
.source-content {
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 6px 8px;
  border-radius: 4px;
  max-height: 80px;
  overflow-y: auto;
  line-height: 1.5;
}
.input-area {
  border-top: 1px solid #ebeef5;
  padding: 16px 20px;
}
.input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  max-width: 800px;
  margin: 0 auto;
}
.input-wrapper :deep(.el-textarea__inner) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  border-radius: 8px;
  resize: none;
}
</style>
