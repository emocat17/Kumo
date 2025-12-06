<template>
  <div class="environments-page">
    <PageHeader title="Python 环境" description="管理 Python 环境及其依赖包。">
      <!-- <template #actions>
        <button class="btn btn-primary" @click="showCreateModal = true">
          <i class="icon-plus">+</i> 新建环境
        </button>
      </template> -->
    </PageHeader>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="search-wrapper">
        <i class="icon-search">🔍</i>
        <input 
          v-model="filters.search" 
          type="text" 
          placeholder="按环境名称搜索..." 
          class="search-input"
        />
      </div>
    </div>

    <!-- Environments Grid -->
    <div v-if="filteredEnvironments.length > 0" class="env-grid">
      <div v-for="env in filteredEnvironments" :key="env.id" class="env-card">
        <div class="card-header">
          <h3 class="env-name" :title="env.path">{{ env.name || 'Default' }}</h3>
          <span :class="['status-badge', env.status]">{{ getStatusLabel(env.status) }}</span>
        </div>
        
        <div class="card-body">
          <div class="info-row">
            <span class="label">Version:</span>
            <span class="value">
                {{ env.version }}
                <span v-if="env.is_conda" class="badge-conda">Conda</span>
            </span>
          </div>
          
          <div class="info-row">
            <span class="label">创建时间:</span>
            <span class="value date">{{ formatDate(env.created_at) }}</span>
          </div>
          
          <div class="info-row">
            <span class="label">更新时间:</span>
            <span class="value date">{{ formatDate(env.updated_at) }}</span>
          </div>
          
          <div class="actions-row">
             <button class="btn btn-primary btn-edit" :disabled="env.status === 'installing'" @click="openInstallModal(env)">
                {{ env.status === 'installing' ? '配置中...' : '编辑' }}
             </button>
          </div>
        </div>

        <div class="card-footer">
            <div class="path-info" :title="env.path">
                {{ env.path }}
            </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <div class="empty-icon">🐍</div>
      <h3>未找到 Python 环境</h3>
      <p>请先在“Python 版本”页面添加环境。</p>
    </div>

    <!-- Install Packages Modal -->
    <BaseModal v-model="showInstallModal" title="编辑环境依赖" width="600px">
        <div v-if="selectedEnv" class="install-container">
            <div class="env-summary">
                <div class="summary-item">
                    <span class="label">Python 版本:</span>
                    <span class="value">{{ selectedEnv.version }}</span>
                </div>
                <div class="summary-item">
                    <span class="label">环境名称:</span>
                    <span class="value">{{ selectedEnv.name || 'Default' }}</span>
                </div>
            </div>
            
            <div class="tabs">
                <button 
                    :class="['tab-btn', { active: activeTab === 'install' }]" 
                    @click="activeTab = 'install'"
                >
                    安装新包
                </button>
                <button 
                    :class="['tab-btn', { active: activeTab === 'list' }]" 
                    @click="switchToPkgList"
                >
                    查看已安装依赖
                </button>
                <button 
                    :class="['tab-btn', { active: activeTab === 'log' }]" 
                    @click="switchToLog"
                >
                    安装日志
                </button>
            </div>

            <!-- Tab 1: Install -->
            <form v-if="activeTab === 'install'" class="install-form" @submit.prevent="installPackages">
                <div class="form-group">
                    <label>包名 (支持多个，换行或空格分隔)</label>
                    <div class="textarea-wrapper">
                        <textarea 
                            v-model="installForm.packages" 
                            class="form-textarea" 
                            :class="{ 'readonly': isFileUploaded }"
                            rows="5" 
                            placeholder="numpy&#10;pandas>=1.5.0"
                            :readonly="isFileUploaded"
                            required
                        ></textarea>
                        <div v-if="isFileUploaded" class="upload-badge">
                            <span class="filename">📄 requirements.txt</span>
                            <button type="button" class="remove-btn" title="移除文件" @click="removeUploadedFile">×</button>
                        </div>
                    </div>
                    
                    <div class="upload-controls">
                         <input 
                            ref="fileInput" 
                            type="file" 
                            accept=".txt" 
                            style="display: none" 
                            @change="handleFileUpload"
                        />
                        <button 
                            type="button" 
                            class="btn btn-upload" 
                            :disabled="installing || isFileUploaded"
                            @click="triggerFileUpload"
                        >
                            上传 requirements.txt
                        </button>
                    </div>
                </div>
                <div v-if="selectedEnv?.is_conda" class="form-group">
                    <label>
                        <input v-model="installForm.is_conda" type="checkbox"> 使用 Conda 安装 (默认 pip)
                    </label>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary" :disabled="installing">
                        {{ installing ? '提交中...' : '开始安装' }}
                    </button>
                </div>
            </form>

            <!-- Tab 2: List Packages -->
            <div v-if="activeTab === 'list'" class="pkg-manager">
                <div class="pkg-toolbar">
                    <input v-model="pkgSearch" placeholder="搜索已安装包..." class="pkg-search" />
                </div>

                <div v-if="!loadingPkgs" class="pkg-list-container">
                    <table v-if="filteredPackages.length > 0" class="pkg-table">
                        <thead>
                            <tr>
                                <th>包名</th>
                                <th>版本</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="pkg in filteredPackages" :key="pkg.name">
                                <td>{{ pkg.name }}</td>
                                <td>{{ pkg.version }}</td>
                                <td>
                                    <button class="btn-icon delete" title="卸载" @click="uninstallPackage(pkg.name)">
                                        🗑️
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    <div v-else class="empty-pkgs">
                        无匹配的包或环境为空
                    </div>
                </div>
                <div v-else class="loading-pkgs">
                    加载中...
                </div>
            </div>

            <!-- Tab 3: Install Log -->
            <div v-if="activeTab === 'log'" class="log-viewer">
                <div class="log-controls">
                    <button class="btn btn-sm btn-outline" @click="fetchLogs">刷新日志</button>
                </div>
                <div class="install-log full-height">
                    <pre v-if="installLog">{{ installLog }}</pre>
                    <div v-else class="empty-log">暂无安装日志</div>
                </div>
            </div>
        </div>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'

