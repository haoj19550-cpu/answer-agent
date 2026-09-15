/** 学习记录与错题本：小程序本地持久化（Taro.setStorage），零后端接口。 */

import Taro from '@tarojs/taro'
import type { Report } from '@/types'

const KEY_HISTORY = 'aa_history'
const KEY_WRONG_BOOK = 'aa_wrong_book'

export interface HistoryItem {
  quiz_id: string
  title: string
  score: number
  accuracy: number
  total: number
  duration_ms: number
  weak_points: string[]
  fair_points: string[]
  created_at: string
  report: Report
}

export interface WrongBookItem {
  quiz_id: string
  title: string
  question_index: number
  stem: string
  error_type: string
  analysis: string
  created_at: string
}

function read<T>(key: string): T[] {
  try {
    return (Taro.getStorageSync(key) as T[]) || []
  } catch {
    return []
  }
}

function write<T>(key: string, items: T[]) {
  try {
    Taro.setStorageSync(key, items)
  } catch {
    /* ignore */
  }
}

export function listHistory(): HistoryItem[] {
  return read<HistoryItem>(KEY_HISTORY).sort((a, b) => b.created_at.localeCompare(a.created_at))
}

export function saveReportToHistory(report: Report, total: number) {
  const items = read<HistoryItem>(KEY_HISTORY).filter((i) => i.quiz_id !== report.quiz_id)
  const weak = Object.entries(report.mastery_levels).filter(([, lv]) => lv === 'weak').map(([kp]) => kp)
  const fair = Object.entries(report.mastery_levels).filter(([, lv]) => lv === 'fair').map(([kp]) => kp)
  items.push({
    quiz_id: report.quiz_id,
    title: report.title,
    score: report.score,
    accuracy: report.accuracy,
    total,
    duration_ms: report.duration_ms,
    weak_points: weak,
    fair_points: fair,
    created_at: report.created_at,
    report,
  })
  write(KEY_HISTORY, items)
}

export function listWrongBook(): WrongBookItem[] {
  return read<WrongBookItem>(KEY_WRONG_BOOK).sort((a, b) => b.created_at.localeCompare(a.created_at))
}

export function addWrongToBook(item: WrongBookItem) {
  const items = read<WrongBookItem>(KEY_WRONG_BOOK)
  if (items.some((i) => i.quiz_id === item.quiz_id && i.question_index === item.question_index)) return
  items.push(item)
  write(KEY_WRONG_BOOK, items)
}

export function removeWrongFromBook(quizId: string, questionIndex: number) {
  write(
    KEY_WRONG_BOOK,
    read<WrongBookItem>(KEY_WRONG_BOOK).filter(
      (i) => !(i.quiz_id === quizId && i.question_index === questionIndex),
    ),
  )
}

/** 最近学习（首页展示前 2 条） */
export function recentHistory(n = 2): HistoryItem[] {
  return listHistory().slice(0, n)
}

export function formatWhen(iso: string): string {
  const d = new Date(iso)
  const now = Date.now()
  const diff = now - d.getTime()
  const day = 86400000
  if (diff < day) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  if (diff < 2 * day) {
    return `昨天 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  return '上周'
}

export function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
