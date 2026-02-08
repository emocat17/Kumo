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
      <button 
        :class="['tab-btn', { active: activeTab === 'tests' }]" 
        @click="activeTab = 'tests'"
      >
        测试与性能
      </button>
    </div>

    <!-- System Overview -->
    <section v-if="activeTab === 'overview'" class="section">
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
    <section v-if="activeTab === 'tests'" class="section test-section">
      <div class="card test-control-card">
        <div class="test-control-row">
          <div class="control-group">
            <label>选择项目</label>
            <ProjectSelector v-model="testProjectId" />
          </div>
          <div class="control-group">
            <label>选择任务</label>
            <select v-model="selectedTaskIds" multiple class="form-select task-multi-select">
              <option v-for="task in testTasks" :key="task.id" :value="task.id">
                {{ task.name }}
              </option>
            </select>
          </div>
          <div class="control-group small">
            <label>时间窗</label>
            <select v-model="timeWindow" class="form-select">
              <option :value="1">1s</option>
              <option :value="10">10s</option>
              <option :value="60">1min</option>
            </select>
          </div>
        </div>
        <div class="test-action-row">
          <div class="action-buttons">
            <button class="btn btn-primary" @click="runSelectedTasks" :disabled="selectedTaskIds.length === 0 || isRunningTests">
              一键执行
            </button>
            <button class="btn btn-secondary" @click="refreshTestMetrics" :disabled="isLoadingMetrics">
              刷新指标
            </button>
          </div>
          <div class="output-hint">
            输出目录: {{ testMetrics?.output_dir || '-' }}
          </div>
        </div>
      </div>

      <div class="overview-grid test-overview-grid">
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <i class="icon-task">📦</i>
          </div>
          <div class="card-content">
            <div class="card-title">产出总量</div>
            <div class="card-value blue">{{ testMetrics?.output.total_files ?? 0 }}</div>
            <div class="card-sub">{{ formatBytes(testMetrics?.output.total_bytes ?? 0) }}</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon cpu-icon">
            <i class="icon-cpu">⚡</i>
          </div>
          <div class="card-content">
            <div class="card-title">窗口新增</div>
            <div class="card-value green">{{ testMetrics?.output.recent_files ?? 0 }}</div>
            <div class="card-sub">{{ formatBytes(testMetrics?.output.recent_bytes ?? 0) }}</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon mem-icon">
            <i class="icon-mem">🚦</i>
          </div>
          <div class="card-content">
            <div class="card-title">窗口执行</div>
            <div class="card-value purple">{{ testMetrics?.executions_window.started ?? 0 }}</div>
            <div class="card-sub">{{ testMetrics?.executions_window.running ?? 0 }} 运行中</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon disk-icon">
            <i class="icon-disk">✅</i>
          </div>
          <div class="card-content">
            <div class="card-title">窗口成功</div>
            <div class="card-value orange">{{ testMetrics?.executions_window.success ?? 0 }}</div>
            <div class="card-sub">{{ testMetrics?.executions_window.failed ?? 0 }} 失败</div>
          </div>
        </div>
      </div>

      <div class="charts-grid">
        <div class="card chart-card">
          <h3 class="chart-title">动态指标</h3>
          <div ref="dynamicChartRef" class="chart-container"></div>
        </div>
        <div class="card chart-card">
          <h3 class="chart-title">全程指标</h3>
          <div ref="fullChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="card test-evidence-card">
        <div class="evidence-header">
          <h3>覆盖度证据</h3>
          <span class="evidence-sub">对照日志与产出文件</span>
        </div>
        <div class="evidence-grid">
          <div class="evidence-panel">
            <div class="panel-title">产出文件</div>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>文件名</th>
                    <th>大小</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!testMetrics?.evidence.output_samples.length">
                    <td colspan="3" class="text-center text-gray">暂无产出</td>
                  </tr>
                  <tr v-for="item in testMetrics?.evidence.output_samples" :key="item.path">
                    <td class="font-mono truncate">{{ item.name }}</td>
                    <td>{{ formatBytes(item.size) }}</td>
                    <td>{{ formatTime(item.mtime) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="evidence-panel">
            <div class="panel-title">任务日志</div>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>任务</th>
                    <th>状态</th>
                    <th>日志文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!testMetrics?.latest_executions.length">
                    <td colspan="3" class="text-center text-gray">暂无日志</td>
                  </tr>
                  <tr v-for="item in testMetrics?.latest_executions" :key="item.task_id">
                    <td>{{ item.task_name }}</td>
                    <td>{{ item.status || '-' }}</td>
                    <td class="font-mono truncate">{{ item.log_file || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
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

interface DashboardStats {
  total_tasks: number
  active_tasks: number
  running_executions: number
  total_executions: number
  success_rate_7d: number
  recent_executions: any[]
  daily_stats: Array<{
    date: string
    success: number
    failed: number
  }>
  failure_stats?: Array<{
      task_id: number
      task_name: string
      failure_count: number
  }>
}

interface TestTask {
  id: number
  name: string
}

interface TestMetricsOverview {
  project_id: number
  project_name: string
  output_dir: string
  task_count: number
  window_seconds: number
  output: {
    total_files: number
    total_bytes: number
    recent_files: number
    recent_bytes: number
    types: Array<{ ext: string; count: number }>
    scanned_files: number
    truncated: boolean
  }
  executions_window: {
    started: number
    finished: number
    success: number
    failed: number
    running: number
  }
  latest_executions: Array<{
    task_id: number
    task_name: string
    execution_id?: number
    status?: string
    start_time?: string
    end_time?: string
    duration?: number
    max_cpu_percent?: number
    max_memory_mb?: number
    log_file?: string
  }>
  timeseries: {
    duration: Array<{ label: string; value: number }>
    max_cpu: Array<{ label: string; value: number }>
    max_memory: Array<{ label: string; value: number }>
  }
  evidence: {
    output_samples: Array<{ name: string; path: string; size: number; mtime: string }>
    log_files: Array<{ task_id: number; task_name: string; log_file?: string }>
  }
}

const activeTab = ref<'overview' | 'performance' | 'tests'>('overview')
const selectedProjectId = ref<number | null>(null)
const systemStats = ref<SystemStats>({} as SystemStats)
const dashboardStats = ref<DashboardStats>({
    total_tasks: 0,
    active_tasks: 0,
    running_executions: 0,
    total_executions: 0,
    success_rate_7d: 0,
    recent_executions: [],
    daily_stats: [],
    failure_stats: []
})
const timer = ref<number | null>(null)
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null
const testProjectId = ref<number | null>(null)
const testTasks = ref<TestTask[]>([])
const selectedTaskIds = ref<number[]>([])
const timeWindow = ref<number>(10)
const testMetrics = ref<TestMetricsOverview | null>(null)
const isLoadingMetrics = ref(false)
const isRunningTests = ref(false)
const metricsTimer = ref<number | null>(null)
const dynamicChartRef = ref<HTMLElement | null>(null)
const fullChartRef = ref<HTMLElement | null>(null)
let dynamicChartInstance: echarts.ECharts | null = null
let fullChartInstance: echarts.ECharts | null = null
const dynamicHistory = ref<Array<{ label: string; files: number; bytes: number }>>([])

const API_BASE = 'http://localhost:8000/api'

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

watch(selectedProjectId, () => {
    fetchDashboardStats()
})

const fetchTestTasks = async () => {
  if (!testProjectId.value) {
    testTasks.value = []
    selectedTaskIds.value = []
    return
  }
  try {
    const res = await fetch(`${API_BASE}/tasks?project_id=${testProjectId.value}`)
    if (res.ok) {
      testTasks.value = await res.json()
      selectedTaskIds.value = testTasks.value.map(t => t.id)
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchTestMetrics = async () => {
  if (!testProjectId.value) return
  isLoadingMetrics.value = true
  try {
    const ids = selectedTaskIds.value.join(',')
    const url = `${API_BASE}/tasks/test-metrics/overview?project_id=${testProjectId.value}&task_ids=${encodeURIComponent(ids)}&window_seconds=${timeWindow.value}`
    const res = await fetch(url)
    if (res.ok) {
      const metrics = (await res.json()) as TestMetricsOverview
      testMetrics.value = metrics
      const label = new Date().toLocaleTimeString()
      dynamicHistory.value.push({
        label,
        files: metrics.output?.recent_files ?? 0,
        bytes: metrics.output?.recent_bytes ?? 0
      })
      if (dynamicHistory.value.length > 60) {
        dynamicHistory.value.shift()
      }
      await nextTick()
      initDynamicChart()
      initFullChart()
    }
  } catch (e) {
    console.error(e)
  } finally {
    isLoadingMetrics.value = false
  }
}

const refreshTestMetrics = async () => {
  await fetchTestMetrics()
}

const runSelectedTasks = async () => {
  if (selectedTaskIds.value.length === 0) return
  isRunningTests.value = true
  try {
    for (const id of selectedTaskIds.value) {
      await fetch(`${API_BASE}/tasks/${id}/run`, { method: 'POST' })
    }
    await fetchTestMetrics()
  } catch (e) {
    console.error(e)
  } finally {
    isRunningTests.value = false
  }
}

const startMetricsTimer = () => {
  if (metricsTimer.value) clearInterval(metricsTimer.value)
  metricsTimer.value = setInterval(() => {
    if (document.hidden) return
    if (activeTab.value === 'tests' && testProjectId.value) {
      fetchTestMetrics()
    }
  }, Math.max(timeWindow.value * 1000, 1000)) as unknown as number
}

watch(testProjectId, async () => {
  dynamicHistory.value = []
  await fetchTestTasks()
  await fetchTestMetrics()
})

watch(selectedTaskIds, async () => {
  dynamicHistory.value = []
  await fetchTestMetrics()
})

watch(timeWindow, () => {
  dynamicHistory.value = []
  startMetricsTimer()
  fetchTestMetrics()
})

const getUsageColor = (percent: number) => {
    if (percent < 50) return '#52c41a' // Green
    if (percent < 80) return '#faad14' // Orange
    return '#ff4d4f' // Red
}

const getFailureBarWidth = (count: number) => {
    if (!dashboardStats.value.failure_stats?.length) return 0
    const max = Math.max(...dashboardStats.value.failure_stats.map(s => s.failure_count))
    return max ? (count / max) * 100 : 0
}

const initChart = () => {
    if (!chartRef.value) return
    
    // Dispose if exists
    if (chartInstance) {
        chartInstance.dispose()
    }
    
    chartInstance = echarts.init(chartRef.value)
    
    const dates = dashboardStats.value.daily_stats.map(s => s.date)
    const successData = dashboardStats.value.daily_stats.map(s => s.success)
    const failedData = dashboardStats.value.daily_stats.map(s => s.failed)
    
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
                emphasis: { focus: 'series' },
                barBorderRadius: [4, 4, 0, 0] // Only top corners
            },
            {
                name: '失败任务',
                type: 'bar',
                stack: 'total',
                barWidth: '40%',
                itemStyle: { color: '#ff4d4f' },
                data: failedData,
                emphasis: { focus: 'series' },
                barBorderRadius: [0, 0, 0, 0]
            }
        ]
    }
    
    chartInstance.setOption(option)
}

const initDynamicChart = () => {
  if (!dynamicChartRef.value) return
  if (dynamicChartInstance) {
    dynamicChartInstance.dispose()
  }
  dynamicChartInstance = echarts.init(dynamicChartRef.value)
  const labels = dynamicHistory.value.map(p => p.label)
  const fileSeries = dynamicHistory.value.map(p => p.files)
  const byteSeries = dynamicHistory.value.map(p => Number((p.bytes / 1024 / 1024).toFixed(3)))
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增文件', '新增体积(MB)'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { color: '#666' } },
    yAxis: [
      { type: 'value', name: '文件数', splitLine: { lineStyle: { type: 'dashed' } } },
      { type: 'value', name: 'MB', splitLine: { show: false } }
    ],
    series: [
      { name: '新增文件', type: 'line', data: fileSeries, smooth: true, itemStyle: { color: '#1890ff' } },
      { name: '新增体积(MB)', type: 'line', yAxisIndex: 1, data: byteSeries, smooth: true, itemStyle: { color: '#52c41a' } }
    ]
  }
  dynamicChartInstance.setOption(option)
}

const initFullChart = () => {
  if (!fullChartRef.value || !testMetrics.value) return
  if (fullChartInstance) {
    fullChartInstance.dispose()
  }
  fullChartInstance = echarts.init(fullChartRef.value)
  const labels = testMetrics.value.timeseries.duration.map(p => p.label)
  const durationSeries = testMetrics.value.timeseries.duration.map(p => p.value)
  const cpuSeries = testMetrics.value.timeseries.max_cpu.map(p => p.value)
  const memSeries = testMetrics.value.timeseries.max_memory.map(p => p.value)
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['耗时(秒)', 'CPU峰值(%)', '内存峰值(MB)'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { color: '#666' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [
      { name: '耗时(秒)', type: 'bar', data: durationSeries, itemStyle: { color: '#1890ff' } },
      { name: 'CPU峰值(%)', type: 'line', data: cpuSeries, smooth: true, itemStyle: { color: '#faad14' } },
      { name: '内存峰值(MB)', type: 'line', data: memSeries, smooth: true, itemStyle: { color: '#722ed1' } }
    ]
  }
  fullChartInstance.setOption(option)
}

const formatBytes = (bytes: number) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let idx = 0
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024
    idx += 1
  }
  return `${value.toFixed(2)} ${units[idx]}`
}

const formatTime = (iso: string) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

// Watch active tab to re-init chart when switching back to overview
watch(activeTab, async (newVal) => {
    if (newVal === 'overview') {
        fetchDashboardStats()
        await nextTick()
        initChart()
    }
    if (newVal === 'tests') {
        await nextTick()
        initDynamicChart()
        initFullChart()
        startMetricsTimer()
    }
})

// Resize handler
const handleResize = () => {
    chartInstance?.resize()
    dynamicChartInstance?.resize()
    fullChartInstance?.resize()
}

onMounted(() => {
  fetchSystemStats()
  fetchDashboardStats()
  startMetricsTimer()
  
  window.addEventListener('resize', handleResize)
  
  // Refresh stats every 3 seconds
  timer.value = setInterval(() => {
      if (document.hidden) return
      
      fetchSystemStats()
      if (activeTab.value === 'overview') {
          fetchDashboardStats()
      }
  }, 3000) as unknown as number
})

onUnmounted(() => {
    if (timer.value) clearInterval(timer.value)
    if (metricsTimer.value) clearInterval(metricsTimer.value)
    window.removeEventListener('resize', handleResize)
    chartInstance?.dispose()
    dynamicChartInstance?.dispose()
    fullChartInstance?.dispose()
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

.test-section {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.test-control-card {
    padding: 20px;
}

.test-control-row {
    display: grid;
    grid-template-columns: 1.2fr 2fr 0.6fr;
    gap: 20px;
    align-items: end;
}

.control-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 13px;
    color: #555;
}

.control-group label {
    font-weight: 600;
    color: #444;
}

.task-multi-select {
    min-height: 120px;
}

.test-action-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 16px;
    gap: 16px;
}

.action-buttons {
    display: flex;
    gap: 12px;
}

.output-hint {
    font-size: 12px;
    color: #777;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 520px;
}

.test-overview-grid {
    grid-template-columns: repeat(4, 1fr);
}

.test-evidence-card {
    padding: 20px;
}

.evidence-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}

.evidence-header h3 {
    margin: 0;
    font-size: 16px;
    color: #333;
}

.evidence-sub {
    font-size: 12px;
    color: #999;
}

.evidence-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.evidence-panel {
    background: #fafafa;
    border: 1px solid #f0f0f0;
    border-radius: 12px;
    padding: 16px;
}

.panel-title {
    font-size: 14px;
    font-weight: 600;
    color: #444;
    margin-bottom: 12px;
}

.table-container {
    max-height: 260px;
    overflow: auto;
}

.truncate {
    max-width: 240px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: inline-block;
}

@media (max-width: 768px) {
    .overview-grid, .bottom-grid, .perf-row-stats, .charts-grid {
        grid-template-columns: 1fr;
    }
}

.charts-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 24px;
}
.failure-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 0 10px;
    flex: 1;
    overflow-y: auto;
}
.failure-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.failure-info {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
}
.failure-rank {
    width: 20px;
    height: 20px;
    background: #f0f0f0;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    color: #666;
}
.failure-rank.rank-1 { background: #ff4d4f; color: white; }
.failure-rank.rank-2 { background: #ff7875; color: white; }
.failure-rank.rank-3 { background: #ffccc7; color: #cf1322; }

.failure-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 500;
    color: #333;
}
.failure-bar-wrapper {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 8px;
}
.failure-bar {
    height: 100%;
    background: #ff4d4f;
    border-radius: 4px;
    min-width: 2px;
}
.failure-count {
    font-size: 12px;
    color: #999;
    min-width: 30px;
    text-align: right;
}
.empty-state {
    text-align: center;
    color: #ccc;
    margin-top: 40px;
}
</style>
