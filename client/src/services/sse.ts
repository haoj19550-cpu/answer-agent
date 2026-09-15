import Taro from '@tarojs/taro'
import { API_BASE } from '@/config'
import type { ApiError, SseEvent } from '@/types'

export interface SseHandlers {
  onEvent: (event: SseEvent) => void
  onError?: (error: Error) => void
  onComplete?: () => void
}

export interface SseSession {
  abort: () => void
}

/** 按行解析 SSE 帧（event:/data:），帧以空行分隔 */
export function createSseParser(onEvent: (event: SseEvent) => void) {
  let buffer = ''
  let eventName = ''
  let dataLines: string[] = []

  const flush = () => {
    if (eventName) {
      onEvent({ event: eventName as SseEvent['event'], data: dataLines.join('\n') })
    }
    eventName = ''
    dataLines = []
  }

  return {
    push(text: string) {
      buffer += text
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const raw of lines) {
        const line = raw.replace(/\r$/, '')
        if (line === '') {
          flush()
        } else if (line.startsWith('event:')) {
          eventName = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim())
        }
      }
    },
    end() {
      if (buffer) {
        this.push('\n')
      }
      flush()
    },
  }
}

/**
 * SSE 客户端：
 * - 微信小程序：Taro.request(enableChunked) + onChunkReceived 按块解码解析
 * - H5：fetch + ReadableStream
 * 解析逻辑收敛在此，页面对协议无感知。
 */
export function openSse(path: string, body: Record<string, unknown>, handlers: SseHandlers): SseSession {
  const parser = createSseParser(handlers.onEvent)
  const decoder = new TextDecoder('utf-8')

  if (process.env.TARO_ENV === 'h5') {
    const controller = new AbortController()
    fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok || !res.body) {
          let payload: ApiError | undefined
          try {
            payload = await res.json()
          } catch {
            /* ignore */
          }
          throw Object.assign(new Error(payload?.message || '请求失败'), {
            code: payload?.code || 'NETWORK_ERROR',
            status: res.status,
          })
        }
        const reader = res.body.getReader()
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          parser.push(decoder.decode(value, { stream: true }))
        }
        parser.end()
        handlers.onComplete?.()
      })
      .catch((err) => {
        if (err?.name !== 'AbortError') handlers.onError?.(err)
      })
    return { abort: () => controller.abort() }
  }

  // 微信小程序：enableChunked 流式接收
  const task = Taro.request({
    url: `${API_BASE}${path}`,
    method: 'POST',
    data: body,
    enableChunked: true,
    header: { 'content-type': 'application/json' },
    success: () => {
      parser.end()
      handlers.onComplete?.()
    },
    fail: (err) => {
      handlers.onError?.(new Error(err.errMsg || '网络异常'))
    },
  })
  task.onChunkReceived((res) => {
    parser.push(decoder.decode(res.data as ArrayBuffer, { stream: true }))
  })
  return { abort: () => task.abort() }
}
