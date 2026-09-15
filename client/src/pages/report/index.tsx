import { useEffect, useRef, useState } from 'react'
import Taro, { useRouter } from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import { Chip, Ring } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { useQuizStore } from '@/stores/quiz'
import { useUserStore } from '@/stores/user'
import { createReport, getGamificationState } from '@/services/api'
import { formatDuration, listHistory, saveReportToHistory } from '@/stores/history'
import type { Report } from '@/types'

const BADGE_LABELS: Record<string, string> = {
  first_quiz: '首次闯关',
  combo_3: '三连击',
  perfect: '满分达人',
  streak_7: '七日坚持',
}

export default function ReportPage() {
  const router = useRouter()
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const startedRef = useRef(false)
  const { quiz, reset } = useQuizStore()
  const { clientId, syncGamification } = useUserStore()

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    const run = async () => {
      try {
        // 本地历史查看模式
        if (router.params.local === '1' && router.params.quizId) {
          const item = listHistory().find((i) => i.quiz_id === router.params.quizId)
          if (item) {
            setReport(item.report)
            return
          }
        }
        const quizId = router.params.quizId || quiz?.quiz_id
        if (!quizId) throw new Error('缺少闯关会话')
        const r = await createReport(clientId, quizId)
        setReport(r)
        saveReportToHistory(r, quiz?.questions.length ?? r.wrong_questions.length + Math.round(r.accuracy * 10))
        getGamificationState(clientId).then(syncGamification).catch(() => undefined)
        if (r.badges.length > 0) {
          Taro.showToast({ title: `获得徽章：${r.badges.map((b) => BADGE_LABELS[b] || b).join('、')}`, icon: 'none' })
        }
      } catch (err) {
        const e = err as { code?: string; message?: string }
        Taro.showToast({ title: e.message || '报告生成失败', icon: 'none' })
        setTimeout(() => Taro.reLaunch({ url: '/pages/home/index' }), 1200)
      } finally {
        setLoading(false)
      }
    }
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading || !report) {
    return (
      <Page module="data">
        <NavBar title="通关报告" />
        <View className="bd">
          <View className="empty">
            <Mascot variant="read" size={110} />
            <Text className="ct" style={{ fontSize: '17px' }}>正在生成你的通关报告…</Text>
          </View>
        </View>
      </Page>
    )
  }

  const masteryGroups = [
    { level: 'good' as const, label: '掌握较好', color: 'var(--mint)', kps: [] as string[] },
    { level: 'fair' as const, label: '需要巩固', color: 'var(--amber)', kps: [] as string[] },
    { level: 'weak' as const, label: '薄弱', color: 'var(--coral)', kps: [] as string[] },
  ]
  for (const [kp, lv] of Object.entries(report.mastery_levels)) {
    masteryGroups.find((g) => g.level === lv)?.kps.push(kp)
  }
  const totalKps = Object.keys(report.mastery_levels).length || 1

  return (
    <Page module="data">
      <NavBar title="通关报告" />
      <View className="bd">
        {/* 分数环 */}
        <View className="card stack g16" style={{ alignItems: 'center', textAlign: 'center', padding: '20px 16px' }}>
          <Mascot variant="cap" size={88} />
          <Chip tone="mt" icon="trophy">本次闯关完成</Chip>
          <Ring percent={report.score} label="总分" />
          <View className="row g20">
            <View className="stack g4" style={{ alignItems: 'center' }}>
              <Text style={{ fontSize: '18px', fontWeight: 700 }}>{Math.round(report.accuracy * 100)}%</Text>
              <Text className="txt-xs txt-mut">正确率</Text>
            </View>
            <View style={{ width: '1px', height: '28px', background: 'var(--line)' }} />
            <View className="stack g4" style={{ alignItems: 'center' }}>
              <Text style={{ fontSize: '18px', fontWeight: 700 }}>{formatDuration(report.duration_ms)}</Text>
              <Text className="txt-xs txt-mut">用时</Text>
            </View>
            <View style={{ width: '1px', height: '28px', background: 'var(--line)' }} />
            <View className="stack g4" style={{ alignItems: 'center' }}>
              <Text style={{ fontSize: '18px', fontWeight: 700 }}>+{report.exp_gained}</Text>
              <Text className="txt-xs txt-mut">经验</Text>
            </View>
          </View>
          {report.badges.length > 0 && (
            <View className="row g6" style={{ flexWrap: 'wrap', justifyContent: 'center' }}>
              {report.badges.map((b) => (
                <Chip key={b} tone="gd" icon="award">{BADGE_LABELS[b] || b}</Chip>
              ))}
            </View>
          )}
        </View>

        {/* 知识掌握情况 */}
        <View className="card mt12">
          <Text className="ct" style={{ fontSize: '15px' }}>知识掌握情况</Text>
          <View className="mscale mt12">
            {masteryGroups.map((g) =>
              g.kps.length > 0 ? (
                <View key={g.level} className="ms-i" style={{ width: `${(g.kps.length / totalKps) * 100}%`, background: g.color }} />
              ) : null,
            )}
          </View>
          <View className="stack g10 mt16">
            {masteryGroups.map(
              (g) =>
                g.kps.length > 0 && (
                  <View key={g.level} className="row g8" style={{ alignItems: 'flex-start' }}>
                    <View className="dot" style={{ background: g.color, marginTop: '6px' }} />
                    <View className="grow">
                      <Text className="txt-m txt-s">{g.label}</Text>
                      <Text className="txt-xs txt-mut mt4" style={{ display: 'block' }}>{g.kps.join('、')}</Text>
                    </View>
                  </View>
                ),
            )}
          </View>
        </View>

        {/* 表现总结 */}
        {report.performance_summary && (
          <View className="card mt12">
            <Text className="ct" style={{ fontSize: '15px' }}>本次表现</Text>
            <Text className="txt-s mt8" style={{ lineHeight: 1.65, display: 'block' }}>{report.performance_summary}</Text>
          </View>
        )}

        {/* 错题归因 */}
        {report.wrong_questions.length > 0 && (
          <View className="card mt12">
            <View className="row bt">
              <Text className="ct" style={{ fontSize: '15px' }}>错题归因</Text>
              <Text className="txt-xs txt-faint">{report.wrong_questions.length} 题</Text>
            </View>
            {report.wrong_questions.map((w) => (
              <View key={w.index} className="row g10 mt12" style={{ alignItems: 'flex-start' }}>
                <Chip tone="co" style={{ marginTop: '1px' }}>第 {w.index + 1} 题</Chip>
                <View className="grow stack g6">
                  <Text className="txt-s txt-m">{w.stem.split('\n')[0]}</Text>
                  <Text className="txt-xs txt-mut">
                    错因：{w.error_type}。{w.analysis}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* 混淆概念辨析 */}
        {report.confusion_pairs.length > 0 && (
          <View className="card mt12">
            <Text className="ct" style={{ fontSize: '15px' }}>易混淆概念辨析</Text>
            {report.confusion_pairs.map((p, i) => (
              <Text key={i} className="txt-s mt8" style={{ lineHeight: 1.65, display: 'block' }}>{p}</Text>
            ))}
          </View>
        )}

        {/* 下一步建议 */}
        <View className="card mt12">
          <Text className="ct" style={{ fontSize: '15px' }}>下一步怎么练</Text>
          <View className="stack g10 mt12">
            {report.suggestions.map((s, i) => (
              <View key={i} className="row g10" style={{ alignItems: 'flex-start' }}>
                <Chip tone="br" style={{ marginTop: '1px', flex: '0 0 22px', justifyContent: 'center', padding: 0 }}>{i + 1}</Chip>
                <Text className="txt-s grow">{s}</Text>
              </View>
            ))}
          </View>
          <View className="row g6 mt12">
            <Chip tone="gh" icon="sparkle">
              {report.ai_generated ? '总结与建议由 AI 生成，仅供参考' : 'AI 暂不可用，以上为模板生成内容'}
            </Chip>
          </View>
        </View>
      </View>
      <View className="act">
        <View
          className="btn btn-s"
          style={{ flex: '0 0 108px' }}
          onClick={() => Taro.showToast({ title: '分享功能即将开放', icon: 'none' })}
        >
          <Icon name="share" size={18} color="#101A2E" />
          <Text>分享</Text>
        </View>
        <View
          className="btn btn-p"
          onClick={() => {
            reset()
            Taro.reLaunch({ url: '/pages/home/index' })
          }}
        >
          再来一场闯关
        </View>
      </View>
    </Page>
  )
}
