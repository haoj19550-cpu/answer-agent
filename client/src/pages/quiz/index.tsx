import { useEffect, useMemo, useState } from 'react'
import Taro from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import { Chip, Nodes, Option, type NodeState } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { TYPE_LABELS, difficultyLabel, useQuizStore, type FeedbackData } from '@/stores/quiz'
import { useUserStore } from '@/stores/user'
import { submitAnswer } from '@/services/api'
import { formatDuration } from '@/stores/history'

const LETTERS = ['A', 'B', 'C', 'D']

export default function QuizPage() {
  const {
    quiz, currentIndex, results, combo, startedAt, questionStartedAt,
    recordAnswer,
  } = useQuizStore()
  const applyAnswerLocal = useUserStore((s) => s.applyLocalAnswer)
  const clientId = useUserStore((s) => s.clientId)
  const [selected, setSelected] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setElapsed(Date.now() - startedAt), 1000)
    return () => clearInterval(timer)
  }, [startedAt])

  useEffect(() => {
    setSelected(null)
  }, [currentIndex])

  const question = quiz?.questions[currentIndex]

  const nodeStates = useMemo<NodeState[]>(() => {
    if (!quiz) return []
    return quiz.questions.map((_, i) => {
      if (results[i]) return results[i].correct ? 'done' : 'miss'
      if (i === currentIndex) return 'now'
      return 'todo'
    })
  }, [quiz, results, currentIndex])

  // 场景题：题干含换行时，首段为情境、其余以等宽代码块呈现
  // 注意：所有 hooks 必须在早退判断之前调用
  const [stemMain, stemCode] = useMemo(() => {
    if (!question) return ['', '']
    const parts = question.stem.split('\n')
    if (question.type === 'scenario' && parts.length > 1) {
      return [parts[0], parts.slice(1).join('\n')]
    }
    return [question.stem, '']
  }, [question])

  if (!quiz || !question) {
    return (
      <Page module="quiz">
        <NavBar title="闯关答题" back />
        <View className="bd">
          <View className="empty">
            <Mascot variant="zzz" size={110} />
            <Text className="ct" style={{ fontSize: '17px' }}>闯关会话已失效</Text>
            <View className="btn btn-p btn-sm" style={{ width: 'auto', padding: '0 24px' }}
              onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}>
              重新开始
            </View>
          </View>
        </View>
      </Page>
    )
  }

  const submit = async () => {
    if (selected === null || submitting) return
    setSubmitting(true)
    try {
      const elapsedMs = Date.now() - questionStartedAt
      const result = await submitAnswer(clientId, quiz.quiz_id, question.index, selected, elapsedMs)
      applyAnswerLocal(result.correct, result.exp_delta, result.combo)
      const feedback: FeedbackData = {
        questionIndex: question.index,
        questionType: question.type,
        stem: question.stem,
        options: question.options,
        userAnswer: selected,
        result,
        elapsedMs,
        isLast: currentIndex === quiz.questions.length - 1,
      }
      recordAnswer(question.index, result, feedback)
      Taro.navigateTo({ url: '/pages/feedback/index' })
    } catch (err) {
      const e = err as { message?: string }
      Taro.showToast({ title: e.message || '提交失败，请重试', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  const typeChipTone = question.type === 'single_choice' ? 'br' : question.type === 'true_false' ? 'mt' : 'sc'

  return (
    <Page module="quiz">
      <NavBar title={quiz.title} back />
      <View className="bd">
        <View className="row bt">
          <Text className="ct" style={{ fontSize: '15px' }}>
            第 {currentIndex + 1} / {quiz.questions.length} 题
          </Text>
          <View className="row g10">
            {combo > 0 && <Chip tone="gd" icon="flame">连击 {combo}</Chip>}
            <Chip tone="gh" icon="clock">{formatDuration(elapsed)}</Chip>
          </View>
        </View>

        <View className="mt12">
          <Nodes states={nodeStates} />
        </View>

        <View className="row g6 mt16">
          <Chip tone={typeChipTone}>{TYPE_LABELS[question.type]}</Chip>
          <Chip tone="gh">{difficultyLabel(question.difficulty)}</Chip>
          <Chip tone="gh">{question.knowledge_point}</Chip>
        </View>

        <View className="card mt12 row g12" style={{ alignItems: 'flex-start' }}>
          <Text className="ct grow" style={{ fontSize: '18px', lineHeight: 1.5 }}>{stemMain}</Text>
          <Mascot variant="think" size={40} bob={false} style={{ marginTop: '-2px' }} />
        </View>
        {stemCode && <View className="code mt12">{stemCode}</View>}

        {question.type === 'true_false' ? (
          <View className="row g12 mt16">
            {question.options.map((opt, i) => (
              <View
                key={i}
                className={`btn btn-s ${selected === i ? 'sel-tf' : ''}`}
                style={{
                  height: '96px', flexDirection: 'column', gap: '6px',
                  ...(selected === i
                    ? { borderColor: 'var(--brand)', background: 'var(--brand-soft)', color: 'var(--brand)', boxShadow: '0 3px 0 var(--brand-press)' }
                    : {}),
                }}
                onClick={() => setSelected(i)}
              >
                <Icon
                  name={i === 0 ? 'check' : 'x'}
                  size={32}
                  color={selected === i ? '#2B4EFF' : i === 0 ? '#00D3A7' : '#8A97AC'}
                />
                <Text>{opt}</Text>
              </View>
            ))}
          </View>
        ) : (
          <View className="stack g10 mt12">
            {question.options.map((opt, i) => (
              <Option
                key={i}
                letter={LETTERS[i]}
                text={opt}
                state={selected === i ? 'sel' : 'idle'}
                onClick={() => setSelected(i)}
              />
            ))}
          </View>
        )}

        {question.type === 'true_false' && (
          <View className="card mt16">
            <View className="row g8">
              <Icon name="info" size={16} color="#2B4EFF" />
              <Text className="txt-xs txt-mut" style={{ lineHeight: 1.6 }}>
                判断题考的是边界条件。拿不准时，想想「彻底」「一定」「所有」这类绝对化表述。
              </Text>
            </View>
          </View>
        )}
      </View>
      <View className="act">
        <View className={`btn btn-p ${selected === null || submitting ? 'dis' : ''}`} onClick={submit}>
          {submitting ? '提交中…' : '提交答案'}
        </View>
      </View>
    </Page>
  )
}
