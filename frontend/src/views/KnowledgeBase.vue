<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="搜索文档标题" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
          <el-button :icon="'Refresh'" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-upload
        ref="uploadRef"
        :action="uploadUrl"
        :headers="uploadHeaders"
        :show-file-list="false"
        :before-upload="beforeUpload"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
      >
        <el-button type="primary" :icon="'Upload'">上传文档</el-button>
      </el-upload>
    </div>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column prop="title" label="文档标题" min-width="180" align="left" />
      <el-table-column prop="file_type" label="类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="getFileTypeTag(row.file_type)">{{ row.file_type.toUpperCase() }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="100" align="center">
        <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="分块数" width="90" align="center" />
      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'success'" type="success" size="small">完成</el-tag>
          <el-tag v-else-if="row.status === 'processing'" type="warning" size="small">处理中</el-tag>
          <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="creator_name" label="上传者" width="100" align="center" />
      <el-table-column prop="created_at" label="上传时间" width="160" align="center">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openChunks(row)">分块</el-button>
          <el-button link type="warning" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="info" size="small" @click="handleReprocess(row)">重新处理</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="load"
        @size-change="handleSizeChange"
      />
    </div>
  </el-card>

  <!-- 编辑弹窗 -->
  <el-dialog v-model="editDialog.visible" title="编辑文档" width="420px" destroy-on-close :close-on-click-modal="false">
    <el-form label-width="80px">
      <el-form-item label="文档标题">
        <el-input v-model="editDialog.title" maxlength="255" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="editDialog.saving" @click="handleEditSave">保存</el-button>
    </template>
  </el-dialog>

  <!-- 分块预览弹窗 -->
  <el-dialog v-model="chunkDialog.visible" title="分块预览" width="800px" destroy-on-close>
    <el-table v-loading="chunkDialog.loading" :data="chunkDialog.list" border stripe max-height="500">
      <el-table-column prop="chunk_index" label="序号" width="70" align="center" />
      <el-table-column prop="token_count" label="Token数" width="90" align="center" />
      <el-table-column prop="content" label="内容" min-width="400" align="left">
        <template #default="{ row }">
          <div class="chunk-content">{{ row.content }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="embedding_status" label="向量化" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.embedding_status === 'done'" type="success" size="small">完成</el-tag>
          <el-tag v-else-if="row.embedding_status === 'pending'" type="info" size="small">待处理</el-tag>
          <el-tag v-else type="danger" size="small">失败</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <div class="pagination-wrap" style="margin-top: 14px;">
      <el-pagination
        v-model:current-page="chunkDialog.page"
        v-model:page-size="chunkDialog.size"
        :total="chunkDialog.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="loadChunks"
        @size-change="handleChunkSizeChange"
      />
    </div>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listKnowledgeDocumentsApi,
  deleteKnowledgeDocumentApi,
  listKnowledgeChunksApi,
  updateKnowledgeDocumentApi,
  reprocessKnowledgeDocumentApi,
} from '../api/knowledge'
import { useUserStore } from '../stores/user'
import { formatDateTime } from '../utils/format'

const userStore = useUserStore()
const TOKEN_KEY = 'asset_token'

const loading = ref(false)
const list = ref([])
const total = ref(0)

const uploadUrl = '/api/knowledge/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`,
}))

const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
})

const editDialog = reactive({
  visible: false,
  id: null,
  title: '',
  saving: false,
})

const chunkDialog = reactive({
  visible: false,
  loading: false,
  list: [],
  total: 0,
  page: 1,
  size: 10,
  documentId: null,
})

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function getFileTypeTag(type) {
  const map = { pdf: 'danger', docx: 'primary', xlsx: 'success', txt: 'info', md: 'warning' }
  return map[type] || 'info'
}

async function load() {
  loading.value = true
  try {
    const params = { page: query.page, size: query.size }
    if (query.keyword) params.keyword = query.keyword
    const res = await listKnowledgeDocumentsApi(params)
    list.value = res.items || []
    total.value = res.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  load()
}

function handleReset() {
  query.keyword = ''
  handleSearch()
}

function handleSizeChange() {
  query.page = 1
  load()
}

function beforeUpload(file) {
  const allowedTypes = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md']
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  if (!allowedTypes.includes(ext)) {
    ElMessage.error(`不支持的文件类型: ${ext}`)
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

function handleUploadSuccess() {
  ElMessage.success('上传成功，文档正在处理中')
  load()
}

function handleUploadError(err) {
  let msg = '上传失败'
  if (err?.response) {
    try {
      const data = typeof err.response === 'string' ? JSON.parse(err.response) : err.response
      msg = data.message || data.detail || msg
    } catch {
      // ignore parse error
    }
  }
  ElMessage.error(msg)
}

function openEdit(row) {
  editDialog.id = row.id
  editDialog.title = row.title
  editDialog.visible = true
}

async function handleEditSave() {
  if (!editDialog.title.trim()) {
    ElMessage.warning('请输入文档标题')
    return
  }
  editDialog.saving = true
  try {
    await updateKnowledgeDocumentApi(editDialog.id, { title: editDialog.title })
    ElMessage.success('保存成功')
    editDialog.visible = false
    load()
  } catch {
    /* error handled by interceptor */
  } finally {
    editDialog.saving = false
  }
}

async function handleReprocess(row) {
  try {
    await ElMessageBox.confirm(
      `确定重新处理文档「${row.title}」吗？现有分块将被删除并重新生成。`,
      '重新处理确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  await reprocessKnowledgeDocumentApi(row.id)
  ElMessage.success('已提交重新处理任务')
  load()
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除文档「${row.title}」吗？关联的分块数据也将被删除，此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  await deleteKnowledgeDocumentApi(row.id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && query.page > 1) {
    query.page -= 1
  }
  load()
}

async function openChunks(row) {
  chunkDialog.documentId = row.id
  chunkDialog.page = 1
  chunkDialog.visible = true
  await loadChunks()
}

async function loadChunks() {
  chunkDialog.loading = true
  try {
    const params = { page: chunkDialog.page, size: chunkDialog.size }
    const res = await listKnowledgeChunksApi(chunkDialog.documentId, params)
    chunkDialog.list = res.items || []
    chunkDialog.total = res.total || 0
  } finally {
    chunkDialog.loading = false
  }
}

function handleChunkSizeChange() {
  chunkDialog.page = 1
  loadChunks()
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 4px;
}
.filter-form :deep(.el-form-item) {
  margin-bottom: 8px;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
.chunk-content {
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.5;
}
</style>
