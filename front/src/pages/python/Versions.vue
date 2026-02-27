<template>
  <div class="page-container">
    <PageHeader 
      title="Python 版本" 
      description="管理服务器上可用的 Python 版本。"
    >
      <template #actions>
        <div class="header-actions">
          <button class="btn btn-outline" @click="cleanupResidual" title="清理残留环境目录">
            <Trash2 :size="16" />
            清理残留
          </button>
          <button class="btn btn-outline" @click="cleanupCache" title="清理 Conda 和 Pip 缓存，解决安装卡住问题">
            <RefreshCw :size="16" />
            清理缓存
          </button>
        </div>
      </template>
    </PageHeader>

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
                list="common-versions"
                required
              />
              <datalist id="common-versions">
                <option v-for="v in commonVersions" :key="v" :value="v" />
              </datalist>
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
                  <th>类型</th>
                  <th>路径</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="versions.length === 0">
                  <td colspan="6" class="empty-cell">暂无 Python 版本，请在左侧添加。</td>
                </tr>
                <tr v-for="ver in versions" :key="ver.id">
                  <td>
                     <div class="ver-name">{{ ver.name || 'Python' }}</div>
                  </td>
                  <td>{{ ver.version || '-' }}</td>
                  <td>
                    <span v-if="ver.is_conda" class="ver-source conda">Conda</span>
                    <span v-else class="ver-source">System</span>
                  </td>
                  <td class="ver-path" :title="ver.path">{{ truncatePath(ver.path) }}</td>
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
                        :disabled="ver.status === 'deleting'"
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
      :title="selectedVersion?.status === 'deleting' ? '删除日志' : '安装日志'"
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

    <!-- Error Modal -->
    <BaseModal
      v-if="isErrorModalOpen"
      v-model="isErrorModalOpen"
      :title="errorTitle"
      width="480px"
    >
      <div class="error-modal-body">
        <p class="error-modal-message">{{ errorMessage }}</p>
      </div>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { Trash2, FileText, RefreshCw } from 'lucide-vue-next'

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

const commonVersions = ['3.8', '3.9', '3.10', '3.11', '3.12']

const isCreatingConda = ref(false)
const condaMessage = ref('')

const isInfoModalOpen = ref(false)
const selectedVersion = ref<PythonVersion | null>(null)
const logContent = ref('')
const logLoading = ref(false)
const logError = ref('')

// Error modal state
const isErrorModalOpen = ref(false)
const errorTitle = ref('操作失败')
const errorMessage = ref('')

const showError = (message: string, title = '操作失败') => {
  errorTitle.value = title
  errorMessage.value = message
  isErrorModalOpen.value = true
}

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
  // Remove backspace characters and handle them
  let result = ''
  for (const ch of raw) {
    if (ch === '\b') {
      result = result.slice(0, -1)
    } else {
      result += ch
    }
  }
  // Remove progress bar characters (|, /, -, \) that appear in sequences
  result = result.replace(/(?:\s*[|/\\-]\s*){2,}/g, '')
  // Remove multiple consecutive spaces
  result = result.replace(/ {2,}/g, ' ')
  // Remove lines that only contain progress bar characters
  result = result.split('\n').filter(line => {
    const trimmed = line.trim()
    return trimmed.length > 0 && !/^[|/\\\- ]+$/.test(trimmed)
  }).join('\n')
  return result.trim()
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

const truncatePath = (path: string, maxLength: number = 30) => {
  if (!path) return '-'
  if (path.length <= maxLength) return path
  return '...' + path.slice(-maxLength)
}

const showVersionInfo = (ver: PythonVersion) => {
  selectedVersion.value = ver
  isInfoModalOpen.value = true
  logContent.value = ''
  logError.value = ''
  fetchLogs(ver.id)
  // Poll logs during installing or deleting
  if (ver.status === 'installing' || ver.status === 'deleting') {
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
      showError(`该环境正在被以下任务使用，无法删除：\n${ver.used_by_tasks.join('\n')}`, '无法删除环境')
      return
  }
  if (confirm(`确定要移除 ${ver.name} 吗？`)) {
    try {
      const response = await fetch(`/api/python/versions/${ver.id}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        let message = '删除失败'
        try {
          const text = await response.text()
          if (text) {
            try {
              const data = JSON.parse(text)
              message = data.detail || data.message || message
            } catch {
              message = text
            }
          }
        } catch {
          message = '删除失败'
        }
        showError(`删除失败: ${message}`, '删除环境失败')
      } else {
        // Start polling to wait for deletion to complete
        startPolling()
        // Immediately fetch to show "deleting" status
        await fetchVersions()
      }
    } catch (error) {
      console.error('Failed to delete:', error)
      showError('删除失败', '删除环境失败')
    }
  }
}

const cleanupCache = async () => {
  if (!confirm('这将清理 Conda 和 Pip 的缓存包，可能解决安装卡住的问题。是否继续？')) {
    return
  }
  
  try {
    const response = await fetch('/api/python/versions/cleanup-cache', {
      method: 'POST'
    })
    
    if (response.ok) {
      const data = await response.json()
      showError(`缓存清理完成！\n\n${data.message || '成功清理缓存'}`, '清理完成')
      await fetchVersions()
    } else {
      const errorData = await response.json().catch(() => ({}))
      showError(`清理失败: ${errorData.detail || errorData.message || '未知错误'}`, '清理失败')
    }
  } catch (error) {
    console.error('Failed to cleanup cache:', error)
    showError('清理缓存请求失败', '清理失败')
  }
}

const cleanupResidual = async () => {
  if (!confirm('这将扫描并清理数据库中不存在但文件系统残留的环境目录。是否继续？')) {
    return
  }
  
  try {
    const response = await fetch('/api/python/versions/cleanup-residual', {
      method: 'POST'
    })
    
    if (response.ok) {
      const data = await response.json()
      let message = `扫描完成！\n\n`
      if (data.cleaned && data.cleaned.length > 0) {
        message += `已清理残留目录: ${data.cleaned.join(', ')}`
      } else {
        message += `未发现残留目录`
      }
      if (data.errors && data.errors.length > 0) {
        message += `\n\n清理错误: ${data.errors.join(', ')}`
      }
      showError(message, '清理完成')
      await fetchVersions()
    } else {
      const errorData = await response.json().catch(() => ({}))
      showError(`清理失败: ${errorData.detail || errorData.message || '未知错误'}`, '清理失败')
    }
  } catch (error) {
    console.error('Failed to cleanup residual:', error)
    showError('清理残留请求失败', '清理失败')
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
.header-actions {
  display: flex;
  gap: 8px;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover {
  border-color: #9ca3af;
  background: #f9fafb;
  color: #1f2937;
}

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

.ver-path {
  font-family: monospace;
  font-size: 11px;
  color: #6b7280;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.error-modal-body {
  padding: 8px 0;
}

.error-modal-message {
  white-space: pre-wrap;
  font-size: 14px;
  color: #4b5563;
}
</style>
