<template>
  <section class="section test-section">
    <!-- 测试控制面板 -->
    <div class="card test-control-card">
      <div class="control-header">
        <h3>数据采集效率测试</h3>
        <span class="control-desc">通过启动并发采集任务，统计单位时间内数据产出速率与资源占用情况</span>
      </div>

      <div class="control-body">
        <div class="control-row">
          <div class="control-group">
            <label>选择项目</label>
            <select v-model="selectedProjectId" class="form-select" @change="onProjectChange">
              <option :value="null">请选择项目</option>
              <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div class="control-group">
            <label>采集任务 (可多选)</label>
            <select v-model="selectedTaskIds" multiple class="form-select task-multi-select">
              <option v-for="t in projectTasks" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <div class="task-count">{{ selectedTaskIds.length }} 个任务已选择</div>
          </div>
          <div class="control-group small">
            <label>监测窗口</label>
            <select v-model="timeWindow" class="form-select">
              <option :value="5">5 秒</option>
              <option :value="10">10 秒</option>
              <option :value="30">30 秒</option>
              <option :value="60">1 分钟</option>
            </select>
          </div>
        </div>

        <div class="action-row">
          <div class="action-buttons">
            <button class="btn btn-primary btn-lg" :disabled="!canStartTest" @click="startTest">
              <PlayIcon :size="18" />
              开始测试
            </button>
            <button class="btn btn-secondary" :disabled="!selectedTaskIds.length || isRefreshing" @click="refreshMetrics">
              <RefreshCwIcon :size="16" :class="{ 'spin': isRefreshing }" />
              刷新数据
            </button>
            <button class="btn btn-secondary" :disabled="!testData" @click="exportReport">
              <DownloadIcon :size="16" />
              导出报告
            </button>
            <button class="btn btn-danger" @click="clearTestOutput">
              <Trash2Icon :size="16" />
              清空测试数据
            </button>
          </div>
          <div v-if="isTesting" class="test-status">
            <span class="status-badge running">测试中</span>
            <span class="status-text">已运行 {{ testDuration }} 秒</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试结果展示 -->
    <div v-if="testData" class="results-section">
      <!-- 核心指标卡片 -->
      <div class="metrics-grid">
        <!-- 吞吐量 - 文件数 -->
        <div class="metric-card">
          <div class="metric-icon files-icon">
            <FileIcon :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-label">文件吞吐量</div>
            <div class="metric-value">{{ throughputFiles.toFixed(1) }}</div>
            <div class="metric-unit">文件/秒</div>
          </div>
          <div class="metric-detail">
            窗口新增: {{ testData.output?.recent_files ?? 0 }} 文件
          </div>
        </div>

        <!-- 吞吐量 - 数据量 -->
        <div class="metric-card">
          <div class="metric-icon data-icon">
            <DatabaseIcon :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-label">数据吞吐量</div>
            <div class="metric-value">{{ throughputMb.toFixed(2) }}</div>
            <div class="metric-unit">MB/秒</div>
          </div>
          <div class="metric-detail">
            窗口新增: {{ formatBytes(testData.output?.recent_bytes ?? 0) }}
          </div>
        </div>

        <!-- 成功率 -->
        <div class="metric-card">
          <div class="metric-icon success-icon">
            <CheckCircleIcon :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-label">任务成功率</div>
            <div class="metric-value" :class="successRateClass">{{ successRate.toFixed(1) }}%</div>
            <div class="metric-unit">窗口成功率</div>
          </div>
          <div class="metric-detail">
            成功 {{ testData.executions_window?.success ?? 0 }} / 失败 {{ testData.executions_window?.failed ?? 0 }}
          </div>
        </div>

        <!-- CPU 峰值 -->
        <div class="metric-card">
          <div class="metric-icon cpu-icon">
            <CpuIcon :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-label">CPU 峰值</div>
            <div class="metric-value" :class="cpuPercentClass">{{ peakCpu.toFixed(1) }}%</div>
            <div class="metric-unit">最大 CPU 占用</div>
          </div>
          <div class="metric-detail">
            平均: {{ avgCpu.toFixed(1) }}%
          </div>
        </div>

        <!-- 内存峰值 -->
        <div class="metric-card">
          <div class="metric-icon mem-icon">
            <MemoryStickIcon :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-label">内存峰值</div>
            <div class="metric-value">{{ peakMem.toFixed(0) }}</div>
            <div class="metric-unit">MB</div>
          </div>
          <div class="metric-detail">
            平均: {{ avgMem.toFixed(0) }} MB
          </div>
        </div>

        <!-- 并发任务数 -->
        <div class="metric-card">
          <div class="metric-icon concurrent-icon">
            <ZapIcon :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-label">并发任务数</div>
            <div class="metric-value">{{ selectedTaskIds.length }}</div>
            <div class="metric-unit">并行采集</div>
          </div>
          <div class="metric-detail">
            窗口运行: {{ testData.executions_window?.started ?? 0 }} 次
          </div>
        </div>

        <!-- 系统稳定性 -->
        <div class="metric-card">
          <div class="metric-icon stable-icon">
            <AlertCircleIcon :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-label">系统稳定性</div>
            <div class="metric-value" :class="stabilityClass">{{ stabilityScore }}分</div>
            <div class="metric-unit">稳定性评分</div>
          </div>
          <div class="metric-detail">
            失败 {{ testData.executions_window?.failed ?? 0 }} / 成功 {{ testData.executions_window?.success ?? 0 }}
          </div>
        </div>
      </div>

      <!-- 实时图表 -->
      <div class="charts-row">
        <div class="card chart-card">
          <h4 class="chart-title">
            <TrendingUpIcon :size="16" />
            实时吞吐量趋势
          </h4>
          <div ref="throughputChartRef" class="chart-container"></div>
        </div>
        <div class="card chart-card">
          <h4 class="chart-title">
            <BarChart3Icon :size="16" />
            资源占用趋势
          </h4>
          <div ref="resourceChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 数据产出详情 -->
      <div class="card details-card">
        <h4 class="details-title">
          <FolderIcon :size="16" />
          数据产出详情
          <span class="details-sub">测试输出目录: /data/test</span>
        </h4>
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">总文件数</span>
            <span class="detail-value">{{ testData.output?.total_files ?? 0 }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">总数据量</span>
            <span class="detail-value">{{ formatBytes(testData.output?.total_bytes ?? 0) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">文件类型分布</span>
            <div class="file-types">
              <span v-for="t in topFileTypes" :key="t.ext" class="file-type-badge">
                {{ t.ext || '无扩展名' }}: {{ t.count }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 任务执行记录 -->
      <div class="card tasks-card">
        <h4 class="details-title">
          <ListIcon :size="16" />
          任务执行记录
        </h4>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>任务名称</th>
                <th>状态</th>
                <th>开始时间</th>
                <th>耗时</th>
                <th>CPU峰值</th>
                <th>内存峰值</th>
                <th>日志</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="exec in recentExecutions" :key="exec.execution_id || exec.task_id">
                <td>{{ exec.task_name }}</td>
                <td>
                  <span class="status-tag" :class="exec.status">{{ exec.status || '-' }}</span>
                </td>
                <td>{{ formatTime(exec.start_time) }}</td>
                <td>{{ formatDuration(exec.duration) }}</td>
                <td>{{ exec.max_cpu_percent?.toFixed(1) ?? '-' }}%</td>
                <td>{{ exec.max_memory_mb?.toFixed(0) ?? '-' }} MB</td>
                <td>
                  <button v-if="exec.log_file" class="btn-link" @click="viewLog(exec)">查看</button>
                  <span v-else class="text-muted">-</span>
                </td>
              </tr>
              <tr v-if="!recentExecutions.length">
                <td colspan="7" class="text-center text-muted">暂无执行记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state-card">
      <div class="empty-icon">
        <FlaskConicalIcon :size="64" />
      </div>
      <h3>数据采集效率测试</h3>
      <p>请选择项目和任务，点击"开始测试"启动并发采集任务</p>
      <p class="empty-hint">系统将实时监控数据产出速率与资源占用情况</p>
    </div>

    <!-- 日志查看器 -->
    <TaskLogModal
      v-if="showLogModal"
      :task-id="logTaskId"
      :task-name="logTaskName"
      :initial-execution-id="logExecutionId"
      @close="closeLogModal"
    />
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  PlayIcon, RefreshCwIcon, DownloadIcon, FileIcon, DatabaseIcon,
  CheckCircleIcon, CpuIcon, MemoryStickIcon,
  TrendingUpIcon, BarChart3Icon, FolderIcon, ListIcon,
  FlaskConicalIcon, Trash2Icon, AlertCircleIcon, ZapIcon
} from 'lucide-vue-next'
import TaskLogModal from '@/components/task/TaskLogModal.vue'

// Types
interface Project {
  id: number
  name: string
}

interface Task {
  id: number
  name: string
  status: string
}

interface TestData {
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
}

// State
const API_BASE = '/api'
const projects = ref<Project[]>([])
const projectTasks = ref<Task[]>([])
const selectedProjectId = ref<number | null>(null)
const selectedTaskIds = ref<number[]>([])
const timeWindow = ref(10)
const testData = ref<TestData | null>(null)
const isRefreshing = ref(false)
const isTesting = ref(false)
const testStartTime = ref<number | null>(null)

// Chart refs
const throughputChartRef = ref<HTMLElement | null>(null)
const resourceChartRef = ref<HTMLElement | null>(null)
let throughputChart: echarts.ECharts | null = null
let resourceChart: echarts.ECharts | null = null

// History for charts
const throughputHistory = ref<Array<{ time: string; files: number; mb: number }>>([])

// Log modal
const showLogModal = ref(false)
const logTaskId = ref<number | string>('')
const logTaskName = ref('')
const logExecutionId = ref<number | undefined>(undefined)

// Computed
const canStartTest = computed(() => selectedProjectId.value && selectedTaskIds.value.length > 0)

const testDuration = computed(() => {
  if (!testStartTime.value) return 0
  return Math.floor((Date.now() - testStartTime.value) / 1000)
})

const throughputFiles = computed(() => {
  if (!testData.value) return 0
  return (testData.value.output?.recent_files ?? 0) / timeWindow.value
})

const throughputMb = computed(() => {
  if (!testData.value) return 0
  return ((testData.value.output?.recent_bytes ?? 0) / 1024 / 1024) / timeWindow.value
})

const successRate = computed(() => {
  if (!testData.value) return 0
  const success = testData.value.executions_window?.success ?? 0
  const failed = testData.value.executions_window?.failed ?? 0
  const total = success + failed
  return total > 0 ? (success / total) * 100 : 100
})

const successRateClass = computed(() => {
  const rate = successRate.value
  if (rate >= 90) return 'text-success'
  if (rate >= 70) return 'text-warning'
  return 'text-danger'
})

const peakCpu = computed(() => {
  if (!testData.value) return 0
  const values = testData.value.latest_executions
    .map(e => e.max_cpu_percent)
    .filter(v => typeof v === 'number') as number[]
  return values.length ? Math.max(...values) : 0
})

const avgCpu = computed(() => {
  if (!testData.value) return 0
  const values = testData.value.latest_executions
    .map(e => e.max_cpu_percent)
    .filter(v => typeof v === 'number') as number[]
  if (!values.length) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
})

const cpuPercentClass = computed(() => {
  const cpu = peakCpu.value
  if (cpu < 50) return 'text-success'
  if (cpu < 80) return 'text-warning'
  return 'text-danger'
})

const peakMem = computed(() => {
  if (!testData.value) return 0
  const values = testData.value.latest_executions
    .map(e => e.max_memory_mb)
    .filter(v => typeof v === 'number') as number[]
  return values.length ? Math.max(...values) : 0
})

const avgMem = computed(() => {
  if (!testData.value) return 0
  const values = testData.value.latest_executions
    .map(e => e.max_memory_mb)
    .filter(v => typeof v === 'number') as number[]
  if (!values.length) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
})

// 系统稳定性评分：基于成功率计算
const stabilityScore = computed(() => {
  const rate = successRate.value
  if (rate >= 95) return 100
  if (rate >= 90) return 90
  if (rate >= 80) return 80
  if (rate >= 70) return 70
  if (rate >= 60) return 60
  if (rate >= 50) return 50
  return Math.max(0, rate)
})

const stabilityClass = computed(() => {
  const score = stabilityScore.value
  if (score >= 90) return 'text-success'
  if (score >= 70) return 'text-warning'
  return 'text-danger'
})

const topFileTypes = computed(() => {
  if (!testData.value?.output?.types) return []
  return testData.value.output.types.slice(0, 5)
})

const recentExecutions = computed(() => {
  if (!testData.value?.latest_executions) return []
  return testData.value.latest_executions.slice(0, 10)
})

// Methods
const formatBytes = (bytes: number) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let idx = 0
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024
    idx++
  }
  return `${value.toFixed(2)} ${units[idx]}`
}

const formatTime = (iso: string | undefined) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

const formatDuration = (seconds: number | undefined) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

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

const fetchTasks = async () => {
  if (!selectedProjectId.value) {
    projectTasks.value = []
    return
  }
  try {
    const res = await fetch(`${API_BASE}/tasks?project_id=${selectedProjectId.value}&limit=100`)
    if (res.ok) {
      projectTasks.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const onProjectChange = () => {
  selectedTaskIds.value = []
  testData.value = null
  fetchTasks()
}

const refreshMetrics = async () => {
  if (!selectedTaskIds.value.length) return
  isRefreshing.value = true
  try {
    const ids = selectedTaskIds.value.join(',')
    const url = `${API_BASE}/tasks/test-metrics/overview?task_ids=${encodeURIComponent(ids)}&window_seconds=${timeWindow.value}`
    const res = await fetch(url)
    if (res.ok) {
      testData.value = await res.json()

      // Update history
      if (testData.value?.output) {
        throughputHistory.value.push({
          time: new Date().toLocaleTimeString(),
          files: testData.value.output?.recent_files ?? 0,
          mb: (testData.value.output?.recent_bytes ?? 0) / 1024 / 1024
        })
      }
      if (throughputHistory.value.length > 30) {
        throughputHistory.value.shift()
      }

      // Initialize or update charts after data is loaded
      await nextTick()
      if (!throughputChart) {
        initThroughputChart()
      }
      if (!resourceChart) {
        initResourceChart()
      }
      updateCharts()
    }
  } catch (e) {
    console.error(e)
  } finally {
    isRefreshing.value = false
  }
}

const startTest = async () => {
  if (!selectedTaskIds.value.length) return

  isTesting.value = true
  testStartTime.value = Date.now()
  throughputHistory.value = []

  try {
    // Start all selected tasks
    await Promise.all(
      selectedTaskIds.value.map(id =>
        fetch(`${API_BASE}/tasks/${id}/run`, { method: 'POST' })
      )
    )

    // Poll for results
    const pollInterval = 2000
    const maxPolls = 120 // Max 4 minutes

    for (let i = 0; i < maxPolls; i++) {
      await refreshMetrics()

      // Check if all tasks finished
      const running = testData.value?.executions_window?.running ?? 0
      if (running === 0 && i > 3) {
        break
      }

      await new Promise(r => setTimeout(r, pollInterval))
    }

    // After test completes, update charts once
    await nextTick()
    updateCharts()
  } catch (e) {
    console.error(e)
  } finally {
    isTesting.value = false
  }
}

// Charts
const initThroughputChart = () => {
  if (!throughputChartRef.value) return
  if (throughputChart) throughputChart.dispose()

  throughputChart = echarts.init(throughputChartRef.value)

  // Set base option once
  throughputChart.setOption({
    animation: true,
    animationDuration: 500,
    tooltip: { trigger: 'axis' },
    legend: { data: ['文件/秒', 'MB/秒'], top: 4 },
    grid: { left: '3%', right: '4%', top: 40, bottom: 20, containLabel: true },
    xAxis: { type: 'category', data: [], axisLabel: { color: '#666', fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '文件数', splitLine: { show: true, lineStyle: { type: 'dashed' } } },
      { type: 'value', name: 'MB', splitLine: { show: false } }
    ],
    series: [
      { name: '文件/秒', type: 'line', data: [], smooth: true, itemStyle: { color: '#1890ff' }, areaStyle: { opacity: 0.1 } },
      { name: 'MB/秒', type: 'line', yAxisIndex: 1, data: [], smooth: true, itemStyle: { color: '#52c41a' }, areaStyle: { opacity: 0.1 } }
    ]
  })
}

const updateThroughputChart = () => {
  if (!throughputChart) return

  const labels = throughputHistory.value.map(h => h.time)
  const filesData = throughputHistory.value.map(h => h.files / timeWindow.value)
  const mbData = throughputHistory.value.map(h => h.mb / timeWindow.value)

  // Only update data, not the entire option - for smooth transitions
  throughputChart.setOption({
    xAxis: { data: labels },
    series: [
      { data: filesData },
      { data: mbData }
    ]
  }, { notMerge: false, lazyUpdate: true })
}

const initResourceChart = () => {
  if (!resourceChartRef.value) return
  if (resourceChart) resourceChart.dispose()

  resourceChart = echarts.init(resourceChartRef.value)

  // Set base option once
  resourceChart.setOption({
    animation: true,
    animationDuration: 500,
    tooltip: { trigger: 'axis' },
    legend: { data: ['CPU %', '内存 MB'], top: 4 },
    grid: { left: '3%', right: '4%', top: 40, bottom: 20, containLabel: true },
    xAxis: { type: 'category', data: [], axisLabel: { color: '#666', fontSize: 10 } },
    yAxis: { type: 'value', name: '值', splitLine: { show: true, lineStyle: { type: 'dashed' } } },
    series: [
      { name: 'CPU %', type: 'line', data: [], smooth: true, itemStyle: { color: '#faad14' }, areaStyle: { opacity: 0.1 } },
      { name: '内存 MB', type: 'line', data: [], smooth: true, itemStyle: { color: '#722ed1' }, areaStyle: { opacity: 0.1 } }
    ]
  })
}

const updateResourceChart = () => {
  if (!resourceChart || !testData.value) return

  const series = testData.value.timeseries
  const labels = series.duration?.map(d => d.label) || []
  const cpuData = series.max_cpu?.map(d => d.value) || []
  const memData = series.max_memory?.map(d => d.value) || []

  // Only update data, not the entire option - for smooth transitions
  resourceChart.setOption({
    xAxis: { data: labels },
    series: [
      { data: cpuData },
      { data: memData }
    ]
  }, { notMerge: false, lazyUpdate: true })
}

const updateCharts = () => {
  updateThroughputChart()
  updateResourceChart()
}

// Log modal
interface ExecutionLog {
  task_id: number
  task_name: string
  execution_id?: number
  status?: string
}

const viewLog = (exec: ExecutionLog) => {
  logTaskId.value = exec.task_id
  logTaskName.value = exec.task_name
  logExecutionId.value = exec.execution_id
  showLogModal.value = true
}

const closeLogModal = () => {
  showLogModal.value = false
}

// Export report
const exportReport = () => {
  if (!testData.value) return

  const report = {
    测试时间: new Date().toLocaleString(),
    项目: testData.value.project_name,
    任务数: selectedTaskIds.value.length,
    监测窗口: `${timeWindow.value}秒`,
    核心指标: {
      文件吞吐量: `${throughputFiles.value.toFixed(2)} 文件/秒`,
      数据吞吐量: `${throughputMb.value.toFixed(2)} MB/秒`,
      成功率: `${successRate.value.toFixed(1)}%`,
      CPU峰值: `${peakCpu.value.toFixed(1)}%`,
      内存峰值: `${peakMem.value.toFixed(0)} MB`
    },
    数据产出: {
      总文件数: testData.value.output?.total_files ?? 0,
      总数据量: formatBytes(testData.value.output?.total_bytes ?? 0),
      窗口新增文件: testData.value.output?.recent_files ?? 0,
      窗口新增数据: formatBytes(testData.value.output?.recent_bytes ?? 0)
    },
    任务执行: {
      已启动: testData.value.executions_window?.started ?? 0,
      已完成: testData.value.executions_window?.finished ?? 0,
      成功: testData.value.executions_window?.success ?? 0,
      失败: testData.value.executions_window?.failed ?? 0,
      运行中: testData.value.executions_window?.running ?? 0
    }
  }

  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `采集效率测试报告_${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// Clear test output directory
const clearTestOutput = async () => {
  if (!confirm('确定要清空测试输出目录吗？此操作不可恢复。')) {
    return
  }
  try {
    const res = await fetch(`${API_BASE}/tasks/test-metrics/clear-output`, { method: 'POST' })
    if (res.ok) {
      const result = await res.json()
      alert(result.message || '清空成功')
      // Refresh metrics after clearing
      refreshMetrics()
    } else {
      const err = await res.json()
      alert(err.detail || '清空失败')
    }
  } catch (e) {
    console.error(e)
    alert('清空失败')
  }
}

// Watchers
watch(selectedTaskIds, async () => {
  throughputHistory.value = []
  if (selectedTaskIds.value.length > 0) {
    await refreshMetrics()
    // Charts will be rendered once data is loaded
  } else {
    testData.value = null
  }
})

watch(timeWindow, () => {
  throughputHistory.value = []
  if (selectedTaskIds.value.length > 0) {
    refreshMetrics()
  }
})

// Lifecycle
onMounted(() => {
  fetchProjects()
  window.addEventListener('resize', () => {
    throughputChart?.resize()
    resourceChart?.resize()
  })
})

onUnmounted(() => {
  throughputChart?.dispose()
  resourceChart?.dispose()
})
</script>

<style scoped>
.test-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Control Card */
.test-control-card {
  padding: 0;
  overflow: hidden;
}

.control-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.control-header h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
}

.control-desc {
  font-size: 13px;
  opacity: 0.9;
}

.control-body {
  padding: 20px;
}

.control-row {
  display: grid;
  grid-template-columns: 200px 1fr 120px;
  gap: 16px;
  align-items: start;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.control-group.small {
  flex: 0 0 120px;
}

.control-group label {
  font-size: 13px;
  font-weight: 600;
  color: #444;
}

.task-multi-select {
  min-height: 80px;
}

.task-count {
  font-size: 12px;
  color: #666;
}

.action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.btn-lg {
  padding: 10px 24px;
  font-size: 15px;
}

.test-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.running {
  background: #fff7e6;
  color: #fa8c16;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.status-text {
  font-size: 13px;
  color: #666;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
}

.metric-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid #f0f0f0;
}

.metric-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.files-icon { background: #e6f7ff; color: #1890ff; }
.data-icon { background: #f6ffed; color: #52c41a; }
.success-icon { background: #f6ffed; color: #52c41a; }
.cpu-icon { background: #fff7e6; color: #fa8c16; }
.mem-icon { background: #f9f0ff; color: #722ed1; }
.status-icon { background: #e6f7ff; color: #1890ff; }
.concurrent-icon { background: #fff1f0; color: #ff4d4f; }
.stable-icon { background: #f0f5ff; color: #2f54eb; }

.metric-content {
  text-align: center;
}

.metric-label {
  font-size: 12px;
  color: #666;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  line-height: 1.2;
}

.metric-unit {
  font-size: 11px;
  color: #999;
}

.metric-detail {
  font-size: 11px;
  color: #888;
  text-align: center;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}

/* Charts */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  padding: 16px;
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.chart-container {
  height: 200px;
}

/* Details Card */
.details-card {
  padding: 16px;
}

.details-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px 0;
  font-size: 14px;
  color: #333;
}

.details-sub {
  font-size: 12px;
  color: #999;
  font-weight: normal;
  margin-left: auto;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: #666;
}

.detail-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.file-types {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-type-badge {
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #666;
}

/* Tasks Card */
.tasks-card {
  padding: 16px;
}

.table-container {
  max-height: 300px;
  overflow: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.data-table th {
  background: #fafafa;
  font-weight: 600;
  font-size: 12px;
  color: #666;
}

.data-table td {
  font-size: 13px;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-tag.success { background: #f6ffed; color: #52c41a; }
.status-tag.failed { background: #fff1f0; color: #ff4d4f; }
.status-tag.running { background: #e6f7ff; color: #1890ff; }

.btn-link {
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}

.btn-link:hover {
  text-decoration: underline;
}

/* Empty State */
.empty-state-card {
  background: white;
  border-radius: 12px;
  padding: 60px;
  text-align: center;
  border: 2px dashed #e8e8e8;
}

.empty-icon {
  color: #d9d9d9;
  margin-bottom: 16px;
}

.empty-state-card h3 {
  margin: 0 0 8px 0;
  color: #333;
}

.empty-state-card p {
  margin: 0 0 4px 0;
  color: #666;
}

.empty-hint {
  font-size: 13px;
  color: #999;
}

/* Utility */
.text-success { color: #52c41a; }
.text-warning { color: #fa8c16; }
.text-danger { color: #ff4d4f; }
.text-muted { color: #999; }
.text-center { text-align: center; }

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.btn-primary {
  background: #1890ff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  border-color: #d9d9d9;
  color: #666;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #40a9ff;
  color: #40a9ff;
}

.btn-danger {
  background: #ff4d4f;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #ff7875;
}

.form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
}

.form-select:focus {
  border-color: #40a9ff;
  outline: none;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
}

/* Responsive */
@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .control-row {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .details-grid {
    grid-template-columns: 1fr;
  }
}
</style>
