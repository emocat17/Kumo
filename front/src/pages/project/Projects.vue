<template>
  <div class="page-container">
    <PageHeader title="项目管理" description="管理您的项目及其工作区。">
      <template #actions>
        <button class="btn btn-primary" @click="openProjectModal()">
          <i class="icon-plus">+</i> 新建项目
        </button>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <div class="search-wrapper">
        <SearchIcon :size="16" class="icon-search" />
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
          
          <div v-if="proj.output_dir" class="info-row">
            <span class="label">输出路径:</span>
            <span class="value" :title="proj.output_dir">{{ proj.output_dir }}</span>
          </div>
          
          <div class="actions-row">
             <button class="btn-icon" title="打开编辑器" @click="openEditor(proj)">
               <Folder :size="18" />
             </button>
             <button class="btn-icon" title="配置项目" @click="openProjectModal(proj)">
               <Edit :size="18" />
             </button>
            <button 
              class="btn-icon delete" 
              :disabled="proj.used_by_tasks && proj.used_by_tasks.length > 0"
              :title="proj.used_by_tasks && proj.used_by_tasks.length > 0 ? `无法删除：${proj.used_by_tasks.join(', ')} 定时任务使用中` : '删除'"
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

    <!-- Create/Edit Project Modal -->
    <BaseModal v-model="showCreateModal" :title="isEditing ? '编辑项目' : '新建项目'" width="620px" height="70vh">
      <form class="create-form" @submit.prevent="handleProjectSubmit">
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
          <label for="description">描述</label>
          <textarea 
            id="description" 
            v-model="form.description" 
            placeholder="项目描述..." 
            class="form-textarea"
            rows="3"
          ></textarea>
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
            <label for="output_dir">数据输出路径</label>
            <div class="input-with-button">
                <input 
                  id="output_dir" 
                  v-model="form.output_dir" 
                  type="text" 
                  placeholder="例如: /data/my_project_data" 
                  class="form-input"
                />
                <button type="button" class="btn btn-secondary browse-btn" @click="isPathSelectorOpen = true">
                  浏览
                </button>
            </div>
            <small class="form-hint">建议使用 /data 目录下的路径，如 /data/my_project_output（容器内路径会自动映射到宿主机）</small>
        </div>

        <div v-if="!isEditing" class="form-group">
          <label for="file">项目文件 (ZIP/7Z/RAR) <span class="required">*</span></label>
          <div class="file-upload-wrapper">
            <input 
              id="file" 
              ref="fileInput" 
              type="file"
              accept=".zip,.7z,.rar"
              class="file-input"
              required
              @change="handleFileChange"
            />
            <div class="file-display" @click="triggerFileSelect">
                <span v-if="selectedFile">{{ selectedFile.name }}</span>
                <span v-else class="placeholder">点击选择 .zip/.7z/.rar 文件</span>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="showCreateModal = false">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
            {{ isSubmitting ? '提交中...' : (isEditing ? '更新' : '保存') }}
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
    
    <!-- Directory Selector Modal -->
    <FileSelectorModal 
      :is-open="isPathSelectorOpen" 
      :is-dir-mode="true"
      @close="isPathSelectorOpen = false" 
      @select="onOutputDirSelected" 
    />

    <!-- Error Modal -->
    <BaseModal v-model="showErrorModal" title="操作失败" width="400px">
      <div class="error-modal-content">
        <div class="error-icon">⚠️</div>
        <p class="error-message">{{ errorMessage }}</p>
      </div>
      <template #footer>
        <button class="btn btn-primary" @click="showErrorModal = false">确定</button>
      </template>
    </BaseModal>

    <!-- Confirm Delete Modal -->
    <BaseModal v-model="showConfirmModal" title="确认删除" width="400px">
      <div class="confirm-modal-content">
        <div class="confirm-icon">⚠️</div>
        <p>确定要删除项目 <strong>{{ deleteTarget?.name }}</strong> 吗？</p>
        <p class="confirm-warning">这将会删除服务器上的项目文件，且不可恢复！</p>
      </div>
      <template #footer>
        <button class="btn btn-secondary" @click="showConfirmModal = false">取消</button>
        <button class="btn btn-danger" @click="confirmDelete">确认删除</button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ProjectEditorModal from '@/components/project/ProjectEditorModal.vue'
import FileSelectorModal from '@/components/common/FileSelectorModal.vue'
import { Folder, Edit, Trash2, SearchIcon } from 'lucide-vue-next'

interface Project {
  id: number
  name: string
  path: string
  work_dir: string
  output_dir?: string
  description: string
  created_at: string
  used_by_tasks?: string[]
}

const projects = ref<Project[]>([])
// const taskCounts = ref<Record<number, number>>({}) // Removed
const searchQuery = ref('')
const showCreateModal = ref(false)
const showEditorModal = ref(false)
const currentProject = ref<Project | null>(null)
const isSubmitting = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)

