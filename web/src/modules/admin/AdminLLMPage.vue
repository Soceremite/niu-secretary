<template>
  <section class="admin-resource llm-admin-page">
    <PageHeader eyebrow="平台" title="AI 渠道管理"
      description="逻辑模型路由与服务商接入。API key 只写入服务器环境变量文件，界面上永远不回显。">
      <el-button :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="primary" @click="openNewEndpoint">+ 接入服务商</el-button>
    </PageHeader>

    <div class="admin-resource-stats">
      <div class="admin-stat-card"><strong>{{ routes.length }}</strong><span>逻辑模型路由</span></div>
      <div class="admin-stat-card"><strong>{{ endpoints.length }}</strong><span>API 服务商</span></div>
      <div class="admin-stat-card"><strong>{{ endpoints.filter((e: any) => e.apiKeySet).length }}</strong><span>已配置 Key</span></div>
      <div class="admin-stat-card"><strong>{{ dirtyCount }}</strong><span>未保存改动</span></div>
    </div>

    <!-- 逻辑模型路由 -->
    <el-card class="data-card llm-panel">
      <template #header>
        <div class="llm-panel-head">
          <strong>逻辑模型路由</strong>
          <span class="llm-hint">每个「用途」走哪条渠道哪个模型；备用链按顺序兜底，全部失败才报错</span>
        </div>
      </template>
      <el-table :data="routes" size="small" border class="admin-data-table">
        <el-table-column prop="name" label="用途" width="130">
          <template #default="scope">
            <strong>{{ scope.row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="主选" min-width="230">
          <template #default="scope">
            <div class="route-primary">
              <el-select v-model="scope.row.endpoint" size="small" class="route-select"
                :class="{ dirty: scope.row._dirty }" @change="markDirty(scope.row)">
                <el-option v-for="ep in endpoints" :key="ep.name" :value="ep.name" :label="ep.name" />
              </el-select>
              <el-input v-model="scope.row.model" size="small" class="route-model"
                :class="{ dirty: scope.row._dirty }" @input="markDirty(scope.row)" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="备用链" min-width="280">
          <template #default="scope">
            <div class="fallback-chips">
              <el-tag v-for="(fb, idx) in scope.row.fallbacks" :key="idx" size="small"
                class="fallback-chip" closable @close="removeFallback(scope.row, idx)">
                {{ fb.endpoint }} · {{ fb.model }}
              </el-tag>
              <el-button size="small" text type="primary" class="fb-add" @click="addFallback(scope.row)">+ 备用</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" :disabled="!scope.row._dirty" @click="saveRoute(scope.row)">保存</el-button>
            <el-button size="small" :loading="probingRoute === scope.row.name" @click="probeRoute(scope.row)">试跑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- API 服务商 -->
    <el-card class="data-card llm-panel">
      <template #header>
        <div class="llm-panel-head">
          <strong>API 服务商</strong>
          <span class="llm-hint">第三方 OpenAI 兼容服务；测连通会拉取模型列表</span>
        </div>
      </template>
      <el-table :data="endpoints" size="small" border class="admin-data-table">
        <el-table-column prop="name" label="名称" width="130">
          <template #default="scope"><strong>{{ scope.row.name }}</strong></template>
        </el-table-column>
        <el-table-column prop="baseUrl" label="Base URL" min-width="240" show-overflow-tooltip />
        <el-table-column label="Key" width="190">
          <template #default="scope">
            <code class="key-env">{{ scope.row.api_key_env }}</code>
            <el-tag size="small" :type="scope.row.apiKeySet ? 'success' : 'danger'">
              {{ scope.row.apiKeySet ? '已配置' : '缺' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="style" label="风格" width="150" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="scope">
            <el-button size="small" :loading="testing === scope.row.name" @click="runTestEndpoint(scope.row)">测连通</el-button>
            <el-button size="small" text @click="editEndpoint(scope.row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="deleteEndpoint(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑服务商 -->
    <el-dialog v-model="endpointFormVisible" width="580px"
      :title="isEdit ? `编辑服务 — ${endpointForm?.endpoint || ''}` : '接入第三方服务商'"
      class="llm-dialog">
      <el-form label-width="120px" size="small">
        <el-form-item label="服务名">
          <el-input v-model="endpointForm.endpoint" placeholder="小写字母数字下划线，如 openrouter"
            :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="endpointForm.baseUrl" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item label="Key 环境变量">
          <el-input v-model="endpointForm.apiKeyEnv" placeholder="留空自动生成，如 OPENROUTER_API_KEY" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="endpointForm.apiKey" type="password" show-password
            :placeholder="isEdit ? '留空 = 保持现有 key 不变' : 'sk-...'" />
        </el-form-item>
        <el-form-item label="风格">
          <el-radio-group v-model="endpointForm.style">
            <el-radio value="chat_completions">chat / completions</el-radio>
            <el-radio value="responses">responses</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="超时（秒）">
          <el-input-number v-model="endpointForm.timeout_s" :min="10" :max="600" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="endpointFormVisible = false">取消</el-button>
        <el-button :loading="endpointTesting" @click="testBeforeSave">先试连通</el-button>
        <el-button type="primary" @click="saveEndpoint">保存</el-button>
      </template>
    </el-dialog>

    <!-- 连通/试跑结果 -->
    <el-dialog v-model="proberVisible" :title="proberTitle" width="560px" class="llm-dialog">
      <template v-if="proberMode === 'test'">
        <div class="probe-summary">
          <el-tag :type="probeResult?.ok && probeResult?.reachable ? 'success' : 'danger'" effect="dark">
            {{ probeResult?.reachable ? '可达' : '不可达' }}
          </el-tag>
          <span>{{ probeResult?.latencyMs }}ms · {{ probeResult?.modelCount }} 个模型 · HTTP {{ probeResult?.http || '-' }}</span>
        </div>
        <el-input v-model="modelFilter" placeholder="过滤模型名…" size="small" clearable class="model-filter" />
        <div class="model-list-box">
          <div v-for="m in filteredTestModels" :key="m" class="model-item">{{ m }}</div>
          <div v-if="!filteredTestModels.length" class="model-empty">无匹配模型</div>
        </div>
      </template>
      <template v-else>
        <div class="probe-summary">
          <el-tag :type="probeResult?.ok ? 'success' : 'danger'" effect="dark">
            {{ probeResult?.ok ? '成功' : '失败' }}
          </el-tag>
          <span>{{ probeResult?.endpoint }} · {{ probeResult?.model }} · {{ probeResult?.latencyMs }}ms</span>
        </div>
        <div class="probe-reply">{{ probeResult?.reply || probeResult?.error }}</div>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/shared/components/PageHeader.vue'
import { executeAdminAction } from '@/app/api/admin'
import { useAuthStore } from '@/app/stores/auth'

const auth = useAuthStore()
const routes = ref<any[]>([])
const endpoints = ref<any[]>([])
const testing = ref('')
const endpointTesting = ref(false)
const endpointFormVisible = ref(false)
const endpointForm = ref<any>({})
const isEdit = computed(() => endpoints.value.some((e) => e.name === endpointForm.value?.endpoint))
const proberVisible = ref(false)
const proberMode = ref<'test' | 'probe'>('test')
const probeResult = ref<any>(null)
const modelFilter = ref('')
const probingRoute = ref('')
const loading = ref(false)

const dirtyCount = computed(() => routes.value.filter((r) => r._dirty).length)

const filteredTestModels = computed(() => {
  const q = (modelFilter.value || '').toLowerCase()
  const list = probeResult.value?.models || []
  return q ? list.filter((m: string) => m.toLowerCase().includes(q)) : list
})

const proberTitle = computed(() =>
  proberMode.value === 'test'
    ? `连通测试 — ${(probeResult.value as any)?.endpoint || ''}`
    : `试跑 — ${(probeResult.value as any)?.route || ''}`
)

async function refresh() {
  loading.value = true
  try {
    const data = await executeAdminAction<any>(auth.token, 'llm.routes.list', {})
    routes.value = (data.routes || []).map((r: any) => ({ ...r }))
    endpoints.value = data.endpoints || []
  } catch (exc: any) {
    ElMessage.error(exc?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function markDirty(row: any) { row._dirty = true }

async function saveRoute(row: any) {
  try {
    await executeAdminAction(auth.token, 'llm.route.update', {
      route: row.name,
      endpoint: row.endpoint,
      model: row.model,
      fallbacks: row.fallbacks,
    })
    row._dirty = false
    ElMessage.success(`路由 ${row.name} 已保存并即时生效`)
  } catch (exc: any) {
    ElMessage.error(exc?.message || '保存失败')
  }
}

async function addFallback(row: any) {
  const ep = endpoints.value[0]?.name || 'opencode_go'
  row.fallbacks = [...(row.fallbacks || []), { endpoint: ep, model: row.model }]
  row._dirty = true
}

function removeFallback(row: any, idx: number) {
  row.fallbacks = (row.fallbacks || []).filter((_: any, i: number) => i !== idx)
  row._dirty = true
}

async function probeRoute(row: any) {
  probingRoute.value = row.name
  try {
    const r = await executeAdminAction<any>(auth.token, 'llm.probe.live',
      { route: row.name, prompt: '回复: pong' })
    probeResult.value = { ...r, route: row.name }
    proberMode.value = 'probe'
    proberVisible.value = true
  } catch (exc: any) {
    ElMessage.error(exc?.message || '试跑失败')
  } finally {
    probingRoute.value = ''
  }
}

async function runTestEndpoint(row: any) {
  testing.value = row.name
  try {
    const r = await executeAdminAction<any>(auth.token, 'llm.endpoint.test',
      { endpoint: row.name, timeout_s: 15 })
    probeResult.value = { ...r, endpoint: row.name }
    proberMode.value = 'test'
    proberVisible.value = true
  } catch (exc: any) {
    ElMessage.error(exc?.message || '测试失败')
  } finally {
    testing.value = ''
  }
}

function editEndpoint(row: any) {
  endpointForm.value = { ...row, apiKey: '', isNew: false }
  endpointFormVisible.value = true
}

function openNewEndpoint() {
  endpointForm.value = {
    endpoint: '', baseUrl: 'https://', apiKeyEnv: '', apiKey: '',
    style: 'chat_completions', timeout_s: 120, isNew: true,
  }
  endpointFormVisible.value = true
}

async function testBeforeSave() {
  endpointTesting.value = true
  try {
    const r = await executeAdminAction<any>(auth.token, 'llm.endpoint.test', {
      endpoint: endpointForm.value.endpoint || '__new_probe__',
      baseUrl: endpointForm.value.baseUrl,
      apiKeyEnv: endpointForm.value.apiKeyEnv || undefined,
      apiKey: endpointForm.value.apiKey || undefined,
      timeout_s: 15,
    })
    probeResult.value = r
    proberMode.value = 'test'
    proberVisible.value = true
  } catch (exc: any) {
    ElMessage.error(exc?.message || '测试失败')
  } finally {
    endpointTesting.value = false
  }
}

async function saveEndpoint() {
  try {
    await executeAdminAction(auth.token, 'llm.endpoint.upsert', endpointForm.value)
    endpointFormVisible.value = false
    ElMessage.success('服务商已保存')
    await refresh()
  } catch (exc: any) {
    ElMessage.error(exc?.message || '保存失败')
  }
}

async function deleteEndpoint(row: any) {
  try {
    await executeAdminAction(auth.token, 'llm.endpoint.delete', { endpoint: row.name })
    ElMessage.success('已删除')
    await refresh()
  } catch (exc: any) {
    ElMessage.error(exc?.message || '删除失败')
  }
}

let off: (() => void) | undefined
onMounted(() => {
  refresh()
  const handler = () => refresh()
  window.addEventListener('niu-admin-refresh', handler)
  off = () => window.removeEventListener('niu-admin-refresh', handler)
})
onBeforeUnmount(() => off?.())
</script>

<style scoped>
.llm-admin-page {
  display: grid;
  gap: 18px;
  padding-bottom: 26px;
}

.admin-resource-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 6px;
}

.llm-panel.el-card {
  border: 3px solid #262015;
  border-radius: 8px;
  background: #fff8e7;
  box-shadow: 6px 6px 0 #262015;
  overflow: hidden;
}

.llm-panel :deep(.el-card__header) {
  background: #f8d75a;
  border-bottom: 3px solid #262015;
  padding: 10px 16px;
}

.llm-panel :deep(.el-card__header) strong {
  color: #261f15;
  font-size: 15px;
}

.llm-panel :deep(.el-card__body) {
  padding: 0;
}

.llm-panel-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.llm-panel-head .llm-hint {
  font-size: 12px;
  color: #6b5742;
  font-weight: 500;
}

.route-primary {
  display: flex;
  gap: 6px;
  align-items: center;
}

.route-select { width: 132px; flex-shrink: 0; }
.route-model { flex: 1; min-width: 120px; }

.route-select.dirty :deep(.el-input__wrapper),
.route-model.dirty :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 2px var(--niu-gold);
}

.fallback-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  align-items: center;
}

.fallback-chip.el-tag {
  border: 2px solid #262015;
  border-radius: 999px;
  background: #f6e8be;
  color: #2a2118;
  font-weight: 600;
  box-shadow: 2px 2px 0 #262015;
}

.fb-add { font-weight: 800; }

.key-env {
  padding: 2px 8px;
  border-radius: 6px;
  background: #f6e8be;
  border: 1px solid rgba(38, 32, 21, 0.24);
  color: #4a3c28;
  font-size: 12px;
  margin-right: 6px;
}

.model-filter { margin: 12px 0; }

.model-list-box {
  max-height: 320px;
  overflow: auto;
  border: 2px solid #262015;
  border-radius: 8px;
  background: #fff8e7;
  box-shadow: 3px 3px 0 #262015;
  padding: 6px;
  margin-top: 4px;
}

.model-item {
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12.5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: #2a2118;
}

.model-item:hover { background: #fff1c3; }

.probe-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 2px solid #262015;
  border-radius: 8px;
  background: #fff8e7;
  box-shadow: 3px 3px 0 #262015;
}

.probe-reply {
  margin-top: 12px;
  padding: 14px;
  border: 2px solid #262015;
  border-radius: 8px;
  background: #fff8e7;
  box-shadow: 3px 3px 0 #262015;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13.5px;
  line-height: 1.6;
  max-height: 260px;
  overflow: auto;
}

:deep(.llm-dialog .el-dialog) {
  border: 3px solid #262015;
  border-radius: 12px !important;
  box-shadow: 10px 10px 0 #262015;
  background: #fff8e7;
}
</style>
