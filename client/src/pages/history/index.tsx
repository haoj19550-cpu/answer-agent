import { useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar, TabBar } from '@/components/chrome'
import { Chip, Ring } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { formatDuration, formatWhen, listHistory, type HistoryItem } from '@/stores/history'
import { HOT_TOPICS } from '@/utils/mock'
import { useQuizStore } from '@/stores/quiz'

type FilterKey = 'all' | 'weak' | 'review'

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [filter, setFilter] = useState<FilterKey>('all')
  const { reset, setInput } = useQuizStore()

  useDidShow(() => {
    setItems(listHistory())
  })

  const filtered = items.filter((i) => {
    if (filter === 'weak') return i.weak_points.length > 0
    if (filter === 'review') return i.weak_points.length > 0 || i.fair_points.length > 0
    return true
  })

  const weakCount = items.filter((i) => i.weak_points.length > 0).length
  const reviewCount = items.filter((i) => i.weak_points.length > 0 || i.fair_points.length > 0).length

  const ringColor = (item: HistoryItem) =>
    item.weak_points.length > 0 ? '#FF5C5C' : item.fair_points.length > 0 ? '#FFB300' : '#00D3A7'

  // ---------- 空状态（屏15） ----------
  if (items.length === 0) {
    return (
      <Page module="err">
        <NavBar title="学习记录" />
        <View className="bd">
          <View className="empty">
            <Mascot variant="zzz" size={110} />
            <Text className="ct" style={{ fontSize: '17px' }}>还没有学习记录</Text>
            <Text className="cs" style={{ maxWidth: '230px' }}>
              完成第一场闯关，这里就会留下你的正确率曲线和薄弱点地图。
            </Text>
            <View
              className="btn btn-p btn-sm"
              style={{ width: 'auto', padding: '0 24px' }}
              onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}
            >
              <Icon name="play" size={18} color="#FFFFFF" />
              <Text>开始第一场闯关</Text>
            </View>
          </View>
          <View className="card mt12">
            <Text className="ct" style={{ fontSize: '15px' }}>别人都在学什么</Text>
            <View className="row g6 mt12" style={{ flexWrap: 'wrap' }}>
              {HOT_TOPICS.map((t) => (
                <Chip
                  key={t}
                  tone="gh"
                  onClick={() => {
                    reset()
                    setInput(t)
                    Taro.navigateTo({ url: '/pages/config/index' })
                  }}
                >
                  {t}
                </Chip>
              ))}
            </View>
            <Text className="txt-xs txt-mut mt12">点一个标签，直接用它开局。</Text>
          </View>
        </View>
        <TabBar active="history" />
      </Page>
    )
  }

  // ---------- 记录列表（屏12） ----------
  return (
    <Page module="data">
      <NavBar title="学习记录" />
      <View className="bd pad0">
        <View style={{ padding: '16px 16px 12px' }}>
          <View className="row g6">
            <Chip tone={filter === 'all' ? 'pick' : 'gh'} onClick={() => setFilter('all')}>全部 {items.length}</Chip>
            <Chip tone={filter === 'weak' ? 'pick' : 'gh'} onClick={() => setFilter('weak')}>薄弱 {weakCount}</Chip>
            <Chip tone={filter === 'review' ? 'pick' : 'gh'} onClick={() => setFilter('review')}>待复习 {reviewCount}</Chip>
            <Mascot variant="hi" size={48} style={{ marginLeft: 'auto' }} />
          </View>
        </View>
        <View className="list flush">
          {filtered.map((item) => {
            const weak = item.weak_points.length > 0
            return (
              <View
                key={item.quiz_id}
                className={`lrow ${weak ? 'weak' : ''}`}
                onClick={() => Taro.navigateTo({ url: `/pages/report/index?quizId=${item.quiz_id}&local=1` })}
              >
                <Ring percent={item.score} small color={ringColor(item)} />
                <View className="grow stack g4">
                  <Text className="txt-m" style={{ fontSize: '15px' }}>{item.title}</Text>
                  {weak ? (
                    <Text className="txt-xs" style={{ color: '#B32B2B' }}>
                      薄弱：{item.weak_points.join('、')} ｜ {formatWhen(item.created_at)}
                    </Text>
                  ) : item.fair_points.length > 0 ? (
                    <Text className="txt-xs txt-faint">
                      需要巩固：{item.fair_points.join('、')} ｜ {formatWhen(item.created_at)}
                    </Text>
                  ) : (
                    <Text className="txt-xs txt-faint">
                      掌握较好 ｜ {item.total} 题 ｜ {formatDuration(item.duration_ms)}
                    </Text>
                  )}
                </View>
                <Icon name="right" size={16} color={weak ? '#FF5C5C' : '#C3CBD9'} />
              </View>
            )
          })}
        </View>
        {filtered.length === 0 && (
          <View style={{ padding: '32px', textAlign: 'center' }}>
            <Text className="txt-s txt-mut">该筛选下暂无记录</Text>
          </View>
        )}
      </View>
      <TabBar active="history" />
    </Page>
  )
}
