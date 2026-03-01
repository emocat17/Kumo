<template>
  <Transition name="slide-down">
    <div v-if="visible" :class="['health-notification', `health-${status}`]">
      <div class="notification-content">
        <div class="notification-icon">
          <AlertCircle v-if="status === 'unhealthy'" />
          <CheckCircle v-else-if="status === 'healthy'" />
          <Loader2 v-else class="spinning" />
        </div>
        <div class="notification-text">
          <div class="notification-title">{{ title }}</div>
          <div v-if="message" class="notification-message">{{ message }}</div>
        </div>
        <div class="notification-actions">
          <button v-if="showReload" @click="handleReload" class="reload-btn">
            刷新页面
          </button>
          <button @click="dismiss" class="dismiss-btn">×</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-vue-next'
import { healthCheckService, type HealthStatus } from '@/services/healthCheck'

const visible = ref(false)
const status = ref<'healthy' | 'unhealthy' | 'checking'>('checking')
const title = ref('')
const message = ref('')
const showReload = ref(false)
const autoDismissTimer = ref<number | null>(null)

const unsubscribe = ref<(() => void) | null>(null)

const updateNotification = (healthStatus: HealthStatus) => {
  status.value = healthStatus.status === 'unknown' ? 'checking' : healthStatus.status
  
  if (healthStatus.status === 'unhealthy') {
    visible.value = true
    showReload.value = true
    
    // 构建错误消息
    const parts: string[] = []
    if (healthStatus.database !== 'connected') {
      parts.push(`数据库: ${healthStatus.database}`)
    }
    if (healthStatus.scheduler !== 'running') {
      parts.push(`调度器: ${healthStatus.scheduler}`)
    }
    if (healthStatus.errorMessage) {
      parts.push(healthStatus.errorMessage)
    }
    
    title.value = '系统状态异常'
    message.value = parts.length > 0 
      ? parts.join(' | ') 
      : `连续失败 ${healthStatus.consecutiveFailures} 次`
    
    // 不自动关闭异常通知
    if (autoDismissTimer.value) {
      clearTimeout(autoDismissTimer.value)
      autoDismissTimer.value = null
    }
  } else if (healthStatus.status === 'healthy') {
    // 如果之前是不健康状态，显示恢复通知
    if (visible.value && status.value === 'unhealthy') {
      title.value = '系统已恢复'
      message.value = '后端服务已恢复正常'
      showReload.value = false
      
      // 3秒后自动关闭
      if (autoDismissTimer.value) {
        clearTimeout(autoDismissTimer.value)
      }
      autoDismissTimer.value = window.setTimeout(() => {
        visible.value = false
      }, 3000)
    } else {
      // 健康状态不显示通知（除非手动触发）
      visible.value = false
    }
  } else {
    // checking状态，短暂显示
    if (!visible.value) {
      visible.value = true
      title.value = '检查系统状态...'
      message.value = ''
      showReload.value = false
    }
  }
}

const handleReload = () => {
  window.location.reload()
}

const dismiss = () => {
  visible.value = false
  if (autoDismissTimer.value) {
    clearTimeout(autoDismissTimer.value)
    autoDismissTimer.value = null
  }
}

onMounted(() => {
  unsubscribe.value = healthCheckService.onStatusChange(updateNotification)
})

onUnmounted(() => {
  if (unsubscribe.value) {
    unsubscribe.value()
  }
  if (autoDismissTimer.value) {
    clearTimeout(autoDismissTimer.value)
  }
})
</script>

<style scoped>
.health-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  min-width: 360px;
  max-width: 500px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 4px solid;
  animation: slideIn 0.3s ease-out;
}

.health-healthy {
  border-left-color: #52c41a;
}

.health-unhealthy {
  border-left-color: #ff4d4f;
}

.health-checking {
  border-left-color: #1890ff;
}

.notification-content {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  gap: 12px;
}

.notification-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  margin-top: 2px;
}

.notification-icon svg {
  width: 100%;
  height: 100%;
}

.health-healthy .notification-icon {
  color: #52c41a;
}

.health-unhealthy .notification-icon {
  color: #ff4d4f;
}

.health-checking .notification-icon {
  color: #1890ff;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.notification-text {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 600;
  font-size: 14px;
  color: #262626;
  margin-bottom: 4px;
}

.notification-message {
  font-size: 13px;
  color: #595959;
  line-height: 1.5;
  word-break: break-word;
}

.notification-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.reload-btn {
  padding: 4px 12px;
  font-size: 12px;
  color: white;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.reload-btn:hover {
  background: #40a9ff;
}

.dismiss-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #8c8c8c;
  background: none;
  border: none;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
  line-height: 1;
}

.dismiss-btn:hover {
  background: #f5f5f5;
  color: #262626;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease-out;
}

.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
