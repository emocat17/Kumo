<template>
  <div class="page-container">
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
        <Search :size="16" class="icon-search" />
        <input 
          v-model="filters.search" 
          type="text" 
          placeholder="按环境名称搜索..." 
          class="search-input"
        />
      </div>
    </div>

    <!-- Environments Grid -->
    <div v-if="filteredEnvironments.length > 0" class="grid-container">
      <div v-for="env in filteredEnvironments" :key="env.id" class="card env-card">
        <div class="card-header">
          <h3 class="card-title env-name" :title="env.path">{{ env.name || 'Default' }}</h3>
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
            <button class="btn btn-primary btn-edit" @click="openInstallModal(env)">
              {{ env.status === 'installing' ? '配置中' : '编辑' }}
            </button>
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
    <BaseModal v-model="showInstallModal" title="编辑环境依赖" width="900px" height="75vh">
        <div v-if="selectedEnv" class="install-container">
            <div class="env-summary-card">
                <div class="summary-item">
                    <span class="label">Python 版本</span>
                    <span class="value">{{ selectedEnv.version }}</span>
                </div>
                <div class="summary-item">
                    <span class="label">环境名称</span>
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
                            <div class="file-info">
                                <FileText :size="18" class="file-icon" />
                                <span class="filename">requirements.txt</span>
                            </div>
                            <button type="button" class="remove-btn" title="移除文件" @click="removeUploadedFile">
                                <X :size="16" />
                            </button>
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
                <!-- <div v-if="selectedEnv?.is_conda" class="form-group">
                    <label>
                        <input v-model="installForm.is_conda" type="checkbox"> 使用 Conda 安装 (默认 pip)
                    </label>
                </div> -->
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary" :disabled="installing">
                        {{ installing ? '提交中...' : '开始安装' }}
                    </button>
                </div>
            </form>

            <!-- Tab 2: List Packages -->
            <div v-if="activeTab === 'list'" class="pkg-manager">
                <div class="pkg-toolbar">
                    <div class="search-wrapper" style="width: 100%">
                        <Search :size="16" class="icon-search" />
                        <input v-model="pkgSearch" placeholder="搜索已安装包..." class="search-input" />
                    </div>
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
                                        <Trash2 :size="16" />
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
import { Trash2, Search, FileText, X } from 'lucide-vue-next'

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
const API_BASE = '/api/python/environments'

const fetchEnvironments = async () => {
  try {
    const res = await fetch(API_BASE)
    if (res.ok) {
      environments.value = await res.json()
    }
  } catch (e: unknown) {
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
    } catch (e: unknown) {
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
    } catch (e: unknown) {
        console.error(e)
    }
}

const openInstallModal = (env: Environment) => {
    selectedEnv.value = env
    showInstallModal.value = true
    
    // If installing, default to log tab
    if (env.status === 'installing') {
        activeTab.value = 'log'
    } else {
        activeTab.value = 'install'
    }

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
  pollingInterval.value = window.setInterval(() => {
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
  return environments.value.filter((env: Environment) => {
    const searchLower = filters.search.toLowerCase()
    const matchSearch = env.name.toLowerCase().includes(searchLower) || 
                        env.version.toLowerCase().includes(searchLower)
    return matchSearch
  })
})

const filteredPackages = computed(() => {
    if (!pkgSearch.value) return packages.value
    const q = pkgSearch.value.toLowerCase()
    return packages.value.filter((p: PackageInfo) => p.name.toLowerCase().includes(q))
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
/* .environments-page removed */

/* .filter-bar, .search-wrapper, .search-input, .icon-search removed */

/* .env-grid removed */

/* .card-header from common.css */

/* .status-badge handled by common.css */

/* .card-body from common.css */

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
}

/* .card-footer from common.css */

.path-info {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: monospace;
}

/* .empty-state removed */

.install-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
    height: 100%;
}

.env-summary-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #eef0f2;
    display: flex;
    align-items: center;
    gap: 40px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    position: relative;
    overflow: hidden;
    margin-bottom: 20px;
}

.env-summary-card::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 6px;
    background: linear-gradient(to bottom, #3b82f6, #60a5fa);
}

.summary-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.summary-item .label {
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

.summary-item .value {
    font-size: 18px;
    color: #0f172a;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

.btn-soft-blue {
    background-color: #60a5fa;
    color: white;
    border: none;
    box-shadow: 0 2px 4px rgba(96, 165, 250, 0.3);
    transition: all 0.2s;
}

.btn-soft-blue:hover:not(:disabled) {
    background-color: #3b82f6;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px rgba(59, 130, 246, 0.4);
}

.upload-badge {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background-color: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 8px;
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from { opacity: 0; transform: translateY(-5px); }
    to { opacity: 1; transform: translateY(0); }
}

.file-info {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #0369a1;
    font-weight: 500;
    font-size: 14px;
}

.remove-btn {
    background: none;
    border: none;
    color: #ef4444;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    transition: background-color 0.2s;
}

.remove-btn:hover {
    background-color: #fee2e2;
}

.tabs {
    display: flex;
    border-bottom: 1px solid #eef0f2;
    margin-bottom: 10px;
}

.tab-btn {
    padding: 8px 16px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 14px;
    color: #6b7280;
    border-bottom: 2px solid transparent;
}

.tab-btn.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
    font-weight: 500;
}

.install-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.install-input-group {
    display: flex;
    gap: 10px;
}

.pkg-input {
    flex: 1;
}

.common-packages {
    margin-top: 10px;
}

.common-packages p {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 8px;
}

.tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.pkg-tag {
    font-size: 12px;
    padding: 4px 8px;
    background: #f3f4f6;
    border-radius: 4px;
    cursor: pointer;
    color: #374151;
    border: 1px solid #e5e7eb;
}

.pkg-tag:hover {
    background: #e5e7eb;
}

.pkg-manager {
    display: flex;
    flex-direction: column;
    min-height: 0;
    flex: 1;
}

.log-viewer {
    display: flex;
    flex-direction: column;
    min-height: 0;
    flex: 1;
}

.log-controls {
    display: flex;
    justify-content: flex-start;
    gap: 8px;
}

.install-log {
    margin-top: 12px;
    background: #1e1e1e;
    color: #f0f0f0;
    padding: 12px;
    border-radius: 6px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: 11px;
    line-height: 1.5;
    white-space: pre-wrap;
}

.install-log pre {
    margin: 0;
    font-family: inherit;
}

.pkg-list-container {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
}

.pkg-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.pkg-table th, .pkg-table td {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid #f0f0f0;
}

.pkg-table th {
    color: #6b7280;
    font-weight: 500;
}
</style>
