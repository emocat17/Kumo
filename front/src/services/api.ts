/**
 * API 封装工具
 * 提供统一的错误处理、重试机制和超时控制
 */

export interface ApiOptions extends RequestInit {
  timeout?: number
  retries?: number
  retryDelay?: number
  showError?: boolean
}

export interface ApiError {
  code: string
  message: string
  status?: number
  details?: any
}

class ApiService {
  private baseURL: string = '/api'
  private defaultTimeout: number = 10000 // 10秒
  private defaultRetries: number = 2
  private defaultRetryDelay: number = 1000 // 1秒

  /**
   * 执行API请求，带重试机制
   */
  async request<T = any>(
    endpoint: string,
    options: ApiOptions = {}
  ): Promise<T> {
    const {
      timeout = this.defaultTimeout,
      retries = this.defaultRetries,
      retryDelay = this.defaultRetryDelay,
      showError = true,
      ...fetchOptions
    } = options

    let lastError: Error | null = null

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), timeout)

        const response = await fetch(`${this.baseURL}${endpoint}`, {
          ...fetchOptions,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...fetchOptions.headers,
          },
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          // 尝试解析错误响应
          let errorData: any = {}
          try {
            const contentType = response.headers.get('content-type')
            if (contentType && contentType.includes('application/json')) {
              errorData = await response.json()
            }
          } catch {
            // 忽略解析错误
          }

          const error: ApiError = {
            code: errorData.error?.code || `HTTP_${response.status}`,
            message: errorData.error?.message || response.statusText || '请求失败',
            status: response.status,
            details: errorData.error?.details,
          }

          // 4xx错误不重试，5xx和网络错误重试
          if (response.status >= 400 && response.status < 500 && attempt < retries) {
            // 客户端错误，不重试
            throw error
          }

          // 最后一次尝试或服务器错误，抛出错误
          if (attempt === retries) {
            throw error
          }

          lastError = error as any
          // 等待后重试
          await this.delay(retryDelay * (attempt + 1))
          continue
        }

        // 成功响应
        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          return await response.json()
        }
        return (await response.text()) as T
      } catch (error) {
        lastError = error as Error

        // AbortError 是超时错误
        if (error instanceof Error && error.name === 'AbortError') {
          if (attempt === retries) {
            throw {
              code: 'TIMEOUT',
              message: '请求超时，请检查网络连接',
            } as ApiError
          }
          // 超时重试
          await this.delay(retryDelay * (attempt + 1))
          continue
        }

        // 网络错误或其他错误
        if (attempt === retries) {
          if (error instanceof Error && 'code' in error) {
            throw error
          }
          throw {
            code: 'NETWORK_ERROR',
            message: error instanceof Error ? error.message : '网络错误',
          } as ApiError
        }

        // 等待后重试
        await this.delay(retryDelay * (attempt + 1))
      }
    }

    // 理论上不会到达这里
    throw lastError || new Error('未知错误')
  }

  /**
   * GET 请求
   */
  async get<T = any>(endpoint: string, options?: ApiOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'GET',
    })
  }

  /**
   * POST 请求
   */
  async post<T = any>(
    endpoint: string,
    data?: any,
    options?: ApiOptions
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * PUT 请求
   */
  async put<T = any>(
    endpoint: string,
    data?: any,
    options?: ApiOptions
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * DELETE 请求
   */
  async delete<T = any>(endpoint: string, options?: ApiOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'DELETE',
    })
  }

  /**
   * 延迟函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * 设置默认配置
   */
  setDefaults(config: {
    timeout?: number
    retries?: number
    retryDelay?: number
  }) {
    if (config.timeout !== undefined) {
      this.defaultTimeout = config.timeout
    }
    if (config.retries !== undefined) {
      this.defaultRetries = config.retries
    }
    if (config.retryDelay !== undefined) {
      this.defaultRetryDelay = config.retryDelay
    }
  }
}

// 导出单例
export const apiService = new ApiService()
