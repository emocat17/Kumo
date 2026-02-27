<template>
  <section class="section perf-section">
    <!-- CPU Performance -->
    <div class="card perf-panel">
      <div class="panel-header">
        <div class="perf-icon cpu-icon">
          <CpuIcon :size="24" />
        </div>
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
        <div class="perf-icon mem-icon">
          <MemoryStickIcon :size="24" />
        </div>
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
          <div class="perf-icon disk-icon">
            <HardDriveIcon :size="24" />
          </div>
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
          <div class="perf-icon net-icon">
            <NetworkIcon :size="24" />
          </div>
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
              <ActivityIcon :size="16" class="icon-pid" />
              <span>活跃进程: </span>
              <span class="pid-val">{{ systemStats.network?.pids }}</span>
          </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { CpuIcon, MemoryStickIcon, HardDriveIcon, NetworkIcon, ActivityIcon } from 'lucide-vue-next'

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

defineProps<{
  systemStats: SystemStats
}>()

const getUsageColor = (percent: number) => {
    if (percent < 50) return '#52c41a' // Green
    if (percent < 80) return '#faad14' // Orange
    return '#ff4d4f' // Red
}
</script>

<style scoped>
@import '@/styles/dashboard.css';

.perf-section {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

/* .card is in dashboard.css */

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

.perf-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    flex-shrink: 0;
}
/* Colors for icons - reuse logic or keep specific if slightly different shade */
.cpu-icon { background-color: #e6f7ff; color: #1890ff; }
.mem-icon { background-color: #f6ffed; color: #52c41a; }
.disk-icon { background-color: #f9f0ff; color: #722ed1; }
.net-icon { background-color: #f0f5ff; color: #2f54eb; }

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

/* Colors - reused from dashboard.css where possible */
/* .blue, .green, .purple, .orange are in dashboard.css */

.blue-bg { background-color: #1890ff; }
.green-bg { background-color: #52c41a; }
.purple-bg { background-color: #722ed1; }
.orange-bg { background-color: #fa8c16; }

.bg-light-blue { background-color: #e6f7ff; }
.bg-light-green { background-color: #f6ffed; }

.two-col { grid-template-columns: 1fr 1fr; }
.mt-3 { margin-top: 12px; }

@media (max-width: 768px) {
    .bottom-grid, .perf-row-stats {
        grid-template-columns: 1fr;
    }
}
</style>
