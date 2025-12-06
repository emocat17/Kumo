<template>
  <div class="dashboard-page">
    <PageHeader title="仪表盘" description="查看系统运行状态和性能监控。" />

    <!-- System Overview -->
    <section class="section">
      <h3 class="section-title">系统概览</h3>
      <div class="overview-grid">
        <div class="card overview-card">
          <div class="card-icon env-icon">🐍</div>
          <div class="card-content">
            <div class="card-value">{{ systemInfo.env_count || 0 }}</div>
            <div class="card-label">Python 环境</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon project-icon">📂</div>
          <div class="card-content">
            <div class="card-value">{{ systemInfo.project_count || 0 }}</div>
            <div class="card-label">项目总数</div>
          </div>
        </div>
        <div class="card overview-card">
          <div class="card-icon time-icon">⏱️</div>
          <div class="card-content">
            <div class="card-value">{{ systemInfo.uptime_minutes || 0 }} <span class="unit">分</span></div>
            <div class="card-label">系统运行时间</div>
          </div>
        </div>
        <div class="card info-card">
           <div class="info-row">
              <span class="info-label">平台:</span>
              <span class="info-value">{{ systemInfo.system_info?.system }} {{ systemInfo.system_info?.release }}</span>
           </div>
           <div class="info-row">
              <span class="info-label">架构:</span>
              <span class="info-value">{{ systemInfo.system_info?.machine }}</span>
           </div>
           <div class="info-row">
              <span class="info-label">处理器:</span>
              <span class="info-value" :title="systemInfo.system_info?.processor">{{ formatProcessor(systemInfo.system_info?.processor) }}</span>
           </div>
           <div class="info-row">
              <span class="info-label">Python:</span>
              <span class="info-value">{{ systemInfo.system_info?.python_version }}</span>
           </div>
        </div>
      </div>
    </section>

    <!-- Performance Monitor -->
    <section class="section">
      <h3 class="section-title">性能配置</h3>
      <div class="perf-grid">
        <!-- CPU -->
        <div class="card perf-card">
           <div class="perf-header">
              <div class="perf-icon cpu-icon">🔳</div>
              <div class="perf-title">
                 <h4>CPU 性能</h4>
                 <span class="subtitle">{{ systemStats.cpu?.cores }} 核心 / {{ systemStats.cpu?.threads }} 线程</span>
              </div>
           </div>
           <div class="perf-stats">
              <div class="stat-item">
                 <div class="stat-value blue">{{ systemStats.cpu?.percent }}%</div>
                 <div class="stat-label">平均使用率</div>
              </div>
              <div class="stat-item">
                 <div class="stat-value green">{{ systemStats.cpu?.freq_current }}</div>
                 <div class="stat-label">频率</div>
              </div>
           </div>
           <div class="cpu-cores">
              <div class="core-label">每核使用率</div>
              <div class="cores-grid">
                 <div v-for="(usage, index) in systemStats.cpu?.per_cpu" :key="index" class="core-item">
                    <div class="core-bar-bg">
                       <div class="core-bar" :style="{ width: usage + '%', backgroundColor: getUsageColor(usage) }"></div>
                    </div>
                    <div class="core-text">Core {{ index + 1 }}: {{ usage }}%</div>
                 </div>
              </div>
           </div>
        </div>

        <!-- Memory -->
        <div class="card perf-card">
           <div class="perf-header">
              <div class="perf-icon mem-icon">🧠</div>
              <div class="perf-title">
                 <h4>内存性能</h4>
                 <span class="subtitle">{{ systemStats.memory?.total }} 总内存</span>
              </div>
           </div>
           <div class="perf-stats">
              <div class="stat-item">
                 <div class="stat-value green">{{ systemStats.memory?.percent }}%</div>
                 <div class="stat-label">已使用</div>
              </div>
              <div class="stat-item">
                 <div class="stat-value blue">{{ systemStats.memory?.available }}</div>
                 <div class="stat-label">可用</div>
              </div>
           </div>
           <div class="progress-section">
              <div class="progress-label">
                  <span>物理内存</span>
                  <span>{{ systemStats.memory?.used }} / {{ systemStats.memory?.total }}</span>
              </div>
              <div class="progress-bar-bg">
                  <div class="progress-bar" :style="{ width: systemStats.memory?.percent + '%', backgroundColor: getUsageColor(systemStats.memory?.percent) }"></div>
              </div>
           </div>
           <div class="progress-section">
              <div class="progress-label">
                  <span>交换空间</span>
                  <span>{{ systemStats.memory?.swap_used }} / {{ systemStats.memory?.swap_total }}</span>
              </div>
              <div class="progress-bar-bg">
                  <div class="progress-bar" :style="{ width: systemStats.memory?.swap_percent + '%', backgroundColor: getUsageColor(systemStats.memory?.swap_percent) }"></div>
              </div>
           </div>
        </div>

        <!-- Disk -->
        <div class="card perf-card">
           <div class="perf-header">
              <div class="perf-icon disk-icon">💾</div>
              <div class="perf-title">
                 <h4>磁盘性能</h4>
                 <span class="subtitle">{{ systemStats.disk?.partitions?.length }} 分区</span>
              </div>
           </div>
           <div class="disk-list">
               <div v-for="disk in systemStats.disk?.partitions" :key="disk.mountpoint" class="disk-item">
                   <div class="disk-info">
                       <span class="mountpoint">{{ disk.mountpoint }}</span>
                       <span class="usage-text">{{ disk.percent }}% ({{ disk.used }} / {{ disk.total }})</span>
                   </div>
                   <div class="progress-bar-bg">
                       <div class="progress-bar" :style="{ width: disk.percent + '%', backgroundColor: getUsageColor(disk.percent) }"></div>
                   </div>
               </div>
           </div>
           <div class="perf-stats mt-4">
              <div class="stat-item">
                 <div class="stat-value blue">{{ systemStats.disk?.read_bytes }}</div>
                 <div class="stat-label">总读取</div>
              </div>
              <div class="stat-item">
                 <div class="stat-value green">{{ systemStats.disk?.write_bytes }}</div>
                 <div class="stat-label">总写入</div>
              </div>
           </div>
        </div>

        <!-- Network -->
        <div class="card perf-card">
           <div class="perf-header">
              <div class="perf-icon net-icon">📡</div>
              <div class="perf-title">
                 <h4>网络性能</h4>
                 <span class="subtitle">总流量</span>
              </div>
           </div>
           <div class="perf-stats">
              <div class="stat-item">
                 <div class="stat-value blue">{{ systemStats.network?.bytes_recv }}</div>
                 <div class="stat-label">接收</div>
              </div>
              <div class="stat-item">
                 <div class="stat-value green">{{ systemStats.network?.bytes_sent }}</div>
                 <div class="stat-label">发送</div>
              </div>
           </div>
           <div class="perf-stats mt-2">
              <div class="stat-item">
                 <div class="stat-value purple">{{ systemStats.network?.packets_recv }}</div>
                 <div class="stat-label">接收数据包</div>
              </div>
              <div class="stat-item">
                 <div class="stat-value orange">{{ systemStats.network?.packets_sent }}</div>
                 <div class="stat-label">发送数据包</div>
              </div>
           </div>
        </div>

      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'

