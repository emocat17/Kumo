<template>
  <BaseModal :model-value="isOpen" title="选择路径" width="600px" @close="onClose">
    <div class="file-selector">
      <div class="current-path">
        <button :disabled="!parentPath" class="nav-btn" @click="loadPath(parentPath)">
          <ArrowUpIcon :size="16" />
        </button>
        <input v-model="currentPath" type="text" class="path-input" @keyup.enter="loadPath(currentPath)" />
        <button class="nav-btn" @click="loadPath(currentPath)">Go</button>
      </div>

      <div class="file-list">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <ul v-else>
           <!-- Drives (Windows) or Root -->
           <li v-for="item in items" :key="item.path" class="file-item" :class="{ selected: selectedPath === item.path }" @click="onItemClick(item)">
             <span class="icon">
               <HardDriveIcon v-if="item.type === 'drive'" :size="16" color="#1890ff" />
               <FolderIcon v-else-if="item.type === 'dir'" :size="16" color="#faad14" />
               <FileIcon v-else :size="16" color="#8c8c8c" />
             </span>
             <span class="name">{{ item.name }}</span>
           </li>
           <li v-if="items.length === 0" class="empty">此文件夹为空</li>
        </ul>
      </div>

      <div class="modal-actions">
        <div class="selected-preview">
            已选择: {{ selectedPath || '未选择' }}
        </div>
        <div class="buttons">
            <button class="btn btn-secondary" @click="onClose">取消</button>
            <button class="btn btn-primary" :disabled="!selectedPath" @click="onConfirm">确定</button>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import { FolderIcon, FileIcon, ArrowUpIcon, HardDriveIcon } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits(['close', 'select'])

interface FileSystemItem {
    name: string
    type: 'file' | 'dir' | 'drive'
    path: string
    size?: number
    mtime?: number
}

const currentPath = ref('')
const parentPath = ref('')
const items = ref<FileSystemItem[]>([])
const loading = ref(false)
const error = ref('')
const selectedPath = ref('')

const API_BASE = '/api/system/fs'

const loadPath = async (path: string = '') => {
  loading.value = true
  error.value = ''
  try {
    const url = path ? `${API_BASE}/list?path=${encodeURIComponent(path)}` : `${API_BASE}/list`
    const res = await fetch(url)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    
    currentPath.value = data.current
    parentPath.value = data.parent
    items.value = data.items
    
    selectedPath.value = '' 
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    error.value = msg || 'Failed to load directory'
  } finally {
    loading.value = false
  }
}

// Simple double click simulation
let lastClickTime = 0
let lastClickItem: FileSystemItem | null = null

const onItemClick = (item: FileSystemItem) => {
    const now = Date.now()
    if (lastClickItem === item && now - lastClickTime < 300) {
        // Double click
        if (item.type === 'dir' || item.type === 'drive') {
            loadPath(item.path)
        }
    } else {
        // Single click
        selectedPath.value = item.path
    }
    lastClickTime = now
    lastClickItem = item
}

const onConfirm = () => {
  if (selectedPath.value) {
    emit('select', selectedPath.value)
    onClose()
  }
}

const onClose = () => {
  emit('close')
}

watch(() => props.isOpen, (newVal) => {
  if (newVal && !currentPath.value) {
    loadPath() // Load root on first open
  }
})
</script>

<style scoped>
.file-selector {
  display: flex;
  flex-direction: column;
  height: 400px;
}

.current-path {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.path-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.nav-btn {
    padding: 4px 8px;
    border: 1px solid #d9d9d9;
    background: white;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
}
.nav-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.file-list {
  flex: 1;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  overflow-y: auto;
  background: #fafafa;
}

.file-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #f5f5f5;
}

.file-item:hover {
  background: #e6f7ff;
}

.file-item.selected {
  background: #bae7ff;
}

.icon {
  margin-right: 10px;
  display: flex;
  align-items: center;
}

.name {
  font-size: 14px;
  color: #333;
}

.modal-actions {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.selected-preview {
    font-size: 12px;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 300px;
}

.buttons {
    display: flex;
    gap: 10px;
}

.btn {
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  border: none;
}

.btn-secondary {
  background: #f5f5f5;
  color: #333;
  border: 1px solid #d9d9d9;
}

.btn-primary {
  background: #1890ff;
  color: white;
}

.btn-primary:disabled {
    background: #bae7ff;
    cursor: not-allowed;
}

.loading, .error, .empty {
    padding: 20px;
    text-align: center;
    color: #999;
}
.error {
    color: #ff4d4f;
}
</style>
