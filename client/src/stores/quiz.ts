import { create } from 'zustand'
import type {
  AnswerResult,
  Difficulty,
  KnowledgeExtraction,
  PublicQuiz,
  QuestionType,
  StudyGoal,
} from '@/types'

export interface FeedbackData {
  questionIndex: number
  questionType: QuestionType
  stem: string
  options: string[]
  userAnswer: number
  result: AnswerResult
  elapsedMs: number
  isLast: boolean
}

interface QuizFlowState {
  // 输入阶段
  materialId: string
  materialTitle: string
  inputText: string
  // 配置阶段
  goal: StudyGoal
  difficulty: Difficulty
  count: 5 | 10
  // 知识点预览
  extraction: KnowledgeExtraction | null
  selectedKps: string[]
  // 闯关阶段
  quiz: PublicQuiz | null
  currentIndex: number
  results: Record<number, { correct: boolean }>
  combo: number
  startedAt: number
  questionStartedAt: number
  feedback: FeedbackData | null

  setInput: (text: string) => void
  setMaterial: (id: string, title: string) => void
  setGoal: (g: StudyGoal) => void
  setDifficulty: (d: Difficulty) => void
  setCount: (c: 5 | 10) => void
  setExtraction: (e: KnowledgeExtraction) => void
  toggleKp: (name: string) => void
  setQuiz: (q: PublicQuiz) => void
  recordAnswer: (index: number, result: AnswerResult, feedback: FeedbackData) => void
  nextQuestion: () => void
  reset: () => void
}

export const useQuizStore = create<QuizFlowState>((set, get) => ({
  materialId: '',
  materialTitle: '',
  inputText: '',
  goal: 'understand',
  difficulty: 'adaptive',
  count: 5,
  extraction: null,
  selectedKps: [],
  quiz: null,
  currentIndex: 0,
  results: {},
  combo: 0,
  startedAt: 0,
  questionStartedAt: 0,
  feedback: null,

  setInput: (text) => set({ inputText: text }),
  setMaterial: (id, title) => set({ materialId: id, materialTitle: title }),
  setGoal: (goal) => set({ goal }),
  setDifficulty: (difficulty) => set({ difficulty }),
  setCount: (count) => set({ count }),
  setExtraction: (extraction) =>
    set({ extraction, selectedKps: extraction.knowledge_points.map((kp) => kp.name) }),
  toggleKp: (name) => {
    const cur = get().selectedKps
    set({ selectedKps: cur.includes(name) ? cur.filter((n) => n !== name) : [...cur, name] })
  },
  setQuiz: (quiz) =>
    set({
      quiz,
      currentIndex: 0,
      results: {},
      combo: 0,
      startedAt: Date.now(),
      questionStartedAt: Date.now(),
      feedback: null,
    }),
  recordAnswer: (index, result, feedback) =>
    set({
      results: { ...get().results, [index]: { correct: result.correct } },
      combo: result.combo,
      feedback,
    }),
  nextQuestion: () =>
    set({ currentIndex: get().currentIndex + 1, questionStartedAt: Date.now(), feedback: null }),
  reset: () =>
    set({
      materialId: '',
      materialTitle: '',
      extraction: null,
      selectedKps: [],
      quiz: null,
      currentIndex: 0,
      results: {},
      combo: 0,
      feedback: null,
    }),
}))

export const GOAL_LABELS: Record<StudyGoal, string> = {
  understand: '理解',
  memorize: '记忆',
  exam: '考试',
  interview: '面试',
  quick: '速记',
}

export const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
  adaptive: '自适应',
}

export const TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: '单选题',
  true_false: '判断题',
  scenario: '场景题',
}

export function difficultyLabel(d: number): string {
  if (d <= 2) return `难度 ${d} 基础`
  if (d === 3) return '难度 3 进阶'
  return `难度 ${d} 挑战`
}

/** 题量 → 配比展示 */
export function mixText(count: 5 | 10): string {
  return count === 10 ? '单选 6 · 判断 2 · 场景 2' : '单选 3 · 判断 1 · 场景 1'
}
