<template>
  <section class="section">
    <!-- Filter Bar -->
    <div class="filter-bar" style="margin-bottom: 20px; display: flex; align-items: center; justify-content: flex-end;">
       <span style="margin-right: 10px; color: #666; font-size: 14px;">筛选项目:</span>
       <ProjectSelector v-model="selectedProjectId" />
    </div>

    <!-- Top Cards -->
    <div class="overview-grid">
      <!-- CPU Card -->
      <div class="card overview-card">
        <div class="card-icon cpu-icon">
          <span class="icon-cpu">🔳</span>
        </div>
        <div class="card-content">
          <div class="card-title">CPU使用率</div>
          <div class="card-value blue">{{ systemStats.cpu?.percent }}%</div>
          <div class="card-sub">{{ systemStats.cpu?.cores }} 核心</div>
        </div>
      </div>

      <!-- Memory Card -->
      <div class="card overview-card">
        <div class="card-icon mem-icon">
          <span class="icon-mem">🧠</span>
        </div>
        <div class="card-content">
          <div class="card-title">内存使用率</div>
          <div class="card-value green">{{ systemStats.memory?.percent }}%</div>
          <div class="card-sub">{{ systemStats.memory?.used }} / {{ systemStats.memory?.total }}</div>
        </div>
      </div>

      <!-- Disk Card -->
      <div class="card overview-card">
        <div class="card-icon disk-icon">
          <span class="icon-disk">💾</span>
        </div>
        <div class="card-content">
          <div class="card-title">磁盘使用率</div>
          <div class="card-value purple">{{ getMainDiskPercent }}%</div>
          <div class="card-sub">{{ getMainDiskUsage }}</div>
        </div>
      </div>

      <!-- Task Card -->
      <div class="card overview-card">
        <div class="card-icon task-icon">
          <span class="icon-task">📊</span>
        </div>
        <div class="card-content">
          <div class="card-title">任务概览</div>
          <div class="card-value orange">{{ dashboardStats.running_executions || 0 }} <span style="font-size: 0.5em; color: #999">正在运行</span></div>
          <div class="card-sub">{{ dashboardStats.active_tasks }} 激活 / {{ dashboardStats.total_tasks }} 总任务</div>
        </div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="charts-grid">
      <!-- Task Statistics Chart -->
      <div class="card chart-card">
        <h3 class="chart-title">每日调度任务执行统计</h3>
        <div ref="chartRef" class="chart-container"></div>
      </div>

      <!-- Failure Top 5 -->
      <div class="card chart-card">
          <h3 class="chart-title">失败任务 TOP 5</h3>
          <div class="failure-list">
              <div v-for="(item, index) in dashboardStats.failure_stats" :key="item.task_id" class="failure-item">
                  <div class="failure-info">
                      <span class="failure-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</span>
                      <span class="failure-name" :title="item.task_name">{{ item.task_name }}</span>
                  </div>
                  <div class="failure-bar-wrapper">
                       <div class="failure-bar" :style="{ width: getFailureBarWidth(item.failure_count) + '%' }"></div>
                       <span class="failure-count">{{ item.failure_count }}次</span>
                  </div>
              </div>
              <div v-if="!dashboardStats.failure_stats?.length" class="empty-state">
                  暂无失败记录
              </div>
          </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
import * as echarts from 'echarts'

// Types (Ideally these should be imported from a shared types file)
interface SystemStats {
  cpu: { percent: number; cores: number }
  memory: { percent: number; total: string; used: string }
  disk: { partitions: Array<{ percent: number; used: string; total: string }> }
}

interface DashboardStats {
  total_tasks: number
  active_tasks: number
  running_executions: number
  daily_stats: Array<{ date: string; success: number; failed: number }>
  failure_stats?: Array<{ task_id: number; task_name: string; failure_count: number }>
}

const props = defineProps<{
  systemStats: SystemStats
}>()

// Local State
const selectedProjectId = ref<number | null>(null)
const dashboardStats = ref<DashboardStats>({
    total_tasks: 0,
    active_tasks: 0,
    running_executions: 0,
    daily_stats: [],
    failure_stats: []
})
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null
let timer: number | null = null

const API_BASE = '/api'

// Computed
const getMainDiskPercent = computed(() => {
    if (!props.systemStats.disk?.partitions?.length) return 0
    return props.systemStats.disk.partitions[0].percent
})

const getMainDiskUsage = computed(() => {
    if (!props.systemStats.disk?.partitions?.length) return '0 / 0'
    const d = props.systemStats.disk.partitions[0]
    return `${d.used} / ${d.total}`
})

const getFailureBarWidth = (count: number) => {
    if (!dashboardStats.value.failure_stats?.length) return 0
    const max = Math.max(...dashboardStats.value.failure_stats.map(s => s.failure_count))
    return max ? (count / max) * 100 : 0
}

// Methods
const fetchDashboardStats = async () => {
    try {
        let url = `${API_BASE}/tasks/dashboard/stats`
        if (selectedProjectId.value) {
            url += `?project_id=${selectedProjectId.value}`
        }
        const res = await fetch(url)
        if (res.ok) {
            dashboardStats.value = await res.json()
            initChart()
        }
    } catch (e) {
        console.error(e)
    }
}

const initChart = () => {
    if (!chartRef.value) return
    
    if (chartInstance) {
        chartInstance.dispose()
    }
    
    chartInstance = echarts.init(chartRef.value)
    
    const dates = dashboardStats.value.daily_stats.map(s => s.date)
    const successData = dashboardStats.value.daily_stats.map(s => s.success)
    const failedData = dashboardStats.value.daily_stats.map(s => s.failed)
    
    const option = {
        animation: false,
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        legend: {
            data: ['成功任务', '失败任务'],
            bottom: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLine: { lineStyle: { color: '#ddd' } },
            axisLabel: { color: '#666' }
        },
        yAxis: {
            type: 'value',
            splitLine: { lineStyle: { type: 'dashed' } }
        },
        series: [
            {
                name: '成功任务',
                type: 'bar',
                stack: 'total',
                barWidth: '40%',
                itemStyle: { color: '#52c41a' },
                data: successData,
                animation: false,
                emphasis: { focus: 'series' },
                barBorderRadius: [4, 4, 0, 0]
            },
            {
                name: '失败任务',
                type: 'bar',
                stack: 'total',
                barWidth: '40%',
                itemStyle: { color: '#ff4d4f' },
                data: failedData,
                animation: false,
                emphasis: { focus: 'series' },
                barBorderRadius: [0, 0, 0, 0]
            }
        ]
    }
    
    chartInstance.setOption(option)
}

const handleResize = () => {
    chartInstance?.resize()
}

// Watchers
watch(selectedProjectId, () => {
    fetchDashboardStats()
})

// Lifecycle
onMounted(() => {
  fetchDashboardStats()
  window.addEventListener('resize', handleResize)
  
  // Refresh stats every 3 seconds
  timer = setInterval(() => {
      if (document.hidden) return
      fetchDashboardStats()
  }, 3000) as unknown as number
})

onUnmounted(() => {
    if (timer) clearInterval(timer)
    window.removeEventListener('resize', handleResize)
    chartInstance?.dispose()
})
</script>

<style scoped>
@import '@/styles/dashboard.css';

/* Reuse styles from parent or keep minimal here */
</style>
