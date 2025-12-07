<template>
  <div class="page-container">
    <PageHeader title="定时任务" description="管理和调度您的自动化任务。">
      <template #actions>
        <button class="btn btn-secondary" @click="refreshTasks" title="刷新">
          <RefreshCwIcon :size="18" :class="{ 'spin': isRefreshing }" />
        </button>
        <button class="btn btn-primary" @click="openCreateModal">
          <PlusIcon :size="18" />
          新建任务
        </button>
      </template>
    </PageHeader>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="search-wrapper">
        <SearchIcon :size="16" class="icon-search" />
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="按名称、描述或命令搜索任务..." 
          class="search-input"
        />
      </div>
      <!-- Add more filters here if needed -->
    </div>

    <!-- Tasks List -->
    <div class="task-list">
      <div v-if="tasks.length === 0" class="empty-state">
        <div class="empty-icon">⏱️</div>
        <h3>暂无定时任务</h3>
        <p>点击右上角“新建任务”开始创建一个自动运行的任务。</p>
      </div>

      <div v-else class="task-cards">
        <div v-for="task in tasks" :key="task.id" class="task-card card">
          <!-- Top Row: Title, Status, Actions -->
          <div class="task-header-row">
            <div class="task-title-group">
              <h3 class="task-name">{{ task.name }}</h3>
              <span :class="['status-badge', task.status]">
                {{ statusText[task.status] }}
              </span>
            </div>
            
            <div class="task-actions">
              <button class="btn-icon" title="查看历史" @click="viewHistory(task)">
                <HistoryIcon :size="16" />
              </button>
              <button class="btn-icon" title="任务日志" @click="viewLogs(task)">
                <TerminalIcon :size="16" />
              </button>
              
              <button 
                v-if="task.status === 'active'" 
                class="btn-icon" 
                title="暂停任务" 
                @click="toggleTaskStatus(task)"
              >
                <PauseIcon :size="16" class="text-orange" />
              </button>
              <button 
                v-else 
                class="btn-icon" 
                title="恢复任务" 
                @click="toggleTaskStatus(task)"
              >
                <PlayIcon :size="16" class="text-green" />
              </button>

              <button 
                v-if="isRunning(task)" 
                class="btn-icon delete" 
                title="停止执行" 
                @click="stopTaskNow(task)"
              >
                <SquareIcon :size="16" fill="currentColor" />
              </button>
              <button 
                v-else 
                class="btn-icon" 
                title="立即执行" 
                @click="runTaskNow(task)"
              >
                <ZapIcon :size="16" class="text-yellow" />
              </button>
              
              <button class="btn-icon" title="编辑任务" @click="editTask(task)">
                <EditIcon :size="16" class="text-blue" />
              </button>
              <button class="btn-icon delete" title="删除任务" @click="deleteTask(task)">
                <Trash2Icon :size="16" />
              </button>
            </div>
          </div>

          <!-- Description -->
          <div class="task-description">
             {{ task.description || '暂无描述' }}
          </div>

          <!-- Info Pills -->
          <div class="task-info-pills">
            <div class="pill command-pill">
              <span class="prompt">>_</span>
              <span class="code">{{ task.command }}</span>
            </div>
            
            <div class="pill">
              <CalendarIcon :size="14" />
              <span>{{ formatTrigger(task) }}</span>
            </div>

            <div class="pill">
              <FolderIcon :size="14" />
              <span>{{ getProjectName(task.project_id) }}</span>
            </div>

            <div class="pill" v-if="task.env_id">
              <BoxIcon :size="14" />
              <span>{{ getEnvName(task.env_id) }}</span>
            </div>
          </div>

          <!-- Times -->
          <div class="task-times">
            <div class="time-item">
               <ClockIcon :size="14" />
               <span>上次运行: {{ task.latest_execution_time ? formatNextRun(task.latest_execution_time) : '从未运行' }}</span>
            </div>
            <div v-if="task.next_run" class="time-item">
               <ClockIcon :size="14" />
               <span>下次运行: {{ formatNextRun(task.next_run) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <BaseModal 
      v-model="showModal" 
      :title="isEditing ? '编辑任务' : '新建任务'" 
      width="600px"
    >
      <form @submit.prevent="handleSaveTask" class="task-form">
        <div class="form-group">
          <label for="task-name">任务名称 <span class="required">*</span></label>
          <input 
            id="task-name" 
            v-model="form.name" 
            type="text" 
            class="form-input" 
            required 
            placeholder="给任务起个名字"
          />
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label for="project">项目选择 <span class="required">*</span></label>
            <select id="project" v-model="form.project_id" class="form-select" required>
              <option value="" disabled>请选择项目</option>
              <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div class="form-group half">
            <label for="env">Python环境</label>
            <select id="env" v-model="form.env_id" class="form-select">
              <option value="" disabled>请选择环境</option>
              <option v-for="e in environments" :key="e.id" :value="e.id">{{ e.name }}</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="command">执行命令 <span class="required">*</span></label>
          <div class="command-input-wrapper">
            <span class="prefix">>_</span>
            <input 
              id="command" 
              v-model="form.command" 
              type="text" 
              class="form-input with-prefix" 
              required 
              placeholder="python main.py"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="description">任务简述</label>
          <textarea 
            id="description" 
            v-model="form.description" 
            class="form-textarea" 
            placeholder="请输入任务描述"
            rows="3"
          ></textarea>
        </div>

        <div class="form-group">
          <label>调度方式 <span class="required">*</span></label>
          <select v-model="form.trigger_type" class="form-select mb-2">
            <option value="date">一次性 (Date)</option>
            <option value="interval">间隔 (Interval)</option>
            <option value="cron">Cron 表达式</option>
            <!-- 'immediate' is usually just run once, maybe not a schedule type but an action. 
                 User said "(1) 立即执行... (2) 一次...". 
                 If "Immediate" is selected, it implies creating and running once? 
                 I will interpret "Immediate" as a one-time task that runs NOW. -->
            <option value="immediate">立即执行 (Immediate)</option>
          </select>

          <!-- Trigger Specific Fields -->
          
          <!-- Date -->
          <div v-if="form.trigger_type === 'date'" class="trigger-config">
             <input 
               v-model="form.trigger_value_date" 
               type="datetime-local" 
               class="form-input"
               required
             />
          </div>

          <!-- Interval -->
          <div v-if="form.trigger_type === 'interval'" class="trigger-config row">
            <input 
              v-model.number="form.trigger_value_interval" 
              type="number" 
              min="1" 
              class="form-input" 
              placeholder="数值"
              required
            />
            <select v-model="form.trigger_unit_interval" class="form-select">
              <option value="seconds">秒</option>
              <option value="minutes">分</option>
              <option value="hours">小时</option>
              <option value="days">天</option>
              <option value="weeks">周</option>
            </select>
          </div>

          <!-- Cron -->
          <div v-if="form.trigger_type === 'cron'" class="trigger-config">
            <div class="cron-input-wrapper">
               <input 
                 v-model="form.trigger_value_cron" 
                 type="text" 
                 class="form-input" 
                 placeholder="* * * * *"
                 required
               />
               <button type="button" class="btn btn-primary" @click="previewCron" title="预览运行时间">
                 预览
               </button>
            </div>
            <div v-if="cronPreview.length > 0" class="cron-preview">
               <p>未来 5 次运行时间:</p>
               <ul>
                 <li v-for="(time, index) in cronPreview" :key="index">{{ time }}</li>
               </ul>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="showModal = false">取消</button>
          <button type="submit" class="btn btn-primary">
            {{ isEditing ? '保存修改' : '创建任务' }}
          </button>
        </div>
      </form>
    </BaseModal>
    <!-- Modals -->
    <TaskHistoryModal
      v-if="showHistoryModal && currentTask"
      ref="historyModal"
      :task-id="currentTask.id"
      :task-name="currentTask.name"
      @view-log="openLogFromHistory"
      @close="showHistoryModal = false"
    />

    <TaskLogModal
      v-if="showLogModal && currentTask"
      ref="logModal"
      :task-id="currentTask.id"
      :task-name="currentTask.name"
      :initial-execution-id="initialExecId"
      @close="closeLogModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import TaskHistoryModal from '@/components/task/TaskHistoryModal.vue'
import TaskLogModal from '@/components/task/TaskLogModal.vue'
import { 
  PlusIcon, RefreshCwIcon, SearchIcon, 
  HistoryIcon, TerminalIcon, PauseIcon, PlayIcon, ZapIcon, EditIcon, Trash2Icon,
  CalendarIcon, FolderIcon, BoxIcon, ClockIcon, InfoIcon, SquareIcon
} from 'lucide-vue-next'

// Mock Data Interfaces
interface Task {
  id: string
  name: string
  status: 'active' | 'paused' | 'error' | 'finished'
  command: string
  project_id: number
  env_id?: number
  trigger_type: string
  trigger_value: any
  next_run?: string
  last_execution_status?: string
  latest_execution_id?: number
  latest_execution_time?: string
  description?: string
}

interface Project {
  id: number
  name: string
}

interface Env {
  id: number
  name: string
}

// State
const tasks = ref<Task[]>([])
const projects = ref<Project[]>([])
const environments = ref<Env[]>([])
const searchQuery = ref('')
const isRefreshing = ref(false)
const showModal = ref(false)
const showHistoryModal = ref(false)
const showLogModal = ref(false)
const isEditing = ref(false)
const editingId = ref<string | null>(null)
const cronPreview = ref<string[]>([])
const currentTask = ref<Task | null>(null)
const initialExecId = ref<number | undefined>(undefined)

const form = reactive({
  name: '',
  project_id: '' as string | number,
  env_id: '' as string | number,
  command: '',
  description: '',
  trigger_type: 'interval',
  trigger_value_date: '',
  trigger_value_interval: 1,
  trigger_unit_interval: 'minutes',
  trigger_value_cron: '* * * * *'
})

const statusText: Record<string, string> = {
  active: '活跃中',
  paused: '已暂停',
  error: '错误',
  finished: '已完成'
}

const API_BASE = 'http://localhost:8000/api'

const loadData = async () => {
  isRefreshing.value = true
  try {
    const [projRes, envRes, taskRes] = await Promise.all([
      fetch(`${API_BASE}/projects`),
      fetch(`${API_BASE}/python/environments`),
      fetch(`${API_BASE}/tasks`)
    ])

    if (projRes.ok) projects.value = await projRes.json()
    if (envRes.ok) environments.value = await envRes.json()
    if (taskRes.ok) {
      const data = await taskRes.json()
      // Parse trigger_value if string
      tasks.value = data.map((t: any) => {
        if (t.trigger_type === 'interval' && typeof t.trigger_value === 'string') {
          try {
             t.trigger_value = JSON.parse(t.trigger_value)
          } catch (e) { /* ignore */ }
        }
        return t
      })
    }
  } catch (e) {
    console.error(e)
  } finally {
    isRefreshing.value = false
  }
}

onMounted(() => {
  loadData()
  // Poll for task status updates
  const interval = setInterval(loadData, 3000)
  onUnmounted(() => clearInterval(interval))
})

// Actions
const refreshTasks = () => {
  loadData()
}

const openCreateModal = () => {
  isEditing.value = false
  editingId.value = null
  resetForm()
  showModal.value = true
}

const editTask = (task: Task) => {
  isEditing.value = true
  editingId.value = task.id
  form.name = task.name
  form.project_id = task.project_id
  form.env_id = task.env_id || ''
  form.command = task.command
  form.description = task.description || ''
  
  // Parse trigger info back to form
  form.trigger_type = task.trigger_type
  if (task.trigger_type === 'interval') {
     const val = task.trigger_value
     form.trigger_value_interval = val.value || 1
     form.trigger_unit_interval = val.unit || 'minutes'
  } else if (task.trigger_type === 'cron') {
     form.trigger_value_cron = task.trigger_value as string
  } else if (task.trigger_type === 'date') {
     form.trigger_value_date = task.trigger_value as string
  }
  
  showModal.value = true
}

const resetForm = () => {
  form.name = ''
  form.project_id = ''
  form.env_id = ''
  form.command = ''
  form.description = ''
  form.trigger_type = 'interval'
  form.trigger_value_date = ''
  form.trigger_value_interval = 1
  form.trigger_unit_interval = 'minutes'
  form.trigger_value_cron = '* * * * *'
  cronPreview.value = []
}

const handleSaveTask = async () => {
  let triggerValue: any = ''
  if (form.trigger_type === 'interval') {
    triggerValue = JSON.stringify({
      value: form.trigger_value_interval,
      unit: form.trigger_unit_interval
    })
  } else if (form.trigger_type === 'cron') {
    triggerValue = form.trigger_value_cron
  } else if (form.trigger_type === 'date') {
    triggerValue = form.trigger_value_date
  }

  const payload = {
    name: form.name,
    command: form.command,
    project_id: form.project_id,
    env_id: form.env_id || null,
    description: form.description || null,
    trigger_type: form.trigger_type,
    trigger_value: triggerValue
  }

  try {
    let res
    if (isEditing.value && editingId.value) {
       res = await fetch(`${API_BASE}/tasks/${editingId.value}`, {
         method: 'PUT',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify(payload)
       })
    } else {
       res = await fetch(`${API_BASE}/tasks`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify(payload)
       })
    }

    if (res.ok) {
      showModal.value = false
      loadData()
    } else {
      const err = await res.json()
      alert(`保存失败: ${err.detail}`)
    }
  } catch (e) {
    console.error(e)
    alert('保存失败')
  }
}

const deleteTask = async (task: Task) => {
  if(confirm(`确定要删除任务 "${task.name}" 吗？`)) {
    try {
      const res = await fetch(`${API_BASE}/tasks/${task.id}`, { method: 'DELETE' })
      if (res.ok) {
        loadData()
      } else {
        alert('删除失败')
      }
    } catch (e) {
      console.error(e)
    }
  }
}

const toggleTaskStatus = async (task: Task) => {
  const action = task.status === 'active' ? 'pause' : 'resume'
  try {
    const res = await fetch(`${API_BASE}/tasks/${task.id}/${action}`, { method: 'POST' })
    if (res.ok) {
      loadData()
    } else {
      alert('操作失败')
    }
  } catch (e) {
    console.error(e)
  }
}

const runTaskNow = async (task: Task) => {
  try {
    const res = await fetch(`${API_BASE}/tasks/${task.id}/run`, { method: 'POST' })
    if (res.ok) {
       // Refresh to get running status
       // We can manually set it to running locally for instant feedback
       // But we need execution ID for stop.
       // Let's just refresh.
       loadData()
    } else {
      alert('触发失败')
    }
  } catch (e) {
    console.error(e)
  }
}

const stopTaskNow = async (task: Task) => {
   if (!task.latest_execution_id) return
   try {
      const res = await fetch(`${API_BASE}/tasks/executions/${task.latest_execution_id}/stop`, { method: 'POST' })
      if (res.ok) {
         loadData()
      } else {
         alert('停止失败')
      }
   } catch (e) {
      console.error(e)
   }
}

const isRunning = (task: Task) => {
   return task.last_execution_status === 'running'
}

const viewHistory = (task: Task) => {
  currentTask.value = task
  showHistoryModal.value = true
}

const viewLogs = (task: Task) => {
  currentTask.value = task
  showLogModal.value = true
}

const openLogFromHistory = (execId: number) => {
  showHistoryModal.value = false
  // Wait for modal transition
  setTimeout(() => {
     if (currentTask.value) {
        initialExecId.value = execId
        showLogModal.value = true
     }
  }, 200)
}

const closeLogModal = () => {
   showLogModal.value = false
   initialExecId.value = undefined
}


const previewCron = () => {
  // Mock preview
  const now = new Date()
  cronPreview.value = Array.from({length: 5}, (_, i) => {
     const d = new Date(now.getTime() + (i + 1) * 3600000 * 24) // +1 day for mock
     return d.toLocaleString()
  })
}

// Helpers
const getProjectName = (id: number) => projects.value.find(p => p.id === id)?.name || 'Unknown'
const getEnvName = (id: number) => environments.value.find(e => e.id === id)?.name || 'Unknown'

const formatTrigger = (task: Task) => {
  if (task.trigger_type === 'interval') {
    const val = task.trigger_value
    return `Every ${val.value} ${val.unit}`
  } else if (task.trigger_type === 'cron') {
    return `Cron: ${task.trigger_value}`
  } else if (task.trigger_type === 'date') {
    return `Once: ${task.trigger_value}`
  }
  return task.trigger_type
}

const formatNextRun = (iso: string) => {
  return new Date(iso).toLocaleString()
}
</script>

<style scoped>
/* .tasks-page removed, using .page-container from common.css */

/* .filter-bar and .search-wrapper removed, using common.css */

.task-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-card {
  display: flex;
  flex-direction: column;
  padding: 24px;
  position: relative;
}

.task-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.task-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.task-description {
  font-size: 14px;
  color: #4b5563;
  margin-bottom: 16px;
  line-height: 1.5;
}

.task-info-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f3f4f6;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: #4b5563;
}

