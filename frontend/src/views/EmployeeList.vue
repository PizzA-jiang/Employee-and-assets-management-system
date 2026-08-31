<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="姓名/工号/部门/职位/电话" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="query.name" placeholder="按姓名搜索" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="query.department" placeholder="按部门搜索" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="在职" :value="1" />
            <el-option label="离职" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
          <el-button :icon="'Refresh'" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <div class="toolbar-right">
        <el-button v-if="userStore.isAdmin" type="success" :icon="'Download'" @click="handleExport">导出Excel</el-button>
        <el-button v-if="userStore.isAdmin" type="primary" :icon="'Plus'" @click="openAdd">新增员工</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="employee_no" label="工号" width="110" align="center" />
      <el-table-column prop="name" label="姓名" width="110" align="center" />
      <el-table-column prop="department" label="部门" min-width="110" align="center">
        <template #default="{ row }">{{ row.department || '-' }}</template>
      </el-table-column>
      <el-table-column prop="position" label="职位" min-width="110" align="center">
        <template #default="{ row }">{{ row.position || '-' }}</template>
      </el-table-column>
      <el-table-column prop="phone" label="电话" width="130" align="center">
        <template #default="{ row }">{{ row.phone || '-' }}</template>
      </el-table-column>
      <el-table-column prop="hire_date" label="入职日期" width="110" align="center">
        <template #default="{ row }">{{ formatDate(row.hire_date) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="EMPLOYEE_STATUS[row.status]?.tag || 'info'" size="small">
            {{ EMPLOYEE_STATUS[row.status]?.label ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" align="center">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column v-if="userStore.isAdmin" label="操作" width="150" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
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

  <!-- 新增/编辑弹窗 -->
  <el-dialog
    v-model="dialog.visible"
    :title="dialog.isEdit ? '编辑员工' : '新增员工'"
    width="520px"
    destroy-on-close
    :close-on-click-modal="false"
  >
    <el-alert
      v-if="!dialog.isEdit"
      title="将同步创建登录账号（用户名 + 初始密码），创建后该员工即可登录系统"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />
    <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="工号" prop="employee_no">
            <el-input v-model="form.employee_no" placeholder="如 E001" maxlength="30" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="姓名" prop="name">
            <el-input v-model="form.name" maxlength="50" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="部门">
            <el-input v-model="form.department" maxlength="50" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="职位">
            <el-input v-model="form.position" maxlength="50" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="电话">
            <el-input v-model="form.phone" maxlength="20" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="入职日期">
            <el-date-picker
              v-model="form.hire_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col v-if="!dialog.isEdit" :span="24">
          <el-divider content-position="left">登录账号</el-divider>
        </el-col>
        <el-col v-if="!dialog.isEdit" :span="12">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" maxlength="50" placeholder="3-50位字符" />
          </el-form-item>
        </el-col>
        <el-col v-if="!dialog.isEdit" :span="12">
          <el-form-item label="初始密码" prop="password">
            <el-input v-model="form.password" type="password" show-password maxlength="50" placeholder="至少6位" />
          </el-form-item>
        </el-col>
        <el-col v-if="dialog.isEdit" :span="12">
          <el-form-item label="在职状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option label="在职" :value="1" />
              <el-option label="离职" :value="0" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button @click="dialog.visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listEmployeesApi,
  createEmployeeApi,
  updateEmployeeApi,
  deleteEmployeeApi,
} from '../api/employees'
import { registerApi } from '../api/auth'
import { useUserStore } from '../stores/user'
import { formatDateTime, formatDate } from '../utils/format'
import { EMPLOYEE_STATUS } from '../constants/asset'

const userStore = useUserStore()

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)

const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
  name: '',
  department: '',
  status: null,
})

const formRef = ref()
const dialog = reactive({
  visible: false,
  isEdit: false,
  editId: null,
})

function emptyForm() {
  return {
    employee_no: '',
    name: '',
    department: '',
    position: '',
    phone: '',
    hire_date: null,
    status: 1,
    username: '',
    password: '',
  }
}

const form = reactive(emptyForm())

const formRules = {
  employee_no: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  username: [
    { required: true, message: '请输入登录用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度至少 6 位', trigger: 'blur' },
  ],
}

async function load() {
  loading.value = true
  try {
    const params = {
      page: query.page,
      size: query.size,
    }
    if (query.keyword) params.keyword = query.keyword
    if (query.name) params.name = query.name
    if (query.department) params.department = query.department
    if (query.status !== null && query.status !== '') params.status = query.status
    const res = await listEmployeesApi(params)
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
  query.name = ''
  query.department = ''
  query.status = null
  handleSearch()
}

function handleExport() {
  import('axios').then(({ default: axios }) => {
    const token = localStorage.getItem('asset_token')
    axios.get('/api/employees/export/excel', {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob',
    }).then(res => {
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'employees_export.xlsx')
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
    employee_no: row.employee_no,
    name: row.name,
    department: row.department || '',
    position: row.position || '',
    phone: row.phone || '',
    hire_date: row.hire_date ? formatDate(row.hire_date) : null,
    status: row.status,
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
  let accountCreated = false
  try {
    if (dialog.isEdit) {
      const payload = {
        employee_no: form.employee_no,
        name: form.name,
        department: form.department || null,
        position: form.position || null,
        phone: form.phone || null,
        hire_date: form.hire_date || null,
        status: form.status,
      }
      await updateEmployeeApi(dialog.editId, payload)
      ElMessage.success('更新成功')
    } else {
      // 先创建登录账号，再创建员工档案（employees.user_id 非空必填）
      const user = await registerApi({
        username: form.username,
        password: form.password,
        role: 'employee',
      })
      accountCreated = true
      await createEmployeeApi({
        employee_no: form.employee_no,
        name: form.name,
        department: form.department || null,
        position: form.position || null,
        phone: form.phone || null,
        hire_date: form.hire_date || null,
        user_id: user.id,
      })
      ElMessage.success('新增成功')
    }
    dialog.visible = false
    load()
  } catch (e) {
    if (!dialog.isEdit && accountCreated) {
      ElMessage.warning('登录账号已创建成功，但员工档案未完成，请在系统中补建该员工的档案信息')
    }
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除员工「${row.name}（${row.employee_no}）」吗？删除后不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  await deleteEmployeeApi(row.id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && query.page > 1) {
    query.page -= 1
  }
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
