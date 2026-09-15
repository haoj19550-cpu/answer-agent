import Taro from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import { Chip } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { useQuizStore } from '@/stores/quiz'
import { addWrongToBook } from '@/stores/history'
import { formatDuration } from '@/stores/history'

const LETTERS = ['A', 'B', 'C', 'D']

export default function FeedbackPage() {
  const { feedback, quiz, extraction, nextQuestion } = useQuizStore()

  if (!feedback || !quiz) {
    return (
      <Page module="quiz">
        <NavBar title="答案解析" back />
        <View className="bd">
          <View className="empty">
            <Mascot variant="zzz" size={110} />
            <Text className="ct" style={{ fontSize: '17px' }}>反馈会话已失效</Text>
            <View className="btn btn-p btn-sm" style={{ width: 'auto', padding: '0 24px' }}
              onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}>
              回到首页
            </View>
          </View>
        </View>
      </Page>
    )
  }

  const { result, userAnswer, options, questionIndex, elapsedMs, isLast } = feedback
  const correct = result.correct
  const kpDef = extraction?.knowledge_points.find((k) => k.name === result.knowledge_point)?.definition

  const goNext = () => {
    if (isLast) {
      Taro.redirectTo({ url: '/pages/report/index' })
    } else {
      nextQuestion()
      Taro.navigateBack()
    }
  }

  const saveWrong = () => {
    addWrongToBook({
      quiz_id: quiz.quiz_id,
      title: quiz.title,
      question_index: questionIndex,
      stem: feedback.stem,
      error_type: '',
      analysis: result.explanation,
      created_at: new Date().toISOString(),
    })
    Taro.showToast({ title: '已加入错题本', icon: 'success' })
  }

  return (
    <Page module="quiz">
      <NavBar title="答案解析" back />
      <View className="bd">
        {/* 判定横幅 */}
        <View className="row g12">
          <View className={`stamp grow ${correct ? 'ok' : 'bad'}`}>
            <View className="mk">
              <Icon name={correct ? 'check' : 'x'} size={18} color={correct ? '#06302A' : '#FFFFFF'} />
            </View>
            <Text>{correct ? '回答正确' : '回答错误'} · 第 {questionIndex + 1} 题</Text>
          </View>
          <Mascot variant={correct ? 'yay' : 'pat'} size={64} />
        </View>

        {correct ? (
          <>
            {/* 答对：正确答案 + 解析 */}
            <View className="card mt12">
              <View className="row g6">
                <Chip tone="mt">正确答案 {LETTERS[result.correct_answer]}</Chip>
                {result.exp_delta > 0 && <Chip tone="gd" icon="zap">+{result.exp_delta} 经验</Chip>}
                <Chip tone="gh">用时 {formatDuration(elapsedMs)}</Chip>
              </View>
              <Text className="txt-s mt12" style={{ lineHeight: 1.65, display: 'block' }}>
                {result.explanation}
              </Text>
            </View>
            {kpDef && (
              <View className="card mt12">
                <Text className="ct" style={{ fontSize: '15px' }}>再往深一层</Text>
                <Text className="txt-s mt8" style={{ lineHeight: 1.65, display: 'block' }}>
                  <Text className="hl">{result.knowledge_point}</Text>：{kpDef}
                </Text>
              </View>
            )}
          </>
        ) : (
          <>
            {/* 答错：答案对比 */}
            <View className="card mt12">
              <View className="row bt" style={{ paddingBottom: '10px', borderBottom: '1px dashed var(--line)' }}>
                <Text className="cs">你的答案</Text>
                <View className="row g6 txt-m" style={{ color: 'var(--coral)', fontSize: '14px' }}>
                  <Icon name="x" size={16} color="#FF5C5C" />
                  <Text>{LETTERS[userAnswer]} {options[userAnswer]}</Text>
                </View>
              </View>
              <View className="row bt" style={{ paddingTop: '10px' }}>
                <Text className="cs">正确答案</Text>
                <View className="row g6 txt-m" style={{ color: '#00775F', fontSize: '14px' }}>
                  <Icon name="check" size={16} color="#00B18D" />
                  <Text>{LETTERS[result.correct_answer]} {options[result.correct_answer]}</Text>
                </View>
              </View>
            </View>
            {/* 为什么错 */}
            <View className="card mt12">
              <View className="row g8">
                <Icon name="alert" size={18} color="#FF5C5C" />
                <Text className="ct" style={{ fontSize: '15px' }}>为什么错</Text>
                <View style={{ marginLeft: 'auto' }}>
                  <Chip tone="co">{result.knowledge_point}</Chip>
                </View>
              </View>
              <Text className="txt-s mt8" style={{ lineHeight: 1.65, display: 'block' }}>
                {result.explanation}
              </Text>
            </View>
          </>
        )}

        {/* 原文出处 */}
        {result.source_excerpt && (
          <View className="quote mt12">
            {result.source_excerpt}
            <Text className="src">材料原文 · Grounded Quiz</Text>
          </View>
        )}

        <View className="row g6 mt12">
          <Chip tone="br">{result.knowledge_point}</Chip>
          <Chip tone="gh" icon="sparkle">由 AI 生成，仅供参考</Chip>
        </View>
      </View>
      <View className="act">
        {!correct && (
          <View className="btn btn-s" style={{ flex: '0 0 116px' }} onClick={saveWrong}>
            <Icon name="bookmark" size={18} color="#101A2E" />
            <Text>错题本</Text>
          </View>
        )}
        <View className={`btn ${correct ? 'btn-m' : 'btn-p'}`} onClick={goNext}>
          {isLast ? '查看通关报告' : correct ? '继续下一题' : '理解后继续'}
        </View>
      </View>
    </Page>
  )
}
