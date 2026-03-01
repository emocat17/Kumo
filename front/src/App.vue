<template>
  <router-view />
  <HealthNotification />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import HealthNotification from '@/components/common/HealthNotification.vue'
import { healthCheckService } from '@/services/healthCheck'
import { autoRecoveryService } from '@/services/autoRecovery'

// 启动健康检查和自动恢复
onMounted(() => {
  // 启动健康检查（每10秒检查一次）
  healthCheckService.start(10000)

  // 启动自动恢复服务
  // 配置：系统不健康超过30秒后，自动刷新页面
  autoRecoveryService.start({
    enabled: true,
    maxUnhealthyDuration: 30000, // 30秒
    autoReload: true,
    reloadDelay: 5000, // 5秒延迟后刷新
    onBeforeReload: () => {
      console.log('[App] 准备自动刷新页面...')
    }
  })
})

onUnmounted(() => {
  healthCheckService.stop()
  autoRecoveryService.stop()
})
</script>

<style>
body {
  margin: 0;
  padding: 0;
  background-color: #f3f4f6;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  zoom: 1.1; /* Scale up content by ~25-50% based on request */
  overflow: hidden; /* Prevent outer scrollbar when zoom is applied */
}

*, *::before, *::after {
  box-sizing: border-box;
}
</style>

