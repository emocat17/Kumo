<template>
  <div class="settings-page">
    <PageHeader title="系统设置" description="配置全局系统参数。" />
    
    <!-- Tabs -->
    <div class="tabs">
      <button 
        :class="['tab-btn', { active: activeTab === 'python' }]" 
        @click="activeTab = 'python'"
      >
        Python 环境配置
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'env' }]" 
        @click="activeTab = 'env'"
      >
        全局环境变量
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'backup' }]" 
        @click="activeTab = 'backup'"
      >
        数据备份与恢复
      </button>
    </div>

    <div class="settings-container">
        
        <!-- Python Env Config Tab -->
        <div v-if="activeTab === 'python'" key="python" class="section">
          <div class="card settings-card">
            <div class="card-header">
              <h3>PyPI 镜像源配置</h3>
              <div class="header-actions">
                 <span v-if="currentSource" class="current-source-badge">
                    当前生效: {{ currentSource.name }}
                 </span>
                 <span v-else class="current-source-badge empty">
                    使用默认源
                 </span>
              </div>
            </div>
            
            <p class="section-desc">
                系统将自动使用列表中优先级最高（排在第一位）的源进行依赖安装。
            </p>
            
            <div class="source-list-header">
                <h4>镜像源列表 (按优先级排序)</h4>
                <button class="btn btn-primary btn-sm" @click="openSourceModal()">
                    <span class="icon-plus">+</span> 新增源
                </button>
            </div>
            
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width: 60px;" class="text-center">优先级</th>
                        <th>名称</th>
                        <th>URL</th>
                        <th style="width: 180px;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(source, index) in pypiSources" :key="index">
                        <td class="text-center">
                            <span class="priority-badge" :class="{ 'top-priority': index === 0 }">{{ index + 1 }}</span>
                        </td>
                        <td>
                            {{ source.name }}
                            <span v-if="index === 0" class="tag-active">使用中</span>
                        </td>
                        <td class="font-mono">{{ source.url }}</td>
                        <td class="actions-cell">
                            <button class="btn-icon" :disabled="index === 0" title="上移" @click="moveSource(index, -1)">
                                ↑
                            </button>
                            <button class="btn-icon" :disabled="index === pypiSources.length - 1" title="下移" @click="moveSource(index, 1)">
                                ↓
                            </button>
                            <div class="divider-vertical"></div>
                            <button class="btn-text" @click="openSourceModal(source, index)">编辑</button>
                            <button class="btn-text text-red" @click="deleteSource(index)">删除</button>
                        </td>
                    </tr>
                    <tr v-if="pypiSources.length === 0">
                        <td colspan="4" class="text-center text-gray">
                            暂无配置，将使用官方默认源 (pypi.org)
                        </td>
                    </tr>
                </tbody>
            </table>

          </div>
        </div>

        <!-- Environment Variables Config Tab -->
        <div v-else-if="activeTab === 'env'" key="env" class="section">
          <div class="card settings-card">
            <div class="card-header">
              <h3>全局环境变量</h3>
              <button class="btn btn-primary btn-sm" @click="openEnvModal()">
                <span class="icon-plus">+</span> 新增变量
              </button>
            </div>
            <p class="section-desc">此处配置的环境变量将自动注入到所有爬虫任务的运行环境中。</p>

            <table class="data-table">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Value</th>
                  <th>描述</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="v in envVars" :key="v.id">
                  <td class="font-mono">{{ v.key }}</td>
                  <td class="font-mono value-cell">
                    <span v-if="v.is_secret" class="badge-secret">Secret</span>
                    {{ v.value }}
                  </td>
                  <td>{{ v.description || '-' }}</td>
                  <td>
                    <button class="btn-text" @click="openEnvModal(v)">编辑</button>
                    <button class="btn-text text-red" @click="deleteEnvVar(v.id)">删除</button>
                  </td>
                </tr>
                <tr v-if="envVars.length === 0">
                  <td colspan="4" class="text-center text-gray">暂无配置</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Network Proxy Config -->
          <div class="card settings-card" style="margin-top: 24px;">
            <div class="card-header">
              <h3>网络代理配置</h3>
            </div>
            
            <div style="padding-top: 10px;">
                <div class="form-group">
                    <label class="custom-label">
                        <input v-model="proxyForm.enabled" type="checkbox" class="custom-checkbox" />
                        <span>启用全局代理</span>
                    </label>
                </div>
                
                <div v-if="proxyForm.enabled" class="form-group">
                     <label>代理地址 (URL)</label>
                     <input v-model="proxyForm.url" type="text" placeholder="例如: http://192.168.1.100:7890" class="form-input" />
                     <p class="help-text">此代理将应用于所有任务执行及 Python 包安装过程。</p>
                </div>

                <div class="form-actions" style="margin-top: 20px;">
                    <button class="btn btn-primary" :disabled="proxySaving" @click="saveProxyConfig">
                        {{ proxySaving ? '保存中...' : '保存配置' }}
                    </button>
                </div>
            </div>
          </div>
        </div>

        <!-- Backup Config Tab -->
        <div v-else-if="activeTab === 'backup'" key="backup" class="section">
          
          <!-- Auto Backup Settings -->
          <div class="card settings-card" style="margin-bottom: 24px;">
            <div class="card-header">
              <h3>自动备份策略</h3>
            </div>
            
            <div style="padding-top: 20px;">
                <div class="form-group">
                    <label class="custom-label">
                        <input v-model="autoBackupForm.enabled" type="checkbox" class="custom-checkbox" />
                        <span>启用自动备份</span>
                    </label>
                </div>

                <div class="form-group">
                    <label>备份间隔 (小时)</label>
                    <input v-model.number="autoBackupForm.interval" type="number" min="1" :disabled="!autoBackupForm.enabled" class="form-input" />
                </div>

                <div class="form-group">
                    <label>保留份数 (最新的 N 份)</label>
                    <input v-model.number="autoBackupForm.retention" type="number" min="1" :disabled="!autoBackupForm.enabled" class="form-input" />
                </div>

                <div class="form-actions">
                    <button class="btn btn-primary" :disabled="autoBackupSaving" @click="saveAutoBackupConfig">
                        {{ autoBackupSaving ? '保存中...' : '保存配置' }}
                    </button>
                </div>
            </div>
          </div>

          <div class="card settings-card">
            <div class="card-header">
              <h3>备份列表</h3>
              <button class="btn btn-primary btn-sm" :disabled="backupLoading" @click="createBackup">
                <span v-if="backupLoading">创建中...</span>
                <span v-else>+ 立即手动备份</span>
              </button>
            </div>
            <p class="section-desc">
                手动创建数据库备份文件。建议在进行重大变更前执行备份。
                <br>
                <small class="text-gray">注意：目前仅支持 SQLite 数据库文件的物理备份。</small>
            </p>

            <table class="data-table">
              <thead>
                <tr>
                  <th>文件名</th>
                  <th>大小</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="backup in backups" :key="backup.filename">
                  <td class="font-mono">
                    <div class="file-info">
                        <DatabaseIcon :size="16" class="text-blue" style="margin-right: 8px"/>
                        {{ backup.filename }}
                    </div>
                  </td>
                  <td>{{ backup.size }}</td>
                  <td>{{ formatDate(backup.created_at) }}</td>
                  <td class="actions-cell">
                    <a :href="`${API_BASE}/system/backups/${backup.filename}/download`" class="btn-text" download>
                        下载
                    </a>
                    <button class="btn-text text-red" @click="deleteBackup(backup.filename)">删除</button>
                  </td>
                </tr>
                <tr v-if="backups.length === 0">
                  <td colspan="4" class="text-center text-gray">暂无备份记录</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

    </div>

    <!-- Env Var Modal -->
    <transition name="modal">
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-content">
        <h3>{{ isEditing ? '编辑环境变量' : '新增环境变量' }}</h3>
        
        <div class="form-group">
          <label>Key (变量名)</label>
          <input v-model="form.key" type="text" placeholder="例如: OPENAI_API_KEY" :disabled="isEditing" />
        </div>
        
        <div class="form-group">
          <label>Value (变量值)</label>
          <input v-model="form.value" :type="form.is_secret ? 'password' : 'text'" placeholder="输入值" />
          <p v-if="isEditing && form.is_secret" class="help-text">留空则保持原值不变。</p>
        </div>

        <div class="form-group checkbox-group">
          <label>
            <input v-model="form.is_secret" type="checkbox" />
            设为机密 (Secret)
          </label>
          <span class="help-text">机密变量在列表中将显示为 ******，并加密存储。</span>
        </div>

        <div class="form-group">
          <label>描述</label>
          <input v-model="form.description" type="text" placeholder="备注用途" />
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="submitEnvVar">保存</button>
        </div>
      </div>
    </div>
    </transition>
    
    <!-- Source Modal -->
    <transition name="modal">
    <div v-if="showSourceModal" class="modal-overlay">
        <div class="modal-content">
            <h3>{{ isEditingSource ? '编辑镜像源' : '新增镜像源' }}</h3>
            
            <div class="form-group">
                <label>名称</label>
                <input v-model="sourceForm.name" type="text" placeholder="例如: 阿里云" />
            </div>
            
            <div class="form-group">
                <label>URL 地址</label>
                <input v-model="sourceForm.url" type="text" placeholder="例如: https://mirrors.aliyun.com/pypi/simple/" />
            </div>
            
            <div class="modal-actions">
                <button class="btn btn-secondary" @click="showSourceModal = false">取消</button>
                <button class="btn btn-primary" @click="submitSource">保存</button>
            </div>
        </div>
    </div>
    </transition>

    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { DatabaseIcon } from 'lucide-vue-next'

