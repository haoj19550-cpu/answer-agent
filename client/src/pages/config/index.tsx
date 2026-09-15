import Taro from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import { Chip, Seg } from '@/components/atoms'
import Mascot from '@/components/Mascot'
import {
  DIFFICULTY_LABELS,
  GOAL_LABELS,
  mixText,
  useQuizStore,
} from '@/stores/quiz'
import type { Difficulty, StudyGoal } from '@/types'

const GOAL_HINTS: Record<StudyGoal, string> = {
  understand: '侧重概念辨析与原理理解。',
  memorize: '记忆目标会提高重复考点与变式题的比例。',
  exam: '侧重高频考点与易错陷阱。',
  interview: '侧重原理深挖与场景运用。',
  quick: '快速过一遍核心概念，整体偏基础。',
}

export default function ConfigPage() {
  const { inputText, goal, difficulty, count, setGoal, setDifficulty, setCount } = useQuizStore()

  const mix = count === 10 ? [60, 20, 20] : [60, 20, 20]

  return (
    <Page module="in">
      <NavBar title="学习配置" back />
      <View className="bd">
        {/* 学习主题 */}
        <View className="card">
          <View className="row bt">
            <View className="row g10">
              <Mascot variant="think" size={48} />
              <Text className="ct" style={{ fontSize: '15px' }}>学习主题</Text>
            </View>
            <Text className="btn-t txt-s" onClick={() => Taro.navigateBack()}>换一个</Text>
          </View>
          <View className="field on mt12">{inputText}</View>
          <View className="txt-xs txt-faint mt8">AI 会先提取 5 到 10 个知识点，再按下面的配置出题。</View>
        </View>

        {/* 学习目标 */}
        <View className="card mt12">
          <Text className="ct" style={{ fontSize: '15px' }}>学习目标</Text>
          <View className="mt12">
            <Seg<StudyGoal>
              square
              options={(Object.keys(GOAL_LABELS) as StudyGoal[]).map((g) => ({
                value: g,
                label: GOAL_LABELS[g],
              }))}
              value={goal}
              onChange={setGoal}
            />
          </View>
          <View className="txt-xs txt-mut mt8">{GOAL_HINTS[goal]}</View>
        </View>

        {/* 难度 */}
        <View className="card mt12">
          <Text className="ct" style={{ fontSize: '15px' }}>难度</Text>
          <View className="mt12">
            <Seg<Difficulty>
              options={(Object.keys(DIFFICULTY_LABELS) as Difficulty[]).map((d) => ({
                value: d,
                label: DIFFICULTY_LABELS[d],
              }))}
              value={difficulty}
              onChange={setDifficulty}
            />
          </View>
          {difficulty === 'adaptive' && (
            <View className="row g6 mt12">
              <Chip tone="br" icon="sparkle">AI 自适应</Chip>
              <Text className="txt-xs txt-mut">从基础题起步，按你的表现实时升降</Text>
            </View>
          )}
        </View>

        {/* 题目数量 */}
        <View className="card mt12">
          <View className="row bt">
            <Text className="ct" style={{ fontSize: '15px' }}>题目数量</Text>
          </View>
          <View className="mt12">
            <Seg<5 | 10>
              options={[
                { value: 5, label: '5 题' },
                { value: 10, label: '10 题' },
              ]}
              value={count}
              onChange={setCount}
            />
          </View>
          <View className="row bt mt16">
            <Text className="txt-s txt-mut">题型配比</Text>
            <Text className="txt-xs txt-faint">{mixText(count)}</Text>
          </View>
          <View className="mscale mt8">
            <View className="ms-i" style={{ width: `${mix[0]}%`, background: 'var(--brand)' }} />
            <View className="ms-i" style={{ width: `${mix[1]}%`, background: 'var(--mint)' }} />
            <View className="ms-i" style={{ width: `${mix[2]}%`, background: 'var(--tang)' }} />
          </View>
        </View>
      </View>
      <View className="act">
        <View
          className="btn btn-p"
          onClick={() => Taro.navigateTo({ url: '/pages/generating/index?phase=extract' })}
        >
          生成闯关
        </View>
      </View>
    </Page>
  )
}
