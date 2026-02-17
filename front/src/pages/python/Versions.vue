<template>
  <div class="page-container">
    <PageHeader title="Python 版本" description="管理服务器上可用的 Python 版本。" />

    <div class="content-grid">
      <!-- Add Version Tabs -->
      <div class="card add-version-card">
        <div class="card-header">
          <h3 class="card-title">添加 Python</h3>
        </div>
        
        <div class="card-body">
          <form class="add-form" @submit.prevent="handleCreateConda">
            <div class="form-group">
              <label for="conda-name">环境名称</label>
              <input 
                id="conda-name" 
                v-model="condaForm.name" 
                type="text" 
                placeholder="例如: my-kumo-env" 
                class="form-input"
                required
              />
            </div>
            
            <div class="form-group">
              <label for="conda-version">Python 版本</label>
              <input 
                id="conda-version" 
                v-model="condaForm.version" 
                type="text" 
                placeholder="例如: 3.10" 
                class="form-input"
                required
              />
            </div>

            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="isCreatingConda">
                {{ isCreatingConda ? '正在创建...' : '创建环境' }}
              </button>
            </div>
            
            <div v-if="condaMessage" class="status-message">
              {{ condaMessage }}
            </div>
          </form>
        </div>
      </div>

      <!-- Versions List -->
      <div class="card list-card">
        <div class="card-header">
          <h3 class="card-title">Python 管理</h3>
        </div>
        <div class="card-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>版本号</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="versions.length === 0">
                  <td colspan="4" class="empty-cell">暂无 Python 版本，请在左侧添加。</td>
                </tr>
                <tr v-for="ver in versions" :key="ver.id">
                  <td>
                     <div class="ver-name">{{ ver.name || 'Python' }}</div>
                  </td>
                  <td>{{ ver.version || '-' }}</td>
                  <td>
                    <span :class="['status-badge', ver.status]">
                      {{ statusMap[ver.status] || ver.status }}
                    </span>
                  </td>
                  <td>
                    <div class="action-buttons">
                      <button class="btn btn-secondary btn-sm" title="查看详情" @click="showVersionInfo(ver)">
                         <FileText :size="16" />
                      </button>
                      <button 
                        class="btn btn-danger btn-sm" 
                        title="删除" 
                        @click="deleteVersion(ver)"
                      >
                         <Trash2 :size="16" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <BaseModal 
      v-model="isInfoModalOpen" 
      title="安装日志" 
      width="900px"
    >
      <div v-if="selectedVersion" class="log-content">
        <div class="log-header">
          <span class="log-title">{{ selectedVersion.name || 'Python' }}</span>
          <span :class="['status-badge', selectedVersion.status]">
            {{ statusMap[selectedVersion.status] || selectedVersion.status }}
          </span>
        </div>
        <div class="log-body">
          <div v-if="logLoading" class="log-hint">加载中...</div>
          <div v-else-if="logError" class="log-hint error">{{ logError }}</div>
          <pre v-else class="log-pre">{{ logContent || '暂无日志' }}</pre>
        </div>
      </div>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { Trash2, FileText } from 'lucide-vue-next'

interface PythonVersion {
  id: number
  path: string
  version: string
  source_type?: string
  status: string
  name: string
  is_in_use?: boolean
  is_conda: boolean
  used_by_tasks?: string[]
}

const versions = ref<PythonVersion[]>([])
const condaForm = ref({ name: '', version: '' })

const statusMap: Record<string, string> = {
  ready: '就绪',
  installing: '安装中',
  error: '错误',
  deleting: '删除中'
}

const isCreatingConda = ref(false)
const condaMessage = ref('')

const isInfoModalOpen = ref(false)
const selectedVersion = ref<PythonVersion | null>(null)
const logContent = ref('')
const logLoading = ref(false)
const logError = ref('')

let pollInterval: number | null = null
let logPollInterval: number | null = null

const fetchVersions = async () => {
  try {
    const response = await fetch('/api/python/versions')
    if (response.ok) {
      const data = await response.json()
      versions.value = data
      
      // Check if any version is installing or deleting, if so, keep polling
      const hasActiveOperations = data.some((v: PythonVersion) => 
        v.status === 'installing' || v.status === 'deleting'
      )
      
      if (hasActiveOperations && !pollInterval) {
        startPolling()
      } else if (!hasActiveOperations && pollInterval) {
        stopPolling()
      }

      if (selectedVersion.value) {
        const latest = data.find((v: PythonVersion) => v.id === selectedVersion.value?.id)
        if (latest) {
          selectedVersion.value = latest
          if (latest.status !== 'installing' && logPollInterval) {
            stopLogPolling()
          }
        }
      }
    }
  } catch (error) {
    console.error('Failed to fetch versions:', error)
  }
}

