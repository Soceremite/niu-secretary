<template>
  <div class="llm-admin-page">
    <!-- 逻辑模型路由 -->
    <section class="llm-section">
      <h3>🔧 逻辑模型路由</h3>
      <p class="llm-hint">每个「用途」走哪条渠道哪个模型；fallback 按顺序兜底。修改后立即生效（写回 config/models.yaml）。</p>
      <el-table :data="routes" size="small" border class="llm-table">
        <el-table-column prop="name" label="用途" width="120">
          <template #default="scope">
            <strong>{{ scope.row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="主选" min-width="220">
          <template #default="scope">
            <el-select v-model="scope.row.endpoint" size="small" style="width:140px" @change="markDirty(scope.row)">
              <el-option v-for="ep in endpoints" :key="ep.name" :value="ep.name" :label="ep.name" />
            </el-select>
            <el-input v-model="scope.row.model" size="small" style="width:200px" @input="markDirty(scope.row)" />
          </template>
        </el-table-column>
        <el-table-column label="备用链" min-width="260">
          <template #default="scope">
            <div class="fallback-chips">
              <el-tag v-for="(fb, idx) in scope.row.fallbacks" :key="idx" size="small" type="info" closable @close="removeFallback(scope.row, idx)">
                {{ fb.endpoint }} · {{ fb.model }}
              </el-tag>
              <el-button size="small" text type="primary" @click="addFallback(scope.row)">+备用</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" type="primary" :disabled="!scope.row._dirty" @click="saveRoute(scope.row)">保存</el-button>
            <el-button size="small" :loading="probingRoute === scope.row.name" @click="probeRoute(scope.row)">试跑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- API 服务商 -->
    <section class="llm-section">
      <h3>🔌 API 服务商</h3>
      <p class="llm-hint">第三方 OpenAI 兼容服务。API key 只写入服务器 env 文件，永远不回显。</p>
      <el-table :data="endpoints" size="small" border class="llm-table">
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="baseUrl" label="Base URL" min-width="240" />
        <el-table-column label="Key" width="150">
          <template #default="scope">
            <code>{{ scope.row.api_key_env }}</code>
            <el-tag size="small" :type="scope.row.apiKeySet ? 'success' : 'danger'" style="margin-left:6px">
              {{ scope.row.apiKeySet ? '已配置' : '缺' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="style" label="风格" width="140" />
        <el-table-column label="操作" width="260">
          <template #default="scope">
            <el-button size="small" :loading="testing === scope.row.name" @click="runTestEndpoint(scope.row)">测连通</el-button>
            <el-button size="small" text @click="editEndpoint(scope.row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="deleteEndpoint(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-button type="primary" style="margin-top:12px" @click="openNewEndpoint">+接入第三方服务商</el-button>
    </section>

    <!-- 编辑 popper -->
    <el-dialog v-model="endpointFormVisible" :title="endpointForm.name ? '编辑服务' : '接入第三方服务商'" width="560px">
      <el-form label-width="110px" size="small">
        <el-form-item label="服务名">
          <el-input v-model="endpointForm.endpoint" placeholder="如 openrouter / my_gateway（小写字母数字下划线）" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="endpointForm.baseUrl" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item label="Key 环境变量">
          <el-input v-model="endpointForm.apiKeyEnv" placeholder="留空自动生成 NAME_API_KEY" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="endpointForm.apiKey" placeholder="留空 = 不改 key，仅改配置" show-password />
        </el-form-item>
        <el-form-item label="风格">
          <el-radio-group v-model="endpointForm.style">
            <el-radio value="chat_completions">chat/completions</el-radio>
            <el-radio value="responses">responses</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="超时(s)">
          <el-input-number v-model="endpointForm.timeout_s" :min="10" :max="600" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="endpointFormVisible = false">取消</el-button>
        <el-button :loading="endpointTesting" @click="testBeforeSave">先试连通</el-button>
        <el-button type="primary" @click="saveEndpoint">保存</el-button>
      </template>
    </el-dialog>

    <!-- 模型列表 & 试跑结果抽屉 -->
    <el-drawer v-model="proberVisible" :title="proberTitle" size="520px">
      <template v-if="proberMode === 'test'">
        <div class="probe-summary">
          <el-tag :type="probeResult?.ok ? 'success' : 'danger'">{{ probeResult?.reachable ? '可达' : '不可达' }}</el-tag>
          <span style="margin-left:10px">{{ probeResult?.latencyMs }}ms · {{ probeResult?.modelCount }} 个模型</span>
        </div>
        <el-input v-model="modelFilter" placeholder="过滤模型名称" size="small" clearable style="margin-top:10px" />
        <ul class="model-list">
          <li v-for="m in filteredTestModels" :key="m">{{ m }}</li>
        </ul>
      </template>
      <template v-else>
        <div class="probe-summary">
          <el-tag :type="probeResult?.ok ? 'success' : 'danger'">{{ probeResult?.ok ? '成功' : '失败' }}</el-tag>
          <span style="margin-left:10px">{{ probeResult?.endpoint }} · {{ probeResult?.model }} · {{ probeResult?.latencyMs }}ms</span>
        </div>
        <div class="probe-reply">{{ probeResult?.reply || probeResult?.error }}</div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, computed, ref } from 'vue'
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

const filteredTestModels = computed(() => {
  const q = (modelFilter.value || '').toLowerCase()
  const list = probeResult.value?.models || []
  return q ? list.filter((m: string) => m.toLowerCase().includes(q)) : list
})

async function refresh() {
  loading.value = true
  try {
    const data = await executeAdminAction<any>(auth.token, 'llm.routes.list', {})
    routes.value = (data.routes || []).map((r: any) => ({ ...r }))
    endpoints.value = data.endpoints || []
  } finally {
    loading.value = false
  }
}

function markDirty(row: any) { row._dirty = true }

async function saveRoute(row: any) {
  await executeAdminAction(auth.token, 'llm.route.update', {
    route: row.name,
    endpoint: row.endpoint,
    model: row.model,
    fallbacks: row.fallbacks,
  })
  row._dirty = false
  await refresh()
}

async function addFallback(row: any) {
  const ep = endpoints.value[0]?.name || 'opencode_go'
  row.fallbacks = [...(row.fallbacks || []), { endpoint: ep, model: '' }]
  markDirty(row)
}

function removeFallback(row: any, idx: number) {
  row.fallbacks = (row.fallbacks || []).filter((_: any, i: number) => i !== idx)
  markDirty(row)
}

async function probeRoute(row: any) {
  probingRoute.value = row.name
  try {
    const r = await executeAdminAction<any>(auth.token, 'llm.probe.live', {
      route: row.name, prompt: '回复: pong'
    })
    probeResult.value = { ...r, route: row.name }
    proberMode.value = 'probe'
    proberVisible.value = true
  } finally {
    probingRoute.value = ''
  }
}

async function runTestEndpoint(row: any) {
  testing.value = row.name
  try {
    const r = await executeAdminAction<any>(auth.token, 'llm.endpoint.test', {
      endpoint: row.name, timeout_s: 15,
    })
    probeResult.value = { ...r, endpoint: row.name }
    proberMode.value = 'test'
    proberVisible.value = true
  } finally {
    testing.value = ''
  }
}

function newEndpointTemplate() {
  return { endpoint: '', baseUrl: 'https://', apiKeyEnv: '', apiKey: '', style: 'chat_completions', timeout_s: 120 }
}

function openNewEndpoint() {
  endpointForm.value = { ...newEndpointTemplate(), isNew: true }
  endpointFormVisible.value = true
}

function editEndpoint(row: any) {
  endpointForm.value = { ...row, apiKey: '', isNew: false }
  endpointFormVisible.value = true
}

async function testBeforeSave() {
  endpointTesting.value = true
  try {
    const r = await executeAdminAction<any>(auth.token, 'llm.endpoint.test', {
      endpoint: endpointForm.value.endpoint || '__new__',
      baseUrl: endpointForm.value.baseUrl,
      apiKeyEnv: endpointForm.value.apiKeyEnv,
      apiKey: endpointForm.value.apiKey || undefined,
      timeout_s: 15,
    })
    probeResult.value = r
    proberMode.value = 'test'
    proberVisible.value = true
  } finally {
    endpointTesting.value = false
  }
}

async function saveEndpoint() {
  await executeAdminAction(auth.token, 'llm.endpoint.upsert', endpointForm.value)
  endpointFormVisible.value = false
  await refresh()
}

async function deleteEndpoint(row: any) {
  await executeAdminAction(auth.token, 'llm.endpoint.delete', { endpoint: row.name })
  await refresh()
}

const proberTitle = computed(() =>
  proberMode.value === 'test'
    ? `连通测试 — ${(probeResult.value as any)?.endpoint || ''}`
    : `试跑 — ${(probeResult.value as any)?.route || ''}`
)

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
.llm-admin-page { display: grid; gap: 16px; }
.llm-section { display: grid; gap: 6px; }
.llm-section h3 { margin: 0; }
.llm-hint { font-size: 13px; color: #888; margin: 0; }
.fallback-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.probe-summary { display: flex; align-items: center; }
.model-list li { list-style: none; }
.probe-reply { margin-top: 10px; padding: 10px; border-radius: 6px; background: #f6f6f6; white-space: pre-wrap; word-break: break-all; }
</style>
