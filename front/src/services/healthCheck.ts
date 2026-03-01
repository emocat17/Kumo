/**
 * 健康检查服务
 * 定期检查后端API健康状态，并在异常时触发恢复机制
 */

export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'checking' | 'unknown'
  database: string
  scheduler: string
  connection_pool?: {
    size: number
    checked_in: number
    checked_out: number
    overflow: number
    invalid: number
  }
  lastCheck?: number
  consecutiveFailures: number
  errorMessage?: string
}

export type HealthCheckCallback = (status: HealthStatus) => void

class HealthCheckService {
  private checkInterval: number | null = null
  private checkIntervalMs: number = 10000 // 默认10秒检查一次
  private consecutiveFailures: number = 0
  private maxFailures: number = 3 // 连续失败3次后认为不健康
  private callbacks: Set<HealthCheckCallback> = new Set()
  private currentStatus: HealthStatus = {
    status: 'unknown',
    database: 'unknown',
    scheduler: 'unknown',
    consecutiveFailures: 0
  }
  private isChecking: boolean = false

  /**
   * 启动健康检查
   */
  start(intervalMs: number = 10000) {
    if (this.checkInterval) {
      this.stop()
    }
    this.checkIntervalMs = intervalMs
    // 立即执行一次检查
    this.checkHealth()
    // 然后定期检查
    this.checkInterval = window.setInterval(() => {
      this.checkHealth()
    }, intervalMs)
  }

  /**
   * 停止健康检查
   */
  stop() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
  }

  /**
   * 执行健康检查
   */
  async checkHealth(): Promise<HealthStatus> {
    // 防止并发检查
    if (this.isChecking) {
      return this.currentStatus
    }

    this.isChecking = true
    this.currentStatus.status = 'checking'

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5秒超时

      const response = await fetch('/api/health', {
        signal: controller.signal,
        cache: 'no-cache'
      })

      clearTimeout(timeoutId)

      if (response.ok) {
        const data = await response.json()
        this.currentStatus = {
          status: data.status === 'healthy' ? 'healthy' : 'unhealthy',
          database: data.database || 'unknown',
          scheduler: data.scheduler || 'unknown',
          connection_pool: data.connection_pool,
          lastCheck: Date.now(),
          consecutiveFailures: 0,
          errorMessage: undefined
        }
        this.consecutiveFailures = 0
      } else {
        // HTTP错误
        this.consecutiveFailures++
        this.currentStatus = {
          status: this.consecutiveFailures >= this.maxFailures ? 'unhealthy' : 'healthy',
          database: 'unknown',
          scheduler: 'unknown',
          lastCheck: Date.now(),
          consecutiveFailures: this.consecutiveFailures,
          errorMessage: `HTTP ${response.status}: ${response.statusText}`
        }
      }
    } catch (error) {
      // 网络错误或其他异常
      this.consecutiveFailures++
      const errorMessage = error instanceof Error ? error.message : String(error)
      const isUnhealthy = this.consecutiveFailures >= this.maxFailures

      this.currentStatus = {
        status: isUnhealthy ? 'unhealthy' : 'healthy',
        database: 'unknown',
        scheduler: 'unknown',
        lastCheck: Date.now(),
        consecutiveFailures: this.consecutiveFailures,
        errorMessage: errorMessage.includes('aborted') ? '请求超时' : errorMessage
      }
    } finally {
      this.isChecking = false
      // 通知所有监听者
      this.notifyCallbacks()
    }

    return this.currentStatus
  }

  /**
   * 获取当前健康状态
   */
  getStatus(): HealthStatus {
    return { ...this.currentStatus }
  }

  /**
   * 注册健康状态变化回调
   */
  onStatusChange(callback: HealthCheckCallback) {
    this.callbacks.add(callback)
    // 立即调用一次，传递当前状态
    callback(this.currentStatus)
    // 返回取消订阅函数
    return () => {
      this.callbacks.delete(callback)
    }
  }

  /**
   * 通知所有回调
   */
  private notifyCallbacks() {
    this.callbacks.forEach(callback => {
      try {
        callback(this.currentStatus)
      } catch (error) {
        console.error('Health check callback error:', error)
      }
    })
  }

  /**
   * 设置最大失败次数
   */
  setMaxFailures(max: number) {
    this.maxFailures = max
  }

  /**
   * 重置失败计数
   */
  resetFailures() {
    this.consecutiveFailures = 0
    this.currentStatus.consecutiveFailures = 0
  }
}

// 导出单例
export const healthCheckService = new HealthCheckService()
