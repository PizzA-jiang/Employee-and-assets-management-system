<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
        <el-form-item label="操作类型">
          <el-select v-model="query.action" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="(item, key) in OPERATION_ACTION" :key="key" :label="item" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标类型">
          <el-select v-model="query.target_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="资产" value="asset" />
            <el-option label="员工" value="employee" />
            <el-option label="文件" value="file" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
          <el-button :icon="'Refresh'" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column prop="username" label="操作人" width="110" align="center">
        <template #default="{ row }">{{ row.username || '-' }}</template>
      </el-table-column>
      <el-table-column prop="action" label="操作类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="ACTION_TAG[row.action] ?? 'info'" size="small">
            {{ OPERATION_ACTION[row.action] || row.action }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_type" label="目标类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="TARGET_TYPE_TAG[row.target_type] ?? 'info'" size="small">
            {{ TARGET_TYPE[row.target_type] || row.target_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_name" label="目标名称" min-width="120" align="center">
        <template #default="{ row }">{{ row.target_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="detail" label="操作详情" min-width="150" align="center">
        <template #default="{ row }">{{ row.detail || '-' }}</template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP地址" width="130" align="center">
        <template #default="{ row }">{{ row.ip_address || '-' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="操作时间" width="160" align="center">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
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
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { listOperationLogsApi } from '../api/operationLogs'
import { formatDateTime } from '../utils/format'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const dateRange = ref(null)

const query = reactive({
  page: 1,
  size: 10,
  action: '',
  target_type: '',
  start_date: '',
  end_date: '',
})

const OPERATION_ACTION = {
  create: '创建',
  update: '更新',
  delete: '删除',
  upload: '上传',
  download: '下载',
  share: '共享',
}

const ACTION_TAG = {
  create: 'success',
  update: 'warning',
  delete: 'danger',
  upload: 'primary',
  download: 'info',
  share: '',
}

const TARGET_TYPE = {
  asset: '资产',
  employee: '员工',
  file: '文件',
}

const TARGET_TYPE_TAG = {
  asset: '',
  employee: 'success',
  file: 'warning',
}

async function load() {
  loading.value = true
  try {
    const params = { page: query.page, size: query.size }
    if (query.action) params.action = query.action
    if (query.target_type) params.target_type = query.target_type
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0] + 'T00:00:00'
      params.end_date = dateRange.value[1] + 'T23:59:59'
    }
    const res = await listOperationLogsApi(params)
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
  query.action = ''
  query.target_type = ''
  dateRange.value = null
  handleSearch()
}

function handleSizeChange() {
  query.page = 1
  load()
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
