<template>
  <div class="section">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

const API_BASE = '/api'

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

const proxyForm = reactive({
    enabled: false,
    url: ''
})
const proxySaving = ref(false)

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

onMounted(() => {
    fetchEnvVars()
    fetchProxyConfig()
})
</script>

<style scoped>
/* Reuse styles */
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

.help-text {
  margin-top: 8px;
  font-size: 12px;
  color: #999;
  display: block;
}

/* Proxy Styles */
.custom-label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 14px;
    color: #374151;
    font-weight: 500;
    margin-bottom: 0;
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