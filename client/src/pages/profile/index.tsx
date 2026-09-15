import { useEffect, useState } from 'react'
import Taro from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar, TabBar } from '@/components/chrome'
import { Bar, Chip } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { shortClientId, useUserStore } from '@/stores/user'
import { listHistory, listWrongBook } from '@/stores/history'
import { getGamificationState } from '@/services/api'
import { APP_VERSION } from '@/config'

/** 连续学习天数：按本地记录的不同自然日回推 */
function calcStreakDays(): number {
  const days = new Set(
    listHistory().map((i) => {
      const d = new Date(i.created_at)
      return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
    }),
  )
  if (days.size === 0) return 0
  let streak = 0
  const cursor = new Date()
  const key = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
  // 今天没学也可以从昨天开始算
  if (!days.has(key(cursor))) cursor.setDate(cursor.getDate() - 1)
  while (days.has(key(cursor))) {
    streak += 1
    cursor.setDate(cursor.getDate() - 1)
  }
  return streak
}

export default function ProfilePage() {
  const { clientId, exp, maxCombo, completedQuizzes, badges, monthlyQuota, quotaUsed, syncGamification } =
    useUserStore()
  const [wrongCount, setWrongCount] = useState(0)
  const [streakDays, setStreakDays] = useState(0)

  useEffect(() => {
    setWrongCount(listWrongBook().length)
    setStreakDays(calcStreakDays())
    getGamificationState(clientId).then(syncGamification).catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId])

  const quotaPercent = monthlyQuota > 0 ? Math.round((quotaUsed / monthlyQuota) * 100) : 0

  const stats = [
    { value: streakDays, label: '连续天数' },
    { value: completedQuizzes, label: '完成闯关' },
    { value: wrongCount, label: '错题积累' },
    { value: badges.length, label: '徽章' },
  ]

  return (
    <Page module="data">
      <NavBar title="我的" />
      <View className="bd">
        {/* 身份卡 */}
        <View className="card row g12">
          <Mascot variant="hi" size={56} />
          <View className="grow stack g4">
            <Text className="ct" style={{ fontSize: '16px' }}>学习者 {shortClientId(clientId)}</Text>
            <Text className="txt-xs txt-faint">本地设备 ID，无需注册登录 ｜ 经验 {exp} ｜ 最高连击 {maxCombo}</Text>
          </View>
          <View className="icon-btn" style={{ width: '36px', height: '36px' }}
            onClick={() => Taro.showToast({ title: '设置即将开放', icon: 'none' })}>
            <Icon name="settings" size={18} color="#2C3A52" />
          </View>
        </View>

        {/* 四项统计 */}
        <View className="card mt12 row bt" style={{ padding: '14px 16px' }}>
          {stats.map((s, i) => (
            <View key={s.label} className="row" style={{ display: 'contents' }}>
              {i > 0 && <View style={{ width: '1px', height: '30px', background: 'var(--line)' }} />}
              <View className="stack g4" style={{ alignItems: 'center', flex: 1 }}>
                <Text style={{ fontSize: '20px', fontWeight: 700 }}>{s.value}</Text>
                <Text className="txt-xs txt-mut">{s.label}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* 生成额度 */}
        <View className="card mt12">
          <View className="row bt">
            <Text className="txt-m txt-s">本月生成额度</Text>
            <Text className="txt-xs txt-faint">{monthlyQuota - quotaUsed} / {monthlyQuota} 次</Text>
          </View>
          <View className="mt8">
            <Bar percent={100 - quotaPercent} />
          </View>
          <Text className="txt-xs txt-mut mt8">每次生成闯关消耗 1 次额度，复习与错题追问不消耗。</Text>
        </View>

        {/* 入口列表 */}
        <View className="list mt12">
          <View className="lrow" style={{ padding: '12px 16px' }}
            onClick={() => Taro.reLaunch({ url: '/pages/history/index' })}>
            <Icon name="bookmark" size={18} color="#5A6A85" />
            <Text className="grow txt-s txt-m">我的错题本</Text>
            <Chip tone="co">{wrongCount}</Chip>
            <Icon name="right" size={16} color="#C3CBD9" />
          </View>
          <View className="lrow" style={{ padding: '12px 16px' }}
            onClick={() => Taro.showToast({ title: '知识掌握图在下一阶段开放', icon: 'none' })}>
            <Icon name="map" size={18} color="#5A6A85" />
            <Text className="grow txt-s txt-m">知识掌握图</Text>
            <Icon name="right" size={16} color="#C3CBD9" />
          </View>
          <View
            className="lrow"
            style={{ padding: '12px 16px' }}
            onClick={() =>
              Taro.showModal({
                title: '隐私与材料说明',
                content: '你的学习材料会发送给大模型用于出题，不会用于训练，会话结束 2 小时后自动清除。',
                showCancel: false,
                confirmText: '我知道了',
              })
            }
          >
            <Icon name="shield" size={18} color="#5A6A85" />
            <Text className="grow txt-s txt-m">隐私与材料说明</Text>
            <Icon name="right" size={16} color="#C3CBD9" />
          </View>
          <View className="lrow" style={{ padding: '12px 16px' }}>
            <Icon name="info" size={18} color="#5A6A85" />
            <Text className="grow txt-s txt-m">关于与版本</Text>
            <Text className="txt-xs txt-faint">{APP_VERSION}</Text>
          </View>
        </View>

        <Text className="txt-xs txt-faint mt16" style={{ lineHeight: 1.7, display: 'block' }}>
          你的学习材料会发送给大模型用于出题，不会用于训练，会话结束 2 小时后自动清除。
        </Text>
      </View>
      <TabBar active="profile" />
    </Page>
  )
}
