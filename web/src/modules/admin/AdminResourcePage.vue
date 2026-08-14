<template>
  <section class="admin-resource" :class="{ 'admin-resource--cards': prefersCardLayout }">
    <PageHeader :eyebrow="config.module" :title="config.title" :description="config.description">
      <el-button v-if="config.createAction" type="primary" @click="openCreate">新增</el-button>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </PageHeader>

    <section class="admin-resource-toolbar" aria-label="管理台筛选">
      <div class="admin-search-box">
        <span>筛选</span>
        <el-input
          v-model="filters.keyword"
          clearable
          placeholder="按标题、日期、来源或备注搜索"
          @clear="filters.page = 1"
        />
      </div>
      <el-date-picker
        v-model="filters.range"
        type="daterange"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        unlink-panels
      />
      <div class="admin-toolbar-actions">
        <el-button :loading="loading" @click="load">应用</el-button>
        <el-button text @click="resetFilters">重置</el-button>
      </div>
    </section>

    <div class="admin-resource-stats">
      <div v-for="card in resourceStats" :key="card.label" class="admin-stat-card">
        <strong>{{ card.value }}</strong>
        <span>{{ card.label }}</span>
      </div>
    </div>

    <el-row v-if="resourceKey === 'platform.ops'" :gutter="16" class="ops-row">
      <el-col :xs="12" :md="6" v-for="card in summaryCards" :key="card.label">
        <el-card shadow="never" class="metric-card">
          <strong>{{ card.value }}</strong>
          <span>{{ card.label }}</span>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="!showCardList" shadow="never" class="data-card">
      <el-table
        v-loading="loading"
        :data="pagedRows"
        row-key="id"
        stripe
        border
        class="admin-data-table"
        :height="adminTableHeight"
        :row-class-name="rowClassName"
        @row-dblclick="openInspect"
      >
        <el-table-column
          v-for="column in config.columns"
          :key="column.key"
          :prop="column.key"
          :label="column.label"
          :width="column.width"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <el-tag v-if="column.key === 'done'" :type="row.done ? 'success' : 'info'">
              {{ row.done ? '已完成' : '未完成' }}
            </el-tag>
            <span v-else>{{ formatCell(row[column.key]) }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="hasActions" label="操作" width="280">
          <template #default="{ row }">
            <div class="admin-row-actions">
              <el-button size="small" @click="openInspect(row)">详情</el-button>
              <el-button v-if="config.toggleAction" size="small" @click="toggle(row)">
                {{ row.done ? '设为未完成' : '完成' }}
              </el-button>
              <el-button v-if="config.updateAction" size="small" @click="openEdit(row)">编辑</el-button>
              <el-popconfirm
                v-if="config.deleteAction"
                title="确认删除这条记录？"
                confirm-button-text="确认"
                cancel-button-text="取消"
                @confirm="remove(row)"
              >
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无匹配数据">
            <el-button v-if="config.createAction" type="primary" @click="openCreate">新增第一条</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="admin-table-footer">
        <span>显示 {{ pagedRows.length }} / {{ filteredRows.length }} 条，共 {{ rows.length }} 条</span>
        <el-pagination
          v-model:current-page="filters.page"
          v-model:page-size="filters.pageSize"
          background
          small
          layout="sizes, prev, pager, next"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredRows.length"
        />
      </div>
    </el-card>

    <section v-if="showCardList" class="admin-card-list" aria-label="管理台记录卡片">
      <article v-for="row in pagedRows" :key="row.id || row.title || JSON.stringify(row).slice(0, 40)" class="admin-record-card">
        <div class="admin-record-card-main">
          <span>{{ config.module }}</span>
          <h3>{{ formatCell(row[primaryColumn.key]) || '未命名记录' }}</h3>
          <p v-if="summaryColumn">{{ formatCell(row[summaryColumn.key]) }}</p>
        </div>
        <dl class="admin-record-fields">
          <template v-for="column in detailColumns" :key="column.key">
            <dt>{{ column.label }}</dt>
            <dd>{{ formatCell(row[column.key]) || '未填写' }}</dd>
          </template>
        </dl>
        <div v-if="hasActions" class="admin-row-actions admin-card-actions">
          <el-button size="small" @click="openInspect(row)">详情</el-button>
          <el-button v-if="config.toggleAction" size="small" @click="toggle(row)">
            {{ row.done ? '设为未完成' : '完成' }}
          </el-button>
          <el-button v-if="config.updateAction" size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm
            v-if="config.deleteAction"
            title="确认删除这条记录？"
            confirm-button-text="确认"
            cancel-button-text="取消"
            @confirm="remove(row)"
          >
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </article>
      <el-empty v-if="!pagedRows.length" description="暂无匹配数据">
        <el-button v-if="config.createAction" type="primary" @click="openCreate">新增第一条</el-button>
      </el-empty>
      <div class="admin-table-footer admin-card-footer">
        <span>显示 {{ pagedRows.length }} / {{ filteredRows.length }} 条，共 {{ rows.length }} 条</span>
        <el-pagination
          v-model:current-page="filters.page"
          v-model:page-size="filters.pageSize"
          background
          small
          layout="sizes, prev, pager, next"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredRows.length"
        />
      </div>
    </section>

    <el-dialog
      v-if="dialogVisible"
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增记录' : '编辑记录'"
      width="680px"
      class="admin-crud-dialog"
      align-center
      destroy-on-close
    >
      <el-form ref="formRef" label-position="top" :model="form" :rules="rules">
        <el-row :gutter="14">
          <el-col v-for="field in config.fields || []" :key="field.key" :xs="24" :md="field.type === 'textarea' ? 24 : 12">
            <el-form-item :label="field.label" :prop="field.key" :required="field.required">
              <el-input-number v-if="field.type === 'number'" v-model="form[field.key]" :min="0" controls-position="right" />
              <el-date-picker v-else-if="field.type === 'date'" v-model="form[field.key]" type="date" value-format="YYYY-MM-DD" />
              <el-time-picker v-else-if="field.type === 'time'" v-model="form[field.key]" value-format="HH:mm" format="HH:mm" />
              <el-select v-else-if="field.type === 'select'" v-model="form[field.key]">
                <el-option v-for="option in field.options || []" :key="option" :label="option" :value="option" />
              </el-select>
              <el-input v-else-if="field.type === 'textarea'" v-model="form[field.key]" type="textarea" :rows="6" />
              <el-input v-else v-model="form[field.key]" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-if="inspectVisible"
      v-model="inspectVisible"
      title="记录详情"
      size="420px"
      class="admin-inspector"
      destroy-on-close
    >
      <template #header>
        <div class="admin-inspector-header">
          <strong>记录详情</strong>
          <el-button size="small" @click="inspectVisible = false">关闭详情</el-button>
        </div>
      </template>
      <dl v-if="selectedRow" class="admin-inspector-list">
        <template v-for="column in config.columns" :key="column.key">
          <dt>{{ column.label }}</dt>
          <dd>{{ formatCell(selectedRow[column.key]) || '未填写' }}</dd>
        </template>
      </dl>
      <pre v-if="selectedRow" class="admin-json-preview">{{ JSON.stringify(selectedRow, null, 2) }}</pre>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import PageHeader from '@/shared/components/PageHeader.vue'
import { executeAdminAction, fetchAdminData } from '@/app/api/admin'
import { useAuthStore } from '@/app/stores/auth'
import { adminResources, type AdminResourceConfig } from './resources'
import { adminToast } from '@/shared/lib/adminFeedback'

const props = defineProps<{ resourceKey: string }>()
const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const rows = ref<Record<string, any>[]>([])
const rawPayload = ref<Record<string, any>>({})
const dialogVisible = ref(false)
const inspectVisible = ref(false)
const isCompactViewport = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingRecord = ref<Record<string, any> | undefined>()
const selectedRow = ref<Record<string, any> | undefined>()
const formRef = ref<FormInstance>()
const form = reactive<Record<string, any>>({})
const filters = reactive({
  keyword: '',
  range: [] as string[],
  page: 1,
  pageSize: 10
})
const adminTableHeight = 566

const config = computed<AdminResourceConfig>(() => adminResources[props.resourceKey] || adminResources['platform.ops'])
const hasActions = computed(() => Boolean(config.value.updateAction || config.value.deleteAction || config.value.toggleAction))
const prefersCardLayout = computed(() => props.resourceKey === 'news.recommend')
const showCardList = computed(() => prefersCardLayout.value || isCompactViewport.value)
const primaryColumn = computed(() => config.value.columns[0])
const summaryColumn = computed(() => config.value.columns.find((column) => column.key === 'summary' || column.key === 'description' || column.key === 'note'))
const detailColumns = computed(() => config.value.columns.filter((column) => column.key !== primaryColumn.value?.key && column.key !== summaryColumn.value?.key))
const rules = computed<FormRules>(() => Object.fromEntries((config.value.fields || [])
  .filter((field) => field.required)
  .map((field) => [field.key, [{ required: true, message: `请填写${field.label}`, trigger: field.type === 'select' ? 'change' : 'blur' }]])))
const summaryCards = computed(() => {
  const summary = rawPayload.value.summary || {}
  return [
    { label: '模块', value: summary.moduleCount || rawPayload.value.modules?.length || 0 },
    { label: '运行', value: summary.recentRunCount || summary.runCount || 0 },
    { label: '待办', value: summary.pendingWorkItemCount || 0 },
    { label: '审核', value: summary.pendingReviewCount || 0 }
  ]
})
const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  if (!keyword) return rows.value
  return rows.value.filter((row) => config.value.columns.some((column) => String(row[column.key] ?? '').toLowerCase().includes(keyword)))
})
const pagedRows = computed(() => {
  const start = (filters.page - 1) * filters.pageSize
  return filteredRows.value.slice(start, start + filters.pageSize)
})
const resourceStats = computed(() => [
  { label: '当前资源', value: config.value.module },
  { label: '读取记录', value: rows.value.length },
  { label: '筛选结果', value: filteredRows.value.length },
  { label: '写入模式', value: config.value.createAction ? '可新增' : hasActions.value ? '可维护' : '只读' }
])

