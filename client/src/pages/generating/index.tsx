import { useEffect, useRef, useState } from 'react'
import Taro, { useRouter } from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import { StageItem, type StageStatus } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { useQuizStore, mixText } from '@/stores/quiz'
import { useUserStore } from '@/stores/user'
import { createMaterial, streamExtract, streamGenerate } from '@/services/api'
import type { SseSession } from '@/services/sse'
import type { IconName } from '@/components/Icon'

interface StageDef {
  icon: IconName
  title: string
  sub: string
}

const STAGES: StageDef[] = [
  { icon: 'layers', title: '正在提取知识点', sub: '识别核心考点与易混淆概念' },
  { icon: 'sparkle', title: '正在生成题目', sub: '' },
  { icon: 'shield', title: '正在校验题目质量', sub: '核对答案唯一性与原文出处' },
  { icon: 'play', title: '准备开局', sub: '校验通过后自动进入第 1 题' },
]

export default function GeneratingPage() {
  const router = useRouter()
  const phase = (router.params.phase as 'extract' | 'generate') || 'extract'
  const [current, setCurrent] = useState(0) // 当前进行中的阶段下标
  const [doneCount, setDoneCount] = useState(0)
  const sessionRef = useRef<SseSession | null>(null)
  const startedRef = useRef(false)

  const {
    materialId, materialTitle, inputText, count, goal, difficulty, selectedKps,
    setMaterial, setExtraction, setQuiz,
  } = useQuizStore.getState()
  const clientId = useUserStore.getState().clientId

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    const toError = (code: string, message: string) => {
      Taro.redirectTo({
        url: `/pages/error/index?code=${encodeURIComponent(code)}&message=${encodeURIComponent(message)}&phase=${phase}`,
      })
    }

    const runGenerate = (matId: string) => {
      sessionRef.current = streamGenerate(clientId, matId, {
        goal, difficulty, count,
        selected_knowledge_points: selectedKps,
      }, {
        onStage: (stage) => {
          if (stage === 'generating') setCurrent(1)
          if (stage === 'validating') { setCurrent(2); setDoneCount(2) }
        },
        onQuiz: (quiz) => {
          setCurrent(3)
          setDoneCount(3)
          setQuiz(quiz)
          setTimeout(() => {
            Taro.redirectTo({ url: '/pages/quiz/index' })
          }, 700)
        },
        onSseError: toError,
      })
    }

    const run = async () => {
      try {
        let matId = materialId
        if (!matId) {
          const value = inputText.trim()
          const material = await createMaterial(
            clientId,
            value.length >= 50 ? 'text' : 'topic',
            value,
          )
          matId = material.material_id
          setMaterial(matId, material.title)
        }

        if (phase === 'extract') {
          setCurrent(0)
          sessionRef.current = streamExtract(clientId, matId, {
            onKnowledge: (extraction) => {
              setDoneCount(1)
              setExtraction(extraction)
              setTimeout(() => {
                Taro.redirectTo({ url: '/pages/knowledge-preview/index' })
              }, 500)
            },
            onSseError: toError,
          })
        } else {
          setDoneCount(1)
          setCurrent(1)
          runGenerate(matId)
        }
      } catch (err) {
        const e = err as { code?: string; message?: string }
        toError(e.code || 'NETWORK_ERROR', e.message || '网络异常，请稍后再试')
      }
    }

    run()
    return () => {
      sessionRef.current?.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const statusOf = (i: number): StageStatus => {
    if (i < doneCount) return 'done'
    if (i === current) return 'now'
    return 'todo'
  }

  const progress = Math.min(100, Math.round(((doneCount + (current > doneCount ? 0.5 : 0)) / STAGES.length) * 100))

  return (
    <Page module="ai">
      <NavBar title="正在生成闯关" back onBack={() => {
        sessionRef.current?.abort()
        Taro.navigateBack({ fail: () => Taro.reLaunch({ url: '/pages/home/index' }) })
      }} />
      <View className="bd">
        <View className="card stack g16" style={{ padding: '20px 16px' }}>
          <View className="row g12">
            <Mascot variant="read" size={64} />
            <View className="grow stack g4">
              <Text className="ct" style={{ fontSize: '16px' }}>AI 正在备课</Text>
              <Text className="cs">{materialTitle || inputText.slice(0, 20)} ｜ {count} 题 ｜ 预计 20 秒</Text>
            </View>
          </View>
          <View className="stack g4">
            <View className="bar lg">
              <View className="bar-i" style={{ width: `${progress}%`, transition: 'width .5s ease' }} />
            </View>
            <View className="row bt txt-xs txt-faint mt4">
              <Text>生成进度</Text>
              <Text>{Math.min(doneCount + 1, 4)} / 4</Text>
            </View>
          </View>
          <View className="stack">
            {STAGES.map((s, i) => (
              <StageItem
                key={s.title}
                icon={s.icon}
                title={s.title}
                sub={i === 1 && statusOf(1) !== 'todo' ? mixText(count).replace(/ · /g, '、').replace('单选', '单选 ').replace('判断', '判断 ').replace('场景', '场景 ') : s.sub}
                status={statusOf(i)}
              />
            ))}
          </View>
        </View>
        <View className="card mt12">
          <View className="row g8">
            <Icon name="info" size={16} color="#2B4EFF" />
            <Text className="txt-xs txt-mut" style={{ lineHeight: 1.6 }}>
              题目全部来自你提供的材料，每道题都附原文出处。生成失败会自动重试，不会把不合格的题目放进来。
            </Text>
          </View>
        </View>
      </View>
      <View className="act">
        <View
          className="btn btn-s"
          onClick={() => {
            sessionRef.current?.abort()
            Taro.navigateBack({ fail: () => Taro.reLaunch({ url: '/pages/home/index' }) })
          }}
        >
          取消生成
        </View>
      </View>
    </Page>
  )
}
