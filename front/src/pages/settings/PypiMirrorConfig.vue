<template>
  <div class="section">
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

const API_BASE = 'http://localhost:8000/api'

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

const syncConfigToBackend = async (silent = false) => {
    const topSource = pypiSources.value.length > 0 ? pypiSources.value[0].url : ''
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
    syncConfigToBackend(true)
}

onMounted(() => {
    fetchConfig()
    loadSourcesFromStorage()
})
</script>

<style scoped>
/* Reuse or import common styles */
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
.text-center { text-align: center; }
.text-gray { color: #999; }

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

input[type="text"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: all 0.2s;
}
input[type="text"]:focus {
    border-color: #40a9ff;
    outline: none;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
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
</style>