// --- Data Models ---
interface Environment {
  id: number
  name: string
  version: string
  path: string
  status: string
  is_conda: boolean
  created_at?: string
  updated_at?: string
}

interface PackageInfo {
    name: string
    version: string
}

// --- State ---
const environments = ref<Environment[]>([])
const showInstallModal = ref(false)
const selectedEnv = ref<Environment | null>(null)
const packages = ref<PackageInfo[]>([])
const loadingPkgs = ref(false)
const pkgSearch = ref('')
const installing = ref(false)
const installLog = ref('')
const activeTab = ref<'install' | 'list' | 'log'>('install')
const pollingInterval = ref<number | null>(null)

const filters = reactive({
  search: '',
  status: ''
})

const installForm = reactive({
    packages: '',
    is_conda: false
})

const fileInput = ref<HTMLInputElement | null>(null)
const isFileUploaded = ref(false)
const originalPackages = ref('') // To restore manual input if file removed

// --- API ---
const API_BASE = 'http://localhost:8000/api/python/environments'

const fetchEnvironments = async () => {
  try {
    const res = await fetch(API_BASE)
    if (res.ok) {
      environments.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchPackages = async (envId: number) => {
    loadingPkgs.value = true
    packages.value = []
    try {
        const res = await fetch(`${API_BASE}/${envId}/packages`)
        if (res.ok) {
            packages.value = await res.json()
        }
    } catch (e) {
        console.error(e)
    } finally {
        loadingPkgs.value = false
    }
}

const fetchLogs = async () => {
    if (!selectedEnv.value) return
    try {
        const res = await fetch(`${API_BASE}/${selectedEnv.value.id}/logs`)
        if (res.ok) {
            const data = await res.json()
            installLog.value = data.log
        }
    } catch (e) {
        console.error(e)
    }
}

const openInstallModal = (env: Environment) => {
    selectedEnv.value = env
    showInstallModal.value = true
    activeTab.value = 'install'
    installForm.packages = ''
    isFileUploaded.value = false
    originalPackages.value = ''
    installLog.value = ''
    fetchLogs() // Pre-fetch logs if any
}

const triggerFileUpload = () => {
    fileInput.value?.click()
}

const handleFileUpload = (event: Event) => {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0]
    
    if (!file) return
    
    if (!file.name.endsWith('.txt')) {
        alert('请选择 .txt 文件 (如 requirements.txt)')
        target.value = '' // Reset input
        return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
        try {
            const content = e.target?.result as string
            // Basic validation: check if empty
            if (!content.trim()) {
                alert('文件内容为空')
                return
            }
            
            // Store original manual input before overwriting
            if (!isFileUploaded.value) {
                originalPackages.value = installForm.packages
            }
            
            installForm.packages = content
            isFileUploaded.value = true
        } catch (err) {
            console.error(err)
            alert('读取文件失败')
        } finally {
            target.value = '' // Reset input so same file can be selected again if needed
        }
    }
    reader.readAsText(file)
}

const removeUploadedFile = () => {
    isFileUploaded.value = false
    installForm.packages = originalPackages.value // Restore manual input
}

const switchToPkgList = () => {
    activeTab.value = 'list'
    if (selectedEnv.value) {
        fetchPackages(selectedEnv.value.id)
    }
}

const switchToLog = () => {
    activeTab.value = 'log'
    fetchLogs()
}

const installPackages = async () => {
    if (!selectedEnv.value || !installForm.packages) return
    
    installing.value = true
    
    try {
        const res = await fetch(`${API_BASE}/${selectedEnv.value.id}/packages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                packages: installForm.packages,
                is_conda: installForm.is_conda
            })
        })
        
        const data = await res.json()
        if (res.ok) {
            // Close modal and refresh envs to show "configuring" status
            showInstallModal.value = false
            fetchEnvironments()
        } else {
            alert(`启动失败: ${data.detail || 'Unknown error'}`)
        }
    } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        alert(`Error: ${msg}`)
    } finally {
        installing.value = false
    }
}

const uninstallPackage = async (pkgName: string) => {
    if (!selectedEnv.value || !confirm(`Are you sure you want to uninstall ${pkgName}?`)) return
    
    try {
        const res = await fetch(`${API_BASE}/${selectedEnv.value.id}/packages/${pkgName}`, {
            method: 'DELETE'
        })
        
        if (res.ok) {
            fetchPackages(selectedEnv.value.id)
        } else {
            const err = await res.json()
            alert(`Uninstall failed: ${err.detail}`)
        }
    } catch (e) {
        console.error(e)
        alert('Uninstall failed')
    }
}

// --- Lifecycle ---
onMounted(() => {
  fetchEnvironments()
  
  // Poll for status updates if any env is installing
  pollingInterval.value = setInterval(() => {
      const hasInstalling = environments.value.some(e => e.status === 'installing')
      if (hasInstalling) {
          fetchEnvironments()
      }
      // Also poll logs if modal is open on log tab
      if (showInstallModal.value && activeTab.value === 'log') {
          fetchLogs()
      }
  }, 2000)
})

onUnmounted(() => {
    if (pollingInterval.value) clearInterval(pollingInterval.value)
})

// --- Computed ---
const filteredEnvironments = computed(() => {
  return environments.value.filter(env => {
    const searchLower = filters.search.toLowerCase()
    const matchSearch = env.name.toLowerCase().includes(searchLower) || 
                        env.version.toLowerCase().includes(searchLower)
    return matchSearch
  })
})

const filteredPackages = computed(() => {
    if (!pkgSearch.value) return packages.value
    const q = pkgSearch.value.toLowerCase()
    return packages.value.filter(p => p.name.toLowerCase().includes(q))
})

// --- Helpers ---
const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    ready: '就绪',
    installing: '配置中...',
    error: '错误',
    deleting: '删除中...'
  }
  return map[status] || status
}

const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
}

</script>

<style scoped>
.environments-page {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-bar {
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
  border: 1px solid #eef0f2;
}

.icon-search {
  font-style: normal;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0; /* Prevent icon from shrinking/stretching */
  width: 20px;
  height: 20px;
}

.search-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f3f4f6; /* Lighter gray background */
  padding: 8px 15px;
  border-radius: 6px;
  width: 300px;
  border: 1px solid #e5e7eb; /* Subtle border to define the input area */
}

.search-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
}

.env-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  overflow-y: auto;
  padding-bottom: 20px;
}

.env-card {
  background: white;
  border-radius: 8px;
  border: 1px solid #eef0f2;
  display: flex;
  flex-direction: column;
  transition: all 0.2s;
}

.env-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.card-header {
  padding: 15px 20px;
  border-bottom: 1px solid #f5f5f5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.env-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.status-badge {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 12px;
}
.status-badge.ready { background: #e3f9e5; color: #1f7a34; }
.status-badge.installing { background: #e3f2fd; color: #1976d2; }
.status-badge.error { background: #ffebee; color: #c62828; }
.status-badge.deleting { background: #ffebee; color: #c62828; animation: pulse 1.5s infinite; }

.card-body {
  padding: 15px 20px;
  flex: 1;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 14px;
}

.date {
    font-size: 12px;
    color: #888;
}

.badge-conda {
    background: #e0f7fa;
    color: #006064;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: 5px;
}

.actions-row {
    display: flex;
    justify-content: center;
    margin-top: 15px;
}

.btn-edit {
    width: 100%;
    justify-content: center;
}

.card-footer {
  padding: 10px 20px;
  border-top: 1px solid #f5f5f5;
  font-size: 12px;
  color: #888;
}

.path-info {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.empty-state {
  text-align: center;
  padding: 60px;
  background: white;
  border-radius: 8px;
  color: #666;
}

.empty-icon { font-size: 48px; margin-bottom: 20px; }

/* Install Modal Styles */
.env-summary {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 6px;
    margin-bottom: 20px;
    border: 1px solid #eef0f2;
    display: flex;
    justify-content: space-between;
}

.summary-item {
    display: flex;
    gap: 10px;
    font-size: 14px;
}

.tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;
}

.tab-btn {
    padding: 8px 16px;
    border: none;
    background: none;
    border-radius: 6px;
    cursor: pointer;
    color: #666;
    font-weight: 500;
}

.tab-btn.active {
    background: #e3f2fd;
    color: #1976d2;
}

/* Package Manager Styles */
.pkg-manager {
    display: flex;
    flex-direction: column;
    gap: 15px;
    max-height: 50vh;
}

.pkg-toolbar {
    display: flex;
    justify-content: space-between;
    gap: 10px;
}

.pkg-search {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
}

.pkg-list-container {
    flex: 1;
    overflow-y: auto;
    border: 1px solid #eee;
    border-radius: 6px;
    min-height: 200px;
}

.pkg-table {
    width: 100%;
    border-collapse: collapse;
}

.pkg-table th, .pkg-table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid #f5f5f5;
}

.pkg-table th {
    background: #f9f9f9;
    position: sticky;
    top: 0;
}

.btn-icon {
    background: none;
    border: none;
    cursor: pointer;
    opacity: 0.6;
}
.btn-icon:hover { opacity: 1; }

/* Form Styles */
.form-textarea {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-family: monospace;
}

.log-viewer {
    display: flex;
    flex-direction: column;
    gap: 10px;
    height: 400px;
}

.log-controls {
    display: flex;
    justify-content: flex-end;
}

.install-log {
    margin-top: 15px;
    background: #f1f1f1;
    padding: 10px;
    border-radius: 4px;
    max-height: 150px;
    overflow-y: auto;
    font-size: 12px;
}

.install-log.full-height {
    margin-top: 0;
    flex: 1;
    max-height: none;
}

.empty-log {
    color: #888;
    text-align: center;
    padding-top: 20px;
}

.btn { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: 500; }
.btn-primary { background: #1976d2; color: white; }
.btn-sm { padding: 4px 12px; font-size: 13px; }
.btn-outline { background: white; border: 1px solid #ddd; color: #333; }
.btn-outline:hover { background: #f5f5f5; }

.textarea-wrapper {
    position: relative;
}

.form-textarea.readonly {
    background-color: #f9f9f9;
    color: #666;
    cursor: default;
}

.upload-controls {
    margin-top: 10px;
    display: flex;
    justify-content: flex-end;
}

.btn-upload {
    background-color: #ADD8E6; /* Light Blue */
    color: #333;
    font-size: 13px;
    padding: 6px 12px;
}

.btn-upload:hover:not(:disabled) {
    background-color: #87CEEB; /* Sky Blue */
}

.btn-upload:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.upload-badge {
    position: absolute;
    top: 10px;
    right: 10px;
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.filename {
    font-size: 12px;
    color: #555;
    font-weight: 500;
}

.remove-btn {
    background: none;
    border: none;
    color: #ff4d4f; /* Redish */
    font-size: 16px;
    cursor: pointer;
    padding: 0;
    line-height: 1;
    font-weight: bold;
}

.remove-btn:hover {
    color: #d32f2f; /* Darker Red */
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>
