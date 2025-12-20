<template>
  <div class="dashboard-page">
    <PageHeader title="仪表盘" description="查看系统运行状态和性能监控。" />

    <!-- Tabs -->
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
    </div>

    <!-- System Overview -->
    <section v-if="activeTab === 'overview'" class="section">
      <!-- Top Cards -->
      <div class="overview-grid">
        <!-- CPU Card -->
        <div class="card overview-card">
          <div class="card-icon cpu-icon">
            <i class="icon-cpu">🔳</i>
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
            <i class="icon-mem">🧠</i>
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
            <i class="icon-disk">💾</i>
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
            <i class="icon-task">📊</i>
          </div>
          <div class="card-content">
            <div class="card-title">任务成功率</div>
            <div class="card-value orange">{{ taskSuccessRate }}%</div>
            <div class="card-sub">{{ totalSuccessTasks }} / {{ totalTasks }} 个任务成功</div>
          </div>
        </div>
      </div>

      <!-- Task Statistics Chart -->
      <div class="card chart-card">
        <h3 class="chart-title">每日调度任务执行统计</h3>
        <div ref="chartRef" class="chart-container"></div>
      </div>
    </section>

    <!-- Performance Monitor -->
    <section v-if="activeTab === 'performance'" class="section perf-section">
      <!-- CPU Performance -->
      <div class="card perf-panel">
        <div class="panel-header">
          <div class="perf-icon cpu-icon">🔳</div>
          <div class="panel-title-group">
            <h4>CPU性能</h4>
            <span class="subtitle">{{ systemStats.cpu?.cores }} 核心 / {{ systemStats.cpu?.threads }} 线程</span>
          </div>
        </div>
        <div class="perf-row-stats">
          <div class="stat-box">
            <div class="stat-val blue">{{ systemStats.cpu?.percent }}%</div>
            <div class="stat-lbl">平均使用率</div>
          </div>
          <div class="stat-box">
            <div class="stat-val green">{{ systemStats.cpu?.freq_current }}</div>
            <div class="stat-lbl">频率</div>
          </div>
          <div class="stat-box">
            <div class="stat-val purple">{{ systemStats.cpu?.freq_max || 'N/A' }}</div>
            <div class="stat-lbl">最大频率</div>
          </div>
          <div class="stat-box">
            <div class="stat-val orange">{{ systemStats.cpu?.load_avg?.[0]?.toFixed(2) }}</div>
            <div class="stat-lbl">负载平均值 (1min)</div>
          </div>
        </div>
        <div class="cpu-cores-detail">
            <div class="detail-label">每核使用率</div>
            <div class="cores-visual">
                <div v-for="(usage, index) in systemStats.cpu?.per_cpu" :key="index" class="core-block-wrapper">
                    <div class="core-block-header">
                        <span>Core {{ index + 1 }}</span>
                        <span>{{ usage }}%</span>
                    </div>
                    <div class="core-progress-bg">
                        <div class="core-progress-fill" :style="{ width: usage + '%', backgroundColor: getUsageColor(usage) }"></div>
                    </div>
                </div>
            </div>
        </div>
      </div>

      <!-- Memory Performance -->
      <div class="card perf-panel">
        <div class="panel-header">
          <div class="perf-icon mem-icon">🧠</div>
          <div class="panel-title-group">
            <h4>内存性能</h4>
            <span class="subtitle">{{ systemStats.memory?.total }} 总内存</span>
          </div>
        </div>
        <div class="perf-row-stats">
            <div class="stat-box">
              <div class="stat-val green">{{ systemStats.memory?.percent }}%</div>
              <div class="stat-lbl">已使用</div>
            </div>
            <div class="stat-box">
              <div class="stat-val blue">{{ systemStats.memory?.available }}</div>
              <div class="stat-lbl">可用</div>
            </div>
            <div class="stat-box">
              <div class="stat-val purple">{{ systemStats.memory?.cached }}</div>
              <div class="stat-lbl">缓存</div>
            </div>
            <div class="stat-box">
              <div class="stat-val orange">{{ systemStats.memory?.swap_percent }}%</div>
              <div class="stat-lbl">交换空间使用</div>
            </div>
        </div>
        <div class="memory-bars">
            <div class="mem-bar-group">
                <div class="bar-label">
                    <span>物理内存</span>
                    <span>{{ systemStats.memory?.used }} / {{ systemStats.memory?.total }}</span>
                </div>
                <div class="progress-bg">
                    <div class="progress-fill green-bg" :style="{ width: systemStats.memory?.percent + '%' }"></div>
                </div>
            </div>
            <div class="mem-bar-group">
                <div class="bar-label">
                    <span>交换内存</span>
                    <span>{{ systemStats.memory?.swap_used }} / {{ systemStats.memory?.swap_total }}</span>
                </div>
                <div class="progress-bg">
                    <div class="progress-fill orange-bg" :style="{ width: systemStats.memory?.swap_percent + '%' }"></div>
                </div>
            </div>
        </div>
      </div>

      <div class="bottom-grid">
        <!-- Disk Performance -->
        <div class="card perf-panel">
            <div class="panel-header">
            <div class="perf-icon disk-icon">💾</div>
            <div class="panel-title-group">
                <h4>磁盘性能</h4>
                <span class="subtitle">{{ systemStats.disk?.partitions?.length }} 分区</span>
            </div>
            </div>
            <div class="disk-partitions">
                <div v-for="disk in systemStats.disk?.partitions" :key="disk.mountpoint" class="disk-row">
                    <div class="disk-row-header">
                        <span class="disk-name">{{ disk.mountpoint }}</span>
                        <span class="disk-val">{{ disk.percent }}%</span>
                    </div>
                    <div class="disk-sub">{{ disk.used }} / {{ disk.total }}</div>
                    <div class="progress-bg small">
                        <div class="progress-fill purple-bg" :style="{ width: disk.percent + '%' }"></div>
                    </div>
                </div>
            </div>
            <div class="io-stats">
                <div class="io-item">
                    <span class="io-val blue">{{ systemStats.disk?.read_count }}</span>
                    <span class="io-lbl">读操作</span>
                </div>
                <div class="io-item">
                    <span class="io-val green">{{ systemStats.disk?.write_count }}</span>
                    <span class="io-lbl">写操作</span>
                </div>
            </div>
        </div>

        <!-- Network Performance -->
        <div class="card perf-panel">
            <div class="panel-header">
            <div class="perf-icon net-icon">📡</div>
            <div class="panel-title-group">
                <h4>网络性能</h4>
                <span class="subtitle">总流量</span>
            </div>
            </div>
            <div class="perf-row-stats two-col">
                <div class="stat-box bg-light-blue">
                    <div class="stat-val blue">{{ systemStats.network?.bytes_recv }}</div>
                    <div class="stat-lbl">接收总量</div>
                </div>
                <div class="stat-box bg-light-green">
                    <div class="stat-val green">{{ systemStats.network?.bytes_sent }}</div>
                    <div class="stat-lbl">发送总量</div>
                </div>
            </div>
            <div class="perf-row-stats two-col mt-3">
                <div class="stat-box">
                    <div class="stat-val purple">{{ systemStats.network?.packets_recv }}</div>
                    <div class="stat-lbl">接收数据包</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val orange">{{ systemStats.network?.packets_sent }}</div>
                    <div class="stat-lbl">发送数据包</div>
                </div>
            </div>
            <div class="active-pids mt-3">
                <i class="icon-pid">📊</i>
                <span>活跃进程: </span>
                <span class="pid-val">{{ systemStats.network?.pids }}</span>
            </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import * as echarts from 'echarts'

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

