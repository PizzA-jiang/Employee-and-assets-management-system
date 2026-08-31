<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="编号/名称/品牌/型号/序列号/位置" clearable style="width: 220px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="query.name" placeholder="按名称搜索" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.asset_type" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="(label, key) in ASSET_TYPE" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="(item, key) in ASSET_STATUS" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
          <el-button :icon="'Refresh'" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <div class="toolbar-right">
        <el-button v-if="userStore.isAdmin" type="success" :icon="'Download'" @click="handleExport">导出Excel</el-button>
        <el-button v-if="userStore.isAdmin" type="primary" :icon="'Plus'" @click="openAdd">新增资产</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="asset_no" label="资产编号" width="120" align="center" />
      <el-table-column prop="name" label="资产名称" min-width="120" align="center" />
      <el-table-column prop="asset_type" label="类型" width="100" align="center">
        <template #default="{ row }">{{ ASSET_TYPE[row.asset_type] || row.asset_type }}</template>
      </el-table-column>
      <el-table-column prop="brand" label="品牌" width="90" align="center">
        <template #default="{ row }">{{ row.brand || '-' }}</template>
      </el-table-column>
      <el-table-column prop="model" label="型号" width="110" align="center">
        <template #default="{ row }">{{ row.model || '-' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="ASSET_STATUS[row.status]?.tag || 'info'" size="small">
            {{ ASSET_STATUS[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="purchase_date" label="采购日期" width="105" align="center">
        <template #default="{ row }">{{ formatDate(row.purchase_date) }}</template>
      </el-table-column>
      <el-table-column prop="purchase_price" label="采购价格(元)" width="115" align="right">
        <template #default="{ row }">{{ fenToYuan(row.purchase_price) ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="location" label="存放位置" min-width="100" align="center">
        <template #default="{ row }">{{ row.location || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="230" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-for="action in actionsOf(row)"
            :key="action"
            link
            :type="action === 'checkout' ? 'success' : 'warning'"
            size="small"
            @click="openFlow(row, action)"
          >
            {{ ACTION_META[action].label }}
          </el-button>
          <template v-if="userStore.isAdmin">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              link
              size="small"
              :type="row.status === 'in_use' ? 'info' : 'danger'"
              :disabled="row.status === 'in_use'"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
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

  <!-- 新增/编辑弹窗 -->
  <el-dialog
    v-model="dialog.visible"
    :title="dialog.isEdit ? '编辑资产' : '新增资产'"
    width="560px"
    destroy-on-close
    :close-on-click-modal="false"
  >
    <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="资产编号" prop="asset_no">
            <el-input v-model="form.asset_no" maxlength="50" placeholder="如 ZC-2026-001" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="资产名称" prop="name">
            <el-input v-model="form.name" maxlength="100" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="资产类型" prop="asset_type">
            <el-select v-model="form.asset_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="(label, key) in ASSET_TYPE" :key="key" :label="label" :value="key" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="品牌">
            <el-input v-model="form.brand" maxlength="50" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="型号">
            <el-input v-model="form.model" maxlength="100" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="序列号">
            <el-input v-model="form.serial_number" maxlength="100" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="采购日期">
            <el-date-picker
              v-model="form.purchase_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="采购价格(元)">
            <el-input-number
              v-model="form.purchase_price_yuan"
              :min="0"
              :max="99999999"
              :precision="2"
              :controls="false"
              placeholder="0.00"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="存放位置">
            <el-input v-model="form.location" maxlength="100" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button @click="dialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
    </template>
  </el-dialog>

  <!-- 领用/归还 流转弹窗 -->
  <el-dialog
    v-model="flow.visible"
    :title="`${flow.meta?.label || ''} - ${flow.asset?.name || ''}（${flow.asset?.asset_no || ''}）`"
    width="440px"
    destroy-on-close
    :close-on-click-modal="false"
  >
    <el-form ref="flowFormRef" :model="flow.form" label-width="90px">
      <el-form-item label="领用人" prop="employee_id" :rules="[{ required: true, message: '请选择员工', trigger: 'change' }]">
        <el-select
          v-if="!flow.lockEmployee"
          v-model="flow.form.employee_id"
          filterable
          placeholder="请选择在职员工"
          style="width: 100%"
        >
          <el-option
            v-for="emp in employeeOptions"
            :key="emp.id"
            :label="`${emp.name}（${emp.employee_no}${emp.department ? ' / ' + emp.department : ''}）`"
            :value="emp.id"
          />
        </el-select>
        <el-tag v-else type="warning" size="large">{{ flow.holderText }}</el-tag>
      </el-form-item>
      <el-alert
        v-if="flow.action === 'return'"
        title="归还人须与该资产的领用人一致，已自动锁定"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 14px"
      />
      <el-form-item label="备注">
        <el-input v-model="flow.form.remark" type="textarea" :rows="2" maxlength="200" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="flow.visible = false">取消</el-button>
      <el-button type="primary" :loading="flow.saving" @click="handleFlowSubmit">
        确认{{ flow.meta?.label }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listAssetsApi,
  createAssetApi,
  updateAssetApi,
  deleteAssetApi,
} from '../api/assets'
import { listEmployeesApi } from '../api/employees'
import { createAssetLogApi, listAssetLogsApi } from '../api/assetLogs'
import { useUserStore } from '../stores/user'
import { formatDate, formatDateTime, fenToYuan, yuanToFen } from '../utils/format'
import { ASSET_STATUS, ASSET_TYPE, STATUS_ACTIONS, ACTION_META } from '../constants/asset'

const userStore = useUserStore()

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const employeeOptions = ref([])

const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
  name: '',
  asset_type: '',
  status: '',
})

const formRef = ref()
const dialog = reactive({
  visible: false,
  isEdit: false,
  editId: null,
})

function emptyForm() {
  return {
    asset_no: '',
    name: '',
    asset_type: null,
    brand: '',
    model: '',
    serial_number: '',
    purchase_date: null,
    purchase_price_yuan: null,
    location: '',
    remark: '',
  }
}

const form = reactive(emptyForm())

const formRules = {
  asset_no: [{ required: true, message: '请输入资产编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入资产名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择资产类型', trigger: 'change' }],
}

// 流转弹窗（领用 / 归还；后续送修、报废等扩展时复用）
const flowFormRef = ref()
const flow = reactive({
  visible: false,
  action: '',
  meta: null,
  asset: null,
  lockEmployee: false,
  holderText: '',
  form: { employee_id: null, remark: '' },
})

function actionsOf(row) {
  return STATUS_ACTIONS[row.status] || []
}

async function load() {
  loading.value = true
  try {
    const params = { page: query.page, size: query.size }
    if (query.keyword) params.keyword = query.keyword
    if (query.name) params.name = query.name
    if (query.asset_type) params.asset_type = query.asset_type
    if (query.status) params.status = query.status
    const res = await listAssetsApi(params)
    list.value = res.items || []
    total.value = res.total || 0
  } finally {
    loading.value = false
  }
}

async function loadEmployees() {
  if (employeeOptions.value.length) return
  const res = await listEmployeesApi({ page: 1, size: 100, status: 1 })
  employeeOptions.value = res.items || []
}

function handleSearch() {
  query.page = 1
  load()
}

function handleReset() {
  query.keyword = ''
  query.name = ''
  query.asset_type = ''
  query.status = ''
  handleSearch()
}

function handleExport() {
  import('axios').then(({ default: axios }) => {
    const token = localStorage.getItem('asset_token')
    axios.get('/api/assets/export/excel', {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob',
    }).then(res => {
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'assets_export.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    })
  })
}

function handleSizeChange() {
  query.page = 1
  load()
}

function openAdd() {
  Object.assign(form, emptyForm())
  dialog.isEdit = false
  dialog.editId = null
  dialog.visible = true
}

function openEdit(row) {
  Object.assign(form, emptyForm(), {
    asset_no: row.asset_no,
    name: row.name,
    asset_type: row.asset_type,
    brand: row.brand || '',
    model: row.model || '',
    serial_number: row.serial_number || '',
    purchase_date: row.purchase_date ? formatDate(row.purchase_date) : null,
    purchase_price_yuan: fenToYuan(row.purchase_price),
    location: row.location || '',
    remark: row.remark || '',
  })
  dialog.isEdit = true
  dialog.editId = row.id
  dialog.visible = true
}

async function handleSave() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload = {
      asset_no: form.asset_no,
      name: form.name,
      asset_type: form.asset_type,
      brand: form.brand || null,
      model: form.model || null,
      serial_number: form.serial_number || null,
      purchase_date: form.purchase_date || null,
      purchase_price: yuanToFen(form.purchase_price_yuan),
      location: form.location || null,
      remark: form.remark || null,
    }
    if (dialog.isEdit) {
      await updateAssetApi(dialog.editId, payload)
      ElMessage.success('更新成功')
    } else {
      await createAssetApi(payload)
      ElMessage.success('新增成功')
    }
    dialog.visible = false
    load()
  } catch {
    /* 错误提示由拦截器统一处理 */
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  if (row.status === 'in_use') {
    ElMessage.warning('资产正在使用中，无法删除，请先归还')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除资产「${row.name}（${row.asset_no}）」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  await deleteAssetApi(row.id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && query.page > 1) {
    query.page -= 1
  }
  load()
}

async function openFlow(row, action) {
  flow.action = action
  flow.meta = ACTION_META[action]
  flow.asset = row
  flow.lockEmployee = false
  flow.holderText = ''
  flow.form.employee_id = null
  flow.form.remark = ''

  if (action === 'return') {
    // 查询该资产最近一次领用记录，锁定归还人
    const res = await listAssetLogsApi({ asset_id: row.id, action: 'checkout', page: 1, size: 1 })
    const lastCheckout = res.items?.[0]
    if (lastCheckout?.employee) {
      flow.form.employee_id = lastCheckout.employee_id
      const emp = lastCheckout.employee
      flow.holderText = `${emp.name}（${emp.employee_no}）`
      flow.lockEmployee = true
    } else if (!userStore.isAdmin) {
      // 非管理员无法查到他人领用记录，直接提示
      ElMessage.warning('未找到该资产的领用记录，无法归还')
      return
    }
  }

  if (!flow.lockEmployee && flow.meta.needEmployee) {
    await loadEmployees()
  }

  flow.visible = true
}

async function handleFlowSubmit() {
  if (flow.meta.needEmployee && !flow.form.employee_id) {
    ElMessage.warning(flow.action === 'return' ? '未找到领用人信息' : '请选择领用员工')
    return
  }
  flow.saving = true
  try {
    await createAssetLogApi({
      asset_id: flow.asset.id,
      employee_id: flow.form.employee_id,
      action: flow.action,
      remark: flow.form.remark || null,
    })
    ElMessage.success(`${flow.meta.label}成功`)
    flow.visible = false
    load()
  } catch {
    /* 业务规则错误（重复领用、非法归还等）由拦截器统一提示 */
  } finally {
    flow.saving = false
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
.toolbar-right {
  display: flex;
  gap: 8px;
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
