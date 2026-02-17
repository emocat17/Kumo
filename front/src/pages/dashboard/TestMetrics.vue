<template>
  <section class="section test-section">
    <div class="card test-control-card">
      <div class="test-control-row">
        <div class="control-group" style="flex: 2;">
          <label>选择任务 (可多选)</label>
          <select v-model="selectedTaskIds" multiple class="form-select task-multi-select" style="height: 100px;">
            <option v-for="task in testTasks" :key="task.id" :value="task.id">
              {{ task.name }}
            </option>
          </select>
          <div v-if="isLoadingTasks" class="text-xs text-gray mt-1">
            加载中...
          </div>
          <div v-else-if="testTasks.length === 0" class="text-xs text-gray mt-1">
            暂无任务
          </div>
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
          <button class="btn btn-primary" :disabled="selectedTaskIds.length === 0 || isRunningTests" @click="runSelectedTasks">
            一键执行
          </button>
          <button class="btn btn-secondary" :disabled="isLoadingMetrics || selectedTaskIds.length === 0" @click="refreshTestMetrics">
            刷新指标
          </button>
          <button class="btn btn-secondary" :disabled="selectedTaskIds.length === 0" @click="exportTestMetrics('json')">
            导出JSON
          </button>
          <button class="btn btn-secondary" :disabled="selectedTaskIds.length === 0" @click="exportTestMetrics('csv')">
            导出CSV
          </button>
        </div>
        <div class="output-hint">
          输出目录: {{ testMetrics?.output_dir || '-' }}
        </div>
      </div>
    </div>

    <div class="overview-grid test-overview-grid">
      <template v-if="fullCategory === 'collection'">
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">📦</span>
          </div>
          <div class="card-content">
            <div class="card-title">产出总量</div>
            <div class="card-value blue">{{ testMetrics?.output.total_files ?? 0 }}</div>
            <div class="card-sub">{{ formatBytes(testMetrics?.output.total_bytes ?? 0) }}</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">📥</span>
          </div>
          <div class="card-content">
            <div class="card-title">吞吐量(文件/s)</div>
            <div class="card-value green">{{ throughputFilesPerSec.toFixed(2) }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon disk-icon">
            <span class="icon-disk">💾</span>
          </div>
          <div class="card-content">
            <div class="card-title">吞吐量(MB/s)</div>
            <div class="card-value orange">{{ throughputMbPerSec.toFixed(2) }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon cpu-icon">
            <span class="icon-cpu">🔳</span>
          </div>
          <div class="card-content">
            <div class="card-title">CPU峰值</div>
            <div class="card-value blue">{{ peakCpuPercent.toFixed(1) }}%</div>
            <div class="card-sub">近次执行峰值</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon mem-icon">
            <span class="icon-mem">🧠</span>
          </div>
          <div class="card-content">
            <div class="card-title">内存峰值</div>
            <div class="card-value purple">{{ peakMemoryMb.toFixed(1) }} MB</div>
            <div class="card-sub">近次执行峰值</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">✅</span>
          </div>
          <div class="card-content">
            <div class="card-title">窗口成功率</div>
            <div class="card-value blue">{{ windowSuccessRate.toFixed(1) }}%</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">⚠️</span>
          </div>
          <div class="card-content">
            <div class="card-title">窗口失败数</div>
            <div class="card-value orange">{{ testMetrics?.executions_window.failed ?? 0 }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">🏃</span>
          </div>
          <div class="card-content">
            <div class="card-title">运行中</div>
            <div class="card-value green">{{ testMetrics?.executions_window.running ?? 0 }}</div>
            <div class="card-sub">当前运行</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">⏱️</span>
          </div>
          <div class="card-content">
            <div class="card-title">首个落盘延迟</div>
            <div class="card-value blue">{{ formatSeconds(testMetrics?.latency?.first_output_latency_seconds ?? null) }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">⏱️</span>
          </div>
          <div class="card-content">
            <div class="card-title">平均落盘延迟</div>
            <div class="card-value blue">{{ formatSeconds(testMetrics?.latency?.avg_output_latency_seconds ?? null) }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">⏱️</span>
          </div>
          <div class="card-content">
            <div class="card-title">最新落盘延迟</div>
            <div class="card-value blue">{{ formatSeconds(testMetrics?.latency?.last_output_latency_seconds ?? null) }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
      </template>
      <template v-else>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">⏲️</span>
          </div>
          <div class="card-content">
            <div class="card-title">最近执行耗时</div>
            <div class="card-value blue">{{ formatSeconds(lastDurationSec) }}</div>
            <div class="card-sub">最近一次完成</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">📈</span>
          </div>
          <div class="card-content">
            <div class="card-title">平均执行耗时</div>
            <div class="card-value blue">{{ formatSeconds(avgDurationSec) }}</div>
            <div class="card-sub">{{ latestExecCount }} 次样本</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon task-icon">
            <span class="icon-task">📥</span>
          </div>
          <div class="card-content">
            <div class="card-title">吞吐量(文件/s)</div>
            <div class="card-value green">{{ throughputFilesPerSec.toFixed(2) }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon disk-icon">
            <span class="icon-disk">💾</span>
          </div>
          <div class="card-content">
            <div class="card-title">吞吐量(MB/s)</div>
            <div class="card-value orange">{{ throughputMbPerSec.toFixed(2) }}</div>
            <div class="card-sub">窗口 {{ timeWindow }}s</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon cpu-icon">
            <span class="icon-cpu">🔳</span>
          </div>
          <div class="card-content">
            <div class="card-title">CPU峰值(平均)</div>
            <div class="card-value green">{{ avgCpuPercent.toFixed(1) }}%</div>
            <div class="card-sub">近次执行</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon mem-icon">
            <span class="icon-mem">🧠</span>
          </div>
          <div class="card-content">
            <div class="card-title">内存峰值(平均)</div>
            <div class="card-value purple">{{ avgMemoryMb.toFixed(1) }} MB</div>
            <div class="card-sub">近次执行</div>
          </div>
        </div>
      </template>
    </div>

    <div class="charts-grid">
      <div class="card chart-card">
        <h3 class="chart-title">动态指标</h3>
        <div ref="dynamicChartRef" class="chart-container"></div>
      </div>
      <div class="card chart-card">
        <h3 class="chart-title">全程指标</h3>
        <div class="chart-controls">
          <div class="control-item">
            <label>测试类型</label>
            <select v-model="fullCategory" class="form-select form-select-sm">
              <option value="collection">采集效率测试</option>
              <option value="processing">数据处理速度测试</option>
            </select>
          </div>
          <div class="control-item">
            <label>指标</label>
            <select v-model="fullMetric" class="form-select form-select-sm">
              <template v-if="fullCategory === 'collection'">
                <option value="throughput_files">吞吐量(文件/s)</option>
                <option value="throughput_mb">吞吐量(MB/s)</option>
                <option value="max_cpu">CPU峰值(%)</option>
                <option value="max_memory">内存峰值(MB)</option>
              </template>
              <template v-else>
                <option value="duration">任务执行耗时(秒)</option>
                <option value="parse_time">文档解析耗时(秒)</option>
                <option value="index_time">索引构建耗时(秒)</option>
                <option value="api_time">API 查询耗时(秒)</option>
              </template>
            </select>
          </div>
        </div>
        <div class="chart-description">
          <div v-if="fullCategory === 'collection'">
            <div class="desc-title">采集效率测试</div>
            <div class="desc-text">单位时间采集数据量与资源占用，用于评估高负载下的稳定性与可靠性。</div>
          </div>
          <div v-else>
            <div class="desc-title">数据处理速度测试</div>
            <div class="desc-text">评估采集完成后各处理阶段的耗时，定位处理瓶颈。</div>
          </div>
        </div>
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
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

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
    parse_time: Array<{ label: string; value: number }>
    index_time: Array<{ label: string; value: number }>
    api_time: Array<{ label: string; value: number }>
  }
  evidence: {
    output_samples: Array<{ name: string; path: string; size: number; mtime: string }>
    log_files: Array<{ task_id: number; task_name: string; log_file?: string }>
  }
  latency: {
    first_output_latency_seconds?: number | null
    avg_output_latency_seconds?: number | null
    last_output_latency_seconds?: number | null
    sample_count: number
  }
}

// State
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
const fullCategory = ref<'collection' | 'processing'>('collection')
const fullMetric = ref<'throughput_files' | 'throughput_mb' | 'max_cpu' | 'max_memory' | 'duration' | 'parse_time' | 'index_time' | 'api_time'>('throughput_files')

const API_BASE = '/api'

// Computed
const peakCpuPercent = computed(() => {
  const values = (testMetrics.value?.latest_executions || [])
    .map(item => item.max_cpu_percent)
    .filter(value => typeof value === 'number') as number[]
  if (!values.length) return 0
  return Math.max(...values)
})

const peakMemoryMb = computed(() => {
  const values = (testMetrics.value?.latest_executions || [])
    .map(item => item.max_memory_mb)
    .filter(value => typeof value === 'number') as number[]
  if (!values.length) return 0
  return Math.max(...values)
})

const throughputFilesPerSec = computed(() => {
  const files = testMetrics.value?.output?.recent_files ?? 0
  const win = timeWindow.value || 1
  return files / win
})

const throughputMbPerSec = computed(() => {
  const bytes = testMetrics.value?.output?.recent_bytes ?? 0
  const win = timeWindow.value || 1
  return (bytes / 1024 / 1024) / win
})

const formatSeconds = (s?: number | null) => {
  if (s === null || s === undefined) return 'N/A'
  return `${s.toFixed(2)}s`
}

const latestExecCount = computed(() => (testMetrics.value?.latest_executions || []).length)
const avgDurationSec = computed(() => {
  const vals = (testMetrics.value?.latest_executions || [])
    .map(i => (typeof i.duration === 'number' ? i.duration : null))
    .filter((v): v is number => v !== null)
  if (!vals.length) return null
  const sum = vals.reduce((a, b) => a + b, 0)
  return sum / vals.length
})
const lastDurationSec = computed(() => {
  const items = (testMetrics.value?.latest_executions || [])
    .filter(i => typeof i.duration === 'number' && !!i.end_time)
    .sort((a, b) => {
      const ta = new Date(a.end_time || a.start_time || '').getTime()
      const tb = new Date(b.end_time || b.start_time || '').getTime()
      return tb - ta
    })
  return items.length ? (items[0].duration as number) : null
})
const avgCpuPercent = computed(() => {
  const vals = (testMetrics.value?.latest_executions || [])
    .map(i => (typeof i.max_cpu_percent === 'number' ? i.max_cpu_percent : null))
    .filter((v): v is number => v !== null)
  if (!vals.length) return 0
  const sum = vals.reduce((a, b) => a + b, 0)
  return sum / vals.length
})
const avgMemoryMb = computed(() => {
  const vals = (testMetrics.value?.latest_executions || [])
    .map(i => (typeof i.max_memory_mb === 'number' ? i.max_memory_mb : null))
    .filter((v): v is number => v !== null)
  if (!vals.length) return 0
  const sum = vals.reduce((a, b) => a + b, 0)
  return sum / vals.length
})
const windowSuccessRate = computed(() => {
  const success = testMetrics.value?.executions_window.success ?? 0
  const failed = testMetrics.value?.executions_window.failed ?? 0
  const total = success + failed
  if (!total) return 0
  return (success / total) * 100
})

// Methods
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

const isLoadingTasks = ref(false)

const fetchTestTasks = async () => {
  isLoadingTasks.value = true
  try {
    const res = await fetch(`${API_BASE}/tasks?limit=1000`)
    if (res.ok) {
      testTasks.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  } finally {
    isLoadingTasks.value = false
  }
}

const fetchTestMetrics = async () => {
  if (selectedTaskIds.value.length === 0) {
      testMetrics.value = null
      return
  }
  isLoadingMetrics.value = true
  try {
    const ids = selectedTaskIds.value.join(',')
    const url = `${API_BASE}/tasks/test-metrics/overview?task_ids=${encodeURIComponent(ids)}&window_seconds=${timeWindow.value}`
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
    } else {
        testMetrics.value = null
    }
  } catch (e) {
    console.error(e)
    testMetrics.value = null
  } finally {
    isLoadingMetrics.value = false
  }
}

const refreshTestMetrics = async () => {
  await fetchTestMetrics()
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const exportTestMetrics = async (format: 'json' | 'csv') => {
  if (selectedTaskIds.value.length === 0) return
  try {
    const params = new URLSearchParams()
    if (selectedTaskIds.value.length) {
      params.append('task_ids', selectedTaskIds.value.join(','))
    }
    params.append('window_seconds', String(timeWindow.value))
    params.append('format', format)
    const res = await fetch(`${API_BASE}/tasks/test-metrics/export?${params.toString()}`)
    if (!res.ok) {
      const err = await res.json()
      alert(`导出失败: ${err.detail || '未知错误'}`)
      return
    }
    const blob = await res.blob()
    const contentDisposition = res.headers.get('content-disposition') || ''
    const match = contentDisposition.match(/filename=([^;]+)/i)
    const filename = match ? match[1].replace(/"/g, '') : `test_metrics.${format}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    alert('导出失败')
  }
}

const runSelectedTasks = async () => {
  if (selectedTaskIds.value.length === 0) return
  isRunningTests.value = true
  try {
    const results = await Promise.all(
      selectedTaskIds.value.map(id => fetch(`${API_BASE}/tasks/${id}/run`, { method: 'POST' }))
    )
    for (const res of results) {
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || '任务启动失败')
      }
    }
    
    const pollInterval = 1000
    const maxPolls = 60
    
    for (let i = 0; i < maxPolls; i += 1) {
      await fetchTestMetrics()
      const running = testMetrics.value?.executions_window.running ?? 0
      
      if (running === 0 && i > 5) {
        break
      }
      await sleep(pollInterval)
    }
  } catch (e) {
    console.error(e)
    alert('任务启动失败')
  } finally {
    isRunningTests.value = false
  }
}

const startMetricsTimer = () => {
  if (metricsTimer.value) clearInterval(metricsTimer.value)
  metricsTimer.value = setInterval(() => {
    if (document.hidden) return
    if (selectedTaskIds.value.length > 0) {
      fetchTestMetrics()
    }
  }, Math.max(timeWindow.value * 1000, 1000)) as unknown as number
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
    legend: { data: ['新增文件', '新增体积(MB)'], top: 6, right: 12, itemGap: 12, textStyle: { fontSize: 12 } },
    grid: { left: '3%', right: '4%', top: 56, bottom: 28, containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { color: '#666', margin: 12 } },
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
  if (!fullChartRef.value) return
  if (fullChartInstance) {
    fullChartInstance.dispose()
  }
  fullChartInstance = echarts.init(fullChartRef.value)
  const metricKey = fullMetric.value
  const isCollection = fullCategory.value === 'collection'
  const hasTestMetrics = Boolean(testMetrics.value)
  const labels = isCollection
    ? dynamicHistory.value.map(p => p.label)
    : hasTestMetrics
    ? testMetrics.value!.timeseries.duration.map(p => p.label)
    : []
  const seriesName =
    metricKey === 'throughput_files'
      ? '吞吐量(文件/s)'
      : metricKey === 'throughput_mb'
      ? '吞吐量(MB/s)'
      : metricKey === 'max_cpu'
      ? 'CPU峰值(%)'
      : metricKey === 'max_memory'
      ? '内存峰值(MB)'
      : metricKey === 'duration'
      ? '任务执行耗时(秒)'
      : metricKey === 'parse_time'
      ? '文档解析耗时(秒)'
      : metricKey === 'index_time'
      ? '索引构建耗时(秒)'
      : 'API 查询耗时(秒)'
  let data: number[] = []
  if (metricKey === 'throughput_files') {
    const win = timeWindow.value || 1
    data = dynamicHistory.value.map(p => p.files / win)
  } else if (metricKey === 'throughput_mb') {
    const win = timeWindow.value || 1
    data = dynamicHistory.value.map(p => (p.bytes / 1024 / 1024) / win)
  } else if (metricKey === 'max_cpu' && hasTestMetrics) {
    data = testMetrics.value!.timeseries.max_cpu.map(p => p.value)
  } else if (metricKey === 'max_memory' && hasTestMetrics) {
    data = testMetrics.value!.timeseries.max_memory.map(p => p.value)
  } else if (metricKey === 'duration' && hasTestMetrics) {
    data = testMetrics.value!.timeseries.duration.map(p => p.value)
  } else if (metricKey === 'parse_time' && hasTestMetrics) {
    data = testMetrics.value!.timeseries.parse_time.map(p => p.value)
  } else if (metricKey === 'index_time' && hasTestMetrics) {
    data = testMetrics.value!.timeseries.index_time.map(p => p.value)
  } else if (metricKey === 'api_time' && hasTestMetrics) {
    data = testMetrics.value!.timeseries.api_time.map(p => p.value)
  }
  const color =
    metricKey === 'throughput_files'
      ? '#52c41a'
      : metricKey === 'throughput_mb'
      ? '#faad14'
      : metricKey === 'max_cpu'
      ? '#faad14'
      : metricKey === 'max_memory'
      ? '#722ed1'
      : '#1890ff'
  const type = ['duration', 'parse_time', 'index_time', 'api_time'].includes(metricKey) ? 'bar' : 'line'
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: [seriesName], top: 6, right: 12, itemGap: 12, textStyle: { fontSize: 12 } },
    grid: { left: '3%', right: '4%', top: 56, bottom: 28, containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { color: '#666', margin: 12 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{ name: seriesName, type, data, smooth: type === 'line', itemStyle: { color } }]
  }
  fullChartInstance.setOption(option)
}

const handleResize = () => {
    dynamicChartInstance?.resize()
    fullChartInstance?.resize()
}

// Watchers
watch(selectedTaskIds, async () => {
  dynamicHistory.value = []
  if (selectedTaskIds.value.length > 0) {
      await fetchTestMetrics()
      startMetricsTimer()
  } else {
      testMetrics.value = null
      if (metricsTimer.value) clearInterval(metricsTimer.value)
  }
})

watch(timeWindow, () => {
  dynamicHistory.value = []
  startMetricsTimer()
  fetchTestMetrics()
})

watch(fullCategory, () => {
  fullMetric.value = fullCategory.value === 'collection' ? 'throughput_files' : 'duration'
  initFullChart()
})
watch(fullMetric, () => {
  initFullChart()
})

// Lifecycle
onMounted(() => {
  fetchTestTasks()
  window.addEventListener('resize', handleResize)
  
  // Start if tasks are pre-selected (unlikely on fresh load but good practice)
  if (selectedTaskIds.value.length > 0) {
      startMetricsTimer()
  }
})

onUnmounted(() => {
    if (metricsTimer.value) clearInterval(metricsTimer.value)
    window.removeEventListener('resize', handleResize)
    dynamicChartInstance?.dispose()
    fullChartInstance?.dispose()
})
</script>

<style scoped>
@import '@/styles/dashboard.css';

/* Reuse styles from Dashboard.vue */
.test-section {
    display: flex;
    flex-direction: column;
    gap: 28px;
}

/* Note: .card is imported from dashboard.css, but we can override padding if needed */
.test-control-card {
    padding: 20px;
}

.test-control-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px 20px;
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
    align-items: flex-start;
    margin-top: 18px;
    gap: 12px 16px;
    flex-wrap: wrap;
}

.action-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.output-hint {
    font-size: 12px;
    color: #777;
    max-width: 100%;
    line-height: 1.4;
    white-space: normal;
}

.test-overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
}

/* .overview-card, .card-icon, etc are in dashboard.css */

.chart-controls {
    display: flex;
    gap: 16px;
    align-items: center;
    margin-bottom: 10px;
}

.chart-controls .control-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.chart-controls label {
    font-size: 13px;
    color: #666;
}

.form-select-sm {
    height: 32px;
}

.chart-description {
    background: #fafafa;
    border: 1px solid #f0f0f0;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 12px;
}

.desc-title {
    font-size: 13px;
    font-weight: 600;
    color: #333;
}

.desc-text {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
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
    .test-overview-grid, .charts-grid, .evidence-grid {
        grid-template-columns: 1fr;
    }
}
</style>
