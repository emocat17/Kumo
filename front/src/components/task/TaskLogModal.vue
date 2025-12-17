<template>
  <BaseModal v-model="isOpen" title="任务日志" width="800px" @close="close">
    <div class="log-container">
       <div class="log-header">
          <span class="log-title">任务: {{ taskName }} (ID: {{ taskId }})</span>
          <div class="log-controls">
             <select v-model="selectedExecutionId" class="form-select log-select" @change="handleExecutionChange">
                <option v-for="exec in executions" :key="exec.id" :value="exec.id">
                   #{{ exec.id }} - {{ formatTime(exec.start_time) }} ({{ exec.status }})
                </option>
             </select>
             <button class="btn btn-secondary" @click="refreshLog" :disabled="loading">
                <RefreshCwIcon :size="16" />
             </button>
             <button class="btn btn-danger" @click="stopExecution(selectedExecutionId)" v-if="isRunning(selectedExecutionId)">
                <SquareIcon :size="16" fill="currentColor" />
             </button>
             <button class="btn btn-danger" @click="deleteExecution(selectedExecutionId)" v-else>
                <Trash2Icon :size="16" />
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
import { RefreshCwIcon, SquareIcon, Trash2Icon } from 'lucide-vue-next'

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
const socket = ref<WebSocket | null>(null)
let statusPollInterval: number | null = null

const API_BASE = 'http://localhost:8000/api'
const WS_BASE = 'ws://localhost:8000/api'

onMounted(async () => {
  await fetchExecutions()
  if (props.initialExecutionId) {
     selectedExecutionId.value = props.initialExecutionId
  } else if (executions.value.length > 0) {
     selectedExecutionId.value = executions.value[0].id
  }
  
  if (selectedExecutionId.value) {
     loadLog(selectedExecutionId.value)
  }
})

onUnmounted(() => {
  cleanup()
})

const close = () => {
  cleanup()
  emit('close')
}

const cleanup = () => {
    if (socket.value) {
        socket.value.close()
        socket.value = null
    }
    if (statusPollInterval) {
        clearInterval(statusPollInterval)
        statusPollInterval = null
    }
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

const loadLog = (execId: number | null) => {
    if (!execId) return
    
    // Clean up previous connection
    cleanup()
    
    const exec = executions.value.find(e => e.id === execId)
    
    // If running, use WebSocket
    if (exec && exec.status === 'running') {
        connectWebSocket(execId)
        // Poll status to know when it finishes
        statusPollInterval = window.setInterval(async () => {
            await fetchExecutions()
            const current = executions.value.find(e => e.id === execId)
            if (current && current.status !== 'running') {
                if (statusPollInterval) clearInterval(statusPollInterval)
            }
        }, 2000)
    } else {
        // If finished, just fetch HTTP
        fetchLogHttp(execId)
    }
}

const fetchLogHttp = async (execId: number) => {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/tasks/executions/${execId}/log`)
    if (res.ok) {
      const data = await res.json()
      logContent.value = data.log
      nextTick(() => {
          if (logViewer.value) logViewer.value.scrollTop = logViewer.value.scrollHeight
      })
    }
  } catch (e) {
    console.error(e)
    logContent.value = 'Error loading log.'
  } finally {
    loading.value = false
  }
}

const connectWebSocket = (execId: number) => {
    loading.value = true
    logContent.value = ''
    
    try {
        // Use relative path or configured base
        const wsUrl = `${WS_BASE}/tasks/ws/logs/${execId}`
        console.log('Connecting to', wsUrl)
        const ws = new WebSocket(wsUrl)
        socket.value = ws
        
        ws.onopen = () => {
            console.log('WS Connected')
            loading.value = false
        }
        
        ws.onmessage = (event) => {
            logContent.value += event.data
            // Auto scroll
            nextTick(() => {
                if (logViewer.value) {
                    logViewer.value.scrollTop = logViewer.value.scrollHeight
                }
            })
        }
        
        ws.onerror = (e) => {
            console.error('WS Error', e)
            loading.value = false
            // Fallback
            fetchLogHttp(execId)
        }
        
        ws.onclose = () => {
            console.log('WS Closed')
        }
    } catch (e) {
        console.error(e)
        fetchLogHttp(execId)
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
         // Re-load log (will switch to HTTP likely if status updated)
         loadLog(id)
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
            loadLog(selectedExecutionId.value)
         }
      } else {
         alert('删除失败')
      }
   } catch (e) {
      console.error(e)
   }
}

const handleExecutionChange = () => {
   loadLog(selectedExecutionId.value)
}

// Button refresh handler
const refreshLog = () => {
    loadLog(selectedExecutionId.value)
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
  color: #f0f0f0;
  padding: 12px;
  border-radius: 6px;
  overflow-y: auto;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  margin-top: 12px;
}

.loading-text, .empty-text {
  color: #888;
  text-align: center;
  margin-top: 20px;
}

.log-select {
  width: 280px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.log-select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
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
