<template>
  <div class="section">
    
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
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { DatabaseIcon } from 'lucide-vue-next'

const API_BASE = 'http://localhost:8000/api'

interface BackupFile {
  filename: string
  size: string
  size_raw: number
  created_at: string
}

const backups = ref<BackupFile[]>([])
const backupLoading = ref(false)

const autoBackupForm = reactive({
    enabled: false,
    interval: 24,
    retention: 7
})
const autoBackupSaving = ref(false)

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

onMounted(() => {
    fetchBackups()
    fetchAutoBackupConfig()
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

input[type="number"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: all 0.2s;
}
input[type="number"]:focus {
    border-color: #40a9ff;
    outline: none;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.form-actions {
    display: flex;
    justify-content: flex-start;
    margin-top: 10px;
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

.text-blue { color: #1890ff; }

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
.text-center { text-align: center; }
.text-gray { color: #999; }

.file-info {
    display: flex;
    align-items: center;
}

.actions-cell {
    display: flex;
    align-items: center;
    gap: 4px;
}
</style>