
<template>
  <div class="audit-logs-container">
    <!-- Toolbar -->
    <div class="toolbar-card card">
      <div class="toolbar-left">
        <div class="filter-group">
          <label>操作类型:</label>
          <select v-model="filterOp" class="form-select">
            <option value="">全部</option>
            <option v-for="op in filterOptions.operation_types" :key="op" :value="op">{{ op }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>目标类型:</label>
          <select v-model="filterTarget" class="form-select">
            <option value="">全部</option>
            <option v-for="t in filterOptions.target_types" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
        <div class="filter-group">
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="搜索名称/详情/IP..." 
            class="form-input"
            @keyup.enter="handleSearch"
          >
          <button class="btn btn-primary" @click="handleSearch">
            <SearchIcon :size="16" /> 搜索
          </button>
        </div>
        <button class="btn btn-secondary" @click="fetchLogs">
          <RefreshCwIcon :size="16" :class="{ 'spin': loading }" /> 刷新
        </button>
      </div>
    </div>

    <!-- Logs Table -->
    <div class="card table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>操作类型</th>
            <th>目标类型</th>
            <th>目标名称</th>
            <th>详情</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && logs.length === 0">
            <td colspan="6" class="text-center">加载中...</td>
          </tr>
          <tr v-else-if="logs.length === 0">
            <td colspan="6" class="text-center">暂无审计日志</td>
          </tr>
          <tr v-for="log in logs" :key="log.id">
            <td class="time-cell">{{ formatDate(log.created_at) }}</td>
            <td>
              <span :class="['badge', getOpClass(log.operation_type)]">{{ log.operation_type }}</span>
            </td>
            <td>{{ log.target_type }}</td>
            <td>{{ log.target_name || '-' }}</td>
            <td class="details-cell" :title="log.details">{{ log.details }}</td>
            <td>
              <span :class="['status-dot', log.status === 'SUCCESS' ? 'success' : 'failed']"></span>
              {{ log.status }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="total > 0" class="pagination-controls">
      <button class="btn btn-secondary btn-sm" :disabled="page === 1" @click="page--">上一页</button>
      <span class="page-info">第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页 (总计 {{ total }} 条)</span>
      <button class="btn btn-secondary btn-sm" :disabled="page * pageSize >= total" @click="page++">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { RefreshCwIcon } from 'lucide-vue-next'

interface AuditLog {
  id: number
  operation_type: string
  target_type: string
  target_id: string
  target_name: string
  details: string
  status: string
  created_at: string
}

const logs = ref<AuditLog[]>([])
const loading = ref(false)
const filterOp = ref('')
const filterTarget = ref('')
const searchQuery = ref('')
const filterOptions = ref({ operation_types: [], target_types: [] })

const API_BASE = 'http://localhost:8000/api'

const fetchOptions = async () => {
  try {
    const res = await fetch(`${API_BASE}/audit/types`)
    if (res.ok) {
      filterOptions.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filterOp.value) params.append('operation_type', filterOp.value)
    if (filterTarget.value) params.append('target_type', filterTarget.value)
    if (searchQuery.value) params.append('search', searchQuery.value)
    
    // Pagination
    params.append('skip', ((page.value - 1) * pageSize.value).toString())
    params.append('limit', pageSize.value.toString())
    
    const res = await fetch(`${API_BASE}/audit?${params.toString()}`)
    if (res.ok) {
      const data = await res.json()
      logs.value = data.items
      total.value = data.total
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  fetchLogs()
}

watch([filterOp, filterTarget], () => {
  page.value = 1
  fetchLogs()
})

watch(page, () => {
  fetchLogs()
})

onMounted(() => {
  fetchOptions()
  fetchLogs()
})

const formatDate = (iso: string) => {
  return new Date(iso).toLocaleString()
}

const getOpClass = (op: string) => {
  if (['CREATE', 'EXECUTE', 'BACKUP'].includes(op)) return 'badge-blue'
  if (['UPDATE'].includes(op)) return 'badge-yellow'
  if (['DELETE', 'STOP'].includes(op)) return 'badge-red'
  return 'badge-gray'
}
</script>

<style scoped>
.btn {
  white-space: nowrap;
  flex-shrink: 0;
}

.toolbar-card {
  padding: 16px;
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  gap: 20px;
  align-items: center;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.filter-group label {
  white-space: nowrap;
}

.form-select {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  outline: none;
}

.form-input {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  outline: none;
  min-width: 200px;
}

.table-card {
  padding: 0;
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #f3f4f6;
}

.data-table th {
  background-color: #f9fafb;
  font-weight: 600;
  color: #4b5563;
}

.time-cell {
  color: #6b7280;
  font-family: monospace;
  font-size: 13px;
  white-space: nowrap;
}

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.badge-blue { background-color: #e0f2fe; color: #0369a1; }
.badge-yellow { background-color: #fef3c7; color: #b45309; }
.badge-red { background-color: #fee2e2; color: #b91c1c; }
.badge-gray { background-color: #f3f4f6; color: #374151; }

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.status-dot.success { background-color: #10b981; }
.status-dot.failed { background-color: #ef4444; }

.details-cell {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #4b5563;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.text-center { text-align: center; color: #9ca3af; padding: 20px; }

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: white;
  border-top: 1px solid #f3f4f6;
}

.page-info {
  font-size: 14px;
  color: #6b7280;
}
</style>
