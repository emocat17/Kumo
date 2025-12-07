<template>
  <BaseModal v-model="isOpen" title="任务执行历史" width="800px" @close="close">
    <div class="history-container">
       <div class="history-header">
          <span class="history-title">任务: {{ taskName }}</span>
          <button class="btn btn-sm btn-secondary" @click="fetchHistory">刷新</button>
       </div>
       
       <div class="table-container">
          <table class="data-table">
             <thead>
                <tr>
                   <th>ID</th>
                   <th>状态</th>
                   <th>开始时间</th>
                   <th>结束时间</th>
                   <th>耗时(秒)</th>
                   <th>操作</th>
                </tr>
             </thead>
             <tbody>
                <tr v-if="executions.length === 0">
                   <td colspan="6" class="empty-cell">暂无执行记录</td>
                </tr>
                <tr v-for="exec in executions" :key="exec.id">
                   <td>#{{ exec.id }}</td>
                   <td>
                      <span :class="['status-badge', exec.status]">{{ exec.status }}</span>
                   </td>
                   <td>{{ formatTime(exec.start_time) }}</td>
                   <td>{{ exec.end_time ? formatTime(exec.end_time) : '-' }}</td>
                   <td>{{ exec.duration ? exec.duration.toFixed(2) : '-' }}</td>
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
import { ref, onMounted, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { TerminalIcon } from 'lucide-vue-next'

const props = defineProps<{
  taskId: string | number
  taskName: string
}>()

const emit = defineEmits(['view-log', 'close'])

const isOpen = ref(true) // Controlled by v-model in parent, but BaseModal handles it via v-model too. 
// Actually BaseModal expects v-model="isOpen". 
// In Tasks.vue: <TaskHistoryModal v-if="show" ... /> so it's mounted when shown.
// We should just set isOpen to true on mount or expose a prop.
// The BaseModal inside uses v-model="isOpen".
// If we use v-if in parent, onMounted works.

const executions = ref<any[]>([])

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
    }
  } catch (e) {
    console.error(e)
  }
}

const viewLog = (execId: number) => {
   emit('view-log', execId)
}

const formatTime = (iso: string) => new Date(iso).toLocaleString()

defineExpose({})
</script>

<style scoped>
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
</style>
