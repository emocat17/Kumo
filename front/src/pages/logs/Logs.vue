<template>
  <div class="page-container">
    <PageHeader title="日志管理" description="管理任务执行日志文件及查看系统操作审计记录。">
    </PageHeader>

    <div class="tabs mb-4">
      <button 
        :class="['tab-btn', { active: activeTab === 'system' }]" 
        @click="activeTab = 'system'"
      >
        系统日志
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'audit' }]" 
        @click="activeTab = 'audit'"
      >
        操作审计
      </button>
    </div>

    <!-- System Logs Tab -->
    <div v-show="activeTab === 'system'">
      <!-- Toolbar -->
      <div class="toolbar-card card">
        <div class="toolbar-left">
          <ProjectSelector v-model="selectedProjectId" style="width: 200px; margin-right: 12px;" />
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
            <div class="search-bar">
              <input 
                v-model="searchQuery" 
                placeholder="搜索日志内容..." 
                class="form-input search-input"
                @keyup.enter="handleSearch"
              />
              <button class="btn btn-primary btn-icon" @click="handleSearch" :disabled="searchLoading">
                <SearchIcon :size="16" />
              </button>
              <button v-if="isSearching" class="btn btn-secondary btn-icon" @click="clearSearch" title="清除搜索">
                <XIcon :size="16" />
              </button>
            </div>
            <button class="close-btn" @click="closeLogModal">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="isSearching" class="search-results">
              <div v-if="searchLoading" class="loading-text">搜索中...</div>
              <div v-else-if="searchResults.length === 0" class="no-results">未找到匹配内容</div>
              <div v-else class="results-list">
                <div v-for="(match, idx) in searchResults" :key="idx" class="result-line">
                  <span class="line-num">{{ match.line }}:</span>
                  <span class="line-content">{{ match.content }}</span>
                </div>
              </div>
            </div>
            <pre v-else-if="logContent">{{ logContent }}</pre>
            <div v-else class="loading-text">加载中...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Audit Logs Tab -->
    <AuditLogs v-if="activeTab === 'audit'" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
import AuditLogs from './AuditLogs.vue'
import { 
  RefreshCwIcon, Trash2Icon, ClockIcon, DownloadIcon, FileTextIcon,
  ChevronDownIcon, ChevronRightIcon, EyeIcon, SearchIcon, XIcon
} from 'lucide-vue-next'

interface LogFile {
  filename: string
  task_name: string
  size: string
  size_raw: number
  created_at: string
  path: string
}

interface SearchMatch {
  line: number
  content: string
}

const activeTab = ref('system')
const logs = ref<LogFile[]>([])
const loading = ref(false)
const selectedProjectId = ref<number | null>(null)
const cleanupDays = ref(7)
const expandedGroups = ref<Record<string, boolean>>({})
const selectedLogs = ref<string[]>([])
const showLogModal = ref(false)
const viewingLog = ref<LogFile | null>(null)
const logContent = ref('')
const searchQuery = ref('')
const searchResults = ref<SearchMatch[]>([])
const isSearching = ref(false)
const searchLoading = ref(false)

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

watch(selectedProjectId, () => {
  fetchLogs()
})

const fetchLogs = async () => {
  loading.value = true
  try {
    let url = `${API_BASE}/logs`
    if (selectedProjectId.value) {
      url += `?project_id=${selectedProjectId.value}`
    }
    const res = await fetch(url)
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
  searchQuery.value = ''
  isSearching.value = false
  searchResults.value = []
  
  try {
    // Request last 200KB to prevent browser crash
    const res = await fetch(`${API_BASE}/logs/${log.filename}/content?tail_kb=200`)
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

const handleSearch = async () => {
  if (!viewingLog.value || !searchQuery.value.trim()) return
  
  searchLoading.value = true
  isSearching.value = true
  try {
    const res = await fetch(`${API_BASE}/logs/${viewingLog.value.filename}/search?q=${encodeURIComponent(searchQuery.value)}`)
    if (res.ok) {
      const data = await res.json()
      searchResults.value = data.matches
    } else {
      alert('搜索失败')
    }
  } catch (e) {
    console.error(e)
    alert('搜索出错')
  } finally {
    searchLoading.value = false
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  isSearching.value = false
  searchResults.value = []
}

const closeLogModal = () => {
  showLogModal.value = false
  viewingLog.value = null
  isSearching.value = false
  searchQuery.value = ''
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

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  width: 90%;
  max-width: 1000px;
  height: 80vh;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

.search-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 500px;
}

.search-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #6b7280;
  cursor: pointer;
  line-height: 1;
  padding: 0;
}

.close-btn:hover {
  color: #111827;
}

.modal-body {
  flex: 1;
  overflow: auto;
  padding: 16px;
  background: #f9fafb;
}

.modal-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #374151;
}

.search-results {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.result-line {
  display: flex;
  padding: 8px 12px;
  border-bottom: 1px solid #f3f4f6;
  font-family: monospace;
  font-size: 13px;
}

.result-line:last-child {
  border-bottom: none;
}

.result-line:hover {
  background-color: #f3f4f6;
}

.line-num {
  width: 50px;
  color: #9ca3af;
  flex-shrink: 0;
  user-select: none;
  text-align: right;
  margin-right: 12px;
}

.line-content {
  color: #374151;
  white-space: pre-wrap;
  word-break: break-all;
}

.no-results {
  padding: 32px;
  text-align: center;
  color: #6b7280;
}

.loading-text {
  text-align: center;
  color: #6b7280;
  padding: 20px;
}
</style>
