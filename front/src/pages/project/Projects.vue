<template>
  <div class="projects-page">
    <PageHeader title="项目管理" description="管理您的项目及其工作区。">
      <template #actions>
        <button class="btn btn-primary" @click="openCreateModal">
          <i class="icon-plus">+</i> 新建项目
        </button>
      </template>
    </PageHeader>

    <!-- Projects Grid -->
    <div class="project-grid" v-if="projects.length > 0">
      <div v-for="proj in projects" :key="proj.id" class="project-card">
        <div class="card-header">
          <h3 class="project-name" :title="proj.name">{{ proj.name }}</h3>
          <span class="created-time">{{ formatDate(proj.created_at) }}</span>
        </div>
        
        <div class="card-body">
          <p class="description">{{ proj.description || '暂无描述' }}</p>
          
          <div class="info-row">
            <span class="label">工作路径:</span>
            <span class="value" :title="proj.work_dir">{{ proj.work_dir }}</span>
          </div>
          
          <div class="actions-row">
            <!-- Future actions: Edit, Delete, Run -->
             <button class="btn btn-primary btn-sm" @click="openEditor(proj)" style="margin-right: 8px;">浏览</button>
             <button class="btn btn-danger btn-sm" @click="deleteProject(proj)">删除</button>
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
      <form @submit.prevent="handleCreateProject" class="create-form">
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
              type="file" 
              accept=".zip"
              @change="handleFileChange"
              class="file-input"
              ref="fileInput"
              required
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ProjectEditorModal from '@/components/project/ProjectEditorModal.vue'

interface Project {
  id: number
  name: string
  path: string
  work_dir: string
  description: string
  created_at: string
}

const router = useRouter()

const projects = ref<Project[]>([])
const showCreateModal = ref(false)
const showEditorModal = ref(false)
const currentProject = ref<Project | null>(null)
const isSubmitting = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)

const form = reactive({
  name: '',
  work_dir: './'
})

const API_BASE = 'http://localhost:8000/api/projects'

const fetchProjects = async () => {
  try {
    const res = await fetch(API_BASE)
    if (res.ok) {
      projects.value = await res.json()
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
    const res = await fetch(`${API_BASE}/create`, {
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
    if(!confirm(`确定要删除项目 "${proj.name}" 吗？这将会删除服务器上的文件。`)) return
    
    try {
        const res = await fetch(`${API_BASE}/${proj.id}`, { method: 'DELETE' })
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
})
</script>

<style scoped>
.projects-page {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.project-card {
  background: white;
  border-radius: 8px;
  border: 1px solid #eef0f2;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.project-card:hover {
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

.project-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.created-time {
    font-size: 12px;
    color: #888;
}

.card-body {
  padding: 15px 20px;
  flex: 1;
}

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

.empty-state {
  text-align: center;
  padding: 40px;
  color: #6b7280;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* Form Styles */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #374151;
}

.required {
  color: #dc2626;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

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

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-secondary {
  background-color: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background-color: #e5e7eb;
}

.btn-danger {
    background-color: #fee2e2;
    color: #dc2626;
}
.btn-danger:hover {
    background-color: #fecaca;
}

.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-sm {
    padding: 4px 8px;
    font-size: 12px;
}
</style>
