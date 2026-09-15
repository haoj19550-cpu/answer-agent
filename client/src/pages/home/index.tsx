import { useEffect, useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { Input, Text, View } from '@tarojs/components'
import { Page, NavBar, TabBar } from '@/components/chrome'
import { Chip, Ring } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { useQuizStore } from '@/stores/quiz'
import { useUserStore } from '@/stores/user'
import { formatWhen, recentHistory, type HistoryItem } from '@/stores/history'
import { HOT_TOPICS } from '@/utils/mock'
import { getGamificationState } from '@/services/api'
import { USE_MOCK } from '@/config'

function greeting(): string {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
}

export default function HomePage() {
  const [topic, setTopic] = useState('')
  const [recent, setRecent] = useState<HistoryItem[]>([])
  const { clientId, combo, syncGamification } = useUserStore()
  const { setInput, reset } = useQuizStore()

  useDidShow(() => {
    setRecent(recentHistory(2))
  })

  useEffect(() => {
    getGamificationState(clientId).then(syncGamification).catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId])

  const startQuiz = (text: string) => {
    const value = text.trim()
    if (!value) {
      Taro.showToast({ title: '先输入想学的主题吧', icon: 'none' })
      return
    }
    reset()
    setInput(value)
    Taro.navigateTo({ url: '/pages/config/index' })
  }

  return (
    <Page module="in">
      <NavBar title="AI 闯关学习" />
      <View className="bd">
        {/* 问候卡 */}
        <View
          className="card row bt"
          style={{ background: 'linear-gradient(135deg, var(--m-in-soft), var(--paper) 60%)' }}
        >
          <View className="stack g4">
            <Text className="ct" style={{ fontSize: '20px' }}>{greeting()}</Text>
            <Text className="cs">
              {recent.length > 0 ? `继续攻克「${recent[0].title}」` : '先从一个主题开始闯关'}
            </Text>
          </View>
          <View className="row g10">
            {combo > 0 && <Chip tone="gd" icon="flame">连击 {combo}</Chip>}
            <Mascot variant="hi" size={64} />
          </View>
        </View>

        {/* 主题输入卡 */}
        <View className="card mt12">
          <Text className="ct">今天想学什么？</Text>
          <View className="cs mt8" style={{ marginBottom: '12px' }}>
            输入一个知识点，或直接贴上你的学习资料，AI 会把它变成一场闯关。
          </View>
          <View className={`field ${topic ? 'on' : ''}`}>
            <Input
              placeholder="例如：Redis 缓存机制"
              value={topic}
              onInput={(e) => setTopic(e.detail.value)}
              style={{ fontSize: '15px' }}
            />
          </View>
          <View className="row g6 mt12" style={{ flexWrap: 'wrap' }}>
            {HOT_TOPICS.slice(0, 4).map((t) => (
              <Chip key={t} tone="gh" onClick={() => setTopic(t)}>{t}</Chip>
            ))}
          </View>
          <View className="row g10 mt16">
            <View
              className="btn btn-s btn-sm grow"
              onClick={() => Taro.navigateTo({ url: '/pages/upload/index' })}
            >
              <Icon name="upload" size={18} color="#101A2E" />
              <Text>上传资料</Text>
            </View>
            <View className="btn btn-s btn-sm grow dis">
              <Icon name="link" size={18} color="#C3CBD9" />
              <Text>粘贴网页</Text>
            </View>
          </View>
          <View className="txt-xs txt-faint mt8">
            粘贴网页在下一阶段开放，现在支持主题、文字与文本型 PDF。
          </View>
          <View className="btn btn-p mt16" onClick={() => startQuiz(topic)}>
            <Icon name="play" size={18} color="#FFFFFF" />
            <Text>开始闯关</Text>
          </View>
        </View>

        {/* 最近学习 */}
        {recent.length > 0 && (
          <>
            <View className="row bt mt20" style={{ padding: '0 2px' }}>
              <Text className="ct" style={{ fontSize: '15px' }}>最近学习</Text>
              <Text
                className="btn-t txt-s"
                onClick={() => Taro.reLaunch({ url: '/pages/history/index' })}
              >
                全部记录
              </Text>
            </View>
            <View className="list mt8">
              {recent.map((item) => (
                <View
                  key={item.quiz_id}
                  className="lrow"
                  onClick={() =>
                    Taro.navigateTo({ url: `/pages/report/index?quizId=${item.quiz_id}&local=1` })
                  }
                >
                  <Ring
                    percent={item.score}
                    small
                    color={item.weak_points.length > 0 ? '#2B4EFF' : '#00D3A7'}
                  />
                  <View className="grow stack g4">
                    <Text className="txt-m" style={{ fontSize: '15px' }}>{item.title}</Text>
                    <Text className="txt-xs txt-faint">
                      {item.total} 题 ｜ {formatWhen(item.created_at)}
                    </Text>
                  </View>
                  {item.weak_points.length > 0 ? (
                    <Chip tone="co">{item.weak_points[0]}</Chip>
                  ) : (
                    <Chip tone="mt">掌握较好</Chip>
                  )}
                </View>
              ))}
            </View>
          </>
        )}
      </View>
      <TabBar active="home" />
    </Page>
  )
}
