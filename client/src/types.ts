/** API 类型（与后端 schemas 对齐） */

export type QuestionType = 'single_choice' | 'true_false' | 'scenario'
export type StudyGoal = 'understand' | 'memorize' | 'exam' | 'interview' | 'quick'
export type Difficulty = 'easy' | 'medium' | 'hard' | 'adaptive'

export interface KnowledgePoint {
  name: string
  definition: string
  importance: number
  confusion_with: string[]
}

export interface KnowledgeExtraction {
  topic: string
  summary: string
  knowledge_points: KnowledgePoint[]
}

export interface PublicQuestion {
  index: number
  type: QuestionType
  stem: string
  options: string[]
  difficulty: number
  knowledge_point: string
}

export interface GamificationSnapshot {
  exp: number
  combo: number
  quota_remaining: number
}

export interface PublicQuiz {
  quiz_id: string
  title: string
  questions: PublicQuestion[]
  gamification?: GamificationSnapshot
}

export interface QuizConfig {
  goal: StudyGoal
  difficulty: Difficulty
  count: 5 | 10
  selected_knowledge_points: string[]
}

export interface AnswerResult {
  correct: boolean
  correct_answer: number
  explanation: string
  knowledge_point: string
  source_excerpt: string
  exp_delta: number
  combo: number
  progress: { answered: number; total: number }
}

export interface WrongQuestion {
  index: number
  stem: string
  error_type: string
  analysis: string
}

export interface Report {
  quiz_id: string
  client_id: string
  title: string
  score: number
  accuracy: number
  duration_ms: number
  mastery_levels: Record<string, 'good' | 'fair' | 'weak'>
  wrong_questions: WrongQuestion[]
  performance_summary: string
  confusion_pairs: string[]
  suggestions: string[]
  ai_generated: boolean
  badges: string[]
  exp_gained: number
  created_at: string
}

export interface GamificationState {
  client_id: string
  exp: number
  combo: number
  max_combo: number
  completed_quizzes: number
  badges: string[]
  monthly_quota: number
  quota_used: number
  quota_remaining: number
}

export interface ApiError {
  code: string
  message: string
  detail?: Record<string, unknown>
}

export type SseStage = 'extracting' | 'generating' | 'validating'

export interface SseEvent {
  event: 'stage' | 'knowledge' | 'quiz' | 'error' | 'done'
  data: string
}