const API_BASE = 'http://localhost:8000/api'
const activeTab = ref<'python' | 'env' | 'backup'>('python')

// --- PyPI Config Logic ---
interface PyPISource {
    name: string
    url: string
}

const pypiSources = ref<PyPISource[]>([
    { name: '阿里云', url: 'https://mirrors.aliyun.com/pypi/simple/' },
    { name: '清华大学', url: 'https://pypi.tuna.tsinghua.edu.cn/simple' },
    { name: '腾讯云', url: 'https://mirrors.cloud.tencent.com/pypi/simple' },
    { name: '官方源', url: 'https://pypi.org/simple' }
])

const backendMirrorUrl = ref('')

const currentSource = computed(() => {
    if (pypiSources.value.length > 0) {
        return pypiSources.value[0]
    }
    return null
})

const showSourceModal = ref(false)
const isEditingSource = ref(false)
const editingSourceIndex = ref<number | null>(null)
const sourceForm = reactive({
    name: '',
    url: ''
})

const fetchConfig = async () => {
  try {
    const res = await fetch(`${API_BASE}/system/config/pypi_mirror`)
    if (res.ok) {
      const data = await res.json()
      backendMirrorUrl.value = data.value || ''
    }
  } catch (e) {
    console.error('Failed to fetch config', e)
  }
}

