<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="搜索文件名" clearable style="width: 200px" @keyup.enter="handleSearch" />
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
        <el-button type="primary" :icon="'Upload'">上传文件</el-button>
      </el-upload>
    </div>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column prop="filename" label="文件名" min-width="180" align="left">
        <template #default="{ row }">
          <span>{{ row.filename }}</span>
          <el-tag v-if="row.is_shared" type="warning" size="small" style="margin-left: 6px">共享</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="100" align="center">
        <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="owner_name" label="所有者" width="110" align="center">
        <template #default="{ row }">{{ row.owner_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="shared_by" label="分享者" width="110" align="center">
        <template #default="{ row }">{{ row.shared_by || '-' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="160" align="center">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleDownload(row)">下载</el-button>
          <el-button
            v-if="userStore.isAdmin"
            link
            type="warning"
            size="small"
            @click="openShare(row)"
          >共享</el-button>
          <el-button
            v-if="row.user_id === currentUserId || userStore.isAdmin"
            link
            type="danger"
            size="small"
            @click="handleDelete(row)"
          >删除</el-button>
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

  <!-- 共享弹窗 -->
  <el-dialog v-model="shareDialog.visible" title="共享文件" width="420px" destroy-on-close :close-on-click-modal="false">
    <el-form label-width="80px">
      <el-form-item label="文件名">
        <el-input :model-value="shareDialog.filename" disabled />
      </el-form-item>
      <el-form-item label="共享给">
        <el-select
          v-model="shareDialog.userIds"
          filterable
          multiple
          placeholder="请选择用户"
          style="width: 100%"
        >
          <el-option
            v-for="user in userOptions"
            :key="user.id"
            :label="`${user.username}（${user.role === 'admin' ? '管理员' : '员工'}）`"
            :value="user.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="shareDialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="shareDialog.saving" @click="handleShare">确定共享</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listCloudFilesApi,
  deleteCloudFileApi,
  shareCloudFileApi,
} from '../api/cloudFiles'
import { listEmployeesApi } from '../api/employees'
import { useUserStore } from '../stores/user'
import { formatDateTime } from '../utils/format'

const userStore = useUserStore()
const TOKEN_KEY = 'asset_token'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const userOptions = ref([])

const currentUserId = computed(() => userStore.userInfo?.id)

const uploadUrl = '/api/cloud-files/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`,
}))

const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
})

const shareDialog = reactive({
  visible: false,
  fileId: null,
  filename: '',
  userIds: [],
  saving: false,
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

async function load() {
  loading.value = true
  try {
    const params = { page: query.page, size: query.size }
    if (query.keyword) params.keyword = query.keyword
    const res = await listCloudFilesApi(params)
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
  const allowedTypes = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip', '.rar']
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
  ElMessage.success('上传成功')
  load()
}

function handleUploadError() {
  ElMessage.error('上传失败')
}

function handleDownload(row) {
  const token = localStorage.getItem(TOKEN_KEY)
  import('axios').then(({ default: axios }) => {
    axios.get(`/api/cloud-files/${row.id}/download`, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob',
    }).then(res => {
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    }).catch(() => {
      ElMessage.error('下载失败')
    })
  })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除文件「${row.filename}」吗？删除后不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  await deleteCloudFileApi(row.id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && query.page > 1) {
    query.page -= 1
  }
  load()
}

async function openShare(row) {
  shareDialog.fileId = row.id
  shareDialog.filename = row.filename
  shareDialog.userIds = []
  shareDialog.visible = true

  if (!userOptions.value.length) {
    try {
      const token = localStorage.getItem(TOKEN_KEY)
      const { default: axios } = await import('axios')
      const res = await axios.get('/api/auth/users', {
        headers: { Authorization: `Bearer ${token}` },
        params: { page: 1, size: 100 },
      })
      userOptions.value = res.data?.data || []
    } catch {
      /* ignore */
    }
  }
}

async function handleShare() {
  if (!shareDialog.userIds.length) {
    ElMessage.warning('请选择至少一个用户')
    return
  }
  shareDialog.saving = true
  try {
    await shareCloudFileApi(shareDialog.fileId, { user_ids: shareDialog.userIds })
    ElMessage.success('共享成功')
    shareDialog.visible = false
  } catch {
    /* error handled by interceptor */
  } finally {
    shareDialog.saving = false
  }
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
</style>
