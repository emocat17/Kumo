<template>
  <div class="page-container">
    <PageHeader title="日志管理" description="管理任务执行日志文件，您可以下载、删除日志文件。其中天数选择只作用于删除功能,只保留近N天的日志。">
      <!-- <template #actions>
        <button class="btn btn-secondary" @click="fetchLogs" title="刷新">
          <RefreshCwIcon :size="18" :class="{ 'spin': loading }" />
        </button>
      </template> -->
    </PageHeader>

    <!-- Toolbar -->
    <div class="toolbar-card card">
      <div class="toolbar-left">
        <select v-model="cleanupDays" class="form-select days-select">
          <option :value="7">7 天</option>
          <option :value="30">30 天</option>
          <option :value="90">90 天</option>
        </select>
        <button class="btn btn-danger" @click="handleClearAll">
          <Trash2Icon :size="16" />
          清除所有日志
        </button>
        <button class="btn btn-primary" @click="handleTimedCleanup">
          <ClockIcon :size="16" />
          定时清理
        </button>
        <button v-if="selectedLogs.length > 0" class="btn btn-danger" @click="handleBatchDelete">
          <Trash2Icon :size="16" />
          批量删除 ({{ selectedLogs.length }})
        </button>
      </div>
    </div>

    <!-- Logs List -->
    <div class="card log-list-card">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 40px">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
              </th>
              <th style="width: 40px"></th>
              <th>文件名</th>
              <th>文件大小</th>
              <th>最后修改</th>
              <th style="width: 120px; text-align: right">操作</th>
            </tr>
          </thead>
          <template v-if="loading">
            <tbody>
              <tr>
                <td colspan="6" class="text-center">加载中...</td>
              </tr>
            </tbody>
          </template>
          <template v-else-if="groupedLogs.length === 0">
            <tbody>
              <tr>
                <td colspan="6" class="text-center">暂无日志文件</td>
              </tr>
            </tbody>
          </template>
          <template v-else>
            <tbody v-for="group in groupedLogs" :key="group.taskName" class="group-tbody">
              <tr class="group-header">
                <td class="checkbox-cell" @click.stop>
                   <input type="checkbox" :checked="isGroupSelected(group)" @change="toggleGroupSelection(group)" />
                </td>
                <td colspan="5" @click="toggleGroup(group.taskName)">
                  <div class="group-title">
                    <component :is="expandedGroups[group.taskName] ? ChevronDownIcon : ChevronRightIcon" :size="20" />
                    <span class="task-name">{{ group.taskName }}</span>
                    <span class="count-badge">{{ group.files.length }} 个文件</span>
                  </div>
                </td>
              </tr>
              <tr v-for="log in group.files" :key="log.filename" v-show="expandedGroups[group.taskName]" class="log-row">
                <td class="checkbox-cell">
                  <input type="checkbox" :value="log.filename" v-model="selectedLogs" />
                </td>
                <td></td>
                <td class="filename-cell">
                  <div class="file-info">
                    <FileTextIcon :size="16" class="text-gray" />
                    {{ log.filename }}
                  </div>
                </td>
                <td>{{ log.size }}</td>
                <td>{{ formatDate(log.created_at) }}</td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-icon" title="查看内容" @click="viewLog(log)">
                      <EyeIcon :size="16" class="text-blue" />
                    </button>
                    <a 
                      :href="`${API_BASE}/logs/${log.filename}/download`" 
                      class="btn-icon" 
                      title="下载日志"
                      download
                    >
                      <DownloadIcon :size="16" class="text-blue" />
                    </a>
                    <button class="btn-icon delete" title="删除日志" @click="deleteLog(log)">
                      <Trash2Icon :size="16" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </template>
        </table>
      </div>
    </div>

    <!-- Log Viewer Modal -->
    <div v-if="showLogModal" class="modal-overlay" @click="closeLogModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ viewingLog?.filename }}</h3>
          <button class="close-btn" @click="closeLogModal">&times;</button>
        </div>
        <div class="modal-body">
          <pre v-if="logContent">{{ logContent }}</pre>
          <div v-else class="loading-text">加载中...</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { 
  RefreshCwIcon, Trash2Icon, ClockIcon, DownloadIcon, FileTextIcon,
  ChevronDownIcon, ChevronRightIcon, EyeIcon
} from 'lucide-vue-next'

interface LogFile {
  filename: string
  task_name: string
  size: string
  size_raw: number
  created_at: string
  path: string
}

const logs = ref<LogFile[]>([])
const loading = ref(false)
const cleanupDays = ref(7)
const expandedGroups = ref<Record<string, boolean>>({})
const selectedLogs = ref<string[]>([])
const showLogModal = ref(false)
const viewingLog = ref<LogFile | null>(null)
const logContent = ref('')

const API_BASE = 'http://localhost:8000/api'

const groupedLogs = computed(() => {
  const groups: Record<string, LogFile[]> = {}
  logs.value.forEach(log => {
    const name = log.task_name || 'Unknown Task'
    if (!groups[name]) {
      groups[name] = []
    }
    groups[name].push(log)
  })
  
  // Convert to array and sort
  return Object.entries(groups).map(([name, files]) => ({
    taskName: name,
    files: files
  })).sort((a, b) => a.taskName.localeCompare(b.taskName))
})

const isAllSelected = computed(() => {
  return logs.value.length > 0 && selectedLogs.value.length === logs.value.length
})

