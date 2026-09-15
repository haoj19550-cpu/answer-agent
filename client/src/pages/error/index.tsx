import Taro, { useRouter } from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import { Chip } from '@/components/atoms'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'

const ERROR_TITLES: Record<string, string> = {
  QUIZ_GENERATION_FAILED: '题目没有生成成功',
  QUOTA_EXCEEDED: '本月额度用完了',
  LLM_TIMEOUT: 'AI 开小差了',
  MATERIAL_NOT_FOUND: '材料已过期',
  NETWORK_ERROR: '网络连接异常',
}

const ERROR_DESCS: Record<string, string> = {
  QUIZ_GENERATION_FAILED: '我们已经自动重试多次、并尝试减少题量，仍然没有通过质量校验。通常是材料太长或主题太宽。',
  QUOTA_EXCEEDED: '本月 30 次生成额度已用完，额度每月 1 日自动恢复。复习与错题本不消耗额度，随时可用。',
  LLM_TIMEOUT: 'AI 服务暂时繁忙，稍等片刻再试一次通常就能恢复。',
  MATERIAL_NOT_FOUND: '学习材料已超过 2 小时被清除，请重新提交后再生成闯关。',
  NETWORK_ERROR: '请检查网络连接后重试。',
}

export default function ErrorPage() {
  const router = useRouter()
  const code = decodeURIComponent(router.params.code || 'QUIZ_GENERATION_FAILED')
  const phase = (router.params.phase as string) || 'generate'
  const title = ERROR_TITLES[code] || '出了点问题'
  const desc = ERROR_DESCS[code] || '请稍后重试。'

  const retry = () => {
    if (code === 'QUOTA_EXCEEDED') {
      Taro.reLaunch({ url: '/pages/home/index' })
      return
    }
    Taro.redirectTo({ url: `/pages/generating/index?phase=${phase}` })
  }

  return (
    <Page module="err">
      <NavBar title="生成闯关" back onBack={() => Taro.reLaunch({ url: '/pages/home/index' })} />
      <View className="bd">
        <View className="card stack g12" style={{ alignItems: 'center', textAlign: 'center', padding: '28px 20px' }}>
          <Mascot variant="wrench" size={88} />
          <Text className="ct" style={{ fontSize: '18px' }}>{title}</Text>
          <Text className="cs" style={{ maxWidth: '250px' }}>{desc}</Text>
        </View>

        <View className="card mt12">
          <Text className="ct" style={{ fontSize: '15px' }}>可以这样解决</Text>
          <View className="stack g10 mt12">
            {[
              '把主题收窄一点，例如从「Redis」改成「Redis 缓存三大问题」。',
              '删掉与主题无关的章节，材料越聚焦，题目越准。',
              '如果是服务繁忙，直接重试一次通常就能通过。',
            ].map((s, i) => (
              <View key={i} className="row g10" style={{ alignItems: 'flex-start' }}>
                <Chip tone="br" style={{ marginTop: '1px', flex: '0 0 22px', justifyContent: 'center', padding: 0 }}>{i + 1}</Chip>
                <Text className="txt-s grow">{s}</Text>
              </View>
            ))}
          </View>
        </View>

        <View className="card mt12">
          <View className="row g8">
            <Icon name="info" size={16} color="#8A97AC" />
            <Text className="txt-xs txt-mut" style={{ lineHeight: 1.6 }}>
              错误码 {code}。{code === 'QUIZ_GENERATION_FAILED' ? '本次不消耗生成额度。' : ''}
            </Text>
          </View>
        </View>
      </View>
      <View className="act">
        <View className="btn btn-s" style={{ flex: '0 0 108px' }}
          onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}>
          <Icon name="left" size={18} color="#101A2E" />
          <Text>返回</Text>
        </View>
        <View className="btn btn-p" onClick={retry}>
          <Icon name="refresh" size={18} color="#FFFFFF" />
          <Text>{code === 'QUOTA_EXCEEDED' ? '回到首页' : '重试一次'}</Text>
        </View>
      </View>
    </Page>
  )
}