const startPolling = () => {
  if (pollInterval) return
  pollInterval = window.setInterval(fetchVersions, 2000)
}

const stopPolling = () => {
  if (pollInterval) {
    window.clearInterval(pollInterval)
    pollInterval = null
  }
}

const cleanLogContent = (raw: string) => {
  let result = ''
  for (const ch of raw) {
    if (ch === '\b') {
      result = result.slice(0, -1)
    } else {
      result += ch
    }
  }
  result = result.replace(/(?:\s*[|/\\-]){3,}\s*/g, ' ')
  return result
}

const fetchLogs = async (versionId: number, options?: { silent?: boolean }) => {
  if (!options?.silent) {
    logLoading.value = true
    logError.value = ''
  }
  try {
    const response = await fetch(`/api/python/versions/${versionId}/logs`)
    if (response.ok) {
      const data = await response.json()
      const nextLog = cleanLogContent(data.log || '')
      if (nextLog !== logContent.value) {
        logContent.value = nextLog
      }
    } else {
      const errorData = await response.json().catch(() => ({}))
      logError.value = errorData.detail || '日志获取失败'
    }
  } catch (error) {
    console.error(error)
    logError.value = '日志获取失败'
  } finally {
    if (!options?.silent) {
      logLoading.value = false
    }
  }
}

const startLogPolling = (versionId: number) => {
  if (logPollInterval) return
  logPollInterval = window.setInterval(() => {
    fetchLogs(versionId, { silent: true })
  }, 2500)
}

const stopLogPolling = () => {
  if (logPollInterval) {
    window.clearInterval(logPollInterval)
    logPollInterval = null
  }
}

const showVersionInfo = (ver: PythonVersion) => {
  selectedVersion.value = ver
  isInfoModalOpen.value = true
  logContent.value = ''
  logError.value = ''
  fetchLogs(ver.id)
  if (ver.status === 'installing') {
    startLogPolling(ver.id)
  }
}

const handleCreateConda = async () => {
  if (!condaForm.value.name || !condaForm.value.version) return
  
  isCreatingConda.value = true
  condaMessage.value = '正在提交创建请求...'
  
  try {
    const response = await fetch('/api/python/versions/create-conda-env', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        name: condaForm.value.name,
        version: condaForm.value.version
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to create conda environment')
    }

    const data = await response.json()
    condaMessage.value = `创建任务已开始！环境路径: ${data.env_path}`
    
    // Immediately fetch versions to show the "installing" state
    await fetchVersions()
    
    // Reset form
    condaForm.value.name = ''
    condaForm.value.version = ''
    
    // Wait a bit and clear message
    setTimeout(() => {
        condaMessage.value = ''
        isCreatingConda.value = false
    }, 3000)

  } catch (error) {
    console.error(error)
    const msg = error instanceof Error ? error.message : String(error)
    condaMessage.value = `错误: ${msg}`
    isCreatingConda.value = false
  }
}


const deleteVersion = async (ver: PythonVersion) => {
  if (ver.is_in_use && ver.used_by_tasks?.length) {
      alert(`该环境正在被以下任务使用，无法删除：\n${ver.used_by_tasks.join('\n')}`)
      return
  }
  if (confirm(`确定要移除 ${ver.name} 吗？`)) {
    try {
      const response = await fetch(`/api/python/versions/${ver.id}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // If immediate success (or started), we refresh list
        // If it's a background task, status will change to 'deleting' and polling will start
        await fetchVersions()
      } else {
        const err = await response.json()
        alert(`删除失败: ${err.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to delete:', error)
      alert('删除失败')
    }
  }
}

onMounted(() => {
  fetchVersions()
})

watch(isInfoModalOpen, (open) => {
  if (!open) {
    stopLogPolling()
  }
})

onUnmounted(() => {
  stopPolling()
  stopLogPolling()
})
</script>

<style scoped>
.content-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
  align-items: start;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

.form-actions {
  margin-top: 24px;
}

.status-message {
  margin-top: 16px;
  padding: 12px;
  background-color: #f0fdf4;
  color: #166534;
  border-radius: 6px;
  font-size: 0.875rem;
}

.ver-name {
  font-weight: 500;
  color: #111827;
}

.ver-source {
  font-size: 0.75rem;
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  margin-top: 4px;
  background-color: #f3f4f6;
  color: #6b7280;
}

.ver-source.conda {
  background-color: #ecfdf5;
  color: #059669;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.empty-cell {
  text-align: center;
  padding: 32px;
  color: #9ca3af;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.log-title {
  font-weight: 600;
  color: #111827;
}

.log-body {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #0b1021;
  padding: 12px;
  min-height: 200px;
}

.log-pre {
  margin: 0;
  color: #d1d5db;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-hint {
  color: #9ca3af;
  font-size: 0.875rem;
}

.log-hint.error {
  color: #ef4444;
}
</style>
