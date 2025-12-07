<template>
  <div class="page-container">
    <PageHeader title="项目管理" description="管理您的项目及其工作区。">
      <template #actions>
        <button class="btn btn-primary" @click="openCreateModal">
          <i class="icon-plus">+</i> 新建项目
        </button>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <div class="search-wrapper">
        <i class="icon-search">🔍</i>
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="按项目名称搜索..." 
          class="search-input"
        />
      </div>
    </div>

    <!-- Projects Grid -->
    <div v-if="filteredProjects.length > 0" class="grid-container">
      <div v-for="proj in filteredProjects" :key="proj.id" class="card project-card">
        <div class="card-header">
          <h3 class="card-title" :title="proj.name">{{ proj.name }}</h3>
          <span class="created-time">{{ formatDate(proj.created_at) }}</span>
        </div>
        
        <div class="card-body">
          <p class="description">{{ proj.description || '暂无描述' }}</p>
          
          <div class="info-row">
            <span class="label">工作路径:</span>
            <span class="value" :title="proj.work_dir">{{ proj.work_dir }}</span>
          </div>
          
          <div class="actions-row">
             <button class="btn-icon" title="打开编辑器" @click="openEditor(proj)">
               <Folder :size="18" />
             </button>
             <button class="btn-icon" title="配置项目" @click="openCreateModal">
               <Edit :size="18" />
             </button>
             <button 
               class="btn-icon delete" 
               title="删除" 
               :disabled="!!taskCounts[proj.id]"
               @click="deleteProject(proj)"
             >
               <Trash2 :size="18" />
             </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <div class="empty-icon">📂</div>
      <h3>暂无项目</h3>
      <p>点击右上角“新建项目”开始您的第一个项目。</p>
    </div>

    <!-- Create Project Modal -->
    <BaseModal v-model="showCreateModal" title="新建项目" width="500px">
      <form class="create-form" @submit.prevent="handleCreateProject">
        <div class="form-group">
          <label for="name">项目名称 <span class="required">*</span></label>
          <input 
            id="name" 
            v-model="form.name" 
            type="text" 
            placeholder="请输入项目名称" 
            class="form-input"
            required
          />
        </div>

        <div class="form-group">
          <label for="work_dir">工作路径 <span class="required">*</span></label>
          <input 
            id="work_dir" 
            v-model="form.work_dir" 
            type="text" 
            placeholder="例如: ./" 
            class="form-input"
            required
          />
          <small class="form-hint">相对于压缩包根目录的执行路径</small>
        </div>

        <div class="form-group">
          <label for="file">项目文件 (ZIP) <span class="required">*</span></label>
          <div class="file-upload-wrapper">
            <input 
              id="file" 
              ref="fileInput" 
              type="file"
              accept=".zip"
              class="file-input"
              required
              @change="handleFileChange"
            />
            <div class="file-display" @click="triggerFileSelect">
                <span v-if="selectedFile">{{ selectedFile.name }}</span>
                <span v-else class="placeholder">点击选择 .zip 文件</span>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="showCreateModal = false">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
            {{ isSubmitting ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>
    </BaseModal>
    
    <!-- Project Editor Modal -->
    <ProjectEditorModal
        v-if="showEditorModal && currentProject"
        :project-id="currentProject.id"
        :project-name="currentProject.name"
        @close="closeEditor"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ProjectEditorModal from '@/components/project/ProjectEditorModal.vue'
import { Folder, Edit, Trash2 } from 'lucide-vue-next'

interface Project {
  id: number
  name: string
  path: string
  work_dir: string
  description: string
  created_at: string
}

const projects = ref<Project[]>([])
const taskCounts = ref<Record<number, number>>({})
const searchQuery = ref('')
const showCreateModal = ref(false)
const showEditorModal = ref(false)
const currentProject = ref<Project | null>(null)
const isSubmitting = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)

const filteredProjects = computed(() => {
  if (!searchQuery.value) return projects.value
  const query = searchQuery.value.toLowerCase()
  return projects.value.filter(p => p.name.toLowerCase().includes(query))
})

const form = reactive({
  name: '',
  work_dir: './'
})

const API_BASE = 'http://localhost:8000/api'

const fetchProjects = async () => {
  try {
    const res = await fetch(`${API_BASE}/projects`)
    if (res.ok) {
      projects.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchTasks = async () => {
  try {
    const res = await fetch(`${API_BASE}/tasks`)
    if (res.ok) {
      const tasks = await res.json()
      // Count tasks per project
      const counts: Record<number, number> = {}
      tasks.forEach((t: any) => {
        counts[t.project_id] = (counts[t.project_id] || 0) + 1
      })
      taskCounts.value = counts
    }
  } catch (e) {
    console.error(e)
  }
}

const openCreateModal = () => {
  showCreateModal.value = true
  form.name = ''
  form.work_dir = './'
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

const triggerFileSelect = () => {
    fileInput.value?.click()
}

const handleFileChange = (event: Event) => {
    const target = event.target as HTMLInputElement
    if (target.files && target.files.length > 0) {
        selectedFile.value = target.files[0]
    }
}

const handleCreateProject = async () => {
  if (!selectedFile.value) {
      alert("请选择项目文件")
      return
  }

  isSubmitting.value = true
  
  const formData = new FormData()
  formData.append('name', form.name)
  formData.append('work_dir', form.work_dir)
  formData.append('file', selectedFile.value)

  try {
    const res = await fetch(`${API_BASE}/projects/create`, {
      method: 'POST',
      body: formData
    })

    if (res.ok) {
      await fetchProjects()
      showCreateModal.value = false
    } else {
      const err = await res.json()
      alert(`创建失败: ${err.detail}`)
    }
  } catch (e) {
    console.error(e)
    alert('创建失败: 网络错误')
  } finally {
    isSubmitting.value = false
  }
}

const openEditor = (proj: Project) => {
  currentProject.value = proj
  showEditorModal.value = true
}

const closeEditor = () => {
    showEditorModal.value = false
    currentProject.value = null
}

const deleteProject = async (proj: Project) => {
    if (taskCounts.value[proj.id]) {
      alert('该项目正在被任务使用，无法删除。')
      return
    }
    if(!confirm(`确定要删除项目 "${proj.name}" 吗？这将会删除服务器上的文件。`)) return
    
    try {
        const res = await fetch(`${API_BASE}/projects/${proj.id}`, { method: 'DELETE' })
        if(res.ok) {
            fetchProjects()
        } else {
            alert('删除失败')
        }
    } catch(e) {
        console.error(e)
    }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

onMounted(() => {
  fetchProjects()
  fetchTasks()
})
</script>

<style scoped>
/* .projects-page removed */

/* .filter-bar, .search-wrapper, .search-input, .icon-search removed */

/* .project-grid removed */

/* .card-header from common.css handles layout */

/* .project-name removed, using .card-title */

.created-time {
    font-size: 12px;
    color: #888;
}

/* .card-body from common.css */

.description {
    font-size: 14px;
    color: #666;
    margin-bottom: 15px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.info-row {
  display: flex;
  margin-bottom: 10px;
  font-size: 14px;
}

.label {
    color: #888;
    margin-right: 8px;
}

.actions-row {
    margin-top: 15px;
    display: flex;
    justify-content: flex-end;
}

/* .empty-state removed */

/* Form Styles - mostly removed, kept specific ones */

/* .form-group, label, required, .form-input removed */

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.file-input {
    display: none;
}

.file-display {
    border: 1px dashed #d1d5db;
    padding: 10px;
    border-radius: 6px;
    text-align: center;
    cursor: pointer;
    background: #f9fafb;
    color: #374151;
}

.file-display:hover {
    background: #f3f4f6;
    border-color: #9ca3af;
}

.placeholder {
    color: #9ca3af;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

/* Button styles removed */
</style>
