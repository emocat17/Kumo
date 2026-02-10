<template>
  <div class="dashboard-page">
    <PageHeader title="仪表盘" description="查看系统运行状态和性能监控。" />

    <!-- Navigation Tabs -->
    <div class="tabs">
      <button 
        :class="['tab-btn', { active: activeTab === 'overview' }]" 
        @click="activeTab = 'overview'"
      >
        系统概览
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'performance' }]" 
        @click="activeTab = 'performance'"
      >
        性能配置
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'test' }]" 
        @click="activeTab = 'test'"
      >
        测试指标
      </button>
    </div>

    <!-- Content Area -->
    <div class="tab-content">
      <keep-alive>
        <component 
          :is="currentTabComponent" 
          :system-stats="systemStats" 
        />
      </keep-alive>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, defineAsyncComponent } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'

// Async Components
const SystemOverview = defineAsyncComponent(() => import('./dashboard/SystemOverview.vue'))
const PerformanceMonitor = defineAsyncComponent(() => import('./dashboard/PerformanceMonitor.vue'))
const TestMetrics = defineAsyncComponent(() => import('./dashboard/TestMetrics.vue'))

interface SystemStats {
  cpu: { 
      percent: number
      count: number
      cores: number
      threads: number
      freq_current: string | number
      freq_max: string | number
      load_avg: number[]
      per_cpu: number[]
  }
  memory: { 
      percent: number
      total: string
      used: string
      available: string
      cached: string
      swap_used: string
      swap_total: string
      swap_percent: number
  }
  disk: { 
      partitions: Array<{
          mountpoint: string
          percent: number
          used: string
          total: string
      }>
      read_count: number
      write_count: number
      read_bytes: string
      write_bytes: string
  }
  network: { 
      bytes_sent: string
      bytes_recv: string
      packets_recv: number | string
      packets_sent: number | string
      pids: number
  }
}

// State
const activeTab = ref<'overview' | 'performance' | 'test'>('overview')
const systemStats = ref<SystemStats>({
    cpu: { percent: 0, count: 0, cores: 0, threads: 0, freq_current: 0, freq_max: 0, load_avg: [], per_cpu: [] },
    memory: { percent: 0, total: '0B', used: '0B', available: '0B', cached: '0B', swap_used: '0B', swap_total: '0B', swap_percent: 0 },
    disk: { partitions: [], read_count: 0, write_count: 0, read_bytes: '0B', write_bytes: '0B' },
    network: { bytes_sent: '0B', bytes_recv: '0B', packets_recv: 0, packets_sent: 0, pids: 0 }
})
let timer: number | null = null

const API_BASE = 'http://localhost:8000/api'

// Computed
const currentTabComponent = computed(() => {
    switch (activeTab.value) {
        case 'performance': return PerformanceMonitor
        case 'test': return TestMetrics
        default: return SystemOverview
    }
})

// Methods
const fetchSystemStats = async () => {
    try {
        const res = await fetch(`${API_BASE}/system/stats`)
        if (res.ok) {
            systemStats.value = await res.json()
        }
    } catch (e) {
        console.error(e)
    }
}

// Lifecycle
onMounted(() => {
    fetchSystemStats()
    timer = setInterval(() => {
        if (document.hidden) return
        fetchSystemStats()
    }, 3000) as unknown as number
})

onUnmounted(() => {
    if (timer) clearInterval(timer)
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 40px;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 32px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 10px;
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