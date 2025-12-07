<template>
  <BaseModal v-model="isOpen" title="任务日志" width="800px" @close="close">
    <div class="log-container">
       <div class="log-header">
          <span class="log-title">任务: {{ taskName }} (ID: {{ taskId }})</span>
          <div class="log-controls">
             <select v-model="selectedExecutionId" class="form-select sm" @change="handleExecutionChange">
                <option v-for="exec in executions" :key="exec.id" :value="exec.id">
                   #{{ exec.id }} - {{ formatTime(exec.start_time) }} ({{ exec.status }})
                </option>
             </select>
             <button class="btn btn-sm btn-secondary" @click="fetchLog(selectedExecutionId)" :disabled="loading">
                刷新
             </button>
             <button class="btn btn-sm btn-danger" @click="stopExecution(selectedExecutionId)" v-if="isRunning(selectedExecutionId)">
                停止
             </button>
             <button class="btn btn-sm btn-danger" @click="deleteExecution(selectedExecutionId)" v-else>
                删除
             </button>
          </div>
       </div>
       
       <div class="log-viewer" ref="logViewer">
          <pre v-if="logContent">{{ logContent }}</pre>
          <div v-else-if="loading" class="loading-text">加载中...</div>
          <div v-else class="empty-text">暂无日志或日志为空</div>
       </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted, onMounted } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'

const props = defineProps<{
  taskId: string | number
  taskName: string
  initialExecutionId?: number
}>()

const emit = defineEmits(['close'])

const isOpen = ref(true)
const executions = ref<any[]>([])
const selectedExecutionId = ref<number | null>(null)
const logContent = ref('')
const loading = ref(false)
const logViewer = ref<HTMLElement | null>(null)
let pollInterval: number | null = null

const API_BASE = 'http://localhost:8000/api'

onMounted(async () => {
  await fetchExecutions()
  if (props.initialExecutionId) {
     selectedExecutionId.value = props.initialExecutionId
  } else if (executions.value.length > 0) {
     selectedExecutionId.value = executions.value[0].id
  }
  
  if (selectedExecutionId.value) {
     fetchLog(selectedExecutionId.value)
  }
})

onUnmounted(() => {
  stopPolling()
})

const close = () => {
  stopPolling()
  emit('close')
}

const fetchExecutions = async () => {
  try {
    const res = await fetch(`${API_BASE}/tasks/${props.taskId}/executions`)
    if (res.ok) {
      executions.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchLog = async (execId: number | null) => {
  if (!execId) return
  
  // Don't set loading to true on poll to avoid flicker
  if (!pollInterval) loading.value = true
  
  try {
    const res = await fetch(`${API_BASE}/tasks/executions/${execId}/log`)
    if (res.ok) {
      const data = await res.json()
      
      const shouldScroll = logViewer.value && (logViewer.value.scrollHeight - logViewer.value.scrollTop === logViewer.value.clientHeight)
      
      logContent.value = data.log
      
      // Auto scroll to bottom only if user was already at bottom or just started
      nextTick(() => {
         if (logViewer.value && (shouldScroll || !pollInterval)) {
            logViewer.value.scrollTop = logViewer.value.scrollHeight
         }
      })
      
      // Check status of execution
      const exec = executions.value.find(e => e.id === execId)
      // We need to refresh execution status periodically too
      if (exec && exec.status === 'running') {
         startPolling()
      } else {
         stopPolling()
         // If we were polling and stopped, refresh executions list to show final status
         if (pollInterval) fetchExecutions() 
      }
    }
  } catch (e) {
    console.error(e)
    logContent.value = 'Error loading log.'
  } finally {
    loading.value = false
  }
}

const isRunning = (id: number | null) => {
   if (!id) return false
   const exec = executions.value.find(e => e.id === id)
   return exec && exec.status === 'running'
}

const stopExecution = async (id: number | null) => {
   if (!id || !confirm('确定要强行停止当前任务吗？')) return
   try {
      const res = await fetch(`${API_BASE}/tasks/executions/${id}/stop`, { method: 'POST' })
      if (res.ok) {
         fetchExecutions()
         fetchLog(id)
      } else {
         alert('停止失败')
      }
   } catch (e) {
      console.error(e)
   }
}

const deleteExecution = async (id: number | null) => {
   if (!id || !confirm('确定要删除这条日志记录吗？')) return
   try {
      const res = await fetch(`${API_BASE}/tasks/executions/${id}`, { method: 'DELETE' })
      if (res.ok) {
         selectedExecutionId.value = null
         logContent.value = ''
         await fetchExecutions()
         if (executions.value.length > 0) {
            selectedExecutionId.value = executions.value[0].id
            fetchLog(selectedExecutionId.value)
         }
      } else {
         alert('删除失败')
      }
   } catch (e) {
      console.error(e)
   }
}

const handleExecutionChange = () => {
   stopPolling()
   fetchLog(selectedExecutionId.value)
}

const startPolling = () => {
  if (pollInterval) return
  pollInterval = window.setInterval(() => {
     fetchLog(selectedExecutionId.value)
  }, 2000)
}

const stopPolling = () => {
  if (pollInterval) {
     window.clearInterval(pollInterval)
     pollInterval = null
  }
}

const formatTime = (iso: string) => new Date(iso).toLocaleString()

defineExpose({})
</script>

<style scoped>
.log-container {
  display: flex;
  flex-direction: column;
  height: 60vh;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
  margin-bottom: 12px;
}

.log-title {
  font-weight: 600;
}

.log-controls {
  display: flex;
  gap: 8px;
}

.log-viewer {
  flex: 1;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 13px;
  white-space: pre-wrap;
}

.loading-text, .empty-text {
  color: #888;
  text-align: center;
  margin-top: 20px;
}

.form-select.sm {
  padding: 4px 8px;
  font-size: 12px;
  width: 250px;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.btn-danger {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

.btn-danger:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}
</style>
