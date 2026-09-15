import Taro from '@tarojs/taro'
import { API_BASE } from '@/config'
import type { ApiError } from '@/types'

export class RequestError extends Error {
  code: string
  status: number
  detail?: Record<string, unknown>

  constructor(status: number, payload: Partial<ApiError> | undefined) {
    super(payload?.message || '网络异常，请稍后再试')
    this.code = payload?.code || 'NETWORK_ERROR'
    this.status = status
    this.detail = payload?.detail
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST'
  data?: Record<string, unknown>
  query?: Record<string, string>
}

/** Taro.request 轻量封装：统一 baseURL / 错误格式 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', data, query } = options
  let url = `${API_BASE}${path}`
  if (query) {
    const qs = Object.entries(query)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&')
    url += `?${qs}`
  }
  const res = await Taro.request<T | ApiError>({
    url,
    method,
    data,
    header: { 'content-type': 'application/json' },
  })
  if (res.statusCode >= 200 && res.statusCode < 300) {
    return res.data as T
  }
  throw new RequestError(res.statusCode, res.data as ApiError)
}

/** multipart 上传（PDF） */
export async function upload<T>(path: string, filePath: string, formData: Record<string, string>): Promise<T> {
  const res = await Taro.uploadFile<T | ApiError>({
    url: `${API_BASE}${path}`,
    filePath,
    name: 'file',
    formData,
  })
  const body = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
  if (res.statusCode >= 200 && res.statusCode < 300) {
    return body as T
  }
  throw new RequestError(res.statusCode, body as ApiError)
}
