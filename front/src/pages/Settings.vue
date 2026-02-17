<template>
  <div class="settings-page">
    <PageHeader title="系统设置" description="配置全局系统参数。" />
    
    <!-- Tabs -->
    <div class="tabs">
      <button 
        :class="['tab-btn', { active: activeTab === 'python' }]" 
        @click="activeTab = 'python'"
      >
        Python 环境配置
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'env' }]" 
        @click="activeTab = 'env'"
      >
        全局环境变量
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'backup' }]" 
        @click="activeTab = 'backup'"
      >
        数据备份与恢复
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'data' }]" 
        @click="activeTab = 'data'"
      >
        数据管理
      </button>
    </div>

    <div class="settings-container">
      <keep-alive>
        <component :is="currentTabComponent" />
      </keep-alive>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'

// Async Components
const PypiMirrorConfig = defineAsyncComponent(() => import('./settings/PypiMirrorConfig.vue'))
const GlobalEnvVars = defineAsyncComponent(() => import('./settings/GlobalEnvVars.vue'))
const BackupManager = defineAsyncComponent(() => import('./settings/BackupManager.vue'))
const DataManager = defineAsyncComponent(() => import('./settings/DataManager.vue'))

const activeTab = ref<'python' | 'env' | 'backup' | 'data'>('python')

const currentTabComponent = computed(() => {
    switch (activeTab.value) {
        case 'env': return GlobalEnvVars
        case 'backup': return BackupManager
        case 'data': return DataManager
        default: return PypiMirrorConfig
    }
})
</script>

<style scoped>
.settings-page {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.settings-container {
  max-width: 1200px;
  margin: 0;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 32px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 24px;
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
</style>
