/** 接口层：材料 / 提取 / 生成 / 判分 / 报告 / 游戏化。USE_MOCK 时走本地样例。 */

import { USE_MOCK } from '@/config'
import { request, upload } from './request'
import { openSse, type SseHandlers, type SseSession } from './sse'
import type {
  AnswerResult,
  GamificationState,
  PublicQuiz,
  QuizConfig,
  Report,
  SseEvent,
} from '@/types'
import { MOCK_ANSWERS, MOCK_EXTRACTION, MOCK_QUIZ, MOCK_REPORT } from '@/utils/mock'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function createMaterial(
  clientId: string,
  sourceType: 'text' | 'topic',
  text: string,
  title = '',
): Promise<{ material_id: string; title: string; char_count: number }> {
  if (USE_MOCK) {
    await delay(200)
    return { material_id: 'mat_mock01', title: title || text.slice(0, 30), char_count: text.length }
  }
  return request('/api/v1/materials', {
    method: 'POST',
    data: { client_id: clientId, source_type: sourceType, text, title },
  })
}

export async function uploadPdf(
  clientId: string,
  filePath: string,
): Promise<{ material_id: string; title: string; char_count: number }> {
  return upload('/api/v1/materials/upload', filePath, { client_id: clientId })
}

interface StreamOptions {
  onStage?: (stage: string, message: string) => void
  onSseError?: (code: string, message: string) => void
}

function wireHandlers(opts: StreamOptions, extra: (evt: SseEvent) => boolean | void): SseHandlers {
  return {
    // 网络层失败（连接拒绝/中断/非 2xx）统一转为错误页跳转
    onError: (err) => {
      const e = err as { code?: string; message?: string }
      opts.onSseError?.(e.code || 'NETWORK_ERROR', e.message || '网络异常，请稍后再试')
    },
    onEvent: (evt) => {
      if (evt.event === 'stage') {
        const payload = JSON.parse(evt.data)
        opts.onStage?.(payload.stage, payload.message)
        return
      }
      if (evt.event === 'error') {
        const payload = JSON.parse(evt.data)
        opts.onSseError?.(payload.code, payload.message)
        return
      }
      extra(evt)
    },
  }
}

/** 第一段 SSE：提取知识点 */
export function streamExtract(
  clientId: string,
  materialId: string,
  opts: StreamOptions & { onKnowledge: (data: typeof MOCK_EXTRACTION) => void },
): SseSession {
  if (USE_MOCK) {
    let cancelled = false
    ;(async () => {
      opts.onStage?.('extracting', '正在提取知识点…')
      await delay(900)
      if (!cancelled) opts.onKnowledge(MOCK_EXTRACTION)
    })()
    return { abort: () => { cancelled = true } }
  }
  return openSse('/api/v1/quizzes/extract', { client_id: clientId, material_id: materialId },
    wireHandlers(opts, (evt) => {
      if (evt.event === 'knowledge') opts.onKnowledge(JSON.parse(evt.data))
    }))
}

/** 第二段 SSE：按配置与勾选生成题目 */
export function streamGenerate(
  clientId: string,
  materialId: string,
  config: QuizConfig,
  opts: StreamOptions & { onQuiz: (quiz: PublicQuiz) => void },
): SseSession {
  if (USE_MOCK) {
    let cancelled = false
    ;(async () => {
      opts.onStage?.('generating', '正在生成题目…')
      await delay(1000)
      if (cancelled) return
      opts.onStage?.('validating', '正在校验题目质量…')
      await delay(800)
      if (!cancelled) opts.onQuiz(MOCK_QUIZ)
    })()
    return { abort: () => { cancelled = true } }
  }
  return openSse('/api/v1/quizzes/generate', {
    client_id: clientId,
    material_id: materialId,
    goal: config.goal,
    difficulty: config.difficulty,
    count: config.count,
    selected_knowledge_points: config.selected_knowledge_points,
  }, wireHandlers(opts, (evt) => {
    if (evt.event === 'quiz') opts.onQuiz(JSON.parse(evt.data))
  }))
}

export async function submitAnswer(
  clientId: string,
  quizId: string,
  questionIndex: number,
  userAnswer: number,
  elapsedMs: number,
): Promise<AnswerResult> {
  if (USE_MOCK) {
    await delay(150)
    const meta = MOCK_ANSWERS[questionIndex]
    const correct = userAnswer === meta.correct_answer
    return {
      correct,
      correct_answer: meta.correct_answer,
      explanation: meta.explanation,
      knowledge_point: MOCK_QUIZ.questions[questionIndex].knowledge_point,
      source_excerpt: meta.source_excerpt,
      exp_delta: correct ? 20 : 0,
      combo: correct ? 1 : 0,
      progress: { answered: questionIndex + 1, total: MOCK_QUIZ.questions.length },
    }
  }
  return request(`/api/v1/quizzes/${quizId}/answers`, {
    method: 'POST',
    data: { client_id: clientId, question_index: questionIndex, user_answer: userAnswer, elapsed_ms: elapsedMs },
  })
}

export async function createReport(clientId: string, quizId: string): Promise<Report> {
  if (USE_MOCK) {
    await delay(700)
    return MOCK_REPORT
  }
  return request('/api/v1/reports', { method: 'POST', data: { client_id: clientId, quiz_id: quizId } })
}

export async function getGamificationState(clientId: string): Promise<GamificationState> {
  if (USE_MOCK) {
    await delay(100)
    return {
      client_id: clientId, exp: 120, combo: 0, max_combo: 3, completed_quizzes: 1,
      badges: ['first_quiz'], monthly_quota: 30, quota_used: 1, quota_remaining: 29,
    }
  }
  return request('/api/v1/gamification/state', { query: { client_id: clientId } })
}
