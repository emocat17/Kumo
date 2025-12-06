<template>
  <div class="modal-overlay" @click.self="closeModal">
    <div class="editor-modal">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-header">
           <div class="folder-icon">📂</div>
           <div class="project-info">
              <div class="title">项目文件浏览器</div>
              <div class="subtitle">{{ projectName }}</div>
           </div>
        </div>
        
        <div class="search-box">
            <input type="text" placeholder="搜索文件..." v-model="searchQuery" disabled title="暂不支持搜索"/>
        </div>

        <div class="sidebar-label">
            <span class="icon">📁</span> 目录结构
        </div>

        <div class="sidebar-content">
           <FileTree 
             v-if="files.length" 
             :items="files" 
             :active-path="currentFilePath"
             @select="handleFileSelect" 
           />
           <div v-else-if="loadingFiles" class="loading-text">加载中...</div>
           <div v-else class="empty-text">无文件</div>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="main-content">
         <!-- Header -->
        <header class="editor-header">
          <div class="left">
            <div class="file-info" v-if="currentFilePath">
                <span class="file-icon">📄</span>
                <div class="file-details">
                    <div class="file-name">文件内容</div>
                    <div class="file-path">{{ currentFilePath }}</div>
                </div>
            </div>
            <div class="no-file" v-else>未选择文件</div>
          </div>
          
          <div class="right">
             <span v-if="saveStatus" class="status-text" :class="saveStatusType">{{ saveStatus }}</span>
             
             <div class="actions">
                <button 
                    class="btn-action" 
                    @click="downloadCurrentFile" 
                    :disabled="!currentFilePath" 
                    title="下载文件"
                >
                    📥
                </button>
                <button 
                    class="btn-action" 
                    @click="saveFile" 
                    :disabled="!currentFilePath || isSaving"
                    title="保存 (Ctrl+S)"
                >
                    💾
                </button>
                
                <div class="divider"></div>

                <select class="lang-select" v-model="language">
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="json">JSON</option>
                    <option value="html">HTML</option>
                    <option value="css">CSS</option>
                    <option value="markdown">Markdown</option>
                    <option value="plaintext">Plain Text</option>
                </select>
             </div>

             <button class="btn-close" @click="closeModal">×</button>
          </div>
        </header>

        <!-- Editor -->
        <div class="editor-container">
            <div class="editor-toolbar" v-if="currentFilePath">
                 <span class="file-meta">{{ currentFilePath.split('/').pop() }}</span>
                 <div class="editor-stats">
                     <span>{{ code.split('\n').length }}行</span>
                     <span>{{ code.length }}字符</span>
                     <span>{{ (code.length / 1024).toFixed(1) }} KB</span>
                     <span class="badge">{{ language.toUpperCase() }}</span>
                 </div>
                 <div class="shortcuts">
                     Ctrl+S保存 | ESC关闭
                 </div>
            </div>

            <vue-monaco-editor
              v-if="currentFilePath"
              v-model:value="code"
              theme="vs-dark"
              :options="editorOptions"
              @mount="handleMount"
              class="monaco-editor"
              :language="language"
            />
            <div v-else class="empty-editor">
              <div class="empty-content">
                <div class="icon">👋</div>
                <p>请在左侧选择文件开始编辑</p>
              </div>
            </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import FileTree, { TreeItem } from '@/components/project/FileTree.vue'

const props = defineProps<{
  projectId: number | string
  projectName: string
}>()

const emit = defineEmits(['close'])

const files = ref<TreeItem[]>([])
const currentFilePath = ref('')
const code = ref('')
const originalCode = ref('')
const isDirty = ref(false)
const isSaving = ref(false)
const saveStatus = ref('')
const saveStatusType = ref('')
const loadingFiles = ref(true)
const searchQuery = ref('')
const language = ref('python')

const editorOptions = {
  automaticLayout: true,
  formatOnType: true,
  formatOnPaste: true,
  minimap: { enabled: true },
  fontSize: 14,
  scrollBeyondLastLine: false,
  roundedSelection: false,
}

const detectLanguage = (path: string) => {
    const ext = path.split('.').pop()?.toLowerCase()
    switch (ext) {
        case 'py': return 'python'
        case 'js': return 'javascript'
        case 'json': return 'json'
        case 'html': return 'html'
        case 'css': return 'css'
        case 'md': return 'markdown'
        case 'txt': return 'plaintext'
        default: return 'plaintext'
    }
}

// Watch for code changes to set dirty flag
watch(code, (newVal) => {
  if (currentFilePath.value) {
    isDirty.value = newVal !== originalCode.value
  }
})

// Keyboard shortcuts
const handleMount = (editor: any, monaco: any) => {
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    saveFile()
  })
  // Add Escape to close? Maybe risky if user just wants to close suggestions
  // Let's handle global escape in onMounted
}

const API_BASE = 'http://localhost:8000/api/projects'

const loadFiles = async () => {
  loadingFiles.value = true
  try {
    const res = await fetch(`${API_BASE}/${props.projectId}/files`)
    if (res.ok) {
      files.value = await res.json()
    }
  } catch (e) {
    console.error("Failed to load files", e)
  } finally {
    loadingFiles.value = false
  }
}

