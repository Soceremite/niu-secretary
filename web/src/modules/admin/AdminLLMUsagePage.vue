<template>
  <section class="admin-resource llm-admin-page">
    <PageHeader eyebrow="平台" title="API 用量"
      description="统一 LLM 层的调用记录：谁在用什么模型、失败与降级情况、token 消耗。只记元信息，不记 prompt 正文。">
      <el-radio-group v-model="days" size="small" @change="refresh">
        <el-radio-button :value="1">24 小时</el-radio-button>
        <el-radio-button :value="7">7 天</el-radio-button>
        <el-radio-button :value="30">30 天</el-radio-button>
        <el-radio-button :value="90">90 天</el-radio-button>
      </el-radio-group>
      <el-button :loading="loading" @click="refresh">刷新</el-button>
    </PageHeader>

    <div class="admin-resource-stats">
      <div class="admin-stat-card"><strong>{{ stats.total }}</strong><span>调用次数</span></div>
      <div class="admin-stat-card"><strong>{{ failRate }}</strong><span>失败率</span></div>
      <div class="admin-stat-card"><strong>{{ stats.fallbacks }}</strong><span>走了备选</span></div>
      <div class="admin-stat-card"><strong>{{ stats.skipped }}</strong><span>端点被跳过</span></div>
      <div class="admin-stat-card"><strong>{{ stats.avgLatencyMs }}ms</strong><span>平均耗时</span></div>
      <div class="admin-stat-card"><strong>{{ tokenText }}</strong><span>tokens 入 / 出</span></div>
    </div>

    <el-card class="data-card llm-panel">
      <template #header>
        <div class="llm-panel-head">
          <strong>按路由 / 模型</strong>
          <span class="llm-hint">
            「走了备选」不为 0 说明主选失败过；「被跳过」通常是端点缺 key——这两列是排查路由问题的探针
          </span>
        </div>
      </template>
      <el-table :data="stats.routes" size="small" border class="admin-data-table"
        empty-text="该时间段内没有调用记录">
        <el-table-column prop="logic_model" label="用途" width="140">
          <template #default="{ row }"><strong>{{ row.logic_model }}</strong></template>
        </el-table-column>
        <el-table-column prop="endpoint" label="端点" width="150" show-overflow-tooltip />
        <el-table-column prop="model" label="模型" min-width="190" show-overflow-tooltip />
        <el-table-column prop="calls" label="次数" width="80" align="right" />
        <el-table-column label="失败" width="76" align="right">
          <template #default="{ row }">
            <span :class="{ 'usage-bad': row.failed > 0 }">{{ row.failed }}</span>
          </template>
        </el-table-column>
        <el-table-column label="备选" width="76" align="right">
          <template #default="{ row }">
            <span :class="{ 'usage-warn': row.fallbacks > 0 }">{{ row.fallbacks }}</span>
          </template>
        </el-table-column>
        <el-table-column label="跳过" width="76" align="right">
          <template #default="{ row }">
            <span :class="{ 'usage-warn': row.skipped > 0 }">{{ row.skipped }}</span>
          </template>
        </el-table-column>
        <el-table-column label="平均耗时" width="106" align="right">
          <template #default="{ row }">{{ row.avg_ms == null ? '-' : `${row.avg_ms}ms` }}</template>
        </el-table-column>
        <el-table-column label="tokens 入/出" width="140" align="right">
          <template #default="{ row }">{{ row.in_tok }} / {{ row.out_tok }}</template>
        </el-table-column>
        <el-table-column label="最近一次" width="170">
          <template #default="{ row }">{{ fmtTime(row.last_ts) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="data-card llm-panel">
      <template #header>
        <div class="llm-panel-head">
          <strong>按调用方</strong>
          <span class="llm-hint">谁在花 token：服务 / cron 管线 / CLI 脚本</span>
        </div>
      </template>
      <el-table :data="stats.callers" size="small" border class="admin-data-table"
        empty-text="该时间段内没有调用记录">
        <el-table-column prop="caller" label="调用方" min-width="240" show-overflow-tooltip />
        <el-table-column prop="calls" label="次数" width="100" align="right" />
        <el-table-column label="失败" width="100" align="right">
          <template #default="{ row }">
            <span :class="{ 'usage-bad': row.failed > 0 }">{{ row.failed }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="stats.recentFailures.length" class="data-card llm-panel">
      <template #header>
        <div class="llm-panel-head">
          <strong>最近的失败 / 跳过</strong>
          <span class="llm-hint">最多 50 条；错误正文已被截断，完整堆栈见服务日志</span>
        </div>
      </template>
      <el-table :data="stats.recentFailures" size="small" border class="admin-data-table">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.ts) }}</template>
        </el-table-column>
        <el-table-column prop="caller" label="调用方" width="180" show-overflow-tooltip />
        <el-table-column prop="logic_model" label="用途" width="120" />
        <el-table-column prop="endpoint" label="端点" width="140" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="140" />
        <el-table-column prop="error_type" label="错误类型" width="160" show-overflow-tooltip />
        <el-table-column prop="error_msg" label="摘要" min-width="260" show-overflow-tooltip />
      </el-table>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/shared/components/PageHeader.vue'
import { executeAdminAction } from '@/app/api/admin'
import { useAuthStore } from '@/app/stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const days = ref(7)
let timer: number | undefined
const stats = ref<any>({
  total: 0, ok: 0, failed: 0, skipped: 0, fallbacks: 0,
  avgLatencyMs: 0, inputTokens: 0, outputTokens: 0,
  routes: [], callers: [], recentFailures: [],
})

const failRate = computed(() => {
  const total = stats.value.total || 0
  if (!total) return '0%'
  return `${Math.round(((stats.value.failed || 0) / total) * 1000) / 10}%`
})
const tokenText = computed(
  () => `${stats.value.inputTokens} / ${stats.value.outputTokens}`,
)

function fmtTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function refresh() {
  loading.value = true
  try {
    const data = await executeAdminAction<any>(auth.token, 'llm.usage.report', {
      days: days.value,
      limit: 50,
    })
    stats.value = {
      total: data.total || 0,
      ok: data.ok || 0,
      failed: data.failed || 0,
      skipped: data.skipped || 0,
      fallbacks: data.fallbacks || 0,
      avgLatencyMs: data.avgLatencyMs || 0,
      inputTokens: data.inputTokens || 0,
      outputTokens: data.outputTokens || 0,
      routes: data.routes || [],
      callers: data.callers || [],
      recentFailures: data.recentFailures || [],
    }
  } catch (exc: any) {
    ElMessage.error(exc?.message || '加载用量失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 60_000)
})
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.usage-bad { color: #c0392b; font-weight: 700; }
.usage-warn { color: #b8860b; font-weight: 700; }
</style>