const toggleSelectAll = (e: Event) => {
  const checked = (e.target as HTMLInputElement).checked
  if (checked) {
    selectedLogs.value = logs.value.map(l => l.filename)
  } else {
    selectedLogs.value = []
  }
}

const isGroupSelected = (group: { files: LogFile[] }) => {
  const groupFiles = group.files.map(f => f.filename)
  return groupFiles.every(f => selectedLogs.value.includes(f))
}

const toggleGroupSelection = (group: { files: LogFile[] }) => {
  const groupFiles = group.files.map(f => f.filename)
  const allSelected = groupFiles.every(f => selectedLogs.value.includes(f))
  
  if (allSelected) {
    // Deselect all in group
    selectedLogs.value = selectedLogs.value.filter(f => !groupFiles.includes(f))
  } else {
    // Select all in group (add missing ones)
    const newSelected = [...selectedLogs.value]
    groupFiles.forEach(f => {
      if (!newSelected.includes(f)) {
        newSelected.push(f)
      }
    })
    selectedLogs.value = newSelected
  }
}

const toggleGroup = (taskName: string) => {
  expandedGroups.value[taskName] = !expandedGroups.value[taskName]
}

onMounted(() => {
  fetchLogs()
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/logs`)
    if (res.ok) {
      logs.value = await res.json()
      // Clear selection on refresh
      selectedLogs.value = []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const viewLog = async (log: LogFile) => {
  viewingLog.value = log
  showLogModal.value = true
  logContent.value = '' // Clear previous content
  
  try {
    const res = await fetch(`${API_BASE}/logs/${log.filename}/content`)
    if (res.ok) {
      const data = await res.json()
      logContent.value = data.content
    } else {
      logContent.value = '无法加载日志内容'
    }
  } catch (e) {
    logContent.value = '加载失败: ' + e
  }
}

const closeLogModal = () => {
  showLogModal.value = false
  viewingLog.value = null
}

const handleBatchDelete = async () => {
  if (!confirm(`确定要删除选中的 ${selectedLogs.value.length} 个日志文件吗？`)) return
  
  try {
    const res = await fetch(`${API_BASE}/logs/batch-delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ filenames: selectedLogs.value })
    })
    
    if (res.ok) {
      const data = await res.json()
      alert(data.message)
      fetchLogs()
    } else {
      alert('批量删除失败')
    }
  } catch (e) {
    console.error(e)
    alert('批量删除失败')
  }
}

const deleteLog = async (log: LogFile) => {
  if (!confirm(`确定要删除日志文件 ${log.filename} 吗？`)) return
  
  try {
    const res = await fetch(`${API_BASE}/logs/${log.filename}`, { method: 'DELETE' })
    if (res.ok) {
      fetchLogs()
    } else {
      alert('删除失败')
    }
  } catch (e) {
    console.error(e)
    alert('删除失败')
  }
}

const handleClearAll = async () => {
  if (!confirm('警告：确定要删除所有日志文件吗？此操作不可恢复！')) return
  
  try {
    const res = await fetch(`${API_BASE}/logs/cleanup?days=0&delete_all=true`, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      alert(data.message)
      fetchLogs()
    } else {
      alert('清理失败')
    }
  } catch (e) {
    console.error(e)
  }
}

const handleTimedCleanup = async () => {
  if (!confirm(`确定要清理 ${cleanupDays.value} 天前的日志文件吗？`)) return
  
  try {
    const res = await fetch(`${API_BASE}/logs/cleanup?days=${cleanupDays.value}`, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      alert(data.message)
      fetchLogs()
    } else {
      alert('清理失败')
    }
  } catch (e) {
    console.error(e)
  }
}

const formatDate = (iso: string) => {
  return new Date(iso).toLocaleString()
}
</script>

<style scoped>
.toolbar-card {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.days-select {
  width: 100px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.log-list-card {
  padding: 0;
  overflow: hidden;
}

.table-container {
  overflow-x: auto;
}

.data-table th {
  background-color: #f9fafb;
  padding: 16px 24px;
  font-weight: 600;
  color: #4b5563;
  border-bottom: 1px solid #e5e7eb;
}

.data-table td {
  padding: 16px 24px;
  border-bottom: 1px solid #f3f4f6;
  color: #374151;
}

.task-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.filename-cell {
  font-family: monospace;
  color: #6b7280;
}

.text-gray { color: #9ca3af; }
.text-blue { color: #3b82f6; }
.text-center { text-align: center; color: #9ca3af; padding: 40px; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.group-tbody {
  border-bottom: 1px solid #e5e7eb;
}

.group-header {
  cursor: pointer;
  background-color: #f9fafb;
  transition: background-color 0.2s;
}

.group-header:hover {
  background-color: #f3f4f6;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  color: #111827;
}

.task-name {
  font-size: 15px;
}

.count-badge {
  font-size: 12px;
  color: #6b7280;
  background-color: #e5e7eb;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: normal;
}

.log-row td {
  background-color: #ffffff;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.checkbox-cell {
  text-align: center;
  width: 40px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  width: 80%;
  max-width: 900px;
  height: 80vh;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #6b7280;
  cursor: pointer;
}

.modal-body {
  flex: 1;
  overflow: auto;
  padding: 16px 24px;
  background-color: #f9fafb;
}

.modal-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
  font-size: 14px;
  color: #374151;
}

.loading-text {
  text-align: center;
  color: #6b7280;
  margin-top: 40px;
}
</style>
