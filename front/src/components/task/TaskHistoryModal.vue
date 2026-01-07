<template>
  <BaseModal v-model="isOpen" title="任务执行历史" width="800px" @close="close">
    <div class="history-container">
       <div class="history-header">
          <span class="history-title">任务: {{ taskName }}</span>
          <div class="controls">
            <button class="btn btn-secondary" title="编辑/多选" @click="toggleEdit">
              <EditIcon :size="16" :class="{ 'text-blue': isEditing }" />
            </button>
            <button class="btn btn-secondary" title="刷新" @click="fetchHistory">
               <RefreshCwIcon :size="16" />
            </button>
          </div>
       </div>

       <div v-if="isEditing" class="batch-actions">
          <span class="selection-info">已选 {{ selectedIds.size }} 项</span>
          <div class="batch-buttons">
             <button class="btn btn-danger btn-sm" :disabled="selectedIds.size === 0" @click="deleteSelected">
                <Trash2Icon :size="14" /> 删除
             </button>
             <button class="btn btn-primary btn-sm" :disabled="selectedIds.size === 0" @click="exportSelected">
                <DownloadIcon :size="14" /> 导出
             </button>
          </div>
       </div>
       
       <div class="table-container">
          <table class="data-table">
             <thead>
                <tr>
                   <th v-if="isEditing" class="checkbox-col">
                      <input type="checkbox" :checked="selectedIds.size === executions.length && executions.length > 0" @change="toggleAll">
                   </th>
                   <th>ID</th>
                   <th>状态</th>
                   <th>开始时间</th>
                   <th>结束时间</th>
                   <th>耗时(秒)</th>
                   <th>CPU (Max)</th>
                   <th>Mem (Max)</th>
                   <th>操作</th>
                </tr>
             </thead>
             <tbody>
                <tr v-if="executions.length === 0">
                   <td :colspan="isEditing ? 9 : 8" class="empty-cell">暂无执行记录</td>
                </tr>
                <tr v-for="exec in executions" :key="exec.id">
                   <td v-if="isEditing" class="checkbox-col">
                      <input type="checkbox" :checked="selectedIds.has(exec.id)" @change="toggleSelection(exec.id)">
                   </td>
                   <td>#{{ exec.id }}</td>
                   <td>
                      <span :class="['status-badge', exec.status]">{{ exec.status }}</span>
                   </td>
                   <td>{{ formatTime(exec.start_time) }}</td>
                   <td>{{ exec.end_time ? formatTime(exec.end_time) : '-' }}</td>
                   <td>{{ exec.duration ? exec.duration.toFixed(2) : '-' }}</td>
                   <td>{{ exec.max_cpu_percent ? exec.max_cpu_percent.toFixed(1) + '%' : '-' }}</td>
                   <td>{{ exec.max_memory_mb ? exec.max_memory_mb.toFixed(1) + ' MB' : '-' }}</td>
                   <td>
                      <button class="btn-icon" title="查看日志" @click="viewLog(exec.id)">
                         <TerminalIcon :size="14" />
                      </button>
                   </td>
                </tr>
             </tbody>
          </table>
       </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { TerminalIcon, RefreshCwIcon, EditIcon, Trash2Icon, DownloadIcon } from 'lucide-vue-next'

const props = defineProps<{
  taskId: string | number
  taskName: string
}>()

const emit = defineEmits(['view-log', 'close'])

const isOpen = ref(true)
const executions = ref<any[]>([])
const isEditing = ref(false)
const selectedIds = ref<Set<number>>(new Set())

const API_BASE = 'http://localhost:8000/api'

onMounted(() => {
  fetchHistory()
})

const close = () => {
  emit('close')
}

const fetchHistory = async () => {
  try {
    const res = await fetch(`${API_BASE}/tasks/${props.taskId}/executions`)
    if (res.ok) {
      executions.value = await res.json()
      // Clear selection on refresh
      selectedIds.value.clear()
    }
  } catch (e) {
    console.error(e)
  }
}

const viewLog = (execId: number) => {
   emit('view-log', execId)
}

const toggleEdit = () => {
  isEditing.value = !isEditing.value
  selectedIds.value.clear()
}

const toggleSelection = (id: number) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
}

const toggleAll = () => {
  if (selectedIds.value.size === executions.value.length) {
    selectedIds.value.clear()
  } else {
    executions.value.forEach(e => selectedIds.value.add(e.id))
  }
}

const deleteSelected = async () => {
  if (selectedIds.value.size === 0) return
  if (!confirm(`确定要删除选中的 ${selectedIds.value.size} 条记录吗？`)) return
  
  try {
    // Delete one by one for now (or implement batch API)
    // Batch API is better but user didn't ask for backend changes.
    // I'll do concurrent requests.
    const promises = Array.from(selectedIds.value).map(id => 
       fetch(`${API_BASE}/tasks/executions/${id}`, { method: 'DELETE' })
    )
    await Promise.all(promises)
    await fetchHistory()
    isEditing.value = false
  } catch (e) {
    console.error(e)
    alert('删除失败')
  }
}

const exportSelected = () => {
  if (selectedIds.value.size === 0) return
  
  const selectedExecs = executions.value.filter(e => selectedIds.value.has(e.id))
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(selectedExecs, null, 2))
  const downloadAnchorNode = document.createElement('a')
  downloadAnchorNode.setAttribute("href", dataStr)
  downloadAnchorNode.setAttribute("download", `task_${props.taskId}_history_export.json`)
  document.body.appendChild(downloadAnchorNode)
  downloadAnchorNode.click()
  downloadAnchorNode.remove()
}

const formatTime = (iso: string) => new Date(iso).toLocaleString()

defineExpose({})
</script>

<style scoped>
.resource-stats {
  font-size: 0.85em;
  font-family: monospace;
  color: #555;
  white-space: nowrap;
}
.divider {
  margin: 0 4px;
  color: #ccc;
}
.history-container {
  display: flex;
  flex-direction: column;
  max-height: 60vh;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
  margin-bottom: 12px;
}

.controls {
  display: flex;
  gap: 8px;
}

.batch-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f9fafb;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
  border: 1px solid #e5e7eb;
}

.selection-info {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.batch-buttons {
  display: flex;
  gap: 8px;
}

.table-container {
  overflow-y: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th, .data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  text-align: left;
}

.data-table th {
  background: #fafafa;
  font-weight: 600;
  color: #666;
}

.status-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.status-badge.success { background: #ecfdf5; color: #059669; }
.status-badge.failed { background: #fef2f2; color: #dc2626; }
.status-badge.running { background: #eff6ff; color: #3b82f6; }

.empty-cell {
  text-align: center;
  color: #999;
  padding: 20px;
}

.btn-icon {
  padding: 4px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.btn-icon:hover {
  background: #f5f5f5;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.btn-secondary { background: white; border-color: #d1d5db; color: #374151; }
.btn-secondary:hover { background: #f9fafb; border-color: #9ca3af; }

.btn-primary { background: #3b82f6; color: white; border-color: transparent; }
.btn-primary:hover { background: #2563eb; }

.btn-danger { background: #fef2f2; color: #dc2626; border-color: #fecaca; }
.btn-danger:hover { background: #fee2e2; border-color: #fca5a5; }

.btn-sm {
  width: auto;
  height: auto;
  padding: 4px 10px;
  font-size: 12px;
  gap: 4px;
}

.text-blue { color: #3b82f6; }
.checkbox-col { width: 40px; text-align: center; }
</style>