// --- Backup Logic ---
interface BackupFile {
  filename: string
  size: string
  size_raw: number
  created_at: string
}

const backups = ref<BackupFile[]>([])
const backupLoading = ref(false)

// Proxy Logic
const proxyForm = reactive({
    enabled: false,
    url: ''
})
const proxySaving = ref(false)

const fetchProxyConfig = async () => {
    try {
        const [resEnabled, resUrl] = await Promise.all([
            fetch(`${API_BASE}/system/config/proxy.enabled`),
            fetch(`${API_BASE}/system/config/proxy.url`)
        ])
        
        if (resEnabled.ok) {
            const data = await resEnabled.json()
            proxyForm.enabled = data.value === 'true'
        }
        if (resUrl.ok) {
            const data = await resUrl.json()
            proxyForm.url = data.value || ''
        }
    } catch (e) {
        console.error("Failed to fetch proxy config", e)
    }
}

const saveProxyConfig = async () => {
    proxySaving.value = true
    try {
        await Promise.all([
            fetch(`${API_BASE}/system/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'proxy.enabled', value: proxyForm.enabled ? 'true' : 'false', description: 'Enable global network proxy' })
            }),
            fetch(`${API_BASE}/system/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'proxy.url', value: proxyForm.url, description: 'Global proxy URL' })
            })
        ])
        alert('代理配置保存成功')
    } catch (e) {
        console.error("Failed to save proxy config", e)
        alert('代理配置保存失败')
    } finally {
        proxySaving.value = false
    }
}

// Auto Backup Logic
const autoBackupForm = reactive({
    enabled: false,
    interval: 24,
    retention: 7
})
const autoBackupSaving = ref(false)

