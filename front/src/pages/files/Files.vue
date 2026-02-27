<template>
  <div class="page-container">
    <PageHeader title="输出文件" description="浏览项目输出数据和任务结果文件。">
      <template #actions>
        <button class="btn btn-secondary" title="刷新" @click="refreshDirectory">
          <RefreshCwIcon :size="18" :class="{ 'spin': isLoading }" />
        </button>
      </template>
    </PageHeader>

    <!-- 目录路径导航 -->
    <div class="path-nav">
      <button 
        v-for="(segment, index) in pathSegments" 
        :key="index"
        class="path-segment"
        @click="navigateToSegment(index)"
      >
        {{ segment }}
        <span v-if="index < pathSegments.length - 1" class="separator">/</span>
      </button>
    </div>

    <!-- 文件列表 -->
    <div class="file-list-container">
      <div v-if="isLoading" class="loading-state">
        <RefreshCwIcon :size="32" class="spin" />
        <p>加载中...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <AlertCircleIcon :size="32" />
        <p>{{ error }}</p>
        <button class="btn btn-secondary" @click="refreshDirectory">重试</button>
      </div>

      <div v-else-if="items.length === 0" class="empty-state">
        <FolderIcon :size="48" />
        <p>当前目录为空</p>
      </div>

      <div v-else class="file-grid">
        <!-- 父目录 -->
        <div v-if="canGoUp" class="file-item parent-dir" @click="goUp">
          <div class="file-icon">
            <ArrowUpIcon :size="32" />
          </div>
          <div class="file-name">上级目录</div>
        </div>

        <!-- 目录 -->
        <div 
          v-for="item in directories" 
          :key="item.path" 
          class="file-item directory"
          @click="navigateTo(item)"
        >
          <div class="file-icon">
            <FolderIcon :size="32" />
          </div>
          <div class="file-name">{{ item.name }}</div>
        </div>

        <!-- 文件 -->
        <div 
          v-for="item in files" 
          :key="item.path" 
          class="file-item file"
          @click="downloadFile(item)"
        >
          <div class="file-icon">
            <FileIcon :size="32" />
          </div>
          <div class="file-name">{{ item.name }}</div>
          <div class="file-size">{{ formatFileSize(item.size) }}</div>
        </div>
      </div>
    </div>

    <!-- 快捷目录选择 -->
    <div class="quick-dirs">
      <span class="quick-dirs-label">快速跳转：</span>
      <button 
        v-for="dir in quickDirs" 
        :key="dir.path"
        class="quick-dir-btn"
        @click="navigateTo(dir)"
      >
        <FolderIcon :size="14" />
        {{ dir.name }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { 
  RefreshCwIcon, 
  FolderIcon, 
  FileIcon, 
  ArrowUpIcon,
  AlertCircleIcon
} from 'lucide-vue-next'

interface FileItem {
  name: string
  path: string
  type: 'dir' | 'file'
  size?: number
}

const API_BASE = '/api'

const currentPath = ref('/data')
const items = ref<FileItem[]>([])
const isLoading = ref(false)
const error = ref('')

const quickDirs = [
  { name: '数据目录', path: '/data' },
  { name: '任务日志', path: '/app/logs/tasks' },
  { name: '安装日志', path: '/app/logs/install' },
]

const pathSegments = computed(() => {
  if (currentPath.value === '/') return ['/']
  return currentPath.value.split('/').filter(Boolean)
})

const canGoUp = computed(() => {
  return currentPath.value !== '/data' && currentPath.value !== '/'
})

const directories = computed(() => items.value.filter(i => i.type === 'dir'))
const files = computed(() => items.value.filter(i => i.type === 'file'))

const fetchDirectory = async (path: string) => {
  isLoading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_BASE}/projects/browse-dirs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '加载失败')
    }
    
    const data = await res.json()
    items.value = data.items || []
    currentPath.value = path
  } catch (e: Error) {
    error.value = e.message || '加载目录失败'
    items.value = []
  } finally {
    isLoading.value = false
  }
}

const refreshDirectory = () => {
  fetchDirectory(currentPath.value)
}

interface QuickDir {
  name: string
  path: string
}

const navigateTo = (item: FileItem | QuickDir) => {
  // QuickDir doesn't have type, always treat as directory
  if (!('type' in item) || item.type === 'dir') {
    fetchDirectory(item.path)
  }
}

const navigateToSegment = (index: number) => {
  if (index === 0 && pathSegments.value[0] === 'data') {
    fetchDirectory('/data')
  } else if (index < pathSegments.value.length - 1) {
    const newPath = '/' + pathSegments.value.slice(0, index + 1).join('/')
    fetchDirectory(newPath)
  }
}

const goUp = () => {
  const segments = currentPath.value.split('/').filter(Boolean)
  if (segments.length > 1) {
    segments.pop()
    fetchDirectory('/' + segments.join('/'))
  } else {
    fetchDirectory('/data')
  }
}

const downloadFile = (item: FileItem) => {
  // 尝试直接下载或预览
  window.open(`/api/projects/files/content?project_id=0&path=${encodeURIComponent(item.path)}`, '_blank')
}

const formatFileSize = (bytes?: number) => {
  if (!bytes) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

onMounted(() => {
  fetchDirectory('/data')
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.path-nav {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 4px;
}

.path-segment {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.path-segment:hover {
  background-color: #eff6ff;
}

.path-segment:last-child {
  color: #1f2937;
  font-weight: 500;
}

.separator {
  color: #9ca3af;
  margin-left: 4px;
}

.file-list-container {
  flex: 1;
  background: white;
  border-radius: 8px;
  padding: 16px;
  min-height: 400px;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: #6b7280;
}

.error-state {
  color: #ef4444;
}

.error-state p {
  margin: 12px 0;
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 16px;
}

.file-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.file-item:hover {
  background-color: #f9fafb;
}

.file-item.directory:hover {
  background-color: #eff6ff;
}

.file-item.file:hover {
  background-color: #fef3c7;
}

.file-icon {
  margin-bottom: 8px;
  color: #6b7280;
}

.file-item.directory .file-icon {
  color: #f59e0b;
}

.file-item.file .file-icon {
  color: #3b82f6;
}

.file-item.parent-dir .file-icon {
  color: #6b7280;
}

.file-name {
  font-size: 13px;
  color: #374151;
  text-align: center;
  word-break: break-word;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

.quick-dirs {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  flex-wrap: wrap;
}

.quick-dirs-label {
  font-size: 13px;
  color: #6b7280;
}

.quick-dir-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: #f3f4f6;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  transition: background-color 0.2s;
}

.quick-dir-btn:hover {
  background: #e5e7eb;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