watch(() => props.resourceKey, () => {
  filters.keyword = ''
  filters.range = []
  filters.page = 1
  load()
}, { immediate: true })

watch(() => [filters.keyword, filters.pageSize], () => {
  filters.page = 1
})

let compactMediaQuery: MediaQueryList | undefined

onMounted(() => {
  window.addEventListener('niu-admin-refresh', load)
  compactMediaQuery = window.matchMedia('(max-width: 600px)')
  updateCompactViewport()
  compactMediaQuery.addEventListener('change', updateCompactViewport)
})
onBeforeUnmount(() => {
  window.removeEventListener('niu-admin-refresh', load)
  compactMediaQuery?.removeEventListener('change', updateCompactViewport)
})

function updateCompactViewport() {
  isCompactViewport.value = Boolean(compactMediaQuery?.matches)
}

async function load() {
  loading.value = true
  try {
    const payload = await fetchAdminData<Record<string, any>>(config.value.resource, auth.token, defaultParams())
    rawPayload.value = payload
    rows.value = normalizeRows(config.value, payload)
  } catch (error: any) {
    adminToast.error(error.message || '读取失败')
    rows.value = []
  } finally {
    loading.value = false
  }
}

function normalizeRows(resource: AdminResourceConfig, payload: Record<string, any>) {
  if (resource.normalize) return resource.normalize(payload)
  return payload.items || []
}