.pill.command-pill {
  font-family: monospace;
}

.pill .prompt {
  color: #9ca3af;
}

.pill .code {
  color: #1f2937;
  font-weight: 500;
}

.task-times {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: #6b7280;
  border-top: 1px solid #f3f4f6;
  padding-top: 12px;
}

.time-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.text-orange { color: #f59e0b; }
.text-green { color: #10b981; }
.text-red { color: #ef4444; }
.text-blue { color: #3b82f6; }
.text-yellow { color: #eab308; }

/* Form Styles */
.task-form {
  padding: 10px 0;
}

.form-row { display: flex; gap: 16px; }
.form-group.half { flex: 1; }

/* .form-group, label, required, input styles removed, using common.css */

.command-input-wrapper {
  display: flex;
  align-items: center;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  padding-left: 12px;
}

.command-input-wrapper .prefix {
  color: #9ca3af;
  font-family: monospace;
  margin-right: 4px;
}

.command-input-wrapper .form-input {
  border: none;
  padding-left: 4px;
  box-shadow: none;
}

.trigger-config {
  margin-top: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.trigger-config.row {
  display: flex;
  gap: 12px;
}

.cron-input-wrapper {
  display: flex;
  gap: 8px;
}

.cron-preview {
  margin-top: 12px;
  font-size: 12px;
  color: #6b7280;
}

.cron-preview ul {
  margin: 4px 0 0 0;
  padding-left: 20px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 30px;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