interface DailyTaskStats {
    dates: string[]
    success: number[]
    failed: number[]
}

const activeTab = ref<'overview' | 'performance'>('overview')
const systemStats = ref<SystemStats>({} as SystemStats)
const taskStats = ref<DailyTaskStats>({ dates: [], success: [], failed: [] })
const timer = ref<number | null>(null)
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const API_BASE = 'http://localhost:8000/api'

// Computed for Cards
const getMainDiskPercent = computed(() => {
    if (!systemStats.value.disk?.partitions?.length) return 0
    // Return max used partition or first one
    return systemStats.value.disk.partitions[0].percent
})

const getMainDiskUsage = computed(() => {
    if (!systemStats.value.disk?.partitions?.length) return '0 / 0'
    const d = systemStats.value.disk.partitions[0]
    return `${d.used} / ${d.total}`
})

const totalSuccessTasks = computed(() => {
    return taskStats.value.success.reduce((a, b) => a + b, 0)
})

const totalFailedTasks = computed(() => {
    return taskStats.value.failed.reduce((a, b) => a + b, 0)
})

const totalTasks = computed(() => totalSuccessTasks.value + totalFailedTasks.value)

const taskSuccessRate = computed(() => {
    if (totalTasks.value === 0) return 100
    return Math.round((totalSuccessTasks.value / totalTasks.value) * 100)
})

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

const fetchTaskStats = async () => {
    try {
        const res = await fetch(`${API_BASE}/tasks/stats/daily?days=14`)
        if (res.ok) {
            taskStats.value = await res.json()
            initChart()
        }
    } catch (e) {
        console.error(e)
    }
}

const getUsageColor = (percent: number) => {
    if (percent < 50) return '#52c41a' // Green
    if (percent < 80) return '#faad14' // Orange
    return '#ff4d4f' // Red
}

const initChart = () => {
    if (!chartRef.value) return
    
    // Dispose if exists
    if (chartInstance) {
        chartInstance.dispose()
    }
    
    chartInstance = echarts.init(chartRef.value)
    
    const option = {
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
            data: taskStats.value.dates,
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
                data: taskStats.value.success,
                emphasis: { focus: 'series' },
                barBorderRadius: [4, 4, 0, 0] // Only top corners
            },
            {
                name: '失败任务',
                type: 'bar',
                stack: 'total',
                barWidth: '40%',
                itemStyle: { color: '#ff4d4f' },
                data: taskStats.value.failed,
                emphasis: { focus: 'series' },
                barBorderRadius: [0, 0, 0, 0]
            }
        ]
    }
    
    chartInstance.setOption(option)
}