const handleFileSelect = async (item: TreeItem) => {
  if (isDirty.value) {
      if (!confirm("当前文件未保存，是否放弃修改？")) {
          return
      }
  }
  
  currentFilePath.value = item.path
  language.value = detectLanguage(item.path)
  
  try {
    const res = await fetch(`${API_BASE}/${props.projectId}/files/content?path=${encodeURIComponent(item.path)}`)
    if (res.ok) {
      const data = await res.json()
      code.value = data.content
      originalCode.value = data.content
      isDirty.value = false
    } else {
        alert("无法读取文件内容")
    }
  } catch (e) {
      console.error(e)
      alert("读取失败")
  }
}

const saveFile = async () => {
  if (!currentFilePath.value) return
  
  isSaving.value = true
  saveStatus.value = '正在保存...'
  saveStatusType.value = 'info'
  
  try {
    const res = await fetch(`${API_BASE}/${props.projectId}/files/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: currentFilePath.value,
        content: code.value
      })
    })
    
    if (res.ok) {
      originalCode.value = code.value
      isDirty.value = false
      saveStatus.value = '保存成功'
      saveStatusType.value = 'success'
      setTimeout(() => saveStatus.value = '', 2000)
    } else {
      throw new Error('Save failed')
    }
  } catch (e) {
    console.error(e)
    saveStatus.value = '保存失败'
    saveStatusType.value = 'error'
  } finally {
    isSaving.value = false
  }
}

const downloadCurrentFile = () => {
    if (!currentFilePath.value) return
    
    const blob = new Blob([code.value], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = currentFilePath.value.split('/').pop() || 'download'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
}

const closeModal = () => {
    if (isDirty.value) {
        if (!confirm("当前文件未保存，确定要退出吗？")) return
    }
    emit('close')
}

// Global Escape key to close
const handleKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
        // Check if monaco has focus? 
        // For now simple implementation
        closeModal()
    }
}

onMounted(() => {
  loadFiles()
  window.addEventListener('keydown', handleKeydown)
})

// Cleanup
import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.editor-modal {
  width: 90vw;
  height: 85vh;
  background-color: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  display: flex;
  overflow: hidden;
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

/* Sidebar Styles (Light Theme) */
.sidebar {
  width: 280px;
  background-color: #f8f9fa;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.folder-icon {
    font-size: 24px;
    color: #1890ff;
}

.project-info .title {
    font-size: 16px;
    font-weight: bold;
    color: #333;
}
.project-info .subtitle {
    font-size: 12px;
    color: #666;
    margin-top: 2px;
}

.search-box {
    padding: 0 16px 16px;
}
.search-box input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 13px;
    outline: none;
}
.search-box input:focus {
    border-color: #1890ff;
}

.sidebar-label {
    padding: 8px 16px;
    font-size: 12px;
    font-weight: bold;
    color: #888;
    display: flex;
    align-items: center;
    gap: 6px;
}

.sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
}

/* Main Content Styles */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  min-width: 0; /* Prevent flex overflow */
}

.editor-header {
  height: 64px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  background-color: #fff;
}

.left {
    display: flex;
    align-items: center;
}

.file-info {
    display: flex;
    align-items: center;
    gap: 12px;
}
.file-icon {
    font-size: 20px;
    color: #1890ff;
    background: #e6f7ff;
    padding: 8px;
    border-radius: 8px;
}
.file-details .file-name {
    font-size: 12px;
    color: #888;
}
.file-details .file-path {
    font-size: 14px;
    font-weight: 600;
    color: #333;
}
.no-file {
    color: #999;
    font-style: italic;
}

.right {
    display: flex;
    align-items: center;
    gap: 16px;
}

.actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

.btn-action {
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    border-radius: 4px;
    cursor: pointer;
    font-size: 16px;
    color: #666;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
}
.btn-action:hover:not(:disabled) {
    background-color: #f0f0f0;
    color: #333;
}
.btn-action:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.divider {
    width: 1px;
    height: 20px;
    background-color: #ddd;
    margin: 0 4px;
}

.lang-select {
    padding: 4px 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 12px;
    color: #333;
    outline: none;
}

.btn-close {
    font-size: 24px;
    border: none;
    background: none;
    color: #999;
    cursor: pointer;
    margin-left: 16px;
    line-height: 1;
}
.btn-close:hover {
    color: #333;
}

.status-text {
    font-size: 12px;
}
.status-text.success { color: #52c41a; }
.status-text.error { color: #ff4d4f; }

/* Editor Area */
.editor-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #1e1e1e; /* Dark background for editor container */
    position: relative;
}

.editor-toolbar {
    height: 36px;
    background-color: #252526; /* Slightly lighter dark */
    border-bottom: 1px solid #333;
    display: flex;
    align-items: center;
    padding: 0 16px;
    color: #ccc;
    font-size: 12px;
    gap: 16px;
}

.file-meta {
    font-style: italic;
    color: #9cdcfe;
}

.editor-stats {
    display: flex;
    gap: 12px;
    color: #888;
}

.badge {
    background-color: #0e639c;
    color: #fff;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: bold;
}

.shortcuts {
    margin-left: auto;
    color: #666;
}

.monaco-editor {
    flex: 1;
    width: 100%;
}

.empty-editor {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #555;
    background-color: #1e1e1e;
}
.empty-content {
    text-align: center;
}
.empty-content .icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
}
</style>
