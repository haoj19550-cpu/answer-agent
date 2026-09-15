import Taro from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import { Chip } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { useQuizStore } from '@/stores/quiz'

function importanceChip(importance: number) {
  if (importance >= 5) return <Chip tone="mt">重要 {importance}</Chip>
  if (importance >= 3) return <Chip tone="gh">重要 {importance}</Chip>
  return <Chip tone="gh">重要 {importance}</Chip>
}

export default function KnowledgePreviewPage() {
  const { extraction, selectedKps, toggleKp, count } = useQuizStore()

  if (!extraction) {
    return (
      <Page module="ai">
        <NavBar title="知识点预览" back />
        <View className="bd">
          <View className="empty">
            <Mascot variant="zzz" size={110} />
            <Text className="ct" style={{ fontSize: '17px' }}>还没有提取到知识点</Text>
            <View className="btn btn-p btn-sm" style={{ width: 'auto', padding: '0 24px' }}
              onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}>
              回到首页
            </View>
          </View>
        </View>
      </Page>
    )
  }

  const checkedCount = selectedKps.length

  return (
    <Page module="ai">
      <NavBar title="知识点预览" back />
      <View className="bd">
        <View className="card">
          <View className="row bt">
            <View className="row g10">
              <Mascot variant="think" size={48} />
              <Text className="ct" style={{ fontSize: '16px' }}>{extraction.topic}</Text>
            </View>
            <Chip tone="br">{extraction.knowledge_points.length} 个知识点</Chip>
          </View>
          <Text className="cs mt8">
            AI 从你的材料里提取了这些知识点。取消勾选不想考的内容，题目会跟着调整。
          </Text>
        </View>

        <View className="card tree mt12" style={{ padding: '14px 16px' }}>
          <View className="tn" style={{ fontWeight: 700 }}>
            <Icon name="layers" size={16} color="#2B4EFF" />
            <Text>{extraction.topic}</Text>
          </View>
          {extraction.knowledge_points.map((kp, idx) => {
            const checked = selectedKps.includes(kp.name)
            return (
              <View key={kp.name} className={`tree-li ${idx === extraction.knowledge_points.length - 1 ? 'last' : ''}`}>
                <View className="tn" onClick={() => toggleKp(kp.name)}>
                  <View className={`ck ${checked ? 'on' : ''}`}>
                    {checked && <Icon name="check" size={14} color="#FFFFFF" />}
                  </View>
                  <Text className={`grow txt-s ${checked ? 'txt-m' : 'txt-faint'}`}>
                    {kp.name}{checked ? '' : '（本次不考）'}
                  </Text>
                  {kp.confusion_with.length > 0 ? <Chip tone="co">易混淆</Chip> : importanceChip(kp.importance)}
                </View>
                {checked && kp.confusion_with.length > 0 && (
                  <View className="tree-li last" style={{ marginTop: '2px' }}>
                    <View className="tn">
                      <Text className="grow txt-s txt-mut">易混淆：{kp.confusion_with.join('、')}</Text>
                    </View>
                  </View>
                )}
              </View>
            )
          })}
        </View>

        <View className="card mt12">
          <View className="row g8">
            <Icon name="alert" size={16} color="#FFB300" />
            <Text className="txt-xs txt-mut" style={{ lineHeight: 1.6 }}>
              标记为「易混淆」的概念对会优先出对比题，这是最容易丢分的地方。
            </Text>
          </View>
        </View>
      </View>
      <View className="act">
        <View
          className={`btn btn-p ${checkedCount === 0 ? 'dis' : ''}`}
          onClick={() => {
            if (checkedCount === 0) {
              Taro.showToast({ title: '至少保留 1 个知识点', icon: 'none' })
              return
            }
            Taro.navigateTo({ url: '/pages/generating/index?phase=generate' })
          }}
        >
          开始闯关（{checkedCount} 个考点 · {count} 题）
        </View>
      </View>
    </Page>
  )
}