// Watch active tab to re-init chart when switching back to overview
watch(activeTab, async (newVal) => {
    if (newVal === 'overview') {
        await nextTick()
        initChart()
    }
})

// Resize handler
const handleResize = () => {
    chartInstance?.resize()
}

onMounted(() => {
  fetchSystemStats()
  fetchTaskStats()
  
  window.addEventListener('resize', handleResize)
  
  // Refresh stats every 3 seconds
  timer.value = setInterval(() => {
      fetchSystemStats()
      // fetchTaskStats() // Don't refresh chart too often, or maybe every minute?
  }, 3000) as unknown as number
})

onUnmounted(() => {
    if (timer.value) clearInterval(timer.value)
    window.removeEventListener('resize', handleResize)
    chartInstance?.dispose()
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

/* Overview Styles */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.03);
  border: 1px solid #f0f0f0;
  transition: transform 0.2s, box-shadow 0.2s;
}

.overview-card {
    display: flex;
    align-items: flex-start;
    gap: 20px;
}

.card-icon {
    width: 64px;
    height: 64px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    flex-shrink: 0;
}
.cpu-icon { background-color: #e6f7ff; color: #1890ff; }
.mem-icon { background-color: #f6ffed; color: #52c41a; }
.disk-icon { background-color: #f9f0ff; color: #722ed1; }
.task-icon { background-color: #fff7e6; color: #fa8c16; }
.net-icon { background-color: #f0f5ff; color: #2f54eb; }

.card-content {
    display: flex;
    flex-direction: column;
}
.card-title {
    font-size: 14px;
    color: #888;
    font-weight: 600;
    margin-bottom: 8px;
}
.card-value {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 4px;
}
.card-sub {
    font-size: 12px;
    color: #999;
}

.chart-card {
    min-height: 400px;
    display: flex;
    flex-direction: column;
}
.chart-title {
    font-size: 16px;
    font-weight: 600;
    color: #333;
    margin-bottom: 20px;
    text-align: center;
}
.chart-container {
    flex: 1;
    width: 100%;
    min-height: 350px;
}

/* Performance Styles */
.perf-section {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.perf-panel {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.panel-header {
    display: flex;
    align-items: center;
    gap: 16px;
    border-bottom: 1px solid #f5f5f5;
    padding-bottom: 16px;
}
.panel-title-group h4 {
    margin: 0;
    font-size: 18px;
    color: #333;
}
.panel-title-group .subtitle {
    font-size: 13px;
    color: #999;
}

.perf-row-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
}
.stat-box {
    background: #fcfcfc;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    border: 1px solid #f5f5f5;
}
.stat-val {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 4px;
}
.stat-lbl {
    font-size: 12px;
    color: #888;
}

.cpu-cores-detail {
    margin-top: 8px;
}
.detail-label {
    font-size: 13px;
    color: #666;
    margin-bottom: 12px;
}
.cores-visual {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 12px;
}
.core-block-wrapper {
    background: #fafafa;
    border-radius: 8px;
    padding: 8px;
    border: 1px solid #f0f0f0;
}
.core-block-header {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #888;
    margin-bottom: 6px;
}
.core-progress-bg {
    height: 6px;
    background: #eee;
    border-radius: 3px;
    overflow: hidden;
}
.core-progress-fill {
    height: 100%;
    transition: width 0.5s ease;
}

.memory-bars {
    display: flex;
    flex-direction: column;
    gap: 20px;
}
.mem-bar-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.bar-label {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #666;
}
.progress-bg {
    height: 12px;
    background: #f5f5f5;
    border-radius: 6px;
    overflow: hidden;
}
.progress-bg.small { height: 6px; }

.progress-fill {
    height: 100%;
    transition: width 0.5s ease;
}

.bottom-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 24px;
}

.disk-partitions {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-height: 200px;
    overflow-y: auto;
}
.disk-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.disk-row-header {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 500;
}
.disk-sub {
    font-size: 11px;
    color: #999;
}

.io-stats {
    display: flex;
    gap: 24px;
    margin-top: 16px;
    border-top: 1px solid #f5f5f5;
    padding-top: 16px;
}
.io-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
}
.io-val { font-size: 18px; font-weight: bold; }
.io-lbl { font-size: 12px; color: #888; }

.active-pids {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #666;
}
.pid-val { font-weight: bold; color: #333; }

/* Colors */
.blue { color: #1890ff; }
.green { color: #52c41a; }
.purple { color: #722ed1; }
.orange { color: #fa8c16; }

.blue-bg { background-color: #1890ff; }
.green-bg { background-color: #52c41a; }
.purple-bg { background-color: #722ed1; }
.orange-bg { background-color: #fa8c16; }

.bg-light-blue { background-color: #e6f7ff; }
.bg-light-green { background-color: #f6ffed; }

.two-col { grid-template-columns: 1fr 1fr; }
.mt-3 { margin-top: 12px; }

@media (max-width: 768px) {
    .overview-grid, .bottom-grid, .perf-row-stats {
        grid-template-columns: 1fr;
    }
}
</style>
