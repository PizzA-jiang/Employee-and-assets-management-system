<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>AI 配置管理</span>
        <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
      </div>
    </template>

    <el-tabs v-model="activeTab">
      <!-- LLM API -->
      <el-tab-pane label="API配置" name="api">
        <el-form label-width="140px" class="config-form">
          <el-form-item label="API Key">
            <el-input
              v-model="form.mimo_api_key"
              placeholder="请输入API Key"
              clearable
            />
            <div class="form-tip">
              <el-button link type="primary" size="small" @click="handleTestApi" :loading="testing">测试连接</el-button>
              <span v-if="testResult" :class="testResult.success ? 'test-ok' : 'test-fail'">
                {{ testResult.message }}
                <template v-if="testResult.model_used"> (模型: {{ testResult.model_used }})</template>
              </span>
            </div>
          </el-form-item>
          <el-form-item label="API地址">
            <el-input v-model="form.mimo_base_url" placeholder="https://llm.goaichat.top/v1" />
            <div class="form-tip">OpenAI兼容格式地址，例如: https://llm.goaichat.top/v1</div>
          </el-form-item>
          <el-form-item label="模型">
            <el-select v-model="form.mimo_model" style="width: 100%" filterable>
              <el-option
                v-for="m in modelOptions"
                :key="m.id"
                :label="m.name"
                :value="m.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="超时时间(秒)">
            <el-input-number v-model.number="form.llm_timeout" :min="5" :max="120" :step="5" />
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 本地模型 -->
      <el-tab-pane label="本地模型" name="local">
        <el-form label-width="140px" class="config-form">
          <el-form-item label="启用本地模型">
            <el-switch v-model="localEnabled" />
          </el-form-item>
          <el-form-item label="端点地址">
            <el-input
              v-model="form.local_llm_endpoint"
              placeholder="http://localhost:11434/v1/chat/completions"
              :disabled="!localEnabled"
            />
            <div class="form-tip">本地模型的完整端点地址</div>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- MCP -->
      <el-tab-pane label="MCP服务器" name="mcp">
        <div class="mcp-toolbar">
          <el-button type="primary" size="small" @click="openMcpDialog(null)">新增服务器</el-button>
        </div>
        <el-table :data="mcpServers" border stripe size="small">
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="host" label="地址" min-width="140" />
          <el-table-column prop="port" label="端口" width="80" align="center" />
          <el-table-column prop="username" label="用户名" width="100" />
          <el-table-column prop="database" label="数据库" width="120" />
          <el-table-column prop="is_enabled" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
                {{ row.is_enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="password" label="密码" width="100">
            <template #default="{ row }">
              <span class="masked">{{ row.password_masked || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="handleTestMcp(row)">测试</el-button>
              <el-button link type="primary" size="small" @click="openMcpDialog(row)">编辑</el-button>
              <el-popconfirm title="确定删除该MCP服务器？" @confirm="handleDeleteMcp(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- RAG -->
      <el-tab-pane label="RAG" name="rag">
        <el-form label-width="140px" class="config-form">
          <el-form-item label="检索文档块数">
            <el-input-number v-model.number="form.rag_top_k" :min="1" :max="20" />
          </el-form-item>
          <el-form-item label="最大上下文长度">
            <el-input-number v-model.number="form.rag_max_context_len" :min="500" :max="16000" :step="500" />
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <!-- MCP Server Dialog -->
    <el-dialog
      v-model="mcpDialog.visible"
      :title="mcpDialog.id ? '编辑MCP服务器' : '新增MCP服务器'"
      width="520px"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <el-form :model="mcpDialog.form" label-width="90px" :rules="mcpRules" ref="mcpFormRef">
        <el-form-item label="名称" prop="name">
          <el-input v-model="mcpDialog.form.name" placeholder="如: 资产数据库" />
        </el-form-item>
        <el-form-item label="地址" prop="host">
          <el-input v-model="mcpDialog.form.host" placeholder="localhost" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model.number="mcpDialog.form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="mcpDialog.form.username" placeholder="可选" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="mcpDialog.form.password" placeholder="可选" />
        </el-form-item>
        <el-form-item label="数据库">
          <el-input v-model="mcpDialog.form.database" placeholder="可选，留空则可查询所有库" />
        </el-form-item>
        <el-form-item label="字符集">
          <el-select v-model="mcpDialog.form.charset" style="width:100%">
            <el-option label="utf8mb4" value="utf8mb4" />
            <el-option label="utf8" value="utf8" />
            <el-option label="gbk" value="gbk" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model.number="mcpDialog.form.is_enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model.number="mcpDialog.form.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mcpDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="mcpDialog.saving" @click="handleMcpSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getAIConfigsApi, updateAIConfigsApi, testAIConfigApi, listAIModelsApi,
  fixAIConfigsApi,
  listMCPServersApi, createMCPServerApi, updateMCPServerApi,
  deleteMCPServerApi, testMCPServerApi,
} from '../api/aiConfig'

const activeTab = ref('api')
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const mcpServers = ref([])
const mcpFormRef = ref(null)
const modelOptions = ref([])

const form = reactive({
  mimo_api_key: '',
  mimo_base_url: 'https://llm.goaichat.top/v1',
  mimo_model: 'mimo-v2.5-pro',
  local_llm_endpoint: '',
  local_llm_enabled: 'false',
  rag_top_k: 5,
  rag_max_context_len: 4000,
  llm_timeout: 30,
})

const localEnabled = ref(false)

const mcpDialog = reactive({
  visible: false,
  id: null,
  saving: false,
  form: {
    name: '',
    host: 'localhost',
    port: 3306,
    username: '',
    password: '',
    database: '',
    charset: 'utf8mb4',
    is_enabled: 1,
    sort_order: 0,
  },
})

const mcpRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
}

async function load() {
  try {
    const list = await getAIConfigsApi()
    for (const item of list) {
      if (item.config_key in form) {
        const raw = item.config_value
        if (item.config_key === 'local_llm_enabled') {
          form[item.config_key] = raw
        } else {
          form[item.config_key] = item.config_type === 'integer' ? Number(raw) || form[item.config_key] : raw
        }
      }
    }
    localEnabled.value = form.local_llm_enabled === 'true'
  } catch { /* handled */ }
  try {
    modelOptions.value = await listAIModelsApi()
  } catch { modelOptions.value = [] }
  await loadMcpServers()
}

async function loadMcpServers() {
  try {
    mcpServers.value = await listMCPServersApi()
  } catch { /* handled */ }
}

async function handleSave() {
  saving.value = true
  form.local_llm_enabled = localEnabled.value ? 'true' : 'false'
  const configs = Object.entries(form).map(([config_key, config_value]) => ({
    config_key,
    config_value: String(config_value),
  }))
  try {
    await updateAIConfigsApi(configs)
    try { await fixAIConfigsApi() } catch { /* ignore */ }
    ElMessage.success('配置已保存')
  } catch { /* handled */ } finally {
    saving.value = false
  }
}

async function handleTestApi() {
  if (!form.mimo_api_key) {
    ElMessage.warning('请先输入API Key')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testAIConfigApi({ config_key: 'mimo_api_key', config_value: form.mimo_api_key })
  } catch {
    testResult.value = { success: false, message: '测试请求失败' }
  } finally {
    testing.value = false
  }
}

// ─── MCP CRUD ──────────────────────────────────────────────────────

function openMcpDialog(row) {
  if (row) {
    mcpDialog.id = row.id
    mcpDialog.form = {
      name: row.name,
      host: row.host,
      port: row.port,
      username: row.username || '',
      password: row.password_masked || '',
      database: row.database || '',
      charset: row.charset || 'utf8mb4',
      is_enabled: row.is_enabled,
      sort_order: row.sort_order || 0,
    }
  } else {
    mcpDialog.id = null
    mcpDialog.form = {
      name: '', host: 'localhost', port: 3306, username: '',
      password: '', database: '', charset: 'utf8mb4', is_enabled: 1, sort_order: 0,
    }
  }
  mcpDialog.visible = true
}

async function handleMcpSave() {
  if (!mcpFormRef.value) return
  try {
    await mcpFormRef.value.validate()
  } catch { return }

  mcpDialog.saving = true
  try {
    if (mcpDialog.id) {
      await updateMCPServerApi(mcpDialog.id, mcpDialog.form)
    } else {
      await createMCPServerApi(mcpDialog.form)
    }
    ElMessage.success('保存成功')
    mcpDialog.visible = false
    await loadMcpServers()
  } catch { /* handled */ } finally {
    mcpDialog.saving = false
  }
}

async function handleDeleteMcp(id) {
  try {
    await deleteMCPServerApi(id)
    ElMessage.success('删除成功')
    await loadMcpServers()
  } catch { /* handled */ }
}

async function handleTestMcp(row) {
  try {
    const res = await testMCPServerApi({
      host: row.host,
      port: row.port,
      username: row.username,
      database: row.database,
    })
    if (res.success) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  } catch { /* handled */ }
}

onMounted(load)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.config-form {
  max-width: 600px;
  margin-top: 16px;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.test-ok { color: #67c23a; }
.test-fail { color: #f56c6c; }
.clickable { cursor: pointer; }
.masked { color: #909399; font-size: 12px; }
.mcp-toolbar {
  margin-bottom: 12px;
}
</style>
