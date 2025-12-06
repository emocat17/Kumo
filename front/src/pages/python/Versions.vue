<template>
  <div class="versions-page">
    <PageHeader title="Python 版本" description="管理服务器上可用的 Python 版本。推荐使用 Conda 环境(需要预先配置)。" />

    <div class="content-grid">
      <!-- Add Version Tabs -->
      <div class="card add-version-card">
        <h3 class="card-title">添加新 Python 版本</h3>
        
        <div class="tabs">
          <button 
            :class="['tab-btn', { active: activeTab === 'path' }]" 
            @click="activeTab = 'path'"
          >
            已有解释器
          </button>
          <button 
            :class="['tab-btn', { active: activeTab === 'conda' }]" 
            @click="activeTab = 'conda'"
          >
            创建 Conda 环境
          </button>
        </div>

        <!-- Tab 1: Add by Path -->
        <form v-if="activeTab === 'path'" class="add-form" @submit.prevent="handleAddVersion">
          <div class="form-group">
            <label for="path">Python 解释器路径</label>
            <div class="input-with-button">
              <input 
                id="path" 
                v-model="newVersion.path" 
                type="text" 
                placeholder="例如: D:\env\miniconda3\envs\Kumo\" 
                class="form-input"
                required
              />
              <button type="button" class="btn btn-secondary browse-btn" @click="isPathSelectorOpen = true">
                浏览
              </button>
            </div>
            <small class="form-hint">请输入 python.exe 所在的文件夹路径或完整路径。</small>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn btn-primary" :disabled="isInstalling">
              {{ isInstalling ? '正在处理...' : '添加 Python 解释器' }}
            </button>
          </div>
        </form>

        <!-- Tab 2: Create Conda Env -->
        <form v-if="activeTab === 'conda'" class="add-form" @submit.prevent="handleCreateConda">
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

      <!-- Versions List -->
      <div class="card list-card">
        <h3 class="card-title">可用 Python 版本</h3>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>版本号</th>
                <th>状态</th>
                <th>路径</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="versions.length === 0">
                <td colspan="5" class="empty-cell">暂无 Python 版本，请在左侧添加。</td>
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
                <td class="path-cell" :title="ver.path">{{ ver.path }}</td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-icon" title="打开终端" @click="openTerminal(ver)">
                       <Terminal :size="16" />
                    </button>
                    <button class="btn-icon delete" title="删除" @click="deleteVersion(ver)">
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

    <FileSelectorModal 
      :is-open="isPathSelectorOpen" 
      @close="isPathSelectorOpen = false" 
      @select="onPathSelected" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FileSelectorModal from '@/components/common/FileSelectorModal.vue'
import { Terminal, Trash2 } from 'lucide-vue-next'

interface PythonVersion {
  id: number
  path: string
  version: string
  source_type: string
  status: string
  name: string
}

const activeTab = ref<'path' | 'conda'>('path')
const versions = ref<PythonVersion[]>([])
const newVersion = ref({ path: '' })
const condaForm = ref({ name: '', version: '' })

const statusMap: Record<string, string> = {
  ready: '就绪',
  installing: '安装中',
  error: '错误',
  deleting: '删除中'
}

const isInstalling = ref(false)
const isCreatingConda = ref(false)
const condaMessage = ref('')
const isPathSelectorOpen = ref(false)

let pollInterval: number | null = null

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

const handleAddVersion = async () => {
  if (!newVersion.value.path) return
  
  isInstalling.value = true
  
  try {
    const response = await fetch('/api/python/versions/add-by-path', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ path: newVersion.value.path })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to add python version')
    }

    // Refresh list
    await fetchVersions()
    newVersion.value.path = ''
  } catch (error) {
    console.error(error)
    const msg = error instanceof Error ? error.message : String(error)
    alert(`添加失败: ${msg}`)
  } finally {
    isInstalling.value = false
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

const openTerminal = async (ver: PythonVersion) => {
  try {
    const response = await fetch('/api/python/versions/open-terminal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ path: ver.path })
    })
    
    if (!response.ok) {
      throw new Error('Failed to open terminal')
    }
  } catch (error) {
    console.error(error)
    alert('无法打开终端，请确保服务器在本地运行。')
  }
}

const deleteVersion = async (ver: PythonVersion) => {
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

const onPathSelected = (path: string) => {
  newVersion.value.path = path
}

onMounted(() => {
  fetchVersions()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.versions-page {
  max-width: 1200px;
  margin: 0 auto;
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

.card {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 24px;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin-top: 0;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background-color: #f3f4f6;
  padding: 4px;
  border-radius: 8px;
}

.tab-btn {
  flex: 1;
  padding: 8px 16px;
  border: none;
  background: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background-color: #e5e7eb;
  color: #374151;
}

.tab-btn.active {
  background-color: white;
  color: #3b82f6; /* Changed to Blue */
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

/* Form Styles */
.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.input-with-button {
  display: flex;
  gap: 8px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  transition: border-color 0.2s;
  flex: 1;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.form-hint {
  display: block;
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 4px;
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

.btn {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-primary:disabled {
  background-color: #93c5fd;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.btn-secondary:hover {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.browse-btn {
  white-space: nowrap;
}

/* Table Styles */
.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table th {
  text-align: left;
  padding: 12px 16px;
  background-color: #f9fafb;
  color: #6b7280;
  font-weight: 600;
  border-bottom: 1px solid #e5e7eb;
}

.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  color: #374151;
  vertical-align: middle;
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

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.status-badge.ready {
  background-color: #eff6ff;
  color: #3b82f6;
}

.status-badge.installing {
  background-color: #fff7ed;
  color: #ea580c;
}

.status-badge.error {
  background-color: #fef2f2;
  color: #dc2626;
}

.path-cell {
  font-family: monospace;
  color: #6b7280;
  max-width: 150px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-icon {
  padding: 6px;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  color: #4b5563;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon:hover {
  background-color: #f3f4f6;
  color: #111827;
}

.btn-icon.delete:hover {
  background-color: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

.btn-icon:hover {
  background-color: #f3f4f6;
}

.btn-icon.delete:hover {
  background-color: #fef2f2;
  color: #dc2626;
  border-color: #fee2e2;
}

.empty-cell {
  text-align: center;
  padding: 32px;
  color: #9ca3af;
}
</style>
