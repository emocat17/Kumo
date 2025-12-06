<template>
  <div class="dashboard">
    <!-- Dashboard Header -->
    <div class="dashboard-header">
      <div>
        <h1 class="page-title">监控面板</h1>
        <p class="page-subtitle">实时系统监控</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary">禁用自动刷新</button>
        <select class="select-input">
          <option>10s</option>
          <option selected>30s</option>
          <option>1m</option>
          <option>5m</option>
        </select>
        <button class="btn btn-primary">刷新</button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button 
        v-for="tab in tabs" 
        :key="tab"
        :class="['tab-item', { active: currentTab === tab }]"
        @click="currentTab = tab"
      >
        {{ tab }}
      </button>
    </div>

    <!-- Content Grid -->
    <div class="dashboard-content" v-if="currentTab === '系统概览'">
      <!-- Row 1: Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon icon-blue">
            <!-- Icon Placeholder -->
          </div>
          <div class="stat-info">
            <div class="stat-value">0</div>
            <div class="stat-label">总任务数</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon icon-green"></div>
          <div class="stat-info">
            <div class="stat-value">0</div>
            <div class="stat-label">活跃任务</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon icon-purple"></div>
          <div class="stat-info">
            <div class="stat-value">0</div>
            <div class="stat-label">环境</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon icon-orange"></div>
          <div class="stat-info">
            <div class="stat-value">0</div>
            <div class="stat-label">项目</div>
          </div>
        </div>
      </div>

      <!-- Row 2: Detailed Info -->
      <div class="details-grid">
        <!-- Worker Nodes -->
        <div class="card">
          <div class="card-header">
            <h3>工作节点</h3>
          </div>
          <div class="card-body centered">
             <div class="status-text">
               <span class="status-value">0 / 0</span>
               <span class="status-label">连接中</span>
             </div>
          </div>
        </div>

        <!-- System Uptime -->
        <div class="card">
          <div class="card-header">
            <h3>系统运行时间</h3>
          </div>
          <div class="card-body centered">
            <div class="uptime-value">0天 0小时</div>
          </div>
        </div>

        <!-- 24h Stats -->
        <div class="card">
          <div class="card-header">
            <h3>过去24小时</h3>
          </div>
          <div class="card-body">
            <div class="stat-row">
              <span>执行次数</span>
              <span class="font-medium">0</span>
            </div>
            <div class="stat-row">
              <span>成功</span>
              <span class="font-medium">0</span>
            </div>
            <div class="stat-row">
              <span>成功率</span>
              <span class="font-medium">0%</span>
            </div>
          </div>
        </div>

        <!-- System Info -->
        <div class="card">
          <div class="card-header">
            <h3>系统信息</h3>
          </div>
          <div class="card-body info-list">
            <div class="info-item">
              <span class="label">ID:</span>
              <span class="value">93e8235f550f</span>
            </div>
            <div class="info-item">
              <span class="label">平台:</span>
              <span class="value">Linux-6.6.87.2...</span>
            </div>
            <div class="info-item">
              <span class="label">架构:</span>
              <span class="value">64bit</span>
            </div>
            <div class="info-item">
              <span class="label">Python:</span>
              <span class="value">3.9.21</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <p>暂无数据</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const tabs = ['系统概览', '性能指标', '任务统计', '工作节点', '指标图表']
const currentTab = ref('系统概览')
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.page-subtitle {
  color: #6b7280;
  margin-top: 4px;
  font-size: 0.875rem;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-secondary {
  background-color: #ffffff;
  border-color: #d1d5db;
  color: #374151;
}

.btn-primary {
  background-color: #3b82f6;
  color: #ffffff;
}

.select-input {
  padding: 8px 32px 8px 12px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background-color: #ffffff;
  font-size: 0.875rem;
  color: #374151;
}

/* Tabs */
.tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 24px;
}

.tab-item {
  padding: 12px 24px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #6b7280;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.tab-item.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}

.stat-card {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  margin-right: 16px;
  background-color: #eff6ff;
}

.icon-blue { background-color: #eff6ff; }
.icon-green { background-color: #f0fdf4; }
.icon-purple { background-color: #faf5ff; }
.icon-orange { background-color: #fff7ed; }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
}

.stat-label {
  color: #6b7280;
  font-size: 0.875rem;
}

/* Details Grid */
.details-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.card {
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  padding: 16px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.card-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.card-body {
  padding: 24px;
}

.card-body.centered {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 120px;
}

.status-text {
  text-align: center;
}

.status-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
}

.status-label {
  color: #6b7280;
  font-size: 0.875rem;
}

.uptime-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  color: #374151;
}

.stat-row:last-child {
  border-bottom: none;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  font-size: 0.875rem;
}

.info-item .label {
  color: #6b7280;
  width: 60px;
  flex-shrink: 0;
}

.info-item .value {
  color: #111827;
  font-family: monospace;
}

.empty-state {
  padding: 48px;
  text-align: center;
  color: #6b7280;
}
</style>