const fetchAutoBackupConfig = async () => {
    try {
        const [resEnabled, resInterval, resRetention] = await Promise.all([
            fetch(`${API_BASE}/system/config/backup.enabled`),
            fetch(`${API_BASE}/system/config/backup.interval_hours`),
            fetch(`${API_BASE}/system/config/backup.retention_count`)
        ])
        
        if (resEnabled.ok) {
            const data = await resEnabled.json()
            autoBackupForm.enabled = data.value === 'true'
        }
        if (resInterval.ok) {
            const data = await resInterval.json()
            autoBackupForm.interval = parseInt(data.value || '24')
        }
        if (resRetention.ok) {
            const data = await resRetention.json()
            autoBackupForm.retention = parseInt(data.value || '7')
        }
    } catch (e) {
        console.error("Failed to fetch auto backup config", e)
    }
}

const saveAutoBackupConfig = async () => {
    autoBackupSaving.value = true
    try {
        await Promise.all([
            fetch(`${API_BASE}/system/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'backup.enabled', value: autoBackupForm.enabled ? 'true' : 'false', description: 'Enable auto backup' })
            }),
            fetch(`${API_BASE}/system/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'backup.interval_hours', value: String(autoBackupForm.interval), description: 'Backup interval in hours' })
            }),
            fetch(`${API_BASE}/system/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'backup.retention_count', value: String(autoBackupForm.retention), description: 'Number of backups to keep' })
            })
        ])
        alert('配置保存成功')
    } catch (e) {
        console.error("Failed to save auto backup config", e)
        alert('配置保存失败')
    } finally {
        autoBackupSaving.value = false
    }
}

const fetchBackups = async () => {
    try {
        const res = await fetch(`${API_BASE}/system/backups`)
        if (res.ok) {
            backups.value = await res.json()
        }
    } catch (e) {
        console.error(e)
    }
}

const createBackup = async () => {
    backupLoading.value = true
    try {
        const res = await fetch(`${API_BASE}/system/backup`, { method: 'POST' })
        if (res.ok) {
            await fetchBackups()
            alert('备份创建成功')
        } else {
            const err = await res.json()
            alert('备份失败: ' + err.detail)
        }
    } catch (e) {
        console.error(e)
        alert('备份请求失败')
    } finally {
        backupLoading.value = false
    }
}

const deleteBackup = async (filename: string) => {
    if (!confirm(`确定要删除备份 ${filename} 吗？此操作不可恢复。`)) return
    
    try {
        const res = await fetch(`${API_BASE}/system/backups/${filename}`, { method: 'DELETE' })
        if (res.ok) {
            await fetchBackups()
        } else {
            alert('删除失败')
        }
    } catch (e) {
        console.error(e)
    }
}

const formatDate = (iso: string) => {
    return new Date(iso).toLocaleString()
}

onMounted(async () => {
    await fetchConfig()
    fetchEnvVars()
    fetchBackups()
    fetchAutoBackupConfig()
    fetchProxyConfig()
    loadSourcesFromStorage()
})

const syncConfigToBackend = async (silent = false) => {
    // Automatically set the first source as the active mirror in backend
    const topSource = pypiSources.value.length > 0 ? pypiSources.value[0].url : ''
    // Only update if changed
    if (topSource !== backendMirrorUrl.value) {
        await savePypiConfig(topSource, silent)
        backendMirrorUrl.value = topSource
    }
}

const savePypiConfig = async (url: string, silent = false) => {
  try {
    await fetch(`${API_BASE}/system/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: 'pypi_mirror',
        value: url,
        description: 'PyPI Mirror URL (Auto-synced from top priority source)'
      })
    })
  } catch (e) {
    console.error('Failed to save config', e)
    if (!silent) alert('同步配置到后端失败')
  }
}

const openSourceModal = (source?: PyPISource, index?: number) => {
    if (source && index !== undefined) {
        isEditingSource.value = true
        editingSourceIndex.value = index
        sourceForm.name = source.name
        sourceForm.url = source.url
    } else {
        isEditingSource.value = false
        editingSourceIndex.value = null
        sourceForm.name = ''
        sourceForm.url = ''
    }
    showSourceModal.value = true
}

const submitSource = () => {
    if (!sourceForm.name || !sourceForm.url) {
        alert('请填写名称和URL')
        return
    }
    
    if (isEditingSource.value && editingSourceIndex.value !== null) {
        pypiSources.value[editingSourceIndex.value] = { ...sourceForm }
    } else {
        // Add to top if it's the first one, else append?
        // Usually append. User can move up.
        pypiSources.value.push({ ...sourceForm })
    }
    showSourceModal.value = false
    saveSourcesToStorage()
    syncConfigToBackend()
}

