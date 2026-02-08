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
             <button class="btn btn-secondary" :disabled="loading" @click="refreshLog">
                <RefreshCwIcon :size="16" />
             </button>
             <button class="btn btn-secondary" :class="{ 'active': showSearch }" @click="toggleSearch">
                <SearchIcon :size="16" />
             </button>
             <button v-if="isRunning(selectedExecutionId)" class="btn btn-danger" @click="stopExecution(selectedExecutionId)">
                <SquareIcon :size="16" fill="currentColor" />
             </button>
             <button v-else class="btn btn-danger" @click="deleteExecution(selectedExecutionId)">
                <Trash2Icon :size="16" />
             </button>
          </div>
       </div>
       
       <!-- Search Bar -->
       <div v-if="showSearch" class="search-bar">
          <div class="search-input-wrapper">
             <SearchIcon :size="14" class="search-icon" />
             <input 
               v-model="searchQuery" 
               placeholder="输入关键词搜索日志..." 
               class="search-input"
               @keyup.enter="performSearch"
             />
             <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">
               <XIcon :size="14" />
             </button>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="!searchQuery || isSearching" @click="performSearch">
             {{ isSearching ? '搜索中...' : '搜索' }}
          </button>
       </div>

       <!-- Search Results -->
       <div v-if="showSearch && searchResults.length > 0" class="search-results">
          <div class="results-header">
             <span>找到 {{ searchResults.length }} 个匹配项 (仅显示前 100 个)</span>
             <button class="close-results" @click="clearSearch">&times;</button>
          </div>
          <div class="results-list">
             <div v-for="(res, idx) in searchResults" :key="idx" class="result-item">
                <span class="line-num">L{{ res.line }}:</span>
                <span class="line-content">{{ res.content }}</span>
             </div>
          </div>
       </div>

       <div ref="logViewer" class="log-viewer">
          <pre v-if="logContent">{{ logContent }}</pre>
          <div v-else-if="loading" class="loading-text">加载中...</div>
          <div v-else class="empty-text">暂无日志或日志为空</div>
       </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, nextTick, onUnmounted, onMounted } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { RefreshCwIcon, SquareIcon, Trash2Icon, SearchIcon, XIcon } from 'lucide-vue-next'

const props = defineProps<{
  taskId: string | number
  taskName: string
  initialExecutionId?: number
}>()

const emit = defineEmits(['close'])

const isOpen = ref(true)
interface TaskExecution {
  id: number
  status: string
  start_time: string
}

interface SearchResult {
  line: number
  content: string
}

const executions = ref<TaskExecution[]>([])
const selectedExecutionId = ref<number | null>(null)
const logContent = ref('')
const loading = ref(false)
const logViewer = ref<HTMLElement | null>(null)
const socket = ref<WebSocket | null>(null)
let statusPollInterval: number | null = null

// Search State
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const isSearching = ref(false)
const showSearch = ref(false)

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
    // Fetch last 200KB
    const res = await fetch(`${API_BASE}/tasks/executions/${execId}/log?tail_kb=200`)
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

const toggleSearch = () => {
  showSearch.value = !showSearch.value
  if (!showSearch.value) {
    clearSearch()
  }
}

const performSearch = async () => {
  if (!searchQuery.value || !selectedExecutionId.value) return
  isSearching.value = true
  try {
    const params = new URLSearchParams({
      q: searchQuery.value,
      limit: '100'
    })
    const res = await fetch(`${API_BASE}/tasks/executions/${selectedExecutionId.value}/log/search?${params.toString()}`)
    if (res.ok) {
      const data = await res.json()
      searchResults.value = data.results || []
    } else {
      searchResults.value = []
    }
  } catch (e) {
    console.error(e)
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
}


const formatTime = (iso: string) => new Date(iso).toLocaleString()

defineExpose({})
</script>

<style scoped>
.log-container {
  display: flex;
  flex-direction: column;
  height: 70vh;
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
  font-size: 16px;
}

.log-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.log-select {
  width: 250px;
  padding: 4px 8px;
}

/* Search Styles */
.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
}

.search-input-wrapper {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 8px;
  color: #999;
}

.search-input {
  width: 100%;
  padding: 6px 30px 6px 30px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.clear-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  padding: 0;
  display: flex;
}

.search-results {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 4px;
  margin-bottom: 10px;
  max-height: 150px;
  overflow-y: auto;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.results-header {
  padding: 6px 10px;
  background: #f1f3f5;
  font-size: 12px;
  color: #666;
  display: flex;
  justify-content: space-between;
  position: sticky;
  top: 0;
}

.close-results {
  background: none;
  border: none;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}

.result-item {
  padding: 4px 10px;
  font-family: monospace;
  font-size: 12px;
  border-bottom: 1px solid #f5f5f5;
  display: flex;
  gap: 8px;
}

.result-item:last-child {
  border-bottom: none;
}

.line-num {
  color: #888;
  min-width: 40px;
  text-align: right;
  user-select: none;
}

.line-content {
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-viewer {
  flex: 1;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.loading-text, .empty-text {
  color: #888;
  text-align: center;
  padding: 20px;
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