function defaultParams() {
  const now = new Date()
  const fallbackTo = now.toISOString().slice(0, 10)
  const fallbackFromDate = new Date(now.getTime() - 30 * 86400000)
  const fallbackFrom = fallbackFromDate.toISOString().slice(0, 10)
  const [from, to] = filters.range.length === 2 ? filters.range : [fallbackFrom, fallbackTo]
  return { from, to, limit: 300, includeDone: true }
}

function resetFilters() {
  filters.keyword = ''
  filters.range = []
  filters.page = 1
  load()
}

function openCreate() {
  dialogMode.value = 'create'
  editingRecord.value = undefined
  resetForm()
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row: Record<string, any>) {
  dialogMode.value = 'edit'
  editingRecord.value = row
  resetForm(row)
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

function openInspect(row: Record<string, any>) {
  selectedRow.value = row
  inspectVisible.value = true
}

function resetForm(record: Record<string, any> = {}) {
  Object.keys(form).forEach((key) => delete form[key])
  for (const field of config.value.fields || []) {
    form[field.key] = record[field.key] ?? field.defaultValue ?? ''
  }
}

async function save() {
  const action = dialogMode.value === 'create' ? config.value.createAction : config.value.updateAction
  if (!action) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const input = buildInput()
    await executeAdminAction(auth.token, action, input)
    adminToast.success('保存成功')
    dialogVisible.value = false
    await load()
  } catch (error: any) {
    adminToast.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row: Record<string, any>) {
  if (!config.value.deleteAction) return
  try {
    await executeAdminAction(auth.token, config.value.deleteAction, { id: row.id, source: 'vue-admin' })
    adminToast.success('已删除')
    await load()
  } catch (error: any) {
    adminToast.error(error.message || '删除失败')
  }
}

async function toggle(row: Record<string, any>) {
  if (!config.value.toggleAction) return
  try {
    await executeAdminAction(auth.token, config.value.toggleAction, { id: row.id, done: !row.done, source: 'vue-admin' })
    adminToast.success('状态已更新')
    await load()
  } catch (error: any) {
    adminToast.error(error.message || '状态更新失败')
  }
}

function buildInput() {
  if (config.value.mapInput) return config.value.mapInput(form, editingRecord.value)
  const input: Record<string, any> = { source: 'vue-admin' }
  if (dialogMode.value === 'edit' && editingRecord.value?.id) input.id = editingRecord.value.id
  for (const field of config.value.fields || []) {
    if (form[field.key] !== '') input[field.key] = form[field.key]
  }
  return input
}

function formatCell(value: unknown) {
  if (Array.isArray(value)) return value.join(' / ')
  if (value && typeof value === 'object') return JSON.stringify(value)
  return value ?? ''
}

function rowClassName({ rowIndex }: { rowIndex: number }) {
  return rowIndex % 2 === 0 ? 'admin-row-even' : 'admin-row-odd'
}
</script>