const deleteSource = (index: number) => {
    if (confirm('确定要删除此源吗？')) {
        pypiSources.value.splice(index, 1)
        saveSourcesToStorage()
        syncConfigToBackend()
    }
}

const moveSource = (index: number, direction: number) => {
    const newIndex = index + direction
    if (newIndex < 0 || newIndex >= pypiSources.value.length) return
    
    const temp = pypiSources.value[index]
    pypiSources.value[index] = pypiSources.value[newIndex]
    pypiSources.value[newIndex] = temp
    
    saveSourcesToStorage()
    syncConfigToBackend()
}

const saveSourcesToStorage = () => {
    localStorage.setItem('pypi_sources', JSON.stringify(pypiSources.value))
}

const loadSourcesFromStorage = () => {
    const stored = localStorage.getItem('pypi_sources')
    if (stored) {
        try {
            pypiSources.value = JSON.parse(stored)
        } catch (e) {
            console.error('Failed to parse pypi sources', e)
        }
    }
    // Initial sync check
    syncConfigToBackend(true)
}

// --- Env Vars Logic ---
interface EnvVar {
  id: number
  key: string
  value: string
  description: string
  is_secret: boolean
}

interface EnvVarPayload {
  key: string
  description: string
  is_secret: boolean
  value?: string
}

const envVars = ref<EnvVar[]>([])
const showModal = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  key: '',
  value: '',
  description: '',
  is_secret: false
})

const fetchEnvVars = async () => {
  try {
    const res = await fetch(`${API_BASE}/system/env-vars`)
    if (res.ok) {
      envVars.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const openEnvModal = (item?: EnvVar) => {
  if (item) {
    isEditing.value = true
    editingId.value = item.id
    form.key = item.key
    form.value = item.is_secret ? '' : item.value
    form.description = item.description
    form.is_secret = item.is_secret
  } else {
    isEditing.value = false
    editingId.value = null
    form.key = ''
    form.value = ''
    form.description = ''
    form.is_secret = false
  }
  showModal.value = true
}

const submitEnvVar = async () => {
  if (!form.key) {
      alert('请输入变量名')
      return
  }
  
  try {
    const url = isEditing.value 
      ? `${API_BASE}/system/env-vars/${editingId.value}`
      : `${API_BASE}/system/env-vars`
    
    const method = isEditing.value ? 'PUT' : 'POST'
    
    const body: EnvVarPayload = {
      key: form.key,
      description: form.description,
      is_secret: form.is_secret
    }
    
    if (!isEditing.value || form.value !== '') {
        body.value = form.value
    }
    
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    if (res.ok) {
      showModal.value = false
      fetchEnvVars()
    } else {
      const err = await res.json()
      alert('操作失败: ' + (err.detail || '未知错误'))
    }
  } catch (error) {
    console.error(error)
    alert('请求出错')
  }
}

const deleteEnvVar = async (id: number) => {
  if (!confirm('确定要删除此变量吗？')) return
  try {
    const res = await fetch(`${API_BASE}/system/env-vars/${id}`, { method: 'DELETE' })
    if (res.ok) fetchEnvVars()
    else alert('删除失败')
  } catch (error) {
    console.error(error)
    alert('请求出错')
  }
}

onMounted(() => {
  fetchConfig()
  fetchEnvVars()
  loadSourcesFromStorage()
})
</script>

<style scoped>
.settings-container {
  max-width: 1200px;
  margin: 0;
}

/* Tabs - Using common.css */

/* Cards */
.settings-card {
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.03);
  border: 1px solid #f0f0f0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #333;
}

/* Badges */
.header-actions {
    display: flex;
    align-items: center;
}

.current-source-badge {
    background: #e6f7ff;
    color: #1890ff;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
}
.current-source-badge.empty {
    background: #f5f5f5;
    color: #999;
}

.tag-active {
    display: inline-block;
    font-size: 12px;
    color: #52c41a;
    background: #f6ffed;
    border: 1px solid #b7eb8f;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 8px;
}

.priority-badge {
    display: inline-block;
    width: 24px;
    height: 24px;
    line-height: 24px;
    text-align: center;
    border-radius: 50%;
    background: #f0f0f0;
    color: #999;
    font-size: 12px;
    font-weight: 600;
}
.priority-badge.top-priority {
    background: #1890ff;
    color: white;
    box-shadow: 0 2px 6px rgba(24, 144, 255, 0.3);
}

/* Section */
.section-desc {
  font-size: 14px;
  color: #666;
  margin-bottom: 24px;
  line-height: 1.5;
  background: #fafafa;
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 4px solid #1890ff;
}

.source-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 20px;
    margin-bottom: 15px;
}
.source-list-header h4 {
    margin: 0;
    font-size: 15px;
    color: #333;
    font-weight: 600;
}

/* Forms */
.form-group {
  margin-top: 15px;
}
.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
  font-size: 14px;
}

