/**
 * 自动恢复服务
 * 检测到系统异常时，自动执行恢复操作（如刷新页面）
 */

import { healthCheckService, type HealthStatus } from './healthCheck'

export interface AutoRecoveryConfig {
  enabled: boolean
  maxUnhealthyDuration: number // 最大不健康持续时间（毫秒），超过此时长后自动恢复
  autoReload: boolean // 是否自动刷新页面
  reloadDelay: number // 自动刷新前的延迟（毫秒）
  onBeforeReload?: () => void // 刷新前的回调
}

class AutoRecoveryService {
  private config: AutoRecoveryConfig = {
    enabled: true,
    maxUnhealthyDuration: 30000, // 30秒
    autoReload: true,
    reloadDelay: 5000, // 5秒后刷新
  }
  private unhealthyStartTime: number | null = null
  private reloadTimer: number | null = null
  private unsubscribe: (() => void) | null = null
  private isReloading: boolean = false

  /**
   * 启动自动恢复服务
   */
  start(config?: Partial<AutoRecoveryConfig>) {
    if (config) {
      this.config = { ...this.config, ...config }
    }

    if (!this.config.enabled) {
      return
    }

    // 监听健康状态变化
    this.unsubscribe = healthCheckService.onStatusChange((status) => {
      this.handleHealthStatusChange(status)
    })
  }

  /**
   * 停止自动恢复服务
   */
  stop() {
    if (this.unsubscribe) {
      this.unsubscribe()
      this.unsubscribe = null
    }
    if (this.reloadTimer) {
      clearTimeout(this.reloadTimer)
      this.reloadTimer = null
    }
    this.unhealthyStartTime = null
  }

  /**
   * 处理健康状态变化
   */
  private handleHealthStatusChange(status: HealthStatus) {
    if (status.status === 'unhealthy') {
      // 记录不健康开始时间
      if (this.unhealthyStartTime === null) {
        this.unhealthyStartTime = Date.now()
        console.warn('[AutoRecovery] 检测到系统不健康状态')
      }

      // 检查是否超过最大不健康持续时间
      const unhealthyDuration = Date.now() - this.unhealthyStartTime
      if (
        unhealthyDuration >= this.config.maxUnhealthyDuration &&
        this.config.autoReload &&
        !this.isReloading
      ) {
        this.triggerReload()
      }
    } else if (status.status === 'healthy') {
      // 系统恢复健康，重置状态
      if (this.unhealthyStartTime !== null) {
        console.info('[AutoRecovery] 系统已恢复健康')
        this.unhealthyStartTime = null
      }
      if (this.reloadTimer) {
        clearTimeout(this.reloadTimer)
        this.reloadTimer = null
      }
    }
  }

  /**
   * 触发页面刷新
   */
  private triggerReload() {
    if (this.isReloading) {
      return
    }

    this.isReloading = true
    console.warn(
      `[AutoRecovery] 系统不健康持续时间超过 ${this.config.maxUnhealthyDuration}ms，将在 ${this.config.reloadDelay}ms 后自动刷新页面`
    )

    // 执行刷新前回调
    if (this.config.onBeforeReload) {
      try {
        this.config.onBeforeReload()
      } catch (error) {
        console.error('[AutoRecovery] onBeforeReload callback error:', error)
      }
    }

    // 延迟刷新
    this.reloadTimer = window.setTimeout(() => {
      console.warn('[AutoRecovery] 执行自动刷新')
      window.location.reload()
    }, this.config.reloadDelay)
  }

  /**
   * 手动触发恢复（刷新页面）
   */
  manualReload() {
    if (this.config.onBeforeReload) {
      try {
        this.config.onBeforeReload()
      } catch (error) {
        console.error('[AutoRecovery] onBeforeReload callback error:', error)
      }
    }
    window.location.reload()
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<AutoRecoveryConfig>) {
    this.config = { ...this.config, ...config }
  }

  /**
   * 获取当前配置
   */
  getConfig(): Readonly<AutoRecoveryConfig> {
    return { ...this.config }
  }
}

// 导出单例
export const autoRecoveryService = new AutoRecoveryService()
