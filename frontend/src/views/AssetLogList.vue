<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
        <el-form-item label="操作类型">
          <el-select
            v-model="query.action"
            placeholder="全部"
            clearable
            style="width: 130px"
            @change="handleSearch"
          >
            <el-option v-for="(label, key) in LOG_ACTION" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
          <el-button :icon="'Refresh'" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-alert
        title="所有员工（含普通员工）的领用、归还等操作均自动记录入库，仅管理员可查看本页面"
        type="info"
        show-icon
        :closable="false"
        class="tip"
      />
    </div>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="id" label="记录ID" width="80" align="center" />
      <el-table-column prop="created_at" label="操作时间" width="160" align="center">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="资产编号" width="130" align="center">
        <template #default="{ row }">{{ row.asset?.asset_no || '-' }}</template>
      </el-table-column>
      <el-table-column label="资产名称" min-width="120" align="center">
        <template #default="{ row }">{{ row.asset?.name || '-' }}</template>
      </el-table-column>
      <el-table-column label="员工姓名" width="100" align="center">
        <template #default="{ row }">{{ row.employee?.name || '-' }}</template>
      </el-table-column>
      <el-table-column label="工号" width="100" align="center">
        <template #default="{ row }">{{ row.employee?.employee_no || '-' }}</template>
      </el-table-column>
      <el-table-column prop="action" label="操作类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="LOG_ACTION_TAG[row.action] ?? 'info'" size="small">
            {{ LOG_ACTION[row.action] || row.action }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="150" align="center">
        <template #default="{ row }">{{ row.remark || '-' }}</template>
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
import { listAssetLogsApi } from '../api/assetLogs'
import { useUserStore } from '../stores/user'
import { formatDateTime } from '../utils/format'
import { LOG_ACTION, LOG_ACTION_TAG } from '../constants/asset'

const userStore = useUserStore()

const loading = ref(false)
const list = ref([])
const total = ref(0)

const query = reactive({
  page: 1,
  size: 10,
  action: '',
})

async function load() {
  loading.value = true
  try {
    const params = { page: query.page, size: query.size }
    if (query.action) params.action = query.action
    const res = await listAssetLogsApi(params)
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
  margin-bottom: 8px;
}
.filter-form :deep(.el-form-item) {
  margin-bottom: 8px;
}
.tip {
  width: 380px;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