interface SystemInfo {
  env_count: number
  project_count: number
  uptime_minutes: number
  system_info: Record<string, string | number>
}

interface SystemStats {
  cpu: { percent: number; count: number }
  memory: { percent: number; total: string; used: string }
  disk: { percent: number; total: string; used: string }
  network: { bytes_sent: string; bytes_recv: string }
}

const systemInfo = ref<SystemInfo>({} as SystemInfo)
const systemStats = ref<SystemStats>({} as SystemStats)
const timer = ref<number | null>(null)

const API_BASE = 'http://localhost:8000/api/system'

const fetchSystemInfo = async () => {
  try {
    const res = await fetch(`${API_BASE}/info`)
    if (res.ok) {
      systemInfo.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchSystemStats = async () => {
  try {
    const res = await fetch(`${API_BASE}/stats`)
    if (res.ok) {
      systemStats.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
}

const formatProcessor = (proc: string) => {
    if (!proc) return 'Unknown'
    // Simplify processor name if too long
    return proc.split(' ')[0] + '...' 
}

const getUsageColor = (percent: number) => {
    if (percent < 50) return '#52c41a' // Green
    if (percent < 80) return '#faad14' // Orange
    return '#ff4d4f' // Red
}

onMounted(() => {
  fetchSystemInfo()
  fetchSystemStats()
  
  // Refresh stats every 3 seconds
  timer.value = setInterval(() => {
      fetchSystemInfo() // Also update uptime
      fetchSystemStats()
  }, 3000) as unknown as number
})

onUnmounted(() => {
    if (timer.value) clearInterval(timer.value)
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-title {
    font-size: 18px;
    font-weight: 600;
    color: #333;
    margin-bottom: 16px;
    padding-left: 8px;
    border-left: 4px solid #1890ff;
}

/* Overview Grid */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border: 1px solid #f0f0f0;
  transition: transform 0.2s;
}
.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.overview-card {
    display: flex;
    align-items: center;
    gap: 20px;
}

.card-icon {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
}
.env-icon { background-color: #e6f7ff; color: #1890ff; }
.project-icon { background-color: #fff7e6; color: #fa8c16; }
.time-icon { background-color: #f6ffed; color: #52c41a; }

.card-content {
    flex: 1;
}
.card-value {
    font-size: 24px;
    font-weight: bold;
    color: #1f1f1f;
    line-height: 1.2;
}
.card-value .unit {
    font-size: 14px;
    font-weight: normal;
    color: #888;
}
.card-label {
    font-size: 13px;
    color: #888;
    margin-top: 4px;
}

.info-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 8px;
}
.info-row {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
}
.info-label { color: #888; }
.info-value { color: #333; font-weight: 500; max-width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Performance Grid */
.perf-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 20px;
}

.perf-card {
    display: flex;
    flex-direction: column;
}

.perf-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
}

.perf-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}
.cpu-icon { background-color: #e6f7ff; color: #1890ff; }
.mem-icon { background-color: #f6ffed; color: #52c41a; }
.disk-icon { background-color: #fff0f6; color: #eb2f96; }
.net-icon { background-color: #f0f5ff; color: #2f54eb; }

.perf-title h4 {
    margin: 0;
    font-size: 16px;
    color: #333;
}
.perf-title .subtitle {
    font-size: 12px;
    color: #999;
}

.perf-stats {
    display: flex;
    justify-content: space-around;
    margin-bottom: 16px;
}

.stat-item {
    text-align: center;
}
.stat-value {
    font-size: 18px;
    font-weight: bold;
}
.stat-label {
    font-size: 12px;
    color: #888;
}

.blue { color: #1890ff; }
.green { color: #52c41a; }
.purple { color: #722ed1; }
.orange { color: #fa8c16; }

.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }

/* Progress Bars */
.progress-section {
    margin-bottom: 12px;
}
.progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #666;
    margin-bottom: 4px;
}
.progress-bar-bg {
    height: 8px;
    background-color: #f5f5f5;
    border-radius: 4px;
    overflow: hidden;
}
.progress-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}

/* CPU Cores */
.cpu-cores {
    margin-top: auto;
}
.core-label {
    font-size: 12px;
    color: #888;
    margin-bottom: 8px;
}
.cores-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 8px;
}
.core-item {
    text-align: center;
}
.core-bar-bg {
    height: 4px;
    background-color: #f5f5f5;
    border-radius: 2px;
    margin-bottom: 2px;
    overflow: hidden;
}
.core-bar {
    height: 100%;
    transition: width 0.3s;
}
.core-text {
    font-size: 10px;
    color: #999;
}

/* Disk List */
.disk-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 150px;
    overflow-y: auto;
}
.disk-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.disk-info {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
}
.mountpoint { font-weight: 500; color: #333; }
.usage-text { color: #888; }

/* Responsive */
@media (max-width: 768px) {
    .perf-grid {
        grid-template-columns: 1fr;
    }
}
</style>