input[type="text"], input[type="password"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: all 0.2s;
}
input[type="text"]:focus, input[type="password"]:focus {
    border-color: #40a9ff;
    outline: none;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
  cursor: pointer;
  user-select: none;
}

/* Buttons - Unified */
.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 2px 0 rgba(0,0,0,0.015);
}

.btn-sm {
  padding: 6px 16px;
  font-size: 13px;
  height: 32px;
}

.btn-primary { 
    background-color: #1890ff; 
    color: white; 
}
.btn-primary:hover { 
    background-color: #40a9ff; 
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(24, 144, 255, 0.25);
}
.btn-primary:active {
    background-color: #096dd9;
    transform: translateY(0);
}

.btn-secondary { 
    background-color: #fff; 
    color: #595959; 
    border: 1px solid #d9d9d9;
    box-shadow: 0 2px 0 rgba(0,0,0,0.015);
    margin-right: 12px; 
}
.btn-secondary:hover { 
    color: #40a9ff;
    border-color: #40a9ff;
}

.btn-text { 
    background: none; 
    color: #1890ff; 
    padding: 4px 8px; 
    font-size: 13px;
    box-shadow: none;
    border-radius: 4px;
}
.btn-text:hover { 
    color: #40a9ff;
    background-color: #e6f7ff;
}

.btn-icon {
    background: white;
    border: 1px solid #d9d9d9;
    color: #666;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
}
.btn-icon:hover:not(:disabled) {
    border-color: #1890ff;
    color: #1890ff;
}
.btn-icon:disabled {
    opacity: 0.3;
    cursor: not-allowed;
    background: #f5f5f5;
}

.text-red { color: #ff4d4f; }
.text-red:hover { color: #ff7875; background-color: #fff1f0; }

.icon-plus { font-weight: bold; line-height: 1; font-size: 16px; }

/* Table */
.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 14px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
}

.data-table th, .data-table td {
  padding: 16px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.data-table th {
  background-color: #fafafa;
  font-weight: 500;
  color: #333;
}

.data-table tr:last-child td {
    border-bottom: none;
}
.data-table tr:hover td {
    background-color: #fafafa;
}

.actions-cell {
    display: flex;
    align-items: center;
    gap: 4px;
}

.divider-vertical {
    width: 1px;
    height: 14px;
    background: #e8e8e8;
    margin: 0 8px;
}

.font-mono { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; color: #555; }
.value-cell { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.text-center { text-align: center; }
.text-gray { color: #999; }

.badge-secret {
  display: inline-block;
  padding: 2px 8px;
  background-color: #fff1f0;
  color: #cf1322;
  border: 1px solid #ffa39e;
  border-radius: 4px;
  font-size: 11px;
  margin-right: 8px;
}

.help-text {
  margin-top: 8px;
  font-size: 12px;
  color: #999;
  display: block;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-content {
  background: white;
  padding: 32px;
  border-radius: 12px;
  width: 480px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}

.modal-content h3 {
    margin-top: 0;
    margin-bottom: 24px;
    font-size: 20px;
    color: #333;
}

.modal-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 32px;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

/* Auto Backup Styles */
.custom-label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 14px;
    color: #374151; /* Match system label color */
    font-weight: 500;
    margin-bottom: 0; /* Override default label margin */
    user-select: none;
}

.custom-checkbox {
    width: 18px;
    height: 18px;
    accent-color: #1890ff;
    cursor: pointer;
    margin: 0;
}

.form-actions {
    display: flex;
    justify-content: flex-start;
    margin-top: 10px;
}
</style>
