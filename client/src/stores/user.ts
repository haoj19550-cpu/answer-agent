import Taro from '@tarojs/taro'
import { create } from 'zustand'

const KEY_CLIENT_ID = 'aa_client_id'
const KEY_GAMIFICATION = 'aa_gamification_local'

interface UserState {
  clientId: string
  exp: number
  combo: number
  maxCombo: number
  completedQuizzes: number
  badges: string[]
  monthlyQuota: number
  quotaUsed: number
  ensureClientId: () => string
  syncGamification: (s: {
    exp: number
    combo: number
    max_combo: number
    completed_quizzes: number
    badges: string[]
    monthly_quota: number
    quota_used: number
  }) => void
  applyLocalAnswer: (correct: boolean, expDelta: number, combo: number) => void
  quotaRemaining: () => number
}

function genClientId(): string {
  return 'xxxxxxxx4xxx'.replace(/x/g, () => ((Math.random() * 16) | 0).toString(16)) + Date.now().toString(16)
}

function loadPersisted() {
  try {
    return Taro.getStorageSync(KEY_GAMIFICATION) || {}
  } catch {
    return {}
  }
}

export const useUserStore = create<UserState>((set, get) => ({
  clientId: '',
  exp: 0,
  combo: 0,
  maxCombo: 0,
  completedQuizzes: 0,
  badges: [],
  monthlyQuota: 30,
  quotaUsed: 0,

  ensureClientId: () => {
    let id = get().clientId
    if (!id) {
      try {
        id = Taro.getStorageSync(KEY_CLIENT_ID)
      } catch {
        id = ''
      }
      if (!id) {
        id = genClientId()
        try {
          Taro.setStorageSync(KEY_CLIENT_ID, id)
        } catch {
          /* ignore */
        }
      }
      const persisted = loadPersisted()
      set({ clientId: id, ...persisted })
    }
    return id
  },

  syncGamification: (s) => {
    const next = {
      exp: s.exp,
      combo: s.combo,
      maxCombo: s.max_combo,
      completedQuizzes: s.completed_quizzes,
      badges: s.badges,
      monthlyQuota: s.monthly_quota,
      quotaUsed: s.quota_used,
    }
    set(next)
    try {
      Taro.setStorageSync(KEY_GAMIFICATION, next)
    } catch {
      /* ignore */
    }
  },

  applyLocalAnswer: (correct, expDelta, combo) => {
    const state = get()
    const next = {
      exp: state.exp + expDelta,
      combo,
      maxCombo: Math.max(state.maxCombo, combo),
    }
    set(next)
    try {
      Taro.setStorageSync(KEY_GAMIFICATION, {
        exp: next.exp,
        combo: next.combo,
        maxCombo: next.maxCombo,
        completedQuizzes: state.completedQuizzes,
        badges: state.badges,
        monthlyQuota: state.monthlyQuota,
        quotaUsed: state.quotaUsed,
      })
    } catch {
      /* ignore */
    }
  },

  quotaRemaining: () => Math.max(0, get().monthlyQuota - get().quotaUsed),
}))

/** 设备 ID 短码（个人中心展示，如「学习者 8f3a」） */
export function shortClientId(id: string): string {
  return id.slice(0, 4)
}
