# 前端服务模块说明

## 健康检查服务 (healthCheck.ts)

定期检查后端API健康状态，并在异常时触发恢复机制。

### 使用方式

```typescript
import { healthCheckService } from '@/services/healthCheck'

// 启动健康检查（每10秒检查一次）
healthCheckService.start(10000)

// 监听健康状态变化
const unsubscribe = healthCheckService.onStatusChange((status) => {
  console.log('健康状态:', status.status)
  if (status.status === 'unhealthy') {
    // 处理不健康状态
  }
})

// 停止健康检查
healthCheckService.stop()

// 手动检查一次
const status = await healthCheckService.checkHealth()
```

### 健康状态类型

- `healthy`: 系统健康
- `unhealthy`: 系统不健康（连续失败达到阈值）
- `checking`: 正在检查中
- `unknown`: 未知状态（初始状态）

## API 服务 (api.ts)

统一的API调用封装，提供错误处理、重试机制和超时控制。

### 使用方式

```typescript
import { apiService } from '@/services/api'

// GET 请求
const data = await apiService.get('/tasks/dashboard/stats')

// POST 请求
const result = await apiService.post('/tasks', {
  name: '任务名称',
  command: 'python script.py'
})

// 带重试和超时的请求
const result = await apiService.get('/some-endpoint', {
  timeout: 5000,      // 5秒超时
  retries: 3,         // 重试3次
  retryDelay: 1000    // 每次重试延迟1秒
})
```

### 错误处理

```typescript
try {
  const data = await apiService.get('/endpoint')
} catch (error) {
  if (error.code === 'TIMEOUT') {
    console.error('请求超时')
  } else if (error.code === 'NETWORK_ERROR') {
    console.error('网络错误')
  } else {
    console.error('其他错误:', error.message)
  }
}
```

## 自动恢复服务 (autoRecovery.ts)

检测到系统异常时，自动执行恢复操作（如刷新页面）。

### 使用方式

```typescript
import { autoRecoveryService } from '@/services/autoRecovery'

// 启动自动恢复服务
autoRecoveryService.start({
  enabled: true,
  maxUnhealthyDuration: 30000,  // 系统不健康超过30秒后触发恢复
  autoReload: true,              // 自动刷新页面
  reloadDelay: 5000,             // 刷新前延迟5秒
  onBeforeReload: () => {
    console.log('准备刷新页面...')
  }
})

// 停止自动恢复服务
autoRecoveryService.stop()

// 手动触发恢复
autoRecoveryService.manualReload()
```

## 集成说明

这些服务已经在 `App.vue` 中自动启动，无需手动初始化。健康检查通知组件 `HealthNotification.vue` 会自动显示系统状态。

### 配置建议

- **开发环境**: 健康检查间隔可以设置为 10-15 秒
- **生产环境**: 健康检查间隔可以设置为 30-60 秒
- **自动恢复**: 建议设置 `maxUnhealthyDuration` 为 30-60 秒，避免频繁刷新