const isPathSelectorOpen = ref(false)

// Delete confirmation and error modal states
const showConfirmModal = ref(false)
const showErrorModal = ref(false)
const errorMessage = ref('')
const deleteTarget = ref<Project | null>(null)

const filteredProjects = computed(() => {
  if (!searchQuery.value) return projects.value
  const query = searchQuery.value.toLowerCase()
  return projects.value.filter(p => p.name.toLowerCase().includes(query))
})

const form = reactive({
  name: '',
  work_dir: './',
  output_dir: '',
  description: ''
})

const API_BASE = '/api'

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

const openProjectModal = (proj?: Project) => {
  showCreateModal.value = true
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
  
  if (proj) {
      isEditing.value = true
      editingId.value = proj.id
      form.name = proj.name
      form.work_dir = proj.work_dir
      form.output_dir = proj.output_dir || ''
      form.description = proj.description || ''
  } else {
      isEditing.value = false
      editingId.value = null
      form.name = ''
      form.work_dir = './'
      form.output_dir = ''
      form.description = ''
  }
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

const handleProjectSubmit = async () => {
    if (isEditing.value) {
        if (!editingId.value) return
        isSubmitting.value = true
        try {
            const res = await fetch(`${API_BASE}/projects/${editingId.value}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: form.name,
                    work_dir: form.work_dir,
                    output_dir: form.output_dir,
                    description: form.description
                })
            })
            if (res.ok) {
                await fetchProjects()
                showCreateModal.value = false
            } else {
                const err = await res.json()
                alert(`更新失败: ${err.detail}`)
            }
        } catch(e) {
            console.error(e)
            alert('更新失败: 网络错误')
        } finally {
            isSubmitting.value = false
        }
    } else {
        if (!selectedFile.value) {
            alert("请选择项目文件")
            return
        }

        isSubmitting.value = true
        
        const formData = new FormData()
        formData.append('name', form.name)
        formData.append('work_dir', form.work_dir)
        formData.append('file', selectedFile.value)
        if (form.description) {
            formData.append('description', form.description)
        }
        if (form.output_dir) {
            formData.append('output_dir', form.output_dir)
        }

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
            // 尝试检查是否实际上创建成功 (针对超时情况)
            try {
                await fetchProjects()
                const exists = projects.value.find(p => p.name === form.name)
                if (exists) {
                    showCreateModal.value = false
                    return
                }
            } catch (innerE) {
                console.error("Recovery check failed", innerE)
            }
            alert('创建失败: 网络错误 (可能是上传超时，请刷新页面查看)')
        } finally {
            isSubmitting.value = false
        }
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
    // Check if project is used by tasks
    if (proj.used_by_tasks && proj.used_by_tasks.length > 0) {
      errorMessage.value = `该项目正在被以下任务使用，请先删除这些任务后再删除项目：\n${proj.used_by_tasks.join('\n')}`
      showErrorModal.value = true
      return
    }
    // Set delete target and show confirm modal
    deleteTarget.value = proj
    showConfirmModal.value = true
}

const confirmDelete = async () => {
    if (!deleteTarget.value) return
    
    const proj = deleteTarget.value
    showConfirmModal.value = false
    
    try {
        const res = await fetch(`${API_BASE}/projects/${proj.id}`, { method: 'DELETE' })
        if(res.ok) {
            fetchProjects()
        } else {
            const errorData = await res.json().catch(() => ({}))
            errorMessage.value = errorData.detail || '删除失败，请稍后重试'
            showErrorModal.value = true
        }
    } catch(e) {
        console.error(e)
        errorMessage.value = '删除失败：网络错误，请检查网络连接'
        showErrorModal.value = true
    }
}

const onOutputDirSelected = (path: string) => {
  form.output_dir = path
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

onMounted(() => {
  fetchProjects()
  // fetchTasks() // Removed
})
</script>

<style scoped>
.project-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

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
    white-space: nowrap;
}

.value {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
.input-with-button {
  display: flex;
  gap: 8px;
}

.browse-btn {
  white-space: nowrap;
}

/* Error Modal Styles */
.error-modal-content {
  text-align: center;
  padding: 10px 0;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-message {
  color: #374151;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  text-align: left;
  background: #fef2f2;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #ef4444;
}

/* Confirm Modal Styles */
.confirm-modal-content {
  text-align: center;
  padding: 10px 0;
}

.confirm-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.confirm-modal-content p {
  margin-bottom: 12px;
  color: #374151;
}

.confirm-warning {
  color: #dc2626 !important;
  font-size: 13px;
  background: #fef2f2;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid #ef4444;
}

/* Button styles */
.btn-danger {
  background: #dc2626;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-danger:hover {
  background: #b91c1c;
}

.btn-secondary {
  background: #6b7280;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-secondary:hover {
  background: #4b5563;
}
</style>
