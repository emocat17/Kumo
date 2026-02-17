<template>
  <div class="section">
    <div class="card settings-card">
      <div class="card-header">
        <h3>数据管理与预览</h3>
        <div class="header-actions">
          <button class="btn btn-primary btn-sm" :disabled="loading" @click="handleRefresh">
            {{ loading ? '刷新中...' : '刷新数据' }}
          </button>
          <button class="btn btn-danger btn-sm" :disabled="clearing" @click="confirmClear">
            {{ clearing ? '清空中...' : '一键清空' }}
          </button>
        </div>
      </div>
      <p class="section-desc">
        用于核对数据库记录与本地文件是否一致，并支持快速清理异常数据。
      </p>
      <div class="meta-grid">
        <div class="meta-item">
          <div class="meta-label">数据库路径</div>
          <div class="meta-value font-mono">{{ overview?.db_path || '-' }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">数据库状态</div>
          <div class="meta-value">
            <span :class="['badge', overview?.db_exists ? 'badge-ok' : 'badge-missing']">
              {{ overview?.db_exists ? '存在' : '不存在' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="card settings-card" style="margin-top: 24px;">
      <div class="tabs">
        <button :class="['tab-btn', { active: activeTab === 'versions' }]" @click="activeTab = 'versions'">
          Python 版本
        </button>
        <button :class="['tab-btn', { active: activeTab === 'envs' }]" @click="activeTab = 'envs'">
          Python 环境
        </button>
        <button :class="['tab-btn', { active: activeTab === 'projects' }]" @click="activeTab = 'projects'">
          项目
        </button>
        <button :class="['tab-btn', { active: activeTab === 'tasks' }]" @click="activeTab = 'tasks'">
          任务
        </button>
      </div>

      <table class="data-table">
        <thead>
          <tr v-if="activeTab === 'versions' || activeTab === 'envs'">
            <th>ID</th>
            <th>名称</th>
            <th>版本</th>
            <th>路径</th>
            <th>状态</th>
            <th>文件</th>
            <th>操作</th>
          </tr>
          <tr v-else-if="activeTab === 'projects'">
            <th>ID</th>
            <th>名称</th>
            <th>路径</th>
            <th>工作目录</th>
            <th>输出目录</th>
            <th>文件</th>
            <th>操作</th>
          </tr>
          <tr v-else>
            <th>ID</th>
            <th>名称</th>
            <th>状态</th>
            <th>项目</th>
            <th>环境</th>
            <th>触发器</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="activeTab === 'versions'">
            <tr v-for="row in versionRows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.name || '-' }}</td>
              <td class="font-mono">{{ row.version || '-' }}</td>
              <td class="font-mono">{{ row.path || '-' }}</td>
              <td>
                <span class="badge">{{ row.status || '-' }}</span>
              </td>
              <td>
                <span :class="['badge', row.path_exists ? 'badge-ok' : 'badge-missing']">
                  {{ row.path_exists ? '存在' : '缺失' }}
                </span>
              </td>
              <td>
                <button
                  class="btn-text text-red"
                  :disabled="isDeletingVersion(row.id) || row.status === 'deleting'"
                  @click="deleteVersion(row.id)"
                >
                  {{ isDeletingVersion(row.id) || row.status === 'deleting' ? '删除中' : '删除' }}
                </button>
              </td>
            </tr>
            <tr v-if="versionRows.length === 0">
              <td colspan="7" class="text-center text-gray">暂无数据</td>
            </tr>
          </template>
          <template v-else-if="activeTab === 'envs'">
            <tr v-for="row in envRows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.name || '-' }}</td>
              <td class="font-mono">{{ row.version || '-' }}</td>
              <td class="font-mono">{{ row.path || '-' }}</td>
              <td>
                <span class="badge">{{ row.status || '-' }}</span>
              </td>
              <td>
                <span :class="['badge', row.path_exists ? 'badge-ok' : 'badge-missing']">
                  {{ row.path_exists ? '存在' : '缺失' }}
                </span>
              </td>
              <td>
                <button
                  class="btn-text text-red"
                  :disabled="isDeletingVersion(row.id) || row.status === 'deleting'"
                  @click="deleteVersion(row.id)"
                >
                  {{ isDeletingVersion(row.id) || row.status === 'deleting' ? '删除中' : '删除' }}
                </button>
              </td>
            </tr>
            <tr v-if="envRows.length === 0">
              <td colspan="7" class="text-center text-gray">暂无数据</td>
            </tr>
          </template>
          <template v-else-if="activeTab === 'projects'">
            <tr v-for="row in projectRows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.name || '-' }}</td>
              <td class="font-mono">{{ row.path || '-' }}</td>
              <td class="font-mono">{{ row.work_dir || '-' }}</td>
              <td class="font-mono">{{ row.output_dir || '-' }}</td>
              <td>
                <span :class="['badge', row.path_exists ? 'badge-ok' : 'badge-missing']">
                  {{ row.path_exists ? '存在' : '缺失' }}
                </span>
              </td>
              <td>
                <button
                  class="btn-text text-red"
                  :disabled="isDeletingProject(row.id)"
                  @click="deleteProject(row.id)"
                >
                  {{ isDeletingProject(row.id) ? '删除中' : '删除' }}
                </button>
              </td>
            </tr>
            <tr v-if="projectRows.length === 0">
              <td colspan="7" class="text-center text-gray">暂无数据</td>
            </tr>
          </template>
          <template v-else>
            <tr v-for="row in taskRows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.name || '-' }}</td>
              <td>
                <span class="badge">{{ row.status || '-' }}</span>
              </td>
              <td>{{ row.project_id != null ? (projectNameMap[row.project_id] || '-') : '-' }}</td>
              <td>{{ row.env_id != null ? (envNameMap[row.env_id] || '-') : '-' }}</td>
              <td>{{ row.trigger_type || '-' }}</td>
              <td>
                <button
                  class="btn-text text-red"
                  :disabled="isDeletingTask(row.id)"
                  @click="deleteTask(row.id)"
                >
                  {{ isDeletingTask(row.id) ? '删除中' : '删除' }}
                </button>
              </td>
            </tr>
            <tr v-if="taskRows.length === 0">
              <td colspan="7" class="text-center text-gray">暂无数据</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const API_BASE = '/api'

type ActiveTab = 'versions' | 'envs' | 'projects' | 'tasks'

interface VersionRow {
  id: number
  name: string
  version: string
  path: string
  status: string
  is_conda: boolean
  path_exists: boolean
}

interface ProjectRow {
  id: number
  name: string
  path: string
  work_dir: string
  output_dir: string
  path_exists: boolean
}

interface TaskRow {
  id: number
  name: string
  status: string
  project_id: number | null
  env_id: number | null
  trigger_type: string
}

interface DataOverview {
  db_path: string
  db_exists: boolean
  python_versions: VersionRow[]
  python_environments: VersionRow[]
  projects: ProjectRow[]
  tasks: TaskRow[]
}

const activeTab = ref<ActiveTab>('versions')
const overview = ref<DataOverview | null>(null)
const loading = ref(false)
const clearing = ref(false)
const deletingVersionIds = ref(new Set<number>())
const deletingProjectIds = ref(new Set<number>())
const deletingTaskIds = ref(new Set<number>())

const envNameMap = computed(() => {
  const map: Record<number, string> = {}
  overview.value?.python_versions?.forEach((v) => {
    map[v.id] = v.name || v.version
  })
  return map
})

const projectNameMap = computed(() => {
  const map: Record<number, string> = {}
  overview.value?.projects?.forEach((p) => {
    map[p.id] = p.name
  })
  return map
})

const versionRows = computed(() => overview.value?.python_versions ?? [])
const envRows = computed(() => overview.value?.python_environments ?? [])
const projectRows = computed(() => overview.value?.projects ?? [])
const taskRows = computed(() => overview.value?.tasks ?? [])

const handleRefresh = () => {
  fetchOverview()
}

const fetchOverview = async (options?: { silent?: boolean }) => {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/system/data/overview`)
    if (!res.ok) throw new Error(await res.text())
    overview.value = await res.json()
  } catch (e) {
    console.error(e)
    if (!options?.silent) {
      alert('获取数据失败')
    }
  } finally {
    loading.value = false
  }
}

const updateDeletingSet = (setRef: typeof deletingVersionIds, id: number, active: boolean) => {
  const next = new Set(setRef.value)
  if (active) {
    next.add(id)
  } else {
    next.delete(id)
  }
  setRef.value = next
}

const isDeletingVersion = (id: number) => deletingVersionIds.value.has(id)
const isDeletingProject = (id: number) => deletingProjectIds.value.has(id)
const isDeletingTask = (id: number) => deletingTaskIds.value.has(id)

const updateVersionStatus = (id: number, status: string) => {
  if (!overview.value) return
  overview.value = {
    ...overview.value,
    python_versions: overview.value.python_versions.map((row) =>
      row.id === id ? { ...row, status } : row
    ),
    python_environments: overview.value.python_environments.map((row) =>
      row.id === id ? { ...row, status } : row
    )
  }
}

const parseErrorMessage = async (res: Response, fallback: string) => {
  try {
    const text = await res.text()
    if (!text) return fallback
    try {
      const data = JSON.parse(text)
      return data.detail || data.message || fallback
    } catch {
      return text
    }
  } catch {
    return fallback
  }
}

const deleteVersion = async (id: number) => {
  if (!confirm('确定删除该记录吗？')) return
  if (isDeletingVersion(id)) return
  updateDeletingSet(deletingVersionIds, id, true)
  updateVersionStatus(id, 'deleting')
  await fetchOverview({ silent: true })
  try {
    const res = await fetch(`${API_BASE}/python/versions/${id}`, { method: 'DELETE' })
    if (!res.ok) {
      const message = await parseErrorMessage(res, '删除失败')
      throw new Error(message)
    }
  } catch (e) {
    console.error(e)
    alert(e instanceof Error ? e.message : '删除失败')
  } finally {
    await fetchOverview({ silent: true })
    updateDeletingSet(deletingVersionIds, id, false)
  }
}

const deleteProject = async (id: number) => {
  if (!confirm('确定删除该项目吗？')) return
  if (isDeletingProject(id)) return
  updateDeletingSet(deletingProjectIds, id, true)
  await fetchOverview({ silent: true })
  try {
    const res = await fetch(`${API_BASE}/projects/${id}`, { method: 'DELETE' })
    if (!res.ok) {
      const message = await parseErrorMessage(res, '删除失败')
      throw new Error(message)
    }
  } catch (e) {
    console.error(e)
    alert(e instanceof Error ? e.message : '删除失败')
  } finally {
    await fetchOverview({ silent: true })
    updateDeletingSet(deletingProjectIds, id, false)
  }
}

const deleteTask = async (id: number) => {
  if (!confirm('确定删除该任务吗？')) return
  if (isDeletingTask(id)) return
  updateDeletingSet(deletingTaskIds, id, true)
  await fetchOverview({ silent: true })
  try {
    const res = await fetch(`${API_BASE}/tasks/${id}`, { method: 'DELETE' })
    if (!res.ok) {
      const message = await parseErrorMessage(res, '删除失败')
      throw new Error(message)
    }
  } catch (e) {
    console.error(e)
    alert(e instanceof Error ? e.message : '删除失败')
  } finally {
    await fetchOverview({ silent: true })
    updateDeletingSet(deletingTaskIds, id, false)
  }
}

const confirmClear = async () => {
  const ok = confirm('此操作将清空数据库数据并清理相关文件，是否继续？')
  if (!ok) return
  clearing.value = true
  try {
    const res = await fetch(`${API_BASE}/system/data/clear`, { method: 'POST' })
    if (!res.ok) throw new Error(await res.text())
    await fetchOverview()
    alert('已清空数据')
  } catch (e) {
    console.error(e)
    alert('清空失败')
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  fetchOverview()
})
</script>

<style scoped>
.settings-card {
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0f0f0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
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

.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.meta-item {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px 16px;
  border: 1px solid #eef1f5;
}

.meta-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}

.meta-value {
  font-size: 14px;
  color: #111827;
}

.tabs {
  display: flex;
  gap: 32px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 16px;
  padding-left: 8px;
}

.tab-btn {
  padding: 12px 4px;
  border: none;
  background: none;
  font-size: 16px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  position: relative;
  transition: all 0.3s;
}

.tab-btn:hover {
  color: #1890ff;
}

.tab-btn.active {
  color: #1890ff;
  font-weight: 600;
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 3px;
  background-color: #1890ff;
  border-radius: 3px 3px 0 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: #f3f4f6;
  color: #4b5563;
}

.badge-ok {
  background: #ecfdf5;
  color: #047857;
}

.badge-missing {
  background: #fef2f2;
  color: #b91c1c;
}
</style>